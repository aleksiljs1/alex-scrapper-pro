import time
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager as WebDriverManager

class ChromeDriverManager:
    """Common Chrome driver management functionality"""
    
    def __init__(self, bot_profile_path=None):
        self.driver = None
        self.bot_profile_path = bot_profile_path or os.path.expanduser("~/.config/google-chrome-bot")
    
    def kill_chrome_processes(self):
        """Kill any existing Chrome processes that might be hanging"""
        try:
            subprocess.run(["pkill", "-f", "chrome"], check=False)
            subprocess.run(["pkill", "-f", "chromedriver"], check=False)
            time.sleep(2)
        except Exception as e:
            print(f"Error killing Chrome processes: {e}")

    def copy_main_profile_to_bot(self):
        """Copy main Chrome profile to bot profile for session persistence"""
        main_profile = os.path.expanduser("~/.config/google-chrome/Default")
        bot_profile = os.path.join(self.bot_profile_path, "Default")

        if os.path.exists(main_profile) and not os.path.exists(bot_profile):
            try:
                os.makedirs(self.bot_profile_path, exist_ok=True)
                subprocess.run(["cp", "-r", main_profile, bot_profile], check=True)
                print("Copied main Chrome profile to bot profile for session persistence")
            except Exception as e:
                print(f"Warning: Could not copy main profile: {e}")
                print("Bot will start with fresh profile")

    def setup_driver(self, retry_count=0):
        """Set up Chrome driver with common options"""
        if retry_count > 2:
            raise Exception("Failed to start Chrome after 3 attempts")

        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--no-sandbox")
            # chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--force-device-scale-factor=0.75')
            chrome_options.add_argument("--width=1920")
            chrome_options.add_argument("--height=1080")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

            # Enable network logging
            chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

            # Use separate Chrome profile for bot to avoid conflicts
            # chrome_options.add_argument(f"--user-data-dir={self.bot_profile_path}")
            # chrome_options.add_argument("--profile-directory=Default")

            service = Service(WebDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            return self.driver

        except WebDriverException as e:
            print(f"WebDriver error (attempt {retry_count + 1}): {e}")
            if (
                "chrome not reachable" in str(e).lower()
                or "session not created" in str(e).lower()
            ):
                print("Chrome not reachable, cleaning up processes and retrying...")
                self.kill_chrome_processes()
                return self.setup_driver(retry_count + 1)
            else:
                raise e
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise e

    def quit(self):
        """Clean up driver and processes"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.kill_chrome_processes()
