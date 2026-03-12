# Manual Scraper Package

This is the organized manual scraper package that uses tab-based navigation to scrape Facebook comments and replies.

## Package Structure

```
manual/
├── __init__.py              # Package initialization
├── main.py                  # Main entry point for manual scraping
├── comment_scraper.py       # Tab-based comment scraper (TabBasedCommentScraper)
├── comment_parser.py        # Comment parsing utilities
└── README.md               # This documentation
```

## How to Run

```bash
# Navigate to the manual directory
cd manual/

# Run the manual scraper
python3 main.py
```

## Features

### Tab-Based Navigation
- Uses Tab key to navigate through comment elements
- Handles reply expansion automatically
- Detects end of comments intelligently

### Reply Support
- Expands "View X replies" elements
- Maps replies to parent comments
- Supports nested reply structures

### Improved Data Structure
- Uses specific field names (`post_id`, `comment_id`, `author_id`)
- Proper parent-child comment relationships
- Stores internal node IDs for mapping

### Smart End Detection
- Stops when no "Like" or "Reply" found in last 25 tabs
- Prevents infinite navigation

## Configuration

Edit the following variables in `main.py`:

```python
TARGET_URL = "https://www.facebook.com/groups/hrdeskctg/posts/2787532908118038/"
DEBUG_USERNAME = "your_facebook_username"
DEBUG_PASSWORD = "your_facebook_password"
```

## Dependencies

Uses shared modules from the `common/` directory:
- `common.driver_manager` - Chrome driver management
- `common.auth` - Facebook authentication
- `common.dataclasses` - Data structures
- `common.utils` - Utility functions

## Output

Returns a `FacebookPost` object containing:
- All scraped comments and replies
- Proper parent-child relationships
- Comment metadata and statistics
- Author information for each comment