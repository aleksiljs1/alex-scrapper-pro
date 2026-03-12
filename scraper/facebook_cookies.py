import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from common.driver_manager import ChromeDriverManager

def create_cookies():
    dm = ChromeDriverManager()
    try:
        dm.kill_chrome_processes()
        dm.copy_main_profile_to_bot()
        driver = dm.setup_driver()

        driver.get("https://www.facebook.com")
        input("🔐 Log in manually in the browser, then press Enter here...")

        cookies = driver.get_cookies()
        cookies_file = os.path.join(current_dir, "facebook_cookies.json")
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)

        print(f"✅ Cookies saved to: {cookies_file}")
        print(f"📄 {len(cookies)} cookies stored")
    finally:
        dm.quit()

if __name__ == "__main__":
    create_cookies()