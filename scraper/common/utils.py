import os
import time
import random


# Global configuration for Facebook data storage
GLOBAL_DATA_ROOT = "/tmp"
FACEBOOK_DATA_PARENT = "facebook_data"

def get_facebook_data_path():
    """Get the absolute path to the facebook_data directory"""
    return os.path.join(GLOBAL_DATA_ROOT, FACEBOOK_DATA_PARENT)

def setup_directories(required_dirs=None):
    """Create required directories for scrapers under global facebook_data directory"""
    if required_dirs is None:
        required_dirs = [
            "post_attachments",                        # Used by post_scraper.py
            "screenshots",                             # Used by comment_scraper.py (initial screenshots)
            "comment_attachments",                     # Used by comment_scraper.py (comment attachments)
            "source_attachments/profile_pictures_from_comments",  # Used by comment_scraper.py (profile pictures)
            "source_attachments/profile_pictures_from_posts",  # Used by post_scraper.py (profile pictures)
            "scraped_data_output/manual",              # Used by comment_scraper.py (JSON output)
            "scraped_data_output/schedule"             # Used by post_scraper.py (JSON output)
        ]
    
    # Get the facebook_data base directory
    base_dir = get_facebook_data_path()
    
    # Create the parent facebook_data directory first
    os.makedirs(base_dir, exist_ok=True)
    print(f"📁 Created/verified parent directory: {base_dir}")
    
    # Create all required subdirectories
    for directory in required_dirs:
        dir_path = os.path.join(base_dir, directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 Created/verified directory: {dir_path}")
    
    return base_dir


def random_wait(min_seconds=2, max_seconds=8):
    """Wait for a random amount of time"""
    wait_time = random.randint(min_seconds, max_seconds)
    print(f"⏳ Waiting {wait_time} seconds...")
    time.sleep(wait_time)
    return wait_time


def generate_timestamp():
    """Generate current timestamp"""
    return int(time.time())
