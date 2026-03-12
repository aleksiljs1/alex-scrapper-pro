import os
import sys
from datetime import datetime

# Add parent directory to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)  # facebook_scraper/
if root_dir in sys.path:
    sys.path.remove(root_dir)
sys.path.insert(0, root_dir)

from common.driver_manager import ChromeDriverManager
from common.auth import FacebookAuth
from profile_scraper import ProfileScraper, AboutTab, AboutSection, AboutField

# Configuration
# TARGET_URL = "https://www.facebook.com/rashad.niloy"
# TARGET_URL = "https://www.facebook.com/Jack131991"
TARGET_URL = "https://www.facebook.com/sk.lalon.184732"
# TARGET_URL = "https://www.facebook.com/babu.alamagira"
# TARGET_URL = "https://www.facebook.com/sa.niloy2012"
# TARGET_URL = "https://www.facebook.com/md.monir.hossain.patwary.2024"
# TARGET_URL = "https://www.facebook.com/sada.mana.347790"
# TARGET_URL = "https://www.facebook.com/moh.iliyacha.pharaji"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Hardcoded credentials for debugging (main function only)
DEBUG_USERNAME = "01730805675"  # Replace with your Facebook username/phone
DEBUG_PASSWORD = "Test@1234"  # Replace with your Facebook password
DEBUG_COOKIES_FILE = os.path.join(BASE_DIR, "facebook_cookies.json")

SAVE_OUTPUT_INSIDE_ROOT = False

class FacebookProfileBot:
    def __init__(self):
        self.driver_manager = ChromeDriverManager()
        self.driver = None
        self.auth = None
        self.scraper = None

    def start(self):
        try:
            self.driver_manager.kill_chrome_processes()
            self.driver_manager.copy_main_profile_to_bot()
            self.driver = self.driver_manager.setup_driver()

            # Initialize auth and scraper
            self.auth = FacebookAuth(self.driver)
            self.scraper = ProfileScraper(
                self.driver, 
                TARGET_URL, 
                is_save_inRoot=SAVE_OUTPUT_INSIDE_ROOT
            )

            # Login to Facebook
            try:
                print("🔐 Attempting to login to Facebook...")
                success = self.auth.login_to_facebook(
                    DEBUG_USERNAME, DEBUG_PASSWORD, DEBUG_COOKIES_FILE
                )
                if not success:
                    print("❌ Login failed, exiting...")
                    return None
            except Exception as e:
                print(f"❌ Login error: {e}, exiting...")
                return None

            # Start profile scraping
            try:
                print(f"🎯 Starting profile scraping for: {TARGET_URL}")
                profile = self.scraper.scrape_profile()

                if profile:
                    print(f"✅ Profile scraping completed!")
                    return profile
                else:
                    print("⚠️ No profile data found")
                    return None

            except Exception as e:
                print(f"❌ Scraping error: {e}")
                raise e

        except Exception as e:
            print(f"❌ Bot startup error: {e}")
            return None

    def quit(self):
        if self.driver_manager:
            self.driver_manager.quit()


def main():
    bot = FacebookProfileBot()

    try:
        profile = bot.start()

        if profile:
            print(f"\n🎉 Successfully scraped Facebook profile!")
            print(f"👤 Name: {profile.name}")
            print(f"🆔 Profile ID: {profile.profile_id}")
            print(f"🔗 URL: {profile.profile_url}")
            print(f"📝 Bio: {profile.bio}")
            print(f"👥 Followers: {profile.followers_count}")
            print(f"👫 Friends: {profile.friends_count}")
            print(f"📂 Category: {profile.category}")

            if profile.work:
                print(f"💼 Work:")
                for item in profile.work:
                    print(f"   - {item}")
            if profile.education:
                print(f"🎓 Education:")
                for item in profile.education:
                    print(f"   - {item}")
            if profile.current_city:
                print(f"📍 Current City: {profile.current_city}")
            if profile.hometown:
                print(f"🏠 Hometown: {profile.hometown}")
            if profile.relationship_status:
                print(f"❤️ Relationship: {profile.relationship_status}")
            if profile.intro_items:
                print(f"📋 Intro Items:")
                for item in profile.intro_items:
                    print(f"   - {item}")

            # Display structured About tab data from GraphQL
            if profile.about_tabs:
                print(f"\n{'='*60}")
                print(f"📋 ABOUT PAGE DETAILS (from GraphQL)")
                print(f"{'='*60}")
                for tab in profile.about_tabs:
                    print(f"\n┌─ 📁 Tab: {tab.name}")
                    if tab.url:
                        print(f"│  URL: {tab.url}")
                    for section in tab.sections:
                        print(f"│")
                        print(f"├── 📂 Section: {section.title} [{section.section_type}]")
                        if not section.fields:
                            print(f"│   └── (no fields)")
                            continue
                        for i, fld in enumerate(section.fields):
                            is_last = i == len(section.fields) - 1
                            prefix = "└──" if is_last else "├──"
                            print(f"│   {prefix} 📄 {fld.text}")
                            print(f"│   {'   ' if is_last else '│  '}  Type: {fld.field_type}")
                            if fld.entities:
                                for ent in fld.entities:
                                    verified = " ✓" if ent.is_verified else ""
                                    print(
                                        f"│   {'   ' if is_last else '│  '}  Entity: {ent.name}{verified} → {ent.profile_url}"
                                    )
                            if fld.details:
                                for detail in fld.details:
                                    # Truncate very long descriptions
                                    display = detail[:120] + "..." if len(detail) > 120 else detail
                                    print(f"│   {'   ' if is_last else '│  '}  Detail: {display}")
                    print(f"└─────────────────────────────────────")

            print(f"\n📸 Profile Picture: {profile.profile_picture_path}")
            print(f"🖼️ Cover Photo: {profile.cover_photo_path}")
            print(f"📅 Scraped at: {datetime.now()}")

        return profile

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        print("Try running the script again.")
    finally:
        bot.quit()


if __name__ == "__main__":
    main()
