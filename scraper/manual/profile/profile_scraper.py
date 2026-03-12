import time
import os
import json
import random
import re
import string
import requests
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Robust import handling for both local and package usage
try:
    from ...common.utils import setup_directories, get_facebook_data_path
except (ImportError, ValueError):
    # Fall back to path manipulation (when run directly or from main.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)  # manual/
    root_dir = os.path.dirname(parent_dir)  # facebook_scraper/
    if root_dir in sys.path:
        sys.path.remove(root_dir)
    sys.path.insert(0, root_dir)
    from common.utils import setup_directories, get_facebook_data_path

# ── About Page Dataclasses ────────────────────────────────────────


@dataclass
class AboutFieldEntity:
    """Entity referenced in a profile field (e.g., employer, school, city page)"""

    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    profile_url: Optional[str] = None
    is_verified: bool = False
    typename: Optional[str] = None


@dataclass
class AboutField:
    """A single profile field entry from the About page GraphQL response"""

    text: Optional[str] = None
    field_type: Optional[str] = None
    entities: List[AboutFieldEntity] = field(default_factory=list)
    details: List[str] = field(default_factory=list)
    icon_url: Optional[str] = None


@dataclass
class AboutSection:
    """A section within an About tab (e.g., Work, College, Location)"""

    section_type: Optional[str] = None
    title: Optional[str] = None
    fields: List[AboutField] = field(default_factory=list)


@dataclass
class AboutTab:
    """An About page tab (Intro, Personal Details, Work, Education)"""

    name: Optional[str] = None
    url: Optional[str] = None
    sections: List[AboutSection] = field(default_factory=list)


# ── Main Profile Dataclass ────────────────────────────────────────


@dataclass
class FacebookProfile:
    """Data class representing a scraped Facebook profile"""

    profile_id: str
    name: str
    profile_url: str
    profile_picture_url: Optional[str] = None
    profile_picture_path: Optional[str] = None
    cover_photo_url: Optional[str] = None
    cover_photo_path: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    followers_count: Optional[int] = None
    friends_count: Optional[int] = None
    work: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    current_city: Optional[str] = None
    hometown: Optional[str] = None
    relationship_status: Optional[str] = None
    intro_items: List[str] = field(default_factory=list)
    about_details: dict = field(default_factory=dict)
    about_tabs: List[AboutTab] = field(default_factory=list)


class ProfileScraper:
    """Scrapes Facebook profile information using Selenium and network log interception.

    Reuses the same patterns as the post/comment scrapers:
    - ChromeDriverManager for driver setup
    - FacebookAuth for login
    - Chrome DevTools Protocol for network log interception
    - JavaScript execution for DOM-based data extraction
    - setup_directories/get_facebook_data_path for standardized storage
    """

    def __init__(self, driver, target_url: str, is_save_inRoot: bool = False):
        self.driver = driver
        self.target_url = target_url.rstrip("/")
        self.is_save_inRoot = is_save_inRoot
        self.processed_requests = set()
        self.profile_data = {}

        # Setup directories under global facebook_data structure
        self.facebook_data_base = setup_directories(
            [
                "profile_attachments",
                "scraped_data_output/profile",
            ]
        )
        self.profile_attachments_dir = os.path.join(
            self.facebook_data_base, "profile_attachments"
        )

    def scrape_profile(self) -> FacebookProfile:
        """Main entry point - scrape a Facebook profile and return a FacebookProfile dataclass"""
        print(f"🎯 Starting profile scraping for: {self.target_url}")

        # Step 1: Navigate to profile URL
        self.driver.get(self.target_url)
        wait_time = random.randint(3, 8)
        print(f"⏳ Waiting {wait_time}s for page to load...")
        time.sleep(wait_time)

        # Step 2: Extract profile data from network logs (GraphQL responses)
        print("📡 Extracting profile data from network logs...")
        self._extract_from_network_logs()

        # Step 3: Extract from DOM as supplement
        print("🔍 Extracting profile data from DOM...")
        self._extract_from_dom()

        # Step 4: Navigate to About page for additional details
        print("📋 Navigating to About page...")
        self._scrape_about_page()

        # Step 5: Build the profile object
        profile = self._build_profile()

        # Step 6: Download media (profile picture, cover photo)
        self._download_media(profile)

        # Step 7: Save to JSON
        self._save_to_json(profile)

        print(f"✅ Profile scraping completed for: {profile.name or self.target_url}")
        return profile

    # ── Network Log Extraction ────────────────────────────────────────

    def _extract_from_network_logs(self):
        """Extract profile data from GraphQL responses in Chrome performance logs"""
        try:
            logs_raw = self.driver.get_log("performance")
            logs = [json.loads(lr["message"])["message"] for lr in logs_raw]

            def log_filter(log_):
                return (
                    log_["method"] == "Network.responseReceived"
                    and log_["params"].get("type") != "Preflight"
                )

            filtered_logs = list(filter(log_filter, logs))

            for log in filtered_logs:
                request_id = log["params"]["requestId"]
                resp_url = log["params"]["response"]["url"]

                if "graphql" not in resp_url.lower():
                    continue
                if request_id in self.processed_requests:
                    continue
                self.processed_requests.add(request_id)

                try:
                    response_info = log["params"]["response"]
                    if response_info.get("status") != 200:
                        continue

                    response = self.driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    body = response.get("body", "")
                    if not body:
                        continue

                    if self._is_profile_response(body):
                        print(f"📊 Found profile data in GraphQL response")
                        self._parse_profile_response(body)

                except Exception as e:
                    if "No resource with given identifier found" not in str(e):
                        print(f"⚠️ Error processing request {request_id}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Error extracting from network logs: {e}")

    def _is_profile_response(self, response_body: str) -> bool:
        """Check if a GraphQL response contains profile-related data"""
        # Skip pure timeline feed responses that don't have profile info
        if (
            "timeline_list_feed_units" in response_body
            and "bio_text" not in response_body
            and "profile_picture" not in response_body
            and "cover_photo" not in response_body
        ):
            return False

        profile_indicators = [
            "ProfileCometHeader",
            "ProfileCometAbout",
            "profile_header_renderer",
            '"bio_text"',
            '"cover_photo"',
            '"profile_picture"',
            "ProfileCometTimelineFeed",
            '"__typename":"User"',
            '"__typename":"Page"',
        ]
        return any(indicator in response_body for indicator in profile_indicators)

    def _parse_profile_response(self, response_body: str):
        """Parse GraphQL response body for profile data"""
        json_objects = self._extract_json_objects(response_body)
        for data in json_objects:
            self._search_for_profile_data(data)

    def _extract_json_objects(self, response_body: str) -> list:
        """Extract JSON objects from response body (may contain multiple newline-separated objects)"""
        objects = []

        # Try single JSON parse first
        try:
            data = json.loads(response_body)
            objects.append(data)
            return objects
        except json.JSONDecodeError:
            pass

        # Try line-by-line parsing (Facebook often sends multiple JSON objects)
        for line in response_body.split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
                objects.append(data)
            except json.JSONDecodeError:
                continue

        return objects

    def _search_for_profile_data(self, data, depth=0):
        """Recursively search JSON for profile-related User/Page node data"""
        if depth > 12:
            return

        if isinstance(data, dict):
            typename = data.get("__typename")

            # Extract from User nodes
            if typename == "User":
                self._extract_from_user_node(data)

            # Extract from Page nodes
            if typename == "Page":
                self._extract_from_page_node(data)

            # Look for profile fields that might appear outside of typed nodes
            if "profile_picture" in data and isinstance(
                data["profile_picture"], dict
            ):
                uri = data["profile_picture"].get("uri")
                if uri and not self.profile_data.get("profile_picture_url"):
                    self.profile_data["profile_picture_url"] = uri

            if "cover_photo" in data and isinstance(data["cover_photo"], dict):
                photo = data["cover_photo"].get("photo", {})
                if isinstance(photo, dict):
                    image = photo.get("image", {})
                    if isinstance(image, dict) and image.get("uri"):
                        if not self.profile_data.get("cover_photo_url"):
                            self.profile_data["cover_photo_url"] = image["uri"]

            if "bio_text" in data and isinstance(data["bio_text"], dict):
                text = data["bio_text"].get("text")
                if text and not self.profile_data.get("bio"):
                    self.profile_data["bio"] = text

            # Recurse into values
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._search_for_profile_data(value, depth + 1)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._search_for_profile_data(item, depth + 1)

    def _extract_from_user_node(self, user_node: dict):
        """Extract profile data from a User type node"""
        # Determine if this node has substantial profile data
        # (to distinguish the target profile from incidental user references)
        substantial_fields = [
            "profile_picture",
            "cover_photo",
            "bio_text",
            "profile_header_renderer",
            "timeline_list_feed_units",
        ]
        has_substantial_data = any(f in user_node for f in substantial_fields)

        # Extract name and ID (basic fields from any User node if not yet set)
        if user_node.get("name") and not self.profile_data.get("name"):
            if has_substantial_data:
                self.profile_data["name"] = user_node["name"]

        if user_node.get("id") and not self.profile_data.get("profile_id"):
            if has_substantial_data:
                self.profile_data["profile_id"] = user_node["id"]

        # profile_url is always set from target_url, skip overwriting from network logs

        if not has_substantial_data:
            return

        # Override with this more detailed node's data
        if user_node.get("name"):
            self.profile_data["name"] = user_node["name"]
        if user_node.get("id"):
            self.profile_data["profile_id"] = user_node["id"]

        # Profile picture
        prof_pic = user_node.get("profile_picture", {})
        if isinstance(prof_pic, dict) and prof_pic.get("uri"):
            self.profile_data["profile_picture_url"] = prof_pic["uri"]

        # Cover photo
        cover = user_node.get("cover_photo", {})
        if isinstance(cover, dict):
            photo = cover.get("photo", {})
            if isinstance(photo, dict):
                image = photo.get("image", {})
                if isinstance(image, dict) and image.get("uri"):
                    self.profile_data["cover_photo_url"] = image["uri"]

        # Bio
        bio = user_node.get("bio_text", {})
        if isinstance(bio, dict) and bio.get("text"):
            self.profile_data["bio"] = bio["text"]

        # Category
        if user_node.get("category"):
            self.profile_data["category"] = user_node["category"]

        # Counts
        self._extract_counts(user_node)

    def _extract_from_page_node(self, page_node: dict):
        """Extract profile data from a Page type node"""
        substantial_fields = [
            "profile_picture",
            "cover_photo",
            "page_likers",
            "category_name",
        ]
        has_substantial_data = any(f in page_node for f in substantial_fields)

        if not has_substantial_data:
            return

        if page_node.get("name"):
            self.profile_data["name"] = page_node["name"]
        if page_node.get("id"):
            self.profile_data["profile_id"] = page_node["id"]
        # if page_node.get("url"):
            # profile_url is always set from target_url, skip overwriting from network logs

        # Profile picture
        prof_pic = page_node.get("profile_picture", {})
        if isinstance(prof_pic, dict) and prof_pic.get("uri"):
            self.profile_data["profile_picture_url"] = prof_pic["uri"]

        # Cover photo
        cover = page_node.get("cover_photo", {})
        if isinstance(cover, dict):
            photo = cover.get("photo", {})
            if isinstance(photo, dict):
                image = photo.get("image", {})
                if isinstance(image, dict) and image.get("uri"):
                    self.profile_data["cover_photo_url"] = image["uri"]

        # Category
        if page_node.get("category_name"):
            self.profile_data["category"] = page_node["category_name"]

        # Page likers as followers
        likers = page_node.get("page_likers", {})
        if isinstance(likers, dict):
            count = likers.get("count")
            if count is not None:
                self.profile_data["followers_count"] = count

    def _extract_counts(self, node: dict):
        """Extract followers/friends counts from a user/page node"""
        # Followers count - try multiple paths
        if node.get("followers_count") is not None:
            self.profile_data["followers_count"] = node["followers_count"]

        follower_count_obj = node.get("follower_count", {})
        if isinstance(follower_count_obj, dict):
            count = follower_count_obj.get("count")
            if count is not None:
                self.profile_data["followers_count"] = count

        # Friends count - try multiple paths
        if node.get("friends_count") is not None:
            self.profile_data["friends_count"] = node["friends_count"]

        friends_obj = node.get("friends", {})
        if isinstance(friends_obj, dict):
            count = friends_obj.get("count")
            if count is not None:
                self.profile_data["friends_count"] = count

    # ── DOM Extraction ────────────────────────────────────────────────

    def _extract_from_dom(self):
        """Extract profile data from the visible DOM using JavaScript"""
        try:
            self._extract_name_from_dom()
            self._extract_profile_picture_from_dom()
            self._extract_cover_photo_from_dom()
            self._extract_intro_items_from_dom()
            self._extract_counts_from_dom()
        except Exception as e:
            print(f"❌ Error extracting from DOM: {e}")

    # Names that are Facebook UI elements, not actual profile names
    INVALID_PROFILE_NAMES = {
        "chats", "notifications", "notification", "marketplace", "watch",
        "gaming", "groups", "events", "memories", "saved", "pages",
        "ads manager", "messenger", "menu", "search", "home",
        "friends", "settings", "help", "log out", "facebook",
        "create", "profile", "video", "reels", "stories",
    }

    def _is_valid_profile_name(self, name: str) -> bool:
        """Check if the extracted name is a valid profile name (not a UI element)."""
        if not name or not name.strip():
            return False
        return name.strip().lower() not in self.INVALID_PROFILE_NAMES

    def _extract_name_from_dom(self):
        """Extract profile name from the DOM"""
        name = self.driver.execute_script(
            """
            try {
                const h1 = document.querySelector('h1');
                return h1 ? h1.textContent.trim() : null;
            } catch(e) { return null; }
        """
        )
        if name and not self.profile_data.get("name"):
            if self._is_valid_profile_name(name):
                self.profile_data["name"] = name
                print(f"📝 Got name from DOM: {name}")
            else:
                print(f"⚠️ DOM returned invalid name (UI element): '{name}', skipping")

    def _extract_profile_picture_from_dom(self):
        """Extract profile picture URL from the DOM"""
        profile_pic = self.driver.execute_script(
            """
            try {
                // Method 1: SVG-based profile picture
                const svgImage = document.querySelector('svg[aria-label*="profile picture"] image');
                if (svgImage) {
                    return svgImage.getAttribute('xlink:href') || svgImage.getAttribute('href');
                }

                // Method 2: img with data-imgperflogname
                const profileImg = document.querySelector('[data-imgperflogname="profilePhoto"] img');
                if (profileImg) return profileImg.src;

                // Method 3: img with alt containing "profile picture"
                const imgs = document.querySelectorAll('img[alt]');
                for (const img of imgs) {
                    const alt = img.alt.toLowerCase();
                    if (alt.includes('profile picture') && img.src && img.width > 100) {
                        return img.src;
                    }
                }
                return null;
            } catch(e) { return null; }
        """
        )
        if profile_pic and not self.profile_data.get("profile_picture_url"):
            self.profile_data["profile_picture_url"] = profile_pic
            print(f"📸 Got profile picture URL from DOM")

    def _extract_cover_photo_from_dom(self):
        """Extract cover photo URL from the DOM"""
        cover_photo = self.driver.execute_script(
            """
            try {
                // Method 1: data-imgperflogname attribute
                const cover = document.querySelector('[data-imgperflogname="profileCoverPhoto"]');
                if (cover) return cover.src || cover.getAttribute('src');

                // Method 2: img inside cover photo container
                const coverImg = document.querySelector('img[data-imgperflogname="profileCoverPhoto"]');
                if (coverImg) return coverImg.src;

                return null;
            } catch(e) { return null; }
        """
        )
        if cover_photo and not self.profile_data.get("cover_photo_url"):
            self.profile_data["cover_photo_url"] = cover_photo
            print(f"🖼️ Got cover photo URL from DOM")

    def _extract_intro_items_from_dom(self):
        """Extract intro section items (work, education, location, etc.) from the DOM"""
        intro_items = self.driver.execute_script(
            """
            try {
                const items = [];
                const seen = new Set();

                // Look for spans containing common profile intro patterns
                const allSpans = document.querySelectorAll('span');
                const patterns = [
                    'Works at', 'Worked at',
                    'Studied at', 'Studies at', 'Goes to', 'Went to',
                    'Lives in',
                    'From ',
                    'Married', 'Single', 'In a relationship', 'Engaged',
                    'Followed by',
                    'Joined '
                ];

                allSpans.forEach(span => {
                    const text = span.textContent.trim();
                    if (text.length > 0 && text.length < 200 && !seen.has(text)) {
                        for (const pattern of patterns) {
                            if (text.startsWith(pattern) || text.includes(pattern)) {
                                // Avoid matching parent elements that contain multiple items
                                if (span.children.length <= 2) {
                                    items.push(text);
                                    seen.add(text);
                                }
                                break;
                            }
                        }
                    }
                });

                return items;
            } catch(e) { return []; }
        """
        )
        if intro_items:
            self.profile_data["intro_items"] = intro_items
            print(f"📋 Got {len(intro_items)} intro items from DOM")

            for item in intro_items:
                print(f"   - {item}")
                item_lower = item.lower()

                if "works at" in item_lower or "worked at" in item_lower:
                    if "work" not in self.profile_data:
                        self.profile_data["work"] = []
                    self.profile_data["work"].append(item)
                elif any(
                    kw in item_lower
                    for kw in ["studied at", "studies at", "goes to", "went to"]
                ):
                    if "education" not in self.profile_data:
                        self.profile_data["education"] = []
                    self.profile_data["education"].append(item)
                elif "lives in" in item_lower:
                    self.profile_data["current_city"] = item
                elif item.startswith("From "):
                    self.profile_data["hometown"] = item

    def _extract_counts_from_dom(self):
        """Extract followers/friends counts from the DOM"""
        counts = self.driver.execute_script(
            """
            try {
                const result = {};

                // Check links for friends/followers
                const links = document.querySelectorAll('a[href*="friends"], a[href*="followers"]');
                links.forEach(link => {
                    const text = link.textContent.trim();
                    if (text.includes('friend')) {
                        const match = text.match(/([\\d,\\.KkMm]+)\\s*friend/i);
                        if (match) result.friends = match[1];
                    }
                    if (text.includes('follower')) {
                        const match = text.match(/([\\d,\\.KkMm]+)\\s*follower/i);
                        if (match) result.followers = match[1];
                    }
                });

                // Also check spans for standalone count text
                if (!result.followers || !result.friends) {
                    const spans = document.querySelectorAll('span');
                    spans.forEach(span => {
                        const text = span.textContent.trim();
                        if (!result.followers && text.match(/^[\\d,\\.]+[KkMm]?\\s+followers?$/)) {
                            const match = text.match(/([\\d,\\.KkMm]+)/);
                            if (match) result.followers = match[1];
                        }
                        if (!result.friends && text.match(/^[\\d,\\.]+[KkMm]?\\s+friends?$/)) {
                            const match = text.match(/([\\d,\\.KkMm]+)/);
                            if (match) result.friends = match[1];
                        }
                    });
                }

                return result;
            } catch(e) { return {}; }
        """
        )
        if counts:
            if counts.get("followers") and not self.profile_data.get("followers_count"):
                self.profile_data["followers_count_text"] = counts["followers"]
                print(f"👥 Got followers count from DOM: {counts['followers']}")
            if counts.get("friends") and not self.profile_data.get("friends_count"):
                self.profile_data["friends_count_text"] = counts["friends"]
                print(f"👥 Got friends count from DOM: {counts['friends']}")

    # ── About Page Scraping (GraphQL-based, Tab+Enter navigation) ───

    # Full set of known About page tab names (used for matching during Tab navigation)
    ALL_POSSIBLE_TAB_NAMES = [
        "Intro",
        "Personal details",
        "Work",
        "Education",
        "Hobbies",
        "Interests",
        "Travel",
        "Links",
        "Contact info",
        "Names",
    ]

    def _scrape_about_page(self):
        """Navigate to /about, Tab-press to find the first About sub-tab,
        click it to trigger a GraphQL response, discover available tabs from
        all_collections.nodes[], then Tab+Enter through remaining tabs.
        """
        about_url = self.target_url + "/about"
        print(f"\n📋 Navigating to About page: {about_url}")
        self.driver.get(about_url)
        wait_time = random.randint(4, 7)
        print(f"⏳ Waiting {wait_time}s for About page to load...")
        time.sleep(wait_time)

        # Drain existing performance logs so we start fresh
        try:
            self.driver.get_log("performance")
        except Exception:
            pass

        about_tabs: list = []
        available_tab_names: list = []  # Discovered dynamically

        # ─── Step 1: Tab-press to find the FIRST matching tab ───────────
        print("\n📋 Tab-pressing to find the first About tab...")
        first_tab_name = self._find_and_click_first_about_tab()

        if not first_tab_name:
            print("⚠️ Could not find any About tab via Tab navigation")
            self.profile_data["about_tabs"] = []
            return

        # Wait for GraphQL response from the clicked first tab
        wait_time = random.randint(3, 6)
        print(f"⏳ Waiting {wait_time}s for '{first_tab_name}' GraphQL response...")
        time.sleep(wait_time)

        # Extract tab data AND discover available tabs from all_collections
        first_tab_url = self.driver.current_url
        first_tab_data, discovered_tabs = self._extract_about_tab_with_discovery(
            first_tab_name, first_tab_url
        )

        if discovered_tabs:
            available_tab_names = [t["name"] for t in discovered_tabs if t.get("name")]
            self.profile_data["about_tab_listing"] = discovered_tabs
            print(f"📑 Discovered {len(available_tab_names)} available tabs: {available_tab_names}")
        else:
            # Fallback: if discovery failed, try all known tabs
            available_tab_names = list(self.ALL_POSSIBLE_TAB_NAMES)
            print("⚠️ Could not discover tabs from all_collections, using full known list")

        if first_tab_data and first_tab_data.sections:
            about_tabs.append(first_tab_data)
            section_count = len(first_tab_data.sections)
            field_count = sum(len(s.fields) for s in first_tab_data.sections)
            print(
                f"✅ Extracted first tab '{first_tab_name}': "
                f"{section_count} sections, {field_count} fields"
            )

        # Build the list of remaining tabs to visit (skip the already-processed first tab)
        remaining_tabs = [
            name for name in available_tab_names
            if name.strip().lower() != first_tab_name.strip().lower()
        ]
        print(f"📋 Remaining tabs to process: {remaining_tabs}")

        # ─── Step 2: Tab+Enter through each remaining available tab ───
        for tab_name in remaining_tabs:
            print(f"\n📋 Looking for '{tab_name}' tab via Tab-key navigation...")

            try:
                # Find and activate the tab using Tab+Enter
                found = self._find_and_click_about_tab(tab_name)
                if not found:
                    print(f"⚠️ Could not find '{tab_name}' tab element")
                    continue

                # Wait for GraphQL response to arrive
                wait_time = random.randint(3, 6)
                print(f"⏳ Waiting {wait_time}s for '{tab_name}' GraphQL response...")
                time.sleep(wait_time)

                # Extract GraphQL response from network logs
                tab_url = self.driver.current_url
                tab_data = self._extract_about_tab_from_network_logs(tab_name, tab_url)
                if tab_data:
                    about_tabs.append(tab_data)
                    section_count = len(tab_data.sections)
                    field_count = sum(len(s.fields) for s in tab_data.sections)
                    print(
                        f"✅ Extracted {tab_name}: {section_count} sections, {field_count} fields"
                    )
                else:
                    print(f"⚠️ No GraphQL data found for '{tab_name}' tab")

            except Exception as e:
                print(f"❌ Error scraping '{tab_name}' tab: {e}")

        self.profile_data["about_tabs"] = about_tabs

        # Update legacy flat fields from the structured about data
        self._update_legacy_fields_from_about_tabs(about_tabs)

        # Last resort: extract name from <title> tag if still missing or invalid
        current_name = self.profile_data.get("name")
        if not current_name or not self._is_valid_profile_name(current_name):
            self._extract_name_from_about_title()

        print(f"\n📊 About page scraping complete: {len(about_tabs)} tabs processed")

    def _extract_name_from_about_title(self):
        # Last-resort name extraction from the About page <title> tag.
        
        name = None

        # Raw HTML response from network logs 
        try:
            name = self._extract_title_from_about_html_response()
        except Exception as e:
            print(f"⚠️ Could not extract <title> from network HTML: {e}")

        # Fallback to document.title with cleanup
        if not name:
            try:
                title = self.driver.execute_script(
                    """
                    try {
                        return document.title || null;
                    } catch(e) { return null; }
                """
                )
                if title:
                    name = self._clean_title(title)
            except Exception as e:
                print(f"⚠️ Could not read document.title: {e}")

        if name and self._is_valid_profile_name(name):
            self.profile_data["name"] = name
            print(f"📝 Got name from About page <title>: {name}")
        else:
            print(f"⚠️ About page <title> did not yield a valid name")

    def _extract_title_from_about_html_response(self) -> Optional[str]:
        """Extract <title> from the raw HTML response of the GET /about request
        found in Chrome performance logs.
        """
        try:
            logs_raw = self.driver.get_log("performance")
            logs = [json.loads(lr["message"])["message"] for lr in logs_raw]

            for log in logs:
                if log["method"] != "Network.responseReceived":
                    continue

                resp_url = log["params"]["response"].get("url", "")
                mime_type = log["params"]["response"].get("mimeType", "")

                # Match the /about page HTML document response
                if "/about" not in resp_url or "text/html" not in mime_type:
                    continue

                request_id = log["params"]["requestId"]
                try:
                    response = self.driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    body = response.get("body", "")
                    if not body:
                        continue

                    # Parse <title>...</title> from the raw HTML
                    match = re.search(r"<title[^>]*>([^<]+)</title>", body, re.IGNORECASE)
                    if match:
                        raw_title = match.group(1).strip()
                        name = self._clean_title(raw_title)
                        if name:
                            print(f"📝 Found clean <title> from HTML response: {name}")
                            return name
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ Error reading network logs for HTML title: {e}")

        return None

    def _clean_title(self, title: str) -> Optional[str]:
        # Clean a raw page title by removing notification counts and Facebook suffixes.

        if not title:
            return None

        name = title.strip()

        # Strip leading notification count: (1) , (23) , (99+) , etc.
        name = re.sub(r"^\(\d+\+?\)\s*", "", name).strip()

        # Strip trailing Facebook suffixes
        for suffix in [" | Facebook", " - Facebook", " · Facebook"]:
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()
                break

        return name if name else None

    def _find_and_click_first_about_tab(self, max_tabs: int = 150) -> Optional[str]:
        """Tab-press through the About page to find the first element whose text
        matches ANY name in ALL_POSSIBLE_TAB_NAMES. Press Enter to activate it.
        """
        known_lower = {name.strip().lower(): name for name in self.ALL_POSSIBLE_TAB_NAMES}

        for i in range(max_tabs):
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.15)

            try:
                focused = self.driver.switch_to.active_element
                text = (focused.get_attribute("textContent") or "").strip()
                href = (focused.get_attribute("href") or "").strip()
                aria = (focused.get_attribute("aria-label") or "").strip()

                text_lower = text.lower()
                aria_lower = aria.lower()

                # Check exact match against any known tab name
                matched_name = known_lower.get(text_lower) or known_lower.get(aria_lower)
                if matched_name:
                    print(
                        f"🎯 Found first tab '{matched_name}' at tab press {i + 1} "
                        f"(text='{text[:60]}', href='{href[:80]}')"
                    )
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    print(f"▶️ Pressed Enter on '{matched_name}' tab")
                    return matched_name

                # Also check href for directory_ suffix pattern
                if href:
                    href_lower = href.lower()
                    for name_lower, name in known_lower.items():
                        dir_suffix = f"directory_{name_lower.replace(' ', '_')}"
                        if dir_suffix in href_lower:
                            print(
                                f"🎯 Found first tab '{name}' (via href) at tab press {i + 1} "
                                f"(text='{text[:60]}', href='{href[:80]}')"
                            )
                            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                            print(f"▶️ Pressed Enter on '{name}' tab")
                            return name

            except Exception:
                continue

        print(f"⚠️ No About tab found after {max_tabs} Tab presses")
        return None

    def _extract_about_tab_with_discovery(
        self, tab_name: str, tab_url: str
    ) -> tuple:
        """Extract about tab data AND discover available tabs from all_collections.

        Returns a tuple of (AboutTab or None, list of discovered tab dicts or []).
        Each discovered tab dict has keys: 'name', 'url'.
        """
        discovered_tabs: list = []
        tab_data: Optional[AboutTab] = None

        try:
            logs_raw = self.driver.get_log("performance")
            logs = [json.loads(lr["message"])["message"] for lr in logs_raw]

            for log in logs:
                if log["method"] != "Network.responseReceived":
                    continue
                if log["params"].get("type") == "Preflight":
                    continue

                request_id = log["params"]["requestId"]
                resp_url = log["params"]["response"]["url"]

                if "graphql" not in resp_url.lower():
                    continue
                if request_id in self.processed_requests:
                    continue
                self.processed_requests.add(request_id)

                try:
                    response_info = log["params"]["response"]
                    if response_info.get("status") != 200:
                        continue

                    response = self.driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    body = response.get("body", "")
                    if not body or "about_app_sections" not in body:
                        continue

                    # Parse using FIRST JSON object only
                    parsed_tab = self._parse_about_graphql(body, tab_name, tab_url)
                    if parsed_tab and parsed_tab.sections:
                        tab_data = parsed_tab

                    # Extract all_collections for tab discovery
                    first_json = None
                    try:
                        first_json = json.loads(body)
                    except json.JSONDecodeError:
                        for line in body.split("\n"):
                            line = line.strip()
                            if line and line.startswith("{"):
                                try:
                                    first_json = json.loads(line)
                                    break
                                except json.JSONDecodeError:
                                    continue

                    if first_json and not discovered_tabs:
                        user = first_json.get("data", {}).get("user", {})
                        about_sections = user.get("about_app_sections", {})
                        nodes = about_sections.get("nodes", [])
                        if nodes:
                            all_collections = nodes[0].get("all_collections", {})
                            all_coll_nodes = all_collections.get("nodes", [])
                            if all_coll_nodes:
                                discovered_tabs = [
                                    {"name": n.get("name", ""), "url": n.get("url", "")}
                                    for n in all_coll_nodes
                                    if n.get("name")
                                ]

                    # If we have both tab data and discovery, we can stop
                    if tab_data and discovered_tabs:
                        break

                except Exception as e:
                    if "No resource with given identifier found" not in str(e):
                        print(f"⚠️ Error processing about request {request_id}: {e}")

        except Exception as e:
            print(f"❌ Error extracting about tab with discovery: {e}")

        return (tab_data, discovered_tabs)

    def _find_and_click_about_tab(self, tab_name: str, max_tabs: int = 150) -> bool:
        """Use Tab key to find an About page tab link by its text, then press Enter.
        """
        tab_name_lower = tab_name.strip().lower()

        for i in range(max_tabs):
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.15)

            try:
                focused = self.driver.switch_to.active_element
                text = (focused.get_attribute("textContent") or "").strip()
                href = (focused.get_attribute("href") or "").strip()
                aria = (focused.get_attribute("aria-label") or "").strip()

                # Match by visible text or aria-label (exact, case-insensitive)
                text_lower = text.lower()
                aria_lower = aria.lower()

                if text_lower == tab_name_lower or aria_lower == tab_name_lower:
                    print(
                        f"🎯 Found '{tab_name}' at tab press {i + 1} "
                        f"(text='{text[:60]}', href='{href[:80]}')"
                    )
                    # Press Enter to activate the tab
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    print(f"▶️ Pressed Enter on '{tab_name}' tab")
                    return True

                # Also match if href contains the directory_ suffix
                dir_suffix = f"directory_{tab_name_lower.replace(' ', '_')}"
                if dir_suffix in href.lower():
                    print(
                        f"🎯 Found '{tab_name}' (via href) at tab press {i + 1} "
                        f"(text='{text[:60]}', href='{href[:80]}')"
                    )
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    print(f"▶️ Pressed Enter on '{tab_name}' tab")
                    return True

            except Exception:
                continue

        print(f"⚠️ '{tab_name}' tab not found after {max_tabs} Tab presses")
        return False

    def _extract_about_tab_from_network_logs(
        self, tab_name: str, tab_url: str
    ) -> Optional[AboutTab]:
        """Extract about tab data from GraphQL responses in Chrome performance logs."""
        try:
            logs_raw = self.driver.get_log("performance")
            logs = [json.loads(lr["message"])["message"] for lr in logs_raw]

            for log in logs:
                if log["method"] != "Network.responseReceived":
                    continue
                if log["params"].get("type") == "Preflight":
                    continue

                request_id = log["params"]["requestId"]
                resp_url = log["params"]["response"]["url"]

                if "graphql" not in resp_url.lower():
                    continue
                if request_id in self.processed_requests:
                    continue
                self.processed_requests.add(request_id)

                try:
                    response_info = log["params"]["response"]
                    if response_info.get("status") != 200:
                        continue

                    response = self.driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    body = response.get("body", "")
                    if not body or "about_app_sections" not in body:
                        continue

                    # Parse using FIRST JSON object only
                    tab_data = self._parse_about_graphql(body, tab_name, tab_url)
                    if tab_data and tab_data.sections:
                        return tab_data

                except Exception as e:
                    if "No resource with given identifier found" not in str(e):
                        print(f"⚠️ Error processing about request {request_id}: {e}")

        except Exception as e:
            print(f"❌ Error extracting about tab from logs: {e}")

        return None

    def _parse_about_graphql(
        self, response_body: str, tab_name: str, tab_url: str
    ) -> Optional[AboutTab]:
        """Parse GraphQL response for about page data.
        """
        # Extract FIRST JSON object only (skip subsequent lines)
        first_json = None
        try:
            first_json = json.loads(response_body)
        except json.JSONDecodeError:
            for line in response_body.split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    first_json = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if first_json is None:
            return None

        try:
            user = first_json.get("data", {}).get("user", {})
            if not user:
                return None

            # Extract profile_id if available
            if user.get("id") and not self.profile_data.get("profile_id"):
                self.profile_data["profile_id"] = user["id"]

            about_sections = user.get("about_app_sections", {})
            nodes = about_sections.get("nodes", [])
            if not nodes:
                return None

            about_node = nodes[0]
            active_collections = about_node.get("activeCollections", {})
            active_nodes = active_collections.get("nodes", [])
            if not active_nodes:
                return None

            active_collection = active_nodes[0]
            style_renderer = active_collection.get("style_renderer", {})
            profile_field_sections = style_renderer.get("profile_field_sections", [])

            tab = AboutTab(name=tab_name, url=tab_url, sections=[])

            for section_data in profile_field_sections:
                section = self._parse_profile_field_section(section_data)
                if section:
                    tab.sections.append(section)

            # Also extract all_collections to store tab listing metadata
            all_collections = about_node.get("all_collections", {})
            all_coll_nodes = all_collections.get("nodes", [])
            if all_coll_nodes and not self.profile_data.get("about_tab_listing"):
                self.profile_data["about_tab_listing"] = [
                    {"name": n.get("name"), "url": n.get("url")}
                    for n in all_coll_nodes
                ]

            return tab

        except Exception as e:
            print(f"⚠️ Error parsing about GraphQL for {tab_name}: {e}")
            return None

    def _parse_profile_field_section(self, section_data: dict) -> Optional[AboutSection]:
        """Parse a single profile_field_section from GraphQL response.

        Extracts: section_type, title.text, and all profile_fields nodes.
        """
        title_obj = section_data.get("title")
        section = AboutSection(
            section_type=section_data.get("field_section_type"),
            title=title_obj.get("text") if isinstance(title_obj, dict) else None,
            fields=[],
        )

        profile_fields = section_data.get("profile_fields", {})
        nodes = profile_fields.get("nodes", [])

        for field_node in nodes:
            parsed_field = self._parse_profile_field(field_node)
            if parsed_field:
                section.fields.append(parsed_field)

        return section

    def _parse_profile_field(self, field_node: dict) -> Optional[AboutField]:
        """Parse a single ProfileField node from GraphQL response.
        """
        title_obj = field_node.get("title", {}) or {}
        title_text = title_obj.get("text")

        parsed = AboutField(
            text=title_text,
            field_type=field_node.get("field_type"),
            entities=[],
            details=[],
            icon_url=None,
        )

        # Extract entities from title.ranges[].entity
        ranges = title_obj.get("ranges", []) or []
        for range_item in ranges:
            entity = range_item.get("entity")
            if entity and isinstance(entity, dict):
                parsed.entities.append(
                    AboutFieldEntity(
                        id=entity.get("id"),
                        name=entity.get("short_name"),
                        url=entity.get("url"),
                        profile_url=entity.get("profile_url"),
                        is_verified=entity.get("is_verified", False),
                        typename=entity.get("__typename"),
                    )
                )

        # Extract list_item_groups -> list_items -> text.text
        list_item_groups = field_node.get("list_item_groups", []) or []
        for group in list_item_groups:
            list_items = group.get("list_items", []) or []
            for item in list_items:
                text_obj = item.get("text")
                if isinstance(text_obj, dict) and text_obj.get("text"):
                    parsed.details.append(text_obj["text"])

        # Extract icon URL (skip inline SVG data URIs)
        icon = field_node.get("icon")
        if isinstance(icon, dict):
            uri = icon.get("uri", "")
            if uri and not uri.startswith("data:"):
                parsed.icon_url = uri

        return parsed

    def _update_legacy_fields_from_about_tabs(self, about_tabs: list):
        """Update the legacy flat profile_data fields from structured about tab data.

        This ensures backward compatibility: work, education, current_city, hometown,
        relationship_status, and bio are populated from the GraphQL about data.
        """
        for tab in about_tabs:
            for section in tab.sections:
                for f in section.fields:
                    ft = f.field_type
                    if not ft or not f.text:
                        continue

                    if ft == "bio":
                        if not self.profile_data.get("bio"):
                            self.profile_data["bio"] = f.text

                    elif ft == "work":
                        if "work" not in self.profile_data:
                            self.profile_data["work"] = []
                        if f.text not in self.profile_data["work"]:
                            self.profile_data["work"].append(f.text)

                    elif ft == "education":
                        if "education" not in self.profile_data:
                            self.profile_data["education"] = []
                        if f.text not in self.profile_data["education"]:
                            self.profile_data["education"].append(f.text)

                    elif ft == "current_city":
                        if not self.profile_data.get("current_city"):
                            self.profile_data["current_city"] = f.text

                    elif ft == "hometown":
                        if not self.profile_data.get("hometown"):
                            self.profile_data["hometown"] = f.text

                    elif ft in ("relationship", "relationship_status"):
                        if not self.profile_data.get("relationship_status"):
                            self.profile_data["relationship_status"] = f.text

    # ── Profile Building ──────────────────────────────────────────────

    def _build_profile(self) -> FacebookProfile:
        """Build a FacebookProfile dataclass from collected data"""
        profile = FacebookProfile(
            profile_id=self.profile_data.get("profile_id", ""),
            name=self.profile_data.get("name", ""),
            profile_url=self.target_url,
            profile_picture_url=self.profile_data.get("profile_picture_url"),
            cover_photo_url=self.profile_data.get("cover_photo_url"),
            bio=self.profile_data.get("bio"),
            category=self.profile_data.get("category"),
            followers_count=self.profile_data.get("followers_count"),
            friends_count=self.profile_data.get("friends_count"),
            work=self.profile_data.get("work", []),
            education=self.profile_data.get("education", []),
            current_city=self.profile_data.get("current_city"),
            hometown=self.profile_data.get("hometown"),
            relationship_status=self.profile_data.get("relationship_status"),
            intro_items=self.profile_data.get("intro_items", []),
            about_details=self.profile_data.get("about_details", {}),
            about_tabs=self.profile_data.get("about_tabs", []),
        )

        # Parse text-based counts if numeric counts weren't found from GraphQL
        if not profile.followers_count and self.profile_data.get(
            "followers_count_text"
        ):
            profile.followers_count = self._parse_count_text(
                self.profile_data["followers_count_text"]
            )
        if not profile.friends_count and self.profile_data.get("friends_count_text"):
            profile.friends_count = self._parse_count_text(
                self.profile_data["friends_count_text"]
            )

        return profile

    def _parse_count_text(self, text: str) -> Optional[int]:
        """Parse count text like '1.2K', '3M', '1,234' into an integer"""
        try:
            text = text.strip().replace(",", "")
            if text.lower().endswith("k"):
                return int(float(text[:-1]) * 1000)
            elif text.lower().endswith("m"):
                return int(float(text[:-1]) * 1000000)
            else:
                return int(float(text))
        except (ValueError, TypeError):
            return None

    # ── Media Downloads ───────────────────────────────────────────────

    def _download_media(self, profile: FacebookProfile):
        """Download profile picture and cover photo"""
        if profile.profile_picture_url:
            filename = f"profile_picture_{profile.profile_id or 'unknown'}.jpg"
            path = self._download_image(profile.profile_picture_url, filename)
            if path:
                profile.profile_picture_path = path

        if profile.cover_photo_url:
            filename = f"cover_photo_{profile.profile_id or 'unknown'}.jpg"
            path = self._download_image(profile.cover_photo_url, filename)
            if path:
                profile.cover_photo_path = path

    def _download_image(self, url: str, filename: str) -> Optional[str]:
        """Download an image and return the local file path"""
        try:
            file_path = os.path.join(self.profile_attachments_dir, filename)

            # Skip if already downloaded
            if os.path.exists(file_path):
                print(f"📸 Image already exists: {filename}")
                return file_path

            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"📸 Downloaded: {filename}")
            return file_path

        except Exception as e:
            print(f"❌ Error downloading {filename}: {e}")
            return None

    # ── JSON Output ───────────────────────────────────────────────────

    def _save_to_json(self, profile: FacebookProfile):
        """Save profile data to JSON files in both facebook_data and project output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_chars = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=6)
        )
        filename = f"profile_{timestamp}_{random_chars}.json"

        output_data = {
            "scraped_at": datetime.now().isoformat(),
            "profile": asdict(profile),
        }

        # Save to facebook_data output
        try:
            fb_output_dir = os.path.join(
                get_facebook_data_path(), "scraped_data_output", "profile"
            )
            os.makedirs(fb_output_dir, exist_ok=True)
            fb_output_path = os.path.join(fb_output_dir, filename)

            with open(fb_output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Profile saved to: {fb_output_path}")
        except Exception as e:
            print(f"❌ Error saving profile to facebook_data: {e}")

        # Also save to project root output/profile/ (absolute path)
        if self.is_save_inRoot:
            try:
                current_file = os.path.abspath(__file__)
                manual_dir = os.path.dirname(current_file)  # manual/profile/
                parent_dir = os.path.dirname(manual_dir)  # manual/
                project_root = os.path.dirname(parent_dir)  # facebook_scraper/
                
                project_output_dir = os.path.join(project_root, "output", "profile")
                os.makedirs(project_output_dir, exist_ok=True)
                project_output_path = os.path.join(project_output_dir, filename)

                with open(project_output_path, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                print(f"💾 Profile also saved to: {project_output_path}")
            except Exception as e:
                print(f"❌ Error saving profile to project output: {e}")
