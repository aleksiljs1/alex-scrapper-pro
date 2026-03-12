"""Tests for the profile JSON format converter."""

import json
import os
import pytest

# Add the backend to path for direct import
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tasks.ingest_task import convert_scraped_to_final


# Sample scraped data (mimics profile_20260302_145445_mho7n8.json structure)
SAMPLE_SCRAPED = {
    "scraped_at": "2026-03-02T14:54:45.815500",
    "profile": {
        "profile_id": "1594662816",
        "name": "Test User",
        "profile_url": "https://www.facebook.com/testuser",
        "profile_picture_url": "https://example.com/pic.jpg",
        "profile_picture_path": "/tmp/facebook_data/profile_attachments/profile_picture_1594662816.jpg",
        "cover_photo_url": "https://example.com/cover.jpg",
        "cover_photo_path": "/tmp/facebook_data/profile_attachments/cover_photo_1594662816.jpg",
        "bio": "Test bio",
        "category": None,
        "followers_count": None,
        "friends_count": 492,
        "work": [
            "BBA Ambassador at Canadian University",
            "Former Sales Manager at Vision Web PPC",
        ],
        "education": [
            "Studied BBA(Hons) at Canadian University",
            "Went to Holy Crescent School",
        ],
        "current_city": "Lives in Dhaka, Bangladesh",
        "hometown": "From Dhaka, Bangladesh",
        "relationship_status": None,
        "intro_items": ["Lives in Dhaka, Bangladesh", "From Dhaka, Bangladesh"],
        "about_details": {},
        "about_tabs": [
            {
                "name": "Intro",
                "url": "https://www.facebook.com/testuser/directory_intro",
                "sections": [
                    {
                        "section_type": "directory_bio",
                        "title": "Bio",
                        "fields": [
                            {
                                "text": "Test bio",
                                "field_type": "bio",
                                "entities": [],
                                "details": [],
                                "icon_url": None,
                            }
                        ],
                    }
                ],
            },
            {
                "name": "Personal details",
                "url": "https://www.facebook.com/testuser/directory_personal_details",
                "sections": [
                    {
                        "section_type": "directory_location",
                        "title": "Location",
                        "fields": [
                            {
                                "text": "Dhaka, Bangladesh",
                                "field_type": "current_city",
                                "entities": [],
                                "details": ["Current city"],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "directory_hometown",
                        "title": "Hometown",
                        "fields": [
                            {
                                "text": "Dhaka, Bangladesh",
                                "field_type": "hometown",
                                "entities": [],
                                "details": ["Hometown"],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "directory_birthday",
                        "title": "Birthday",
                        "fields": [
                            {
                                "text": "January 3, 1995",
                                "field_type": "birthday",
                                "entities": [],
                                "details": [],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "relationship",
                        "title": "Status",
                        "fields": [
                            {
                                "text": "Married to Tammim Ahmed",
                                "field_type": "relationship",
                                "entities": [
                                    {
                                        "id": "12345",
                                        "name": "Tammim",
                                        "url": "https://www.facebook.com/tam.ahmed",
                                        "profile_url": "https://www.facebook.com/tam.ahmed",
                                        "is_verified": False,
                                        "typename": "User",
                                    }
                                ],
                                "details": ["Since February 26, 2021"],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "family",
                        "title": "Family members",
                        "fields": [
                            {
                                "text": "মারুফা রহমান",
                                "field_type": "family",
                                "entities": [
                                    {
                                        "id": "67890",
                                        "name": "মারুফা রহমান",
                                        "url": "https://www.facebook.com/Tani.Marufa",
                                        "profile_url": "https://www.facebook.com/Tani.Marufa",
                                        "is_verified": False,
                                        "typename": "User",
                                    }
                                ],
                                "details": ["Mother"],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "directory_gender",
                        "title": "Gender",
                        "fields": [],
                    },
                    {
                        "section_type": "directory_languages",
                        "title": "Languages",
                        "fields": [
                            {
                                "text": "Bangla",
                                "field_type": "language",
                                "entities": [],
                                "details": [],
                                "icon_url": None,
                            }
                        ],
                    },
                ],
            },
            {
                "name": "Work",
                "url": "https://www.facebook.com/testuser/directory_work",
                "sections": [
                    {
                        "section_type": "directory_work",
                        "title": "Work",
                        "fields": [
                            {
                                "text": "BBA Ambassador at Canadian University",
                                "field_type": "work",
                                "entities": [],
                                "details": [
                                    "January 1, 2020 - Present",
                                    "Badda, Dhaka",
                                ],
                                "icon_url": None,
                            },
                            {
                                "text": "Former Sales Manager at Vision Web PPC",
                                "field_type": "work",
                                "entities": [],
                                "details": ["March 3, 2022 - December 2022"],
                                "icon_url": None,
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Education",
                "url": "https://www.facebook.com/testuser/directory_education",
                "sections": [
                    {
                        "section_type": "directory_college",
                        "title": "College",
                        "fields": [
                            {
                                "text": "Studied BBA(Hons) at Canadian University",
                                "field_type": "education",
                                "entities": [],
                                "details": ["Class of 2023", "Major: BBA(Hons)"],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "directory_high_school",
                        "title": "High school",
                        "fields": [
                            {
                                "text": "Went to Holy Crescent School",
                                "field_type": "education",
                                "entities": [],
                                "details": [],
                                "icon_url": None,
                            }
                        ],
                    },
                ],
            },
            {
                "name": "Names",
                "url": "https://www.facebook.com/testuser/directory_names",
                "sections": [
                    {
                        "section_type": "nicknames",
                        "title": "Other names",
                        "fields": [
                            {
                                "text": "Maruf",
                                "field_type": "nicknames",
                                "entities": [],
                                "details": ["Nickname"],
                                "icon_url": None,
                            }
                        ],
                    },
                    {
                        "section_type": "name_pronunciation",
                        "title": "Name pronunciation",
                        "fields": [],
                    },
                ],
            },
        ],
    },
}


def test_convert_basic_fields():
    """Test that basic profile fields are preserved."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)

    assert result["profile_id"] == "1594662816"
    assert result["name"] == "Test User"
    assert result["profile_url"] == "https://www.facebook.com/testuser"
    assert result["bio"] == "Test bio"
    assert result["friends_count"] == 492
    assert result["scraped_at"] == "2026-03-02T14:54:45.815500"


def test_convert_work():
    """Test work items are extracted from about_tabs."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    work = result["work"]

    assert len(work) == 2
    assert work[0]["organization"] == "Canadian University"
    assert work[0]["designation"] == "BBA Ambassador"
    assert "January 1, 2020 - Present" in work[0]["details"]

    assert work[1]["organization"] == "Vision Web PPC"
    assert work[1]["designation"] == "Former Sales Manager"


def test_convert_education():
    """Test education items are extracted from about_tabs."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    edu = result["education"]

    assert len(edu) == 2
    assert edu[0]["institution"] == "Canadian University"
    assert edu[0]["type"] == "College"
    assert edu[0]["field_of_study"] == "BBA(Hons)"

    assert edu[1]["institution"] == "Holy Crescent School"
    assert edu[1]["type"] == "High school"


def test_convert_location():
    """Test location parsing from about_tabs."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)

    assert result["current_city"]["district"] == "Dhaka"
    assert result["current_city"]["country"] == "Bangladesh"

    assert result["hometown"]["district"] == "Dhaka"
    assert result["hometown"]["country"] == "Bangladesh"


def test_convert_birthday():
    """Test birthday extraction."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    assert result["birthday_info"]["birthday"] == "January 3, 1995"


def test_convert_relationship():
    """Test relationship extraction."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    rel = result["relationship"]

    assert len(rel) == 1
    assert rel[0]["status"] == "Married to Tammim Ahmed"
    assert rel[0]["partner_info"]["name"] == "Tammim"
    assert "Since February 26, 2021" in rel[0]["details"]


def test_convert_family():
    """Test family members extraction."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    fam = result["family_members"]

    assert len(fam) == 1
    assert fam[0]["name"] == "মারুফা রহমান"
    assert fam[0]["relationship"] == "Mother"
    assert fam[0]["profile_url"] == "https://www.facebook.com/Tani.Marufa"


def test_convert_languages():
    """Test language skills extraction."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    assert "Bangla" in result["language_skills"]


def test_convert_names():
    """Test nickname extraction."""
    result = convert_scraped_to_final(SAMPLE_SCRAPED)
    assert result["names"]["nicknames"] == ["Maruf"]


def test_convert_empty_profile():
    """Test conversion with minimal data."""
    minimal = {
        "scraped_at": "2026-01-01T00:00:00",
        "profile": {
            "profile_id": "123",
            "name": "Minimal User",
            "about_tabs": [],
        },
    }
    result = convert_scraped_to_final(minimal)
    assert result["profile_id"] == "123"
    assert result["name"] == "Minimal User"
    assert result["work"] == []
    assert result["education"] == []
