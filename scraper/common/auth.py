import time
import os
import json
import random
import subprocess
import shutil
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class FacebookAuth:
    """Common Facebook authentication functionality"""

    def __init__(self, driver, cookies_file_path=None):
        self.driver = driver
        self.cookies_file_path = cookies_file_path

        # Check for system dialog availability (similar to post_scraper.py)
        self.system_dialog_available = False
        self.dialog_cmd = None

        # Check for zenity (GNOME/GTK)
        if shutil.which("zenity"):
            self.system_dialog_available = True
            self.dialog_cmd = "zenity"
        # Check for kdialog (KDE)
        elif shutil.which("kdialog"):
            self.system_dialog_available = True
            self.dialog_cmd = "kdialog"
        # Check for notify-send for notifications
        elif shutil.which("notify-send"):
            print("🔔 Notify-send available - will use notifications + console")
        else:
            print("💬 Using console-only manual intervention")

    def save_cookies(self, cookies_file_path):
        """Save current browser cookies to file"""
        if not cookies_file_path:
            return False

        try:
            print("🍪 Saving cookies...")
            cookies = self.driver.get_cookies()
            with open(cookies_file_path, "w") as f:
                json.dump(cookies, f, indent=2)
            print(f"💾 Cookies saved to: {cookies_file_path}")
            return True
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False

    def delete_cookie_file(self, cookies_file_path):
        """Delete the cookie file if it exists"""
        if cookies_file_path and os.path.exists(cookies_file_path):
            try:
                os.remove(cookies_file_path)
                print(f"🗑️ Deleted invalid cookie file: {cookies_file_path}")
                return True
            except Exception as e:
                print(f"❌ Error deleting cookie file: {e}")
                return False
        return False

    def prompt_manual_login(self):
        """Prompt user to manually login using system dialog or console"""
        try:
            if self.system_dialog_available:
                # Use system dialog (zenity/kdialog)
                if self.dialog_cmd == "zenity":
                    result = subprocess.run(
                        [
                            "zenity",
                            "--info",
                            "--title=Manual Login Required",
                            "--text=Please complete the Facebook login process manually in the browser window.\n\nPress OK after successful login to continue...",
                            "--width=400",
                        ],
                        capture_output=True,
                    )
                elif self.dialog_cmd == "kdialog":
                    result = subprocess.run(
                        [
                            "kdialog",
                            "--msgbox",
                            "Please complete the Facebook login process manually in the browser window.\n\nPress OK after successful login to continue...",
                        ],
                        capture_output=True,
                    )

                if result.returncode == 0:
                    print("✅ User confirmed manual login completion")
                    return True
                else:
                    print("❌ Manual login cancelled by user")
                    return False
            else:
                # Fallback to console input
                print("\n" + "=" * 60)
                print("🔑 MANUAL LOGIN REQUIRED")
                print("=" * 60)
                print(
                    "Please complete the Facebook login process manually in the browser window."
                )
                print("After successful login, press ENTER to continue...")
                print("=" * 60)

                input()  # Wait for user to press Enter
                print("✅ Continuing with manual login verification...")
                return True

        except KeyboardInterrupt:
            print("\n❌ Manual login cancelled by user")
            return False
        except Exception as e:
            print(f"❌ Error in manual login prompt: {e}")
            return False

    def verify_facebook_login(self, max_tabs=100):
        """Verify Facebook login by checking URL first, then navigation elements"""
        try:
            required_elements = ["Friends", "Saved"]
            found_elements = []

            print("🔍 Verifying login by checking for navigation elements...")

            # --- URL-based check first ---
            # If we're not on a login/checkpoint/security page, login already succeeded
            current_url = self.driver.current_url
            print(f"🌐 Current URL: {current_url}")
            login_blocked_patterns = ["login", "checkpoint", "recover", "two_step", "arkose", "security"]
            if "facebook.com" in current_url and not any(p in current_url for p in login_blocked_patterns):
                print("✅ URL indicates successful login — skipping tab navigation")
                if self.cookies_file_path:
                    self.save_cookies(self.cookies_file_path)
                return True

            # Press Tab up to max_tabs times to find required elements
            for tab_count in range(max_tabs):
                try:
                    # Get the currently focused element
                    active_element = self.driver.switch_to.active_element

                    # Check if this element contains any of our required text
                    element_text = (
                        active_element.text.strip() if active_element.text else ""
                    )

                    # Skip if element text is too long (likely a container with all page content)
                    if len(element_text) > 200:
                        # Don't print for large elements to avoid spam
                        pass
                    else:
                        # Print element text content for debugging (only for reasonably sized elements)
                        if element_text:
                            print(f"Login Tab {tab_count}: '{element_text}'")
                        else:
                            print(f"Login Tab {tab_count}: [empty/no text]")

                        # Check if element contains "Close" - dismiss dialog
                        if "Close" in element_text and len(element_text.strip()) <= 10:
                            print(
                                f"🔍 Found 'Close' dialog at login tab {tab_count} - dismissing..."
                            )
                            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                            time.sleep(1)
                            continue

                        # Only check for required text in reasonably sized elements
                        if element_text:
                            for required_text in required_elements:
                                if (
                                    required_text in element_text
                                    and required_text not in found_elements
                                ):
                                    found_elements.append(required_text)
                                    print(f"✅ Found element: {required_text}")

                            # If we found all required elements, login is successful
                            if len(found_elements) >= len(required_elements):
                                print(
                                    f"🎉 Login verification successful! Found all required elements: {found_elements}"
                                )
                                # Save cookies after successful verification
                                if self.cookies_file_path:
                                    self.save_cookies(self.cookies_file_path)
                                return True

                    # Press Tab to move to next element
                    ActionChains(self.driver).send_keys(Keys.TAB).perform()
                    time.sleep(0.1)  # Small delay between tabs

                except Exception as e:
                    # Continue even if there's an error with a specific element
                    continue

            print(f"❌ Login verification failed. Found elements: {found_elements}")
            print(
                f"❌ Missing elements: {[elem for elem in required_elements if elem not in found_elements]}"
            )
            return False

        except Exception as e:
            print(f"❌ Error during login verification: {e}")
            return False

    def login_to_facebook(self, username, password, cookies_file_path=None):
        """Login to Facebook with cookies first, then fallback to username/password"""
        # If cookies_file_path is provided, save it to instance variable
        if cookies_file_path:
            self.cookies_file_path = cookies_file_path

        try:
            print("🔐 Starting Facebook login...")

            # Step 1: Check if cookies_file_path is provided AND the file exists
            if self.cookies_file_path and os.path.exists(self.cookies_file_path):
                print("🍪 Cookies file found, attempting login with cookies...")
                self.driver.get("https://www.facebook.com")
                time.sleep(2)

                try:
                    with open(self.cookies_file_path, "r") as f:
                        cookies = json.load(f)

                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except Exception as e:
                            print(
                                f"Warning: Could not add cookie {cookie.get('name')}: {e}"
                            )

                    # Refresh page to apply cookies
                    self.driver.refresh()
                    time.sleep(3)

                    # Check if login successful with cookies using element verification
                    print("🍪 Verifying cookie-based login...")
                    if self.verify_facebook_login():
                        print("✅ Login successful using cookies!")
                        return True
                    else:
                        print("⚠️ Cookies login failed, deleting invalid cookie file")
                        self.delete_cookie_file(self.cookies_file_path)

                except Exception as e:
                    print(f"⚠️ Error loading cookies: {e}, deleting invalid cookie file")
                    self.delete_cookie_file(self.cookies_file_path)
            else:
                if not self.cookies_file_path:
                    print("🍪 No cookies file path provided")
                else:
                    print(f"🍪 Cookies file not found at: {self.cookies_file_path}")
                print("👤 Proceeding with username/password login...")

            # Step 2: Login with username and password
            if not username or not password:
                raise Exception("❌ No username or password provided for login")

            print("👤 Logging in with username and password...")
            self.driver.get("https://www.facebook.com")
            time.sleep(2)

            # Type username
            print("👤 Typing username...")
            ActionChains(self.driver).send_keys(username).perform()

            # Press Tab and type password
            print("🔑 Moving to password field and typing password...")
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.5)
            ActionChains(self.driver).send_keys(password).perform()

            # Press Enter to submit
            print("🚀 Pressing Enter to login...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for login response
            wait_time = random.randint(3, 8)
            print(f"⏳ Waiting {wait_time} seconds for login response...")
            time.sleep(wait_time)

            # Check login success using element verification
            print("👤 Verifying username/password login...")
            if self.verify_facebook_login():
                print("✅ Login successful with username/password!")
                return True
            else:
                print("❌ Username/password login failed")

                # Prompt for manual login
                print("🔑 Attempting manual login...")
                if self.prompt_manual_login():
                    # Verify manual login
                    print("🔍 Verifying manual login...")
                    if self.verify_facebook_login():
                        print("✅ Manual login successful!")
                        return True
                    else:
                        print("❌ Manual login verification failed")
                        # Delete cookie file if verification fails (only if cookies_file_path provided)
                        if self.cookies_file_path:
                            self.delete_cookie_file(self.cookies_file_path)
                        return False
                else:
                    print("❌ Manual login cancelled")
                    return False

        except Exception as e:
            print(f"❌ Error during login: {e}")
            return False

