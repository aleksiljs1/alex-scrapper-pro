"""
Ingest Task — Reads scraped JSON from shared volume, converts it to the
final EXAMPLE_PROFILE format, and stores it in MongoDB.

The conversion extracts structured data from `about_tabs` to produce:
- work: [{organization, designation, details}]
- education: [{institution, type, field_of_study, details}]
- current_city: {upazila, district, division, country}
- hometown: {upazila, district, division, country}
- birthday_info: {birthday, birthdate, birth_year}
- relationship: [{status, partner_info, details}]
- family_members: [{name, relationship, profile_url}]
- gender, language_skills, names
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from app.tasks.celery_app import celery_app
from app.config import settings
from app.services.queue_service import publish_status


# ─── Conversion Helpers ──────────────────────────────────────────────────────


def _parse_location_string(location_str: str | None) -> dict | None:
    """Parse 'Dhaka, Bangladesh' or 'Lives in Dhaka, Bangladesh' into structured dict."""
    if not location_str:
        return None

    cleaned = location_str
    for prefix in ["Lives in ", "From "]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]

    parts = [p.strip() for p in cleaned.split(",")]
    result = {"upazila": None, "district": None, "division": None, "country": None}

    if len(parts) == 1:
        result["district"] = parts[0]
    elif len(parts) == 2:
        result["district"] = parts[0]
        result["country"] = parts[1]
    elif len(parts) == 3:
        # Could be: upazila, district, country  OR  district, division, country
        # Heuristic: if 3rd part looks like a country name, treat 1st as upazila
        result["upazila"] = parts[0]
        result["district"] = parts[1]
        result["country"] = parts[2]
    elif len(parts) >= 4:
        result["upazila"] = parts[0]
        result["district"] = parts[1]
        result["division"] = parts[2]
        result["country"] = parts[3]

    return result


def _extract_work_item(text: str, details: list[str]) -> dict:
    """
    Parse work text like 'Business Analyst at Company' or 'Former X at Y' or 'Worked at Z'.
    Returns {organization, designation, details}.
    """
    designation = None
    organization = text

    match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if match:
        designation = match.group(1).strip()
        organization = match.group(2).strip()

    return {
        "organization": organization,
        "designation": designation,
        "details": details or [],
    }


def _extract_education_item(text: str, section_type: str, details: list[str]) -> dict:
    """
    Parse education text like 'Studied CS at University' or 'Went to School'.
    Returns {institution, type, field_of_study, details}.
    """
    institution = text
    field_of_study = None

    # Try "Studied X at Y"
    match = re.match(r"^Studied\s+(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if match:
        field_of_study = match.group(1).strip()
        institution = match.group(2).strip()
    else:
        # Try "Went to X"
        match = re.match(r"^Went to\s+(.+)$", text, re.IGNORECASE)
        if match:
            institution = match.group(1).strip()
        else:
            # Try "X at Y"
            match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
            if match:
                field_of_study = match.group(1).strip()
                institution = match.group(2).strip()

    # Also check details for "Major: X"
    for detail in details:
        major_match = re.match(r"^Major:\s*(.+)$", detail, re.IGNORECASE)
        if major_match and not field_of_study:
            field_of_study = major_match.group(1).strip()

    # Map section_type to education type
    edu_type = None
    if "college" in (section_type or "").lower():
        edu_type = "College"
    elif "high_school" in (section_type or "").lower():
        edu_type = "High school"
    elif "grad" in (section_type or "").lower():
        edu_type = "Graduate school"

    return {
        "institution": institution,
        "type": edu_type,
        "field_of_study": field_of_study,
        "details": details or [],
    }


def _extract_relationship(fields: list[dict]) -> list[dict]:
    """Extract relationship info from about_tabs relationship section fields."""
    relationships = []
    for field in fields:
        text = field.get("text", "")
        if not text:
            continue

        partner_info = None
        entities = field.get("entities", [])
        if entities:
            entity = entities[0]
            partner_info = {
                "name": entity.get("name"),
                "profile_url": entity.get("profile_url"),
            }

        # Try to extract partner name from text like "Married to Name"
        if not partner_info:
            match = re.match(
                r"^(?:Married to|In a relationship with|Engaged to)\s+(.+)$",
                text,
                re.IGNORECASE,
            )
            if match:
                partner_info = {"name": match.group(1).strip(), "profile_url": None}

        relationships.append(
            {
                "status": text,
                "partner_info": partner_info,
                "details": field.get("details", []),
            }
        )
    return relationships


def _extract_family(fields: list[dict]) -> list[dict]:
    """Extract family members from about_tabs family section fields."""
    members = []
    for field in fields:
        text = field.get("text", "")
        if not text:
            continue

        # Text is usually just the name; relationship is in details
        name = text
        relationship = None
        profile_url = None

        details = field.get("details", [])
        if details:
            relationship = details[0]  # First detail is usually the relationship

        entities = field.get("entities", [])
        if entities:
            entity = entities[0]
            if entity.get("name"):
                name = entity["name"]
            profile_url = entity.get("profile_url")

        members.append(
            {
                "name": name,
                "relationship": relationship,
                "profile_url": profile_url,
            }
        )
    return members


def _extract_birthday(fields: list[dict]) -> dict | None:
    """Extract birthday info from about_tabs birthday section fields."""
    if not fields:
        return {"birthday": None, "birthdate": None, "birth_year": None}

    for field in fields:
        text = field.get("text", "")
        if text:
            return {
                "birthday": text,
                "birthdate": None,
                "birth_year": None,
            }
    return {"birthday": None, "birthdate": None, "birth_year": None}


def convert_scraped_to_final(scraped_data: dict) -> dict:
    """
    Convert scraped profile format (from scraper output) to EXAMPLE_PROFILE.json format.

    Input: { "scraped_at": "...", "profile": { ... about_tabs ... } }
    Output: flat EXAMPLE_PROFILE.json format
    """
    profile = scraped_data.get("profile", {})
    scraped_at = scraped_data.get("scraped_at")
    about_tabs = profile.get("about_tabs", [])

    # ─── Extract from about_tabs ──────────────────────

    work_items = []
    education_items = []
    current_city = None
    hometown = None
    birthday_info = {"birthday": None, "birthdate": None, "birth_year": None}
    relationships = []
    family_members = []
    gender = None
    language_skills = []
    names_info = {"nicknames": [], "name_pronunciation": None}
    category = profile.get("category")

    for tab in about_tabs:
        tab_name = (tab.get("name") or "").lower()
        sections = tab.get("sections", [])

        for section in sections:
            section_type = section.get("section_type", "") or ""
            fields = section.get("fields", [])

            # ── Work ──
            if section_type == "directory_work" or (
                tab_name == "work" and section_type.startswith("directory_work")
            ):
                for f in fields:
                    text = f.get("text", "")
                    if text:
                        work_items.append(
                            _extract_work_item(text, f.get("details", []))
                        )

            # ── Education ──
            elif section_type in (
                "directory_college",
                "directory_high_school",
                "directory_grad_school",
            ) or (tab_name == "education"):
                for f in fields:
                    text = f.get("text", "")
                    if text and f.get("field_type") == "education":
                        education_items.append(
                            _extract_education_item(
                                text, section_type, f.get("details", [])
                            )
                        )

            # ── Location (current city) ──
            elif section_type == "directory_location":
                for f in fields:
                    if f.get("field_type") == "current_city" and f.get("text"):
                        current_city = _parse_location_string(f["text"])

            # ── Hometown ──
            elif section_type == "directory_hometown":
                for f in fields:
                    if f.get("field_type") == "hometown" and f.get("text"):
                        hometown = _parse_location_string(f["text"])

            # ── Birthday ──
            elif section_type == "directory_birthday":
                birthday_info = _extract_birthday(fields)

            # ── Relationship ──
            elif section_type == "relationship":
                relationships = _extract_relationship(fields)

            # ── Family ──
            elif section_type == "family":
                family_members = _extract_family(fields)

            # ── Gender ──
            elif section_type == "directory_gender":
                for f in fields:
                    if f.get("text"):
                        gender = f["text"]

            # ── Languages ──
            elif section_type == "directory_languages":
                for f in fields:
                    if f.get("text"):
                        language_skills.append(f["text"])

            # ── Category ──
            elif section_type == "directory_category":
                for f in fields:
                    if f.get("field_type") == "category" and f.get("text"):
                        category = f["text"]

            # ── Names / Nicknames ──
            elif section_type == "nicknames":
                for f in fields:
                    if f.get("text"):
                        names_info["nicknames"].append(f["text"])

            elif section_type == "name_pronunciation":
                for f in fields:
                    if f.get("text"):
                        names_info["name_pronunciation"] = f["text"]

    # ─── Fallback: if about_tabs didn't have location, try legacy fields ──

    if current_city is None and profile.get("current_city"):
        city_val = profile["current_city"]
        if isinstance(city_val, str):
            current_city = _parse_location_string(city_val)
        elif isinstance(city_val, dict):
            current_city = city_val

    if hometown is None and profile.get("hometown"):
        ht_val = profile["hometown"]
        if isinstance(ht_val, str):
            hometown = _parse_location_string(ht_val)
        elif isinstance(ht_val, dict):
            hometown = ht_val

    # Fallback work from legacy flat strings
    if not work_items and profile.get("work"):
        for w in profile["work"]:
            if isinstance(w, str):
                work_items.append(_extract_work_item(w, []))
            elif isinstance(w, dict):
                work_items.append(w)

    # Fallback education from legacy flat strings
    if not education_items and profile.get("education"):
        for e in profile["education"]:
            if isinstance(e, str):
                education_items.append(
                    _extract_education_item(e, "", [])
                )
            elif isinstance(e, dict):
                education_items.append(e)

    # ─── Relationship fallback ──
    if not relationships and profile.get("relationship_status"):
        relationships = [
            {
                "status": profile["relationship_status"],
                "partner_info": None,
                "details": [],
            }
        ]

    # ─── Build final format ──────────────────────────

    final = {
        "profile_id": profile.get("profile_id"),
        "name": profile.get("name"),
        "profile_url": profile.get("profile_url"),
        "profile_picture_url": profile.get("profile_picture_url"),
        "profile_picture_path": profile.get("profile_picture_path"),
        "cover_photo_url": profile.get("cover_photo_url"),
        "cover_photo_path": profile.get("cover_photo_path"),
        "bio": profile.get("bio"),
        "category": category,
        "followers_count": profile.get("followers_count"),
        "friends_count": profile.get("friends_count"),
        "work": work_items,
        "education": education_items,
        "current_city": current_city,
        "hometown": hometown,
        "birthday_info": birthday_info,
        "relationship": relationships,
        "family_members": family_members,
        "gender": gender,
        "language_skills": language_skills,
        "names": names_info if (names_info["nicknames"] or names_info["name_pronunciation"]) else None,
        "intro_items": profile.get("intro_items", []),
        "scraped_at": scraped_at,
    }

    return final


# ─── Celery Task ─────────────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def ingest_profile_json(self, profile_id: str, url: str, json_file_path: str):
    """
    1. Read JSON from shared volume
    2. Convert from scraped format to final EXAMPLE_PROFILE format
    3. Upsert into MongoDB
    4. Update status to 'finished'
    """
    from app.db.mongodb import get_sync_collection

    collection = get_sync_collection("profiles")

    try:
        # Read JSON
        with open(json_file_path, "r", encoding="utf-8") as f:
            scraped_data = json.load(f)

        # Convert to final format
        final_profile = convert_scraped_to_final(scraped_data)

        # Preserve raw scraped data for debugging / raw view
        raw_profile = scraped_data.get("profile", {})
        scraped_data_ref = {
            "about_tabs": raw_profile.get("about_tabs", []),
        }

        # Update document with converted profile data
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    "status": "finished",
                    "profile": final_profile,
                    "scraped_data": scraped_data_ref,
                    "scraped_at": scraped_data.get("scraped_at"),
                    "updated_at": datetime.utcnow(),
                    "json_file_path": json_file_path,
                },
                "$unset": {"error_message": ""},
            },
        )

        publish_status(
            profile_id,
            url,
            "finished",
            name=final_profile.get("name"),
        )

    except Exception as exc:
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    "status": "failed",
                    "error_message": f"Ingestion error: {str(exc)}",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        publish_status(profile_id, url, "failed")
        raise self.retry(exc=exc)
