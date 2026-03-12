#!/usr/bin/env python3
"""
CLI entry point for the scraper bot.
Usage: python run_scrape.py <facebook_profile_url>

Called by the Celery worker via: docker exec scraper-bot python /app/run_scrape.py <url>
Outputs JSON to /tmp/facebook_data/scraped_data_output/profile/
"""
import sys
import os

# Setup path
sys.path.insert(0, "/app")

from common.driver_manager import ChromeDriverManager
from common.auth import FacebookAuth
from manual.profile.profile_scraper import ProfileScraper

# Credentials from environment or defaults
FB_USERNAME = os.environ.get("FB_USERNAME", "01730805675")
FB_PASSWORD = os.environ.get("FB_PASSWORD", "Test@1234")
COOKIES_FILE = "/app/facebook_cookies.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_scrape.py <facebook_profile_url>")
        sys.exit(1)

    target_url = sys.argv[1]
    print(f"🎯 Scraping profile: {target_url}")

    driver_manager = ChromeDriverManager()
    driver = None

    try:
        driver_manager.kill_chrome_processes()
        driver_manager.copy_main_profile_to_bot()
        driver = driver_manager.setup_driver()

        auth = FacebookAuth(driver)
        success = auth.login_to_facebook(FB_USERNAME, FB_PASSWORD, COOKIES_FILE)
        if not success:
            print("❌ Login failed")
            sys.exit(2)

        scraper = ProfileScraper(driver, target_url, is_save_inRoot=False)
        profile = scraper.scrape_profile()

        if profile:
            print(f"✅ Done: {profile.name} ({profile.profile_id})")
            sys.exit(0)
        else:
            print("❌ No profile data")
            sys.exit(3)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(4)
    finally:
        if driver_manager:
            driver_manager.quit()


if __name__ == "__main__":
    main()
