import os
import sys
from datetime import datetime

# Add parent directory to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from common.driver_manager import ChromeDriverManager
from common.auth import FacebookAuth
from comment_scraper import TabBasedCommentScraper

# Configuration
# TARGET_URL = "https://www.facebook.com/reel/746150505251247"
TARGET_URL = "https://www.facebook.com/pori.monii/posts/pfbid0puiiAoEj81oMuaT3cMMPM3SmmcmSkSffVhUXFCLRstec9nNtXCdmZ1Ug19itXNyol"
# TARGET_URL = "https://www.facebook.com/groups/1090616303211975/posts/1135834728690132"
# TARGET_URL = "https://www.facebook.com/reel/1472525077323795"
# TARGET_URL = "https://www.facebook.com/Anwartv.video/videos/763723399737836/"
# TARGET_URL = "https://www.facebook.com/BBCBengaliService/posts/pfbid026RPC9CftZHPB7cbfF9Snwt4wjcgZQD5o1J13itrKU55egqS8rDhpeWauxmE2mCLhl"
# TARGET_URL = "https://www.facebook.com/JamunaTelevision/posts/pfbid0UHRZfJiYot6LSzqYSsSvXYnHvHBy4rBmfQ6Q8QiQWqRi9YWozFE3mKhRQTb9sYY5l"
# TARGET_URL = "https://www.facebook.com/JamunaTelevision/posts/pfbid0aXEQEgqaaqLLGQmywHswU2NRKM3SpVX2LDdTHNTZvkhqTmdNcgRVHbHY13AcioaSl"
# TARGET_URL = "https://www.facebook.com/MyNagad/videos/1418138002624708"
# TARGET_URL = "https://www.facebook.com/amarbKash16247/videos/1329531922135607"
# TARGET_URL = "https://www.facebook.com/MyNagad/posts/pfbid02Kz8weopQmQXCXgFDbk7wr4cwYtWZ8EyQbGc1cGMxqzbhbgMQVgGen3HLbw1dzvnLl"
# TARGET_URL = "https://www.facebook.com/groups/hrdeskctg/posts/2808201542717841"
# TARGET_URL = "https://www.facebook.com/BBCBengaliService/posts/pfbid0S6dFZx9u4FQggqNSdgrvrtPazEdsLoWeV3dQKyCRxHhFysEDqTyU5nTsfCGWQGmxl"
# TARGET_URL = "https://www.facebook.com/BBCBengaliService/posts/pfbid02ZHbAWz7TpS2TVMSryrR8r85rbEcmJkRQ6GHnfZZs6FT8GB1K3jcxEuHSgyPxjjq7l"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Hardcoded credentials for debugging (main function only)
# DEBUG_USERNAME = "01730805675"  # Replace with your Facebook username/phone
DEBUG_USERNAME = "017230805675"  # Replace with your Facebook username/phone
DEBUG_PASSWORD = "Test@1234"  # Replace with your Facebook password
DEBUG_COOKIES_FILE = os.path.join(BASE_DIR, "facebook_cookies.json")
SCRAPE_TILL_DATE = datetime.fromisoformat("2025-09-08T18:21:21+00:00")


class FacebookManualBot:
    def __init__(self):
        self.driver_manager = ChromeDriverManager()
        self.driver = None
        self.auth = None
        self.scraper = None
        self.output_file = os.path.join(BASE_DIR, "output.json")

    def start(
        self,
        scrape_comments_type: str = "All comments",
        facebook_post_data: dict = None,
    ):
        try:
            self.driver_manager.kill_chrome_processes()
            self.driver_manager.copy_main_profile_to_bot()
            self.driver = self.driver_manager.setup_driver()

            # Initialize auth and scraper
            self.auth = FacebookAuth(self.driver)
            self.scraper = TabBasedCommentScraper(
                self.driver,
                TARGET_URL,
                scrape_comments_type,
                facebook_post_data,
                # comment_limit=22,
                scrape_till_datetime=SCRAPE_TILL_DATE,
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

            # Start tab-based comment scraping
            try:
                print(
                    f"🎯 Starting manual tab-based comment scraping for: {TARGET_URL}"
                )
                facebook_post = self.scraper.scrape_facebook_comments()

                # Return results
                if facebook_post:
                    print(
                        f"✅ Manual scraping completed! Found {len(facebook_post.comments)} comments"
                    )
                    return facebook_post
                else:
                    print("⚠️ No comments found")
                    return None

            except Exception as e:
                print(f"❌ Scraping error: {e}")
                # Re-raise exception to stop execution instead of continuing
                raise e

        except Exception as e:
            print(f"❌ Bot startup error: {e}")
            return None

    def quit(self):
        if self.driver_manager:
            self.driver_manager.quit()


def main():
    bot = FacebookManualBot()

    try:
        # You can specify the comment type to scrape: "All comments", "Newest", or "Most relevant"
        # You can also optionally provide facebook_post_data to use existing post field values
        facebook_post = bot.start(
            scrape_comments_type="Newest", facebook_post_data=None
        )

        if facebook_post:
            print(
                f"\n🎉 Successfully scraped Facebook post with manual tab-based approach!"
            )
            print(f"🔗 Post URL: {facebook_post.post_url}")
            print(f"📊 Total comments found: {len(facebook_post.comments)}")
            print(f"📅 Scraped at: {datetime.now()}")

            # Show comment summary
            main_comments = [c for c in facebook_post.comments if c.parent == "root"]
            reply_comments = [c for c in facebook_post.comments if c.parent != "root"]

            print(f"💬 Main comments: {len(main_comments)}")
            print(f"🔗 Reply comments: {len(reply_comments)}")

            # Show first 3 comments as preview
            for i, comment in enumerate(facebook_post.comments[:3], 1):
                comment_type = "REPLY" if comment.parent != "root" else "COMMENT"
                print(f"\n💬 {comment_type} #{i}:")
                print(f"   Author: {comment.user_name}")
                print(f"   Text: {comment.comment_text[:100]}...")
                print(f"   Time: {comment.comment_time}")
                print(f"   Replies: {len(comment.comments_replies)}")

        return facebook_post

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        print("Try running the script again.")
    finally:
        bot.quit()


if __name__ == "__main__":
    main()
