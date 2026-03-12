# Profile Scraper Package

This is the organized profile scraper package that uses tab-based navigation to scrape Facebook profile information including About page details.

## Package Structure

```
manual/profile/
├── __init__.py              # Package initialization
├── main.py                  # Main entry point for profile scraping
├── profile_scraper.py       # Tab-based profile scraper (ProfileScraper)
└── README.md               # This documentation
```

## How to Run

```bash
# Navigate to the project root
cd facebook_scraper/

# Run the profile scraper
uv run manual/profile/main.py

# Or from inside the profile directory
cd manual/profile/
uv run main.py
```

## Features

### Profile Data Extraction
- Extracts basic profile information (name, ID, bio, category)
- Downloads profile picture and cover photo
- Captures followers and friends counts
- Collects intro section items (work, education, location)

### Tab-Based About Page Navigation
- Uses Tab key to navigate through About page tabs
- Dynamically discovers available tabs from GraphQL responses
- Handles different profiles with varying tab availability
- Stops automatically after processing all available tabs

### GraphQL Response Parsing
- Intercepts Facebook GraphQL API responses
- Extracts structured About page data from `all_collections.nodes[]`
- Parses profile field sections with entities and details
- Captures entity metadata (URLs, verification status, icons)

### Structured About Page Data
- Organized by tabs (Intro, Personal details, Work, Education, etc.)
- Sections within each tab with typed fields
- Entity references (employers, schools, cities) with profile URLs
- Detail items (dates, majors, descriptions, job titles)

### Dual Storage System
- Saves to global `/tmp/facebook_data/scraped_data_output/profile/`
- Also saves to project `output/profile/` directory
- Downloads media to `profile_attachments/` directory

## Configuration

Edit the following variables in `main.py`:

```python
TARGET_URL = "https://www.facebook.com/target_profile_username"
DEBUG_USERNAME = "your_facebook_username"
DEBUG_PASSWORD = "your_facebook_password"
DEBUG_COOKIES_FILE = os.path.join(BASE_DIR, "facebook_cookies.json")
```

## Dependencies

Uses shared modules from the `common/` directory:
- `common.driver_manager` - Chrome driver management
- `common.auth` - Facebook authentication
- `common.utils` - Directory setup and utility functions

## Output

Returns a `FacebookProfile` dataclass containing:
- Basic profile information (name, ID, URL, bio, category)
- Profile picture and cover photo (URLs and local paths)
- Social metrics (followers count, friends count)
- Legacy flat fields (work, education, current_city, hometown, relationship_status)
- Intro items list
- Structured `about_tabs` with sections and fields:
  - Each tab has name, URL, and sections
  - Each section has type, title, and fields
  - Each field has text, type, entities, and details
  - Entities include name, URL, verification status

### Output Files

**JSON Output:**
- `profile_YYYYMMDD_HHMMSS_randomid.json` in both storage locations
- Contains scraped timestamp and complete profile data

**Downloaded Media:**
- Profile picture: `profile_picture_{profile_id}.jpg`
- Cover photo: `cover_photo_{profile_id}.jpg`
- Stored in `profile_attachments/` directory

## Data Structure

```python
@dataclass
class FacebookProfile:
    profile_id: str
    name: str
    profile_url: str
    profile_picture_url: Optional[str]
    profile_picture_path: Optional[str]
    cover_photo_url: Optional[str]
    cover_photo_path: Optional[str]
    bio: Optional[str]
    category: Optional[str]
    followers_count: Optional[int]
    friends_count: Optional[int]
    work: List[str]
    education: List[str]
    current_city: Optional[str]
    hometown: Optional[str]
    relationship_status: Optional[str]
    intro_items: List[str]
    about_details: dict
    about_tabs: List[AboutTab]
```

## Notes

- The scraper uses Chrome DevTools Protocol for network log interception
- Tab navigation requires focus on the browser window
- About page tabs are discovered dynamically (profiles have different available tabs)
- Only the first JSON object from multi-line GraphQL responses is parsed
- Profile URL is always set from the target URL parameter
