import re


def normalize_fb_url(url: str) -> tuple[str, str]:
    """
    Normalize a Facebook URL and extract the slug.
    Returns (normalized_url, slug).
    """
    url = url.strip()

    # Handle bare usernames
    if not url.startswith("http"):
        url = "https://www.facebook.com/" + url

    # Remove trailing slash and query params
    url = url.rstrip("/").split("?")[0]

    # Extract slug (last path segment)
    slug = url.rstrip("/").split("/")[-1]

    return url, slug


def extract_text_after_at(text: str) -> tuple[str, str]:
    """
    Extract designation and organization from text like 'Business Analyst at Company'.
    Also handles 'Former X at Company', 'Worked at Company', 'Works at Company', 'Studied X at University'.
    Returns (designation, organization).
    """
    if not text:
        return ("", "")

    # Pattern: "text at Organization"
    match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if match:
        designation = match.group(1).strip()
        organization = match.group(2).strip()
        return (designation, organization)

    # Fallback: the whole text is the organization
    return ("", text)


def parse_location_string(location_str: str | None) -> dict | None:
    """
    Parse a location string like 'Dhaka, Bangladesh' or 'Purbadhala, Dhaka, Bangladesh'
    into a structured location dict.

    Returns dict with keys: upazila, district, division, country
    """
    if not location_str:
        return None

    # Remove common prefixes
    cleaned = location_str
    for prefix in ["Lives in ", "From "]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]

    parts = [p.strip() for p in cleaned.split(",")]

    result = {
        "upazila": None,
        "district": None,
        "division": None,
        "country": None,
    }

    if len(parts) == 1:
        result["district"] = parts[0]
    elif len(parts) == 2:
        result["district"] = parts[0]
        result["country"] = parts[1]
    elif len(parts) == 3:
        result["upazila"] = parts[0]
        result["district"] = parts[1]
        result["country"] = parts[2]
    elif len(parts) >= 4:
        result["upazila"] = parts[0]
        result["district"] = parts[1]
        result["division"] = parts[2]
        result["country"] = parts[3]

    return result
