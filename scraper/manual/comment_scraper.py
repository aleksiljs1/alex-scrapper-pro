import time
import os
import random
import json
import re
import requests
import threading
import atexit
from datetime import datetime, timezone
from typing import List, Optional
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import sys


# Custom exceptions for network monitoring
class NetworkError(Exception):
    """Raised when no response is received within timeout period"""

    pass


class InvalidResponse(Exception):
    """Raised when response doesn't contain valid comment data"""

    pass


class ErrorResponse(Exception):
    """Raised when response has non-200 status code"""

    pass


# Robust import handling for both local and package usage
try:
    # Try relative imports first (for package usage)
    from ..common.dataclasses import FacebookPost, Comment, Author, Reactions
    from ..common.utils import setup_directories
    from ..common.request_tracker_server import run_server
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    from common.dataclasses import FacebookPost, Comment, Author, Reactions
    from common.utils import setup_directories
    from common.request_tracker_server import run_server


# Reaction ID mapping based on mapping.txt
REACTION_ID_MAPPING = {
    "115940658764963": "haha",
    "444813342392137": "angry",
    "1635855486666999": "like",
    "1678524932434102": "love",
    "613557422527858": "care",
    "908563459236466": "sad",
    "478547315650144": "wow",
}


class TabBasedCommentScraper:
    """Tab-based comment scraper that navigates through comments using Tab key"""

    def __init__(
        self,
        driver,
        target_url: str,
        scrape_comments_type: str = "All comments",
        facebook_post_data: Optional[dict] = None,
        use_server_tracking: bool = True,
        server_port: int = 3103,
        comment_limit: int = -1,
        scrape_till_datetime: Optional[datetime] = None,
    ):
        # Validate scrape_comments_type
        valid_types = ["All comments", "Newest", "Most relevant"]
        if scrape_comments_type not in valid_types:
            raise ValueError(
                f"Invalid scrape_comments_type '{scrape_comments_type}'. Must be one of: {valid_types}"
            )

        self.driver = driver
        self.target_url = target_url
        self.scrape_comments_type = scrape_comments_type
        self.facebook_post_data = facebook_post_data or {}
        self.scraped_comments: List[Comment] = []
        self.comment_counter = 0
        self.screenshot_path: Optional[str] = (
            None  # Store screenshot path for FacebookPost
        )
        self.use_server_tracking = use_server_tracking
        self.server_port = server_port
        self.tracker_server_url = f"http://localhost:{server_port}"
        self.server_thread = None
        self.comment_limit = comment_limit
        self.scrape_till_datetime = scrape_till_datetime

        # Start FastAPI server if enabled
        if self.use_server_tracking:
            self._start_tracker_server()

        # Request blocking setup
        self.blocked_request_count = 0

        # Comment counting for timing delays
        self.comment_count = 0  # Count of comments (Like element resets)
        self.comments_threshold = (
            5  # Dynamic threshold starting at 5, increases by 10 after each End press
        )

        # scrape_comments_type counter  for video link stop condition (stop after second scrape_comments_type)
        self.scrape_comments_type_counter = 0

        # comment button counter for live video link stop condition (stop after second comment button)
        self.comment_button_counter = 0
        # share button counter for live video link stop condition (stop after second share button)
        self.share_button_counter = 0

        # Tabs since last Like counter for universal stop condition (stop after 200 tabs without Like)
        self.tabs_since_last_like = 0  # Count of tabs since last "Like" element found

        # Store first Share element for videos (click after Most relevant actions)
        self.first_share_element = None  # Store the first Share element for videos

        # Store last Reply element for all post types (used after View replies actions)
        self.last_reply_element = None  # Store the last "Reply" element encountered

        # Detect URL type (reel, video, or regular post)
        self.is_reel_url = self._is_reel_url(target_url)
        self.is_video_url = self._is_video_url(target_url)
        self.is_live_video_url = False  # Will be set after page loads using driver's current URL

        if self.is_reel_url:
            print(f"🎬 Detected reel URL - will use reel-specific scraping approach")
        elif self.is_video_url:
            print(f"🎥 Detected video URL - will use video-specific scraping approach")
        else:
            print(
                f"📰 Detected regular/group post URL - will use standard scraping approach"
            )

        print(f"🎯 Comment type to scrape: '{self.scrape_comments_type}'")

        # Setup directories using global facebook_data structure
        self.facebook_data_base = setup_directories()
        self.base_dir = self.facebook_data_base

        # For immediate parent-child mapping
        self.node_id_to_comment = {}  # Map from internal_node_id to comment for immediate lookup

        # JavaScript request blocking will be enabled after page load

    def _start_tracker_server(self):
        """Start the FastAPI server in a background thread"""
        try:
            print(f"🚀 Starting FastAPI tracker server on port {self.server_port}...")

            # Import and start server

            self.server_thread = threading.Thread(
                target=run_server, args=("localhost", self.server_port), daemon=True
            )
            self.server_thread.start()

            # Wait for server to start
            max_retries = 10
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.tracker_server_url}/health")
                    if response.status_code == 200:
                        print(
                            f"✅ FastAPI tracker server started successfully on port {self.server_port}"
                        )
                        break
                except:
                    time.sleep(0.5)
            else:
                print("⚠️ Could not verify server startup, but continuing anyway")

        except Exception as e:
            print(f"⚠️ Could not start FastAPI tracker server: {e}")
            print("⚠️ Falling back to JavaScript-only tracking")
            self.use_server_tracking = False

    def _enable_request_blocking_js(self):
        """Enable request blocking and response tracking using JavaScript injection to override fetch/XMLHttpRequest"""
        try:
            if self.use_server_tracking:
                print(
                    "🚫 Enabling JavaScript-based request blocking with FastAPI server..."
                )
                # Use server-based tracking
                self._enable_server_based_tracking_js()
            else:
                print(
                    "🚫 Enabling JavaScript-based request blocking and response tracking..."
                )
                # Use original JavaScript-only tracking
                self._enable_original_js_tracking()

        except Exception as e:
            print(f"❌ Error enabling JavaScript request blocking: {e}")
            print(
                "⚠️ Continuing without request blocking - tooltip queries may cause rate limiting"
            )

    def _enable_server_based_tracking_js(self):
        """Enable JavaScript tracking that sends data to FastAPI server"""
        try:
            # Read the JavaScript client code
            current_dir = os.path.dirname(os.path.abspath(__file__))
            js_file_path = os.path.join(
                current_dir, "request_tracker_client_comments.js"
            )

            if os.path.exists(js_file_path):
                with open(js_file_path, "r") as f:
                    js_code = f.read()

                # Update the server URL in the JavaScript code
                js_code = (
                    f"const TRACKER_SERVER_URL = '{self.tracker_server_url}'\n"
                    + js_code
                )

                # Inject the JavaScript code
                self.driver.execute_script(js_code)
                print(
                    "✅ JavaScript-based request blocking with FastAPI server enabled successfully"
                )
            else:
                print(
                    "⚠️ request_tracker_client_comments.js not found, falling back to original tracking"
                )
                self.use_server_tracking = False
                self._enable_original_js_tracking()

        except Exception as e:
            print(f"⚠️ Error enabling server-based tracking: {e}")
            print("⚠️ Falling back to original JavaScript tracking")
            self.use_server_tracking = False
            self._enable_original_js_tracking()

    def _enable_original_js_tracking(self):
        """Enable original JavaScript-only tracking (fallback)"""
        try:
            # JavaScript code to override fetch and XMLHttpRequest
            js_code = """
                window.scraperBotTrackedResponses = [];
                window.scraperBotResponseCount = 0;

                window.scraperBotWaitForRequest = function (
                requestType,
                startTimeMs,
                detectionTimeoutMs,
                totalTimeoutMs,
                ) {
                return new Promise((resolve, reject) => {
                    let detectionPhaseEnd = startTimeMs + detectionTimeoutMs;
                    let totalTimeoutEnd = startTimeMs + totalTimeoutMs;
                    let targetRequest = null;
                    let requestDetected = false;

                    // Phase 1: Detection phase
                    function checkForRequest() {
                    let currentTime = Date.now();
                    let pendingRequests = window.scraperBotPendingRequests || [];

                    // Look for recent request of specified type
                    for (let i = pendingRequests.length - 1; i >= 0; i--) {
                        let request = pendingRequests[i];
                        if (
                        request &&
                        request.type === requestType &&
                        request.timestamp >= startTimeMs
                        ) {
                        targetRequest = request;
                        requestDetected = true;
                        console.log(
                            "✅ " + requestType + " request detected (ID: " + request.id + ")",
                        );
                        break;
                        }
                    }

                    if (requestDetected) {
                        // Move to Phase 2: Wait for completion
                        waitForCompletion();
                        return;
                    }

                    if (currentTime < detectionPhaseEnd) {
                        // Continue checking for request
                        setTimeout(checkForRequest, 200);
                    } else {
                        // No request detected in detection phase
                        console.log(
                        "ℹ️ No " +
                        requestType +
                        " request triggered - likely no more content to load",
                        );
                        resolve({ success: true, reason: "no_request_needed" });
                    }
                    }

                    // Phase 2: Wait for completion
                    function waitForCompletion() {
                    let currentTime = Date.now();
                    let pendingRequests = window.scraperBotPendingRequests || [];

                    // Find our target request
                    let currentTarget = null;
                    for (let i = pendingRequests.length - 1; i >= 0; i--) {
                        let request = pendingRequests[i];
                        if (request && request.id === targetRequest.id) {
                        currentTarget = request;
                        break;
                        }
                    }

                    if (currentTarget) {
                        if (currentTarget.completed) {
                        // Request completed, validate response
                        if (currentTarget.status !== 200) {
                            reject({
                            type: "ErrorResponse",
                            message:
                                "Non-200 response for " +
                                requestType +
                                ": status " +
                                currentTarget.status +
                                " (request: " +
                                currentTarget.id +
                                ")",
                            });
                            return;
                        }

                        if (!currentTarget.isValid) {
                            reject({
                            type: "InvalidResponse",
                            message:
                                "No valid response found for " +
                                requestType +
                                " (request: " +
                                currentTarget.id +
                                ")",
                            });
                            return;
                        }

                        console.log(
                            "✅ " +
                            requestType +
                            " request completed successfully (request: " +
                            currentTarget.id +
                            ")",
                        );
                        resolve({
                            success: true,
                            reason: "completed",
                            requestId: currentTarget.id,
                        });
                        return;
                        }
                    }

                    if (currentTime < totalTimeoutEnd) {
                        // Continue waiting
                        setTimeout(waitForCompletion, 500);
                    } else {
                        // Timeout reached
                        let requestId = targetRequest ? targetRequest.id : "unknown";
                        reject({
                        type: "NetworkError",
                        message:
                            "Request " +
                            requestType +
                            " (ID: " +
                            requestId +
                            ") did not complete within timeout",
                        });
                    }
                    }

                    // Start the detection phase
                    checkForRequest();
                });
                };

                // Override XMLHttpRequest
                const originalXHROpen = XMLHttpRequest.prototype.open;
                const originalXHRSend = XMLHttpRequest.prototype.send;

                XMLHttpRequest.prototype.open = function (method, url, ...args) {
                this._scraperBotUrl = url;
                this._scraperBotMethod = method;
                return originalXHROpen.apply(this, [method, url, ...args]);
                };

                XMLHttpRequest.prototype.send = function (data) {
                // Check if it's a GraphQL POST request
                if (
                    this._scraperBotUrl &&
                    this._scraperBotUrl.includes("/api/graphql/") &&
                    this._scraperBotMethod === "POST" &&
                    data
                ) {
                    let bodyStr = "";
                    if (typeof data === "string") {
                    bodyStr = data;
                    }

                    // Debug: Log all XHR GraphQL request bodies and check for fb_api_req_friendly_name patterns
                    console.log(
                    "🔍 DEBUG: XHR GraphQL request body preview: " +
                    bodyStr.substring(0, 200) +
                    "...",
                    );

                    // Enhanced debugging for fb_api_req_friendly_name detection
                    if (bodyStr.includes("fb_api_req_friendly_name")) {
                    console.log("🎯 DEBUG: Found fb_api_req_friendly_name in request body!");
                    const friendlyNameMatch = bodyStr.match(
                        /fb_api_req_friendly_name[:\s]*([^&\s,}]+)/,
                    );
                    if (friendlyNameMatch) {
                        console.log(
                        "🏷️ DEBUG: fb_api_req_friendly_name value: " + friendlyNameMatch[1],
                        );
                    }
                    } else if (bodyStr.includes("friendly_name")) {
                    console.log(
                        '🔍 DEBUG: Found "friendly_name" (without fb_api_req_ prefix) in request',
                    );
                    const friendlyMatch = bodyStr.match(/friendly_name[:\s]*([^&\s,}]+)/);
                    if (friendlyMatch) {
                        console.log("🏷️ DEBUG: friendly_name value: " + friendlyMatch[1]);
                    }
                    } else if (
                    bodyStr.includes("CommentsListComponentsPaginationQuery") ||
                    bodyStr.includes("CommentListComponentsRootQuery") ||
                    bodyStr.includes("Depth1CommentsListPaginationQuery") ||
                    bodyStr.includes("Depth2CommentsListPaginationQuery")
                    ) {
                    console.log("🎯 DEBUG: Found comment query name directly in request!");
                    }

                    // Check for tooltip query or hovercard query (block these)
                    if (bodyStr.includes("CometUFICommentReactionIconTooltipContentQuery")) {
                    this.abort();
                    return;
                    } else if (bodyStr.includes("CometHovercardQueryRendererQuery")) {
                    this.abort();
                    return;
                    } else if (bodyStr.includes("CometUFIConversationGuideContainerQuery")) {
                    this.abort();
                    return;
                    }

                    // Track specific comment-related requests based on fb_api_req_friendly_name (multiple formats)
                    let requestType = null;

                    // Check for various formats of CommentsListComponentsPaginationQuery
                    if (
                    bodyStr.includes(
                        "fb_api_req_friendly_name:CommentsListComponentsPaginationQuery",
                    ) ||
                    bodyStr.includes(
                        "fb_api_req_friendly_name%3ACommentsListComponentsPaginationQuery",
                    ) ||
                    bodyStr.includes("CommentsListComponentsPaginationQuery")
                    ) {
                    requestType = "VIEW_MORE_COMMENTS";
                    console.log("🎯 DEBUG: Detected VIEW_MORE_COMMENTS request");
                    }
                    // Check for various formats of CommentListComponentsRootQuery
                    else if (
                    bodyStr.includes(
                        "fb_api_req_friendly_name:CommentListComponentsRootQuery",
                    ) ||
                    bodyStr.includes(
                        "fb_api_req_friendly_name%3ACommentListComponentsRootQuery",
                    ) ||
                    bodyStr.includes("CommentListComponentsRootQuery")
                    ) {
                    requestType = "COMMENT_SORT_CHANGE";
                    console.log("🎯 DEBUG: Detected COMMENT_SORT_CHANGE request");
                    }
                    // Check for various formats of Depth1CommentsListPaginationQuery
                    else if (
                    bodyStr.includes(
                        "fb_api_req_friendly_name:Depth1CommentsListPaginationQuery",
                    ) ||
                    bodyStr.includes(
                        "fb_api_req_friendly_name%3ADepth1CommentsListPaginationQuery",
                    ) ||
                    bodyStr.includes("Depth1CommentsListPaginationQuery")
                    ) {
                    requestType = "VIEW_REPLIES_DEPTH1";
                    console.log("🎯 DEBUG: Detected VIEW_REPLIES_DEPTH1 request");
                    }
                    // Check for various formats of Depth2CommentsListPaginationQuery
                    else if (
                    bodyStr.includes(
                        "fb_api_req_friendly_name:Depth2CommentsListPaginationQuery",
                    ) ||
                    bodyStr.includes(
                        "fb_api_req_friendly_name%3ADepth2CommentsListPaginationQuery",
                    ) ||
                    bodyStr.includes("Depth2CommentsListPaginationQuery")
                    ) {
                    requestType = "VIEW_REPLIES_DEPTH2";
                    console.log("🎯 DEBUG: Detected VIEW_REPLIES_DEPTH2 request");
                    }

                    if (requestType) {
                    console.log(
                        "📡 Scraper Bot tracking " + requestType + " GraphQL request...",
                    );

                    // Initialize pending requests tracking if not exists
                    if (!window.scraperBotPendingRequests) {
                        window.scraperBotPendingRequests = [];
                    }

                    // Generate unique request ID
                    const requestId =
                        "req_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);

                    // Store pending request
                    const pendingRequest = {
                        id: requestId,
                        type: requestType,
                        url: this._scraperBotUrl,
                        requestBody: bodyStr,
                        timestamp: Date.now(),
                        completed: false,
                        response: null,
                    };
                    window.scraperBotPendingRequests.push(pendingRequest);

                    if (window.scraperBotPendingRequests.length > 100) {
                        window.scraperBotPendingRequests[0] = null;
                        window.scraperBotPendingRequests.shift(); // Remove oldest
                    }

                    // Store request info for response tracking
                    this._scraperBotRequestId = requestId;
                    this._scraperBotRequestType = requestType;
                    this._scraperBotRequestBody = bodyStr;
                    this._scraperBotRequestUrl = this._scraperBotUrl;

                    console.log(
                        "🔄 Created pending request: " + requestId + " (" + requestType + ")",
                    );

                    // Set up response handler
                    const originalOnReadyStateChange = this.onreadystatechange;
                    this.onreadystatechange = function () {
                        // Call original handler first
                        if (originalOnReadyStateChange) {
                        originalOnReadyStateChange.apply(this, arguments);
                        }

                        // Check if request is complete
                        if (this.readyState === 4) {
                        try {
                            // Find the pending request
                            const pendingIndex = window.scraperBotPendingRequests.findIndex(
                            (req) => req.id === this._scraperBotRequestId,
                            );
                            if (pendingIndex !== -1) {
                            const pending = window.scraperBotPendingRequests[pendingIndex];
                            pending.completed = true;
                            pending.status = this.status;
                            pending.responseBody = this.responseText;
                            pending.completedAt = Date.now();

                            if (this.status === 200) {
                                // Validate response content
                                const responseText = this.responseText || "";
                                const hasValidContent =
                                responseText.includes("comment") ||
                                responseText.includes("Comment") ||
                                responseText.includes("feedback") ||
                                responseText.includes("Feedback") ||
                                responseText.includes('__typename":"Feedback"');

                                pending.isValid = hasValidContent;

                                if (hasValidContent) {
                                window.scraperBotResponseCount++;
                                const responseData = {
                                    id: window.scraperBotResponseCount,
                                    requestId: this._scraperBotRequestId,
                                    requestType: this._scraperBotRequestType,
                                    url: this._scraperBotRequestUrl,
                                    requestBody: this._scraperBotRequestBody,
                                    responseBody: this.responseText,
                                    status: this.status,
                                    timestamp: Date.now(),
                                };

                                // Store response data (keep only last 100 to avoid memory issues)
                                window.scraperBotTrackedResponses.push(responseData);
                                if (window.scraperBotTrackedResponses.length > 100) {
                                    window.scraperBotTrackedResponses[0] = null;
                                    window.scraperBotTrackedResponses.shift(); // Remove oldest
                                }

                                console.log(
                                    "✅ Valid response for " +
                                    this._scraperBotRequestType +
                                    " request #" +
                                    this._scraperBotRequestId,
                                );
                                } else {
                                console.log(
                                    "❌ Invalid response for " +
                                    this._scraperBotRequestType +
                                    " request #" +
                                    this._scraperBotRequestId +
                                    " (no comment data)",
                                );
                                }
                            } else {
                                pending.isValid = false;
                                console.log(
                                "❌ Error response for " +
                                this._scraperBotRequestType +
                                " request #" +
                                this._scraperBotRequestId +
                                " (status: " +
                                this.status +
                                ")",
                                );
                            }
                            }
                        } catch (err) {
                            console.log(
                            "⚠️ Error processing response for request #" +
                            this._scraperBotRequestId +
                            ":",
                            err,
                            );
                        }
                        }
                    };
                    }
                }

                // Continue with normal requests
                return originalXHRSend.apply(this, [data]);
                };

                console.log(
                "✅ Scraper Bot request blocking enabled - will block Reaction Count tooltips & Profile Summary views",
                );
            """

            # Inject the JavaScript code
            self.driver.execute_script(js_code)
            print(
                "✅ JavaScript-based request blocking and response tracking enabled successfully"
            )

        except Exception as e:
            print(f"❌ Error enabling JavaScript request blocking: {e}")
            print(
                "⚠️ Continuing without request blocking - tooltip queries may cause rate limiting"
            )

    def _enable_form_removal_js(self):
        """Enable JavaScript injection to continuously remove form elements from DOM"""
        try:
            print("🗑️ Enabling continuous JavaScript-based form removal...")

            # JavaScript code to continuously remove form elements
            js_code = """
            
            // Function to remove all form elements from DOM
            function removeAllForms() {
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    try {
                        form.remove();
                    } catch (e) {
                        // Continue if removal fails
                    }
                });
            }
            
            // Set up MutationObserver to watch for new form elements
            const observer = new MutationObserver(function(mutations) {
                let hasNewForms = false;
                
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                // Check if the added node is a form or contains forms
                                if (node.tagName === 'FORM' || node.querySelector && node.querySelector('form')) {
                                    hasNewForms = true;
                                }
                            }
                        });
                    }
                });
                
                // If new forms were detected, remove them immediately
                if (hasNewForms) {
                    console.log('🎯 Scraper Bot detected new form elements in DOM - removing immediately');
                    removeAllForms();
                }
            });
            
            // Start observing the document for changes
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            // Also set up continuous polling as backup (every 100ms)
            setInterval(function() {
                const forms = document.querySelectorAll('form');
                if (forms.length > 0) {
                    removeAllForms();
                }
            }, 100);
            
            // Add global keydown listener to detect Enter key presses and remove forms immediately
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' || event.keyCode === 13) {
                    console.log('🎯 Scraper Bot detected Enter key press - removing forms immediately');
                    
                    // Remove forms immediately
                    removeAllForms();
                    
                    // Also remove forms after delays to catch any that load later
                    setTimeout(removeAllForms, 100);
                    setTimeout(removeAllForms, 300);
                    setTimeout(removeAllForms, 500);
                    setTimeout(removeAllForms, 1000);
                }
            });
            
            // Remove any existing forms immediately
            removeAllForms();
            
            // Also create a manual function that can be called from Python
            window.scraperBotRemoveForms = removeAllForms;
            
            console.log('✅ Scraper Bot continuous form removal system enabled - forms will be removed immediately');
            """

            # Inject the JavaScript code
            self.driver.execute_script(js_code)
            print("✅ JavaScript-based continuous form removal enabled successfully")

        except Exception as e:
            print(f"❌ Error enabling JavaScript form removal: {e}")
            print("⚠️ Continuing without form removal - forms may remain in DOM")

    def _get_tracked_responses_from_js(self):
        """Get tracked responses from JavaScript global variables or server"""
        try:
            if self.use_server_tracking:
                # Get from FastAPI server
                response = requests.get(f"{self.tracker_server_url}/responses")
                if response.status_code == 200:
                    return response.json()
                return []
            else:
                # Get from JavaScript (original method)
                responses = self.driver.execute_script("""
                    return window.scraperBotTrackedResponses || [];
                """)

                # Clear the JavaScript array to avoid re-processing
                self.driver.execute_script("""
                    window.scraperBotTrackedResponses = [];
                """)

                return responses
        except Exception as e:
            print(f"❌ Error getting tracked responses: {e}")
            return []

    def _process_js_tracked_responses(self):
        """Process responses captured by JavaScript fetch override or server"""
        try:
            responses = self._get_tracked_responses_from_js()

            if not responses:
                return

            source = (
                "server-tracked" if self.use_server_tracking else "JavaScript-captured"
            )
            print(f"📨 Processing {len(responses)} {source} responses...")

            for response_data in responses:
                response_body = response_data.get("responseBody", "")
                response_url = response_data.get("url", "")
                response_id = response_data.get("id", "unknown")
                status = response_data.get("status", 0)

                if response_body and status == 200:
                    print(f"📝 Processing {source} response #{response_id}")
                    # Use the existing _process_response method
                    self._process_response(response_body, response_url)
                elif status != 200:
                    print(
                        f"⚠️ Skipping {source} response #{response_id} - status: {status}"
                    )
                else:
                    print(f"⚠️ Skipping {source} response #{response_id} - empty body")

        except Exception as e:
            print(f"❌ Error processing tracked responses: {e}")

    def _wait_for_request_completion(
        self, request_type: str, timeout_seconds: int = 60
    ):
        """Wait for a specific request type to complete and validate its response"""
        try:
            print(
                f"⏳ Waiting for {request_type} request to complete (timeout: {timeout_seconds}s)..."
            )
            start_time = time.time()
            start_time_ms = int(start_time * 1000)  # Convert to milliseconds

            if self.use_server_tracking:
                # Use FastAPI server for waiting
                return self._wait_for_request_via_server(
                    request_type, start_time_ms, timeout_seconds
                )
            else:
                # Use original JavaScript method
                return self._wait_for_request_via_js(
                    request_type, start_time_ms, timeout_seconds
                )

        except (NetworkError, InvalidResponse, ErrorResponse):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            print(f"❌ Error waiting for {request_type} request: {e}")
            raise NetworkError(f"Error waiting for {request_type} request: {e}")

    def _wait_for_request_via_server(
        self, request_type: str, start_time_ms: int, timeout_seconds: int
    ):
        """Wait for request completion using FastAPI server"""
        try:
            params = {
                "request_type": request_type,
                "start_time_ms": start_time_ms,
                "detection_timeout_ms": 2000,
                "total_timeout_ms": timeout_seconds * 1000,
            }

            response = requests.post(f"{self.tracker_server_url}/wait", params=params)

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    if result.get("reason") == "no_request_needed":
                        print(
                            f"ℹ️ No {request_type} request triggered - likely no more content to load"
                        )
                        return True
                    elif result.get("reason") == "completed":
                        print(f"✅ {request_type} request completed successfully")
                        return True
                else:
                    error = result.get("error", {})
                    error_type = error.get("type", "UnknownError")
                    error_message = error.get("message", "Unknown error")

                    if error_type == "ErrorResponse":
                        raise ErrorResponse(error_message)
                    elif error_type == "InvalidResponse":
                        raise InvalidResponse(error_message)
                    elif error_type == "NetworkError":
                        raise NetworkError(error_message)
                    else:
                        raise Exception(error_message)
            else:
                raise NetworkError(
                    f"Failed to communicate with tracker server: {response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Server communication error: {e}")
            raise NetworkError(f"Failed to communicate with tracker server: {e}")

    def _wait_for_request_via_js(
        self, request_type: str, start_time_ms: int, timeout_seconds: int
    ):
        """Wait for request completion using JavaScript (original method)"""
        detection_timeout_ms = 2000
        total_timeout_ms = timeout_seconds * 1000

        print(
            f"🔍 Phase 1: Checking if {request_type} request is triggered (waiting 2s)..."
        )

        result = self.driver.execute_async_script(
            f"""
            var requestType = arguments[0];
            var startTimeMs = arguments[1];
            var detectionTimeoutMs = arguments[2];
            var totalTimeoutMs = arguments[3];
            var callback = arguments[4];

            window.scraperBotWaitForRequest(requestType, startTimeMs, detectionTimeoutMs, totalTimeoutMs)
                .then(function(result) {{
                    callback({{ success: true, data: result }});
                }})
                .catch(function(error) {{
                    callback({{ success: false, error: error }});
                }});
        """,
            request_type,
            start_time_ms,
            detection_timeout_ms,
            total_timeout_ms,
        )

        # Handle the result
        if result.get("success"):
            data = result.get("data", {})
            if data.get("reason") == "no_request_needed":
                print(
                    f"ℹ️ No {request_type} request triggered - likely no more content to load, continuing..."
                )
                return True
            elif data.get("reason") == "completed":
                print(
                    f"✅ {request_type} request completed successfully (request: {data.get('requestId', 'unknown')})"
                )
                return True
        else:
            error = result.get("error", {})
            error_type = error.get("type", "UnknownError")
            error_message = error.get("message", "Unknown error occurred")

            if error_type == "ErrorResponse":
                raise ErrorResponse(error_message)
            elif error_type == "InvalidResponse":
                raise InvalidResponse(error_message)
            elif error_type == "NetworkError":
                raise NetworkError(error_message)
            else:
                raise Exception(error_message)

    def _wait_for_view_more_comments(self, timeout_seconds: int = 60):
        """Wait for VIEW_MORE_COMMENTS request to complete"""
        return self._wait_for_request_completion("VIEW_MORE_COMMENTS", timeout_seconds)

    def _wait_for_comment_sort_change(self, timeout_seconds: int = 60):
        """Wait for COMMENT_SORT_CHANGE request to complete"""
        return self._wait_for_request_completion("COMMENT_SORT_CHANGE", timeout_seconds)

    def _wait_for_view_replies_depth1(self, timeout_seconds: int = 60):
        """Wait for VIEW_REPLIES_DEPTH1 request to complete"""
        return self._wait_for_request_completion("VIEW_REPLIES_DEPTH1", timeout_seconds)

    def _wait_for_view_replies_depth2(self, timeout_seconds: int = 60):
        """Wait for VIEW_REPLIES_DEPTH2 request to complete"""
        return self._wait_for_request_completion("VIEW_REPLIES_DEPTH2", timeout_seconds)

    def _focus_on_stored_reply_element(self):
        """Focus on the stored last Reply element after View replies actions"""
        try:
            if self.last_reply_element:
                print("🎯 Focusing on stored last 'Reply' element...")
                # Use JavaScript to focus on the element
                self.driver.execute_script(
                    "arguments[0].focus();", self.last_reply_element
                )
                time.sleep(0.1)
                print("✅ Successfully focused on stored Reply element")
                return True
            else:
                print(
                    "⚠️ No stored Reply element found - falling back to Shift+Tab method"
                )
                # Fallback: Press Shift+Tab 3 times if no stored Reply element
                for i in range(3):
                    ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(
                        Keys.TAB
                    ).key_up(Keys.SHIFT).perform()
                    time.sleep(0.1)
                return False
        except Exception as e:
            print(f"❌ Error focusing on stored Reply element: {e}")
            print("⚠️ Falling back to Shift+Tab method")
            # Fallback: Press Shift+Tab 3 times on error
            try:
                for i in range(3):
                    ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(
                        Keys.TAB
                    ).key_up(Keys.SHIFT).perform()
                    time.sleep(0.1)
            except Exception as fallback_error:
                print(f"❌ Fallback Shift+Tab also failed: {fallback_error}")
            return False

    def _is_reel_url(self, url: str) -> bool:
        """Check if URL is for reel content (reel after facebook.com)"""
        url_lower = url.lower()

        # Check for /reel/ pattern in URL
        if "/reel/" in url_lower:
            print(f"🎬 Reel URL detected - found '/reel/' in URL")
            return True

        print(f"📱 Not a reel URL - no '/reel/' pattern found")
        return False

    def _is_video_url(self, url: str) -> bool:
        """Check if URL is for video content (video, videos, watch) - excludes reels"""
        url_lower = url.lower()

        # Skip if it's already identified as a reel
        if "/reel/" in url_lower:
            return False

        video_indicators = ["/video/", "/videos/", "watch"]

        # Debug logging to see what's being detected
        for indicator in video_indicators:
            if indicator in url_lower:
                print(f"🎥 Video URL detected - found indicator: '{indicator}' in URL")
                return True

        print(f"📰 Regular post URL detected - no video indicators found")
        return False

    def _is_live_video_url(self) -> bool:
        """Check if URL is for live video content - uses driver's current URL"""
        url_lower = self.driver.current_url.lower()

        video_indicators = ["watch/live/?ref=watch_permalink&v="]

        # Debug logging to see what's being detected
        for indicator in video_indicators:
            if indicator in url_lower:
                print(f"🎥 Live Video URL detected - found indicator: '{indicator}' in URL")
                return True

        print(f"📰 No live video indicators found")
        return False

    def scrape_facebook_comments(self) -> FacebookPost:
        """Main method to scrape comments using tab-based navigation"""
        try:
            mode = (
                "with server tracking"
                if self.use_server_tracking
                else "with JavaScript-only tracking"
            )
            print(
                f"🎯 Starting tab-based comment scraping {mode} for: {self.target_url}"
            )

            # Log scraping limits
            if self.comment_limit != -1:
                print(f"📊 Comment limit: {self.comment_limit} comments")
            else:
                print(f"📊 Comment limit: Unlimited")

            if self.scrape_till_datetime is not None:
                print(f"📅 Scraping until datetime: {self.scrape_till_datetime}")
            else:
                print(f"📅 Datetime limit: None")

            # Navigate to URL and do initial setup
            self.driver.get(self.target_url)
            self._wait_and_log("Page load", 3, 8)

            # Check for live video URL after page loads (uses driver's current URL)
            self.is_live_video_url = self._is_live_video_url()

            # Enable JavaScript-based request blocking after page loads
            self._enable_request_blocking_js()

            # Enable form removal JavaScript injection
            self._enable_form_removal_js()

            # Capture screenshot after page load but before scraping starts
            self._capture_initial_screenshot()

            most_relevant_found = None
            # Execute appropriate initial loading sequence based on URL type
            if self.is_reel_url:
                print("🎬 Executing reel-specific initial loading sequence...")
                most_relevant_found = self._execute_initial_reel_loading()
            else:
                print("🔍 Executing initial comment loading sequence...")
                most_relevant_found = self._execute_initial_comment_loading()

            if most_relevant_found is not False:
                # Start tab-based navigation through comments
                self._navigate_through_comments_with_tabs()

                # Final check for any remaining JavaScript-tracked responses
                print("🔍 Final check for remaining JavaScript-tracked responses...")
                self._process_js_tracked_responses()

            # Deduplicate Comments
            self._deduplicate_comments()

            # Create and return FacebookPost
            return self._create_facebook_post()

        except Exception as e:
            print(f"❌ Error in tab-based comment scraping: {e}")
            raise e
        finally:
            # Cleanup server resources if using server tracking
            if self.use_server_tracking:
                try:
                    requests.post(f"{self.tracker_server_url}/clear")
                    print("✅ Cleared tracker server data")
                except:
                    pass

    def _execute_initial_reel_loading(self):
        """Execute reel-specific initial loading: Find element with aria-label='Comment' -> Press Enter -> Continue with regular flow"""
        try:
            print("🎬 Executing initial reel loading sequence...")

            # Step 1: Find element with aria-label="Comment"
            found_comment_element = False
            max_tabs = 100

            for i in range(max_tabs):
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.1)

                try:
                    focused_element = self.driver.switch_to.active_element
                    element_text = focused_element.get_attribute("textContent") or ""
                    aria_label = focused_element.get_attribute("aria-label") or ""

                    print(
                        f"Tab {i + 1}: '{element_text.strip()[:50]}{'...' if len(element_text.strip()) > 50 else ''}' (aria-label: '{aria_label}')"
                    )

                    # Check for element with aria-label="Comment"
                    if aria_label == "Comment":
                        print(
                            f"🎯 Found element with aria-label='Comment' at tab {i + 1}"
                        )
                        found_comment_element = True
                        break

                except Exception as e:
                    continue

            if not found_comment_element:
                raise Exception("Could not find element with aria-label='Comment'")

            # Step 2: Click the Comment element
            print("🖱️ Clicking on Comment element...")
            try:
                focused_element.click()
            except Exception as e:
                print(f"⚠️ Failed to click Comment element: {e}")
                # Fallback to Enter if click fails
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Step 3: Wait random seconds for page to load
            wait_time = random.randint(6, 12)
            print(f"⏳ Waiting {wait_time} seconds for page to load...")
            time.sleep(wait_time)

            # Step 4: Press Shift key
            print("⬆️ Pressing Shift key...")
            ActionChains(self.driver).key_down(Keys.SHIFT).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)

            # check if the focused element is "Miost relevant"
            focused_element = self.driver.switch_to.active_element
            element_text = focused_element.get_attribute("textContent") or ""
            if "most relevant" not in (element_text).lower():
                print(
                    "⚠️ Warning: Could not find 'Most relevant' element. Possibly 0 comments?"
                )
                return False

            # Step 5: Press Enter
            print("▶️ Pressing Enter...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)

            # Step 6: Find and click the specified comment type element using Down arrow navigation
            self._find_and_click_comment_type_element()

            self._wait_and_log("Initial reel comment loading", 3, 6)

        except Exception as e:
            print(f"❌ Error in initial reel loading: {e}")
            raise e

    def _execute_initial_comment_loading(self):
        """Execute: Most relevant -> Enter -> Down arrows to find comment type element -> Enter"""
        try:
            print("🔍 Executing initial comment loading sequence...")

            # For videos: First find and store the first Share / See more element before handling Most relevant
            if self.is_video_url:
                print(
                    "🎥 Video detected - searching for first Share / See more element to store..."
                )
                self._find_and_store_video_elements()

            # Find "Most relevant" element
            found_most_relevant = False
            max_tabs = 100

            for i in range(max_tabs):
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.1)

                try:
                    focused_element = self.driver.switch_to.active_element
                    element_text = focused_element.get_attribute("textContent") or ""

                    print(
                        f"Tab {i + 1}: '{element_text.strip()[:50]}{'...' if len(element_text.strip()) > 50 else ''}'"
                    )

                    # Check for Close dialog
                    if "Close" in element_text and len(element_text.strip()) <= 10:
                        print(f"🔍 Found 'Close' dialog - dismissing...")
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(1)
                        continue

                    # Check for Most relevant
                    if "Most relevant" in element_text and len(element_text.strip()) <= 16:
                        print(f"🎯 Found 'Most relevant' element at tab {i + 1}")
                        most_relevant_element = focused_element
                        found_most_relevant = True
                        break
                    # Check for All comments
                    if "All comments" in element_text and len(element_text.strip()) <= 16:
                        print(f"🎯 Found 'All comments' element at tab {i + 1}")
                        most_relevant_element = focused_element
                        found_most_relevant = True
                        break
                    # Check for Newest
                    if "Newest" in element_text and len(element_text.strip()) <= 16:
                        print(f"🎯 Found 'Newest' element at tab {i + 1}")
                        most_relevant_element = focused_element
                        found_most_relevant = True
                        break

                except Exception as e:
                    continue

            if not found_most_relevant:
                print(
                    "⚠️ Warning: Could not find 'Most relevant' element. Possibly 0 comments?"
                )
                return False

            # Execute sequence: Enter -> Down arrows to find comment type element -> Enter -> Tab (for videos only) -> Wait
            print("▶️ Pressing Enter...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)

            # Find and click the specified comment type element using Down arrow navigation
            self._find_and_click_comment_type_element()

            # Focus back on saved Most relevant element
            print("🎯 Focusing on saved Most relevant element...")
            try:
                self.driver.execute_script(
                    "arguments[0].focus();", most_relevant_element
                )
                time.sleep(0.5)
                print("✅ Successfully focused on Most relevant element")
            except Exception as e:
                print(f"⚠️ Error focusing on Most relevant element: {e}")

            # For videos only: Wait for comments to load first, then focus on See all element
            if self.is_video_url:
                print("➡️ Video - pressing Tab once and waiting for comments to load...")
                ActionChains(self.driver).send_keys(Keys.TAB).perform()

                # Wait for video comment loading
                print("⏳ Waiting for video comment loading...")
                time.sleep(6)

                # After comments load, focus on the stored See all element to continue scraping
                if self.see_all_element:
                    print(
                        "🔗 Video comments loaded - now focusing on stored See all element..."
                    )
                    try:
                        # Focus on See all element using JavaScript (no clicking, no Escape/Enter handling)
                        self.driver.execute_script(
                            "arguments[0].focus();", self.see_all_element
                        )
                        time.sleep(0.5)
                        print(
                            "✅ Successfully focused on See all element - continuing with tab navigation..."
                        )
                    except Exception as e:
                        print(f"⚠️ Error focusing on stored See all element: {e}")
                elif self.first_share_element:
                    print(
                        "⚠️ No See all element found, falling back to Share element..."
                    )
                    try:
                        self.first_share_element.click()
                        time.sleep(0.5)
                        print("⛔ Pressing Escape after clicking Share...")
                        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                    except Exception as e:
                        print(f"⚠️ Error clicking stored Share element: {e}")
                else:
                    print(
                        "⚠️ Warning: No See all or Share elements were stored for video"
                    )
            else:
                # Wait for regular post comment loading
                print("⏳ Waiting for regular post comment loading...")
                time.sleep(10)

        except Exception as e:
            print(f"❌ Error in initial comment loading: {e}")
            raise e

    def _find_and_store_video_elements(self):
        """Find and store the first Share element and See all element for videos"""
        try:
            print("🔍 Searching for Share and See all elements to store...")

            # Reset tab position to start fresh
            max_tabs = 200  # Increased limit to ensure we find both elements

            # Initialize variables to track both elements
            self.first_share_element = None
            self.see_all_element = None

            for i in range(max_tabs):
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.1)

                try:
                    focused_element = self.driver.switch_to.active_element
                    element_text = focused_element.get_attribute("textContent") or ""
                    element_text_lower = element_text.lower().strip()

                    # Enhanced logging for debugging
                    try:
                        element_text_stripped = element_text.strip()
                        tag_name = focused_element.tag_name
                        aria_label = focused_element.get_attribute("aria-label") or ""

                        if element_text_stripped:
                            display_text = element_text_stripped[:50]
                            if len(element_text_stripped) > 50:
                                display_text += "..."
                            print(f"🔍 Tab {i + 1}: '{display_text}' [{tag_name}]")
                        else:
                            extra_info = (
                                f" aria-label='{aria_label}'" if aria_label else ""
                            )
                            print(f"🔍 Tab {i + 1}: [EMPTY {tag_name}{extra_info}]")
                    except Exception as e:
                        print(
                            f"🔍 Tab {i + 1}: '{element_text.strip()[:50]}{'...' if len(element_text.strip()) > 50 else ''}'"
                        )

                    # if live video, we will look for "comment" and click on it
                    if (self.is_live_video_url and "comment" == element_text_lower):
                        print(
                            f"📍 Found Comment element on Live Video at tab {i + 1} - will click on it and continue searching for Most Relevant"
                        )
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(10)
                        return

                    # Check for Share element
                    if (
                        "share" == element_text_lower
                        and self.first_share_element is None
                    ):
                        print(
                            f"📍 Found first Share element at tab {i + 1} - storing for later use"
                        )
                        self.first_share_element = focused_element
                        break

                    # Check for See all element
                    if "see all" == element_text_lower and self.see_all_element is None:
                        print(
                            f"📍 Found See all element at tab {i + 1} - storing and clicking..."
                        )
                        self.see_all_element = focused_element

                        # Press Enter on See all element to expand comments
                        try:
                            print("▶️ Pressing Enter on See all element...")
                            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                            time.sleep(1)
                            print("✅ Successfully pressed Enter on See all element")
                        except Exception as e:
                            print(f"⚠️ Error pressing Enter on See all element: {e}")

                    # If we found See all element, that's enough to proceed (Share is optional)
                    if self.see_all_element is not None:
                        print(
                            "✅ Found and clicked See all element - continuing to search for Most relevant"
                        )
                        break

                    # If we found both elements, we can also exit
                    if (
                        self.first_share_element is not None
                        and self.see_all_element is not None
                    ):
                        print(
                            "✅ Found both Share and See all elements - continuing to search for Most relevant"
                        )
                        break

                except Exception as e:
                    continue

            # Log what we found
            if self.first_share_element is None:
                print("⚠️ Warning: Could not find Share element to store")
            if self.see_all_element is None:
                print("⚠️ Warning: Could not find See all element to store")

        except Exception as e:
            print(f"❌ Error finding video elements: {e}")

    def _find_and_click_comment_type_element(self):
        """Find and click the specified comment type element (All comments, Newest, Most relevant) using Down arrow navigation"""
        try:
            print(
                f"🔍 Searching for '{self.scrape_comments_type}' element using Tab navigation..."
            )

            max_downs = 10  # Limit down presses to prevent infinite loop
            found_element = False

            for i in range(max_downs):
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.2)

                try:
                    focused_element = self.driver.switch_to.active_element
                    element_text = focused_element.get_attribute("textContent") or ""
                    element_text_clean = element_text.strip()

                    # Enhanced logging for debugging
                    try:
                        tag_name = focused_element.tag_name

                        if element_text_clean:
                            display_text = element_text_clean[:100]
                            if len(element_text_clean) > 100:
                                display_text += "..."
                            print(f"🔍 Tab {i + 1}: '{display_text}' [{tag_name}]")
                        else:
                            print(f"🔍 Tab {i + 1}: [EMPTY {tag_name}]")
                    except Exception as e:
                        print(
                            f"🔍 Tab {i + 1}: '{element_text_clean[:100]}{'...' if len(element_text_clean) > 100 else ''}'"
                        )

                    # Check if we found the target comment type element (using startswith to handle additional description text)
                    if element_text_clean.startswith(self.scrape_comments_type):
                        print(
                            f"🎯 Found '{self.scrape_comments_type}' element at down {i + 1}"
                        )
                        found_element = True
                        break

                except Exception as e:
                    continue

            if not found_element:
                if self.scrape_comments_type == "All comments":
                    print(
                        f"⚠️ Warning: Could not find '{self.scrape_comments_type}' element, will check if Newest comment is found."
                    )
                    self.scrape_comments_type = "Newest"
                    return self._execute_initial_comment_loading()
                print(
                    f"⚠️ Warning: Could not find '{self.scrape_comments_type}' element, will continue without clicking it"
                )
                return True

            # Click the found element
            print(f"🖱️ Clicking '{self.scrape_comments_type}' element...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for the COMMENT_SORT_CHANGE request to complete
            try:
                print(f"⏳ Waiting for comment sort change request to complete...")
                self._wait_for_comment_sort_change(timeout_seconds=60)
                print(
                    f"✅ Comment sort changed to '{self.scrape_comments_type}' successfully"
                )
            except (NetworkError, InvalidResponse, ErrorResponse) as e:
                print(f"❌ Error during comment sort change: {e}")
                raise e

            return True

        except Exception as e:
            print(
                f"❌ Error finding and clicking '{self.scrape_comments_type}' element: {e}"
            )
            return False

    def _check_scraping_limits(self) -> bool:
        """Check if we've reached comment_limit or scrape_till_datetime limit

        Returns:
            True if limits are reached and scraping should stop, False otherwise
        """
        try:
            # Check comment_limit
            if self.comment_limit != -1 and len(self.scraped_comments) >= self.comment_limit:
                print(f"🛑 Reached comment limit: {len(self.scraped_comments)}/{self.comment_limit} comments scraped")
                return True

            # Check scrape_till_datetime limit
            if self.scrape_till_datetime is not None and len(self.scraped_comments) > 0:
                # Sort comments by comment_time (newest first)
                sorted_comments = sorted(
                    self.scraped_comments,
                    key=lambda c: c.comment_time.timestamp() if c.comment_time else 0,
                    reverse=True
                )

                # Check if oldest comment is older than scrape_till_datetime
                oldest_comment = sorted_comments[-1]
                if oldest_comment.comment_time and oldest_comment.comment_time.timestamp() < self.scrape_till_datetime.timestamp():
                    print(f"📅 Found comments older than scrape_till_datetime. Filtering out of range comments...")
                    # Filter out comments older than scrape_till_datetime
                    filtered_comments = [
                        c for c in sorted_comments
                        if c.comment_time and c.comment_time.timestamp() > self.scrape_till_datetime.timestamp()
                    ]
                    self.scraped_comments = filtered_comments
                    print(f"✅ Filtered to {len(self.scraped_comments)} comments within date range")
                    return True

            return False

        except Exception as e:
            print(f"❌ Error checking scraping limits: {e}")
            return False

    def _navigate_through_comments_with_tabs(self):
        """Navigate through comments using Tab key and handle replies"""
        try:
            print("🚀 Starting tab-based navigation through comments...")

            while True:
                # Check if we've reached the scraping limits before pressing Tab
                if self._check_scraping_limits():
                    print("🛑 Scraping limits reached - stopping navigation")
                    break

                # Press Tab (no delay)
                ActionChains(self.driver).send_keys(Keys.TAB).perform()

                # Increment tabs since last like counter
                self.tabs_since_last_like += 1

                # Periodic progress logging every 50 tabs
                if self.tabs_since_last_like % 50 == 0:
                    print(
                        f"⏰ Progress: {self.tabs_since_last_like} tabs since last 'Like' element (will stop at 200)"
                    )

                # Get current element
                try:
                    focused_element = self.driver.switch_to.active_element
                    element_text = focused_element.get_attribute("textContent") or ""

                    # Store last "Reply" element for later use after View replies clicks
                    if element_text.strip().lower() == "reply":
                        self.last_reply_element = focused_element
                        print(f"💾 Stored last 'Reply' element for future navigation")

                    # Log element for debugging with additional attributes
                    try:
                        element_text_stripped = element_text.strip()
                        tag_name = focused_element.tag_name
                        aria_label = focused_element.get_attribute("aria-label") or ""

                        # Enhanced logging with more context
                        if element_text_stripped:
                            # Show text content (first 100 chars)
                            display_text = element_text_stripped[:100]
                            if len(element_text_stripped) > 100:
                                display_text += "..."
                            print(f"🔍 Tab: '{display_text}' [{tag_name}]")
                        else:
                            # For empty elements, show tag and aria-label if available
                            extra_info = (
                                f" aria-label='{aria_label}'" if aria_label else ""
                            )
                            print(f"🔍 Tab: [EMPTY {tag_name}{extra_info}]")
                    except Exception as e:
                        # Fallback to original simple logging if enhanced logging fails
                        print(
                            f"🔍 Tab: '{element_text.strip()[:100]}{'...' if len(element_text.strip()) > 100 else ''}'"
                        )

                    # Handle different types of elements
                    element_handled = self._handle_element(element_text)

                    # Check for end condition
                    should_stop = self._should_stop_navigation(
                        element_text, element_handled
                    )
                    if should_stop:
                        print("🛑 Reached end of comments - stopping navigation")
                        break

                    # Get JavaScript-tracked responses (Fetch override method)
                    self._process_js_tracked_responses()

                except (NetworkError, InvalidResponse, ErrorResponse) as e:
                    print(f"❌ Critical error during element handling: {e}")
                    # Re-raise critical network errors to stop scraping
                    raise e
                except Exception as e:
                    print(f"❌ Error handling element: {e}")
                    continue

        except Exception as e:
            print(f"❌ Error in tab navigation: {e}")
            raise e

    def _handle_element(self, element_text: str) -> bool:
        """Handle different types of elements and return True if element was handled"""
        element_text_lower = element_text.lower().strip()

        # For reel and video URLs, prioritize "View more comments" over replies
        if self.is_reel_url or self.is_video_url:
            return self._handle_video_element(element_text, element_text_lower)
        else:
            return self._handle_regular_post_element(element_text, element_text_lower)

    def _handle_video_element(self, element_text: str, element_text_lower: str) -> bool:
        """Handle elements for video and reel URLs with specific priority order"""

        # FIRST: Handle "See all" elements (highest priority for all post types)
        if "see all" in element_text_lower:
            print(
                f"👁️ Found 'See all' element: {element_text.strip()} - CLICKING TO EXPAND"
            )
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.5)  # Brief pause after clicking
            return True

        # Second: Handle "View more comments" elements (high priority for videos)
        if self._is_view_more_comments_element(element_text):
            print(
                f"📝 Found 'View more comments' element: {element_text.strip()} - CLICKING TO LOAD MORE"
            )
            # Press Enter to load more comments
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for the VIEW_MORE_COMMENTS request to complete
            try:
                print(f"⏳ Waiting for View More Comments request to complete...")
                self._wait_for_view_more_comments(timeout_seconds=60)
                print(f"✅ View More Comments loaded successfully")
            except (NetworkError, InvalidResponse, ErrorResponse) as e:
                print(f"❌ Error loading more comments: {e}")
                raise e

            # Focus on stored last Reply element (replaces Shift+Tab 3x method)
            print("⬅️ Focusing on stored Reply element after View more comments...")
            self._focus_on_stored_reply_element()
            return True

        # FOURTH: Handle reply-related elements
        if self._is_reply_element(element_text):
            print(
                f"🔗 Found reply element: {element_text.strip()} - CLICKING TO EXPAND"
            )
            # Press Enter to expand replies
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for the VIEW_REPLIES_DEPTH1 request to complete
            try:
                print(f"⏳ Waiting for View Replies request to complete...")
                self._wait_for_view_replies_depth1(timeout_seconds=60)
                print(f"✅ View Replies loaded successfully")
            except (NetworkError, InvalidResponse, ErrorResponse) as e:
                print(f"❌ Error loading replies: {e}")
                raise e

            # Focus on stored last Reply element (replaces Shift+Tab 3x method)
            print("⬅️ Focusing on stored Reply element after View replies...")
            self._focus_on_stored_reply_element()
            return True

        # FIFTH: Handle Close dialogs
        if "close" in element_text_lower and len(element_text.strip()) <= 10:
            print("🔍 Found Close dialog - dismissing...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)
            return True

        # SIXTH: Handle Like elements (no End key for videos)
        if "like" in element_text_lower:
            self.comment_count += 1  # Increment comment count
            self.tabs_since_last_like = 0  # Reset counter when Like found
            print(
                f"✅ Found Like (Comment #{self.comment_count}) - reset tabs_since_last_like counter"
            )
            return True

        return False

    def _handle_regular_post_element(
        self, element_text: str, element_text_lower: str
    ) -> bool:
        """Handle elements for regular post URLs (original logic)"""

        # FIRST: Handle "See all" elements (highest priority for all post types)
        if "see all" in element_text_lower:
            print(
                f"👁️ Found 'See all' element: {element_text.strip()} - CLICKING TO EXPAND"
            )
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.5)  # Brief pause after clicking
            return True

        # Second: Handle "View more comments" elements (high priority for regular posts)
        if self._is_view_more_comments_element(element_text):
            print(
                f"📝 Found 'View more comments' element: {element_text.strip()} - CLICKING TO LOAD MORE"
            )
            # Press Enter to load more comments
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for the VIEW_MORE_COMMENTS request to complete
            try:
                print(f"⏳ Waiting for View More Comments request to complete...")
                self._wait_for_view_more_comments(timeout_seconds=60)
                print(f"✅ View More Comments loaded successfully")
            except (NetworkError, InvalidResponse, ErrorResponse) as e:
                print(f"❌ Error loading more comments: {e}")
                raise e

            # Focus on stored last Reply element (replaces Shift+Tab 3x method)
            print("⬅️ Focusing on stored Reply element after View more comments...")
            self._focus_on_stored_reply_element()
            return True

        # FOURTH: Handle reply-related elements
        if self._is_reply_element(element_text):
            print(
                f"🔗 Found reply element: {element_text.strip()} - CLICKING TO EXPAND"
            )
            # Press Enter to expand replies
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for the VIEW_REPLIES_DEPTH1 request to complete
            try:
                print(f"⏳ Waiting for View Replies request to complete...")
                self._wait_for_view_replies_depth1(timeout_seconds=60)
                print(f"✅ View Replies loaded successfully")
            except (NetworkError, InvalidResponse, ErrorResponse) as e:
                print(f"❌ Error loading replies: {e}")
                raise e

            # Focus on stored last Reply element (replaces Shift+Tab 3x method)
            print("⬅️ Focusing on stored Reply element after View replies...")
            self._focus_on_stored_reply_element()
            return True

        # FIFTH: Handle Close dialogs
        if "close" in element_text_lower and len(element_text.strip()) <= 10:
            print("🔍 Found Close dialog - dismissing...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)
            return True

        # SIXTH: Handle Like elements (with End key for regular posts)
        if "like" in element_text_lower:
            self.comment_count += 1  # Increment comment count
            self.tabs_since_last_like = 0  # Reset counter when Like found
            print(
                f"✅ Found Like (Comment #{self.comment_count}) - reset tabs_since_last_like counter"
            )

            # Press End and wait after reaching threshold (dynamic)
            if self.comment_count % self.comments_threshold == 0:
                print(
                    f"🔚 Processed {self.comments_threshold} comments - pressing End key..."
                )
                ActionChains(self.driver).send_keys(Keys.END).perform()

                # Wait for the VIEW_MORE_COMMENTS request triggered by End key
                try:
                    print(f"⏳ Waiting for End key triggered request to complete...")
                    self._wait_for_view_more_comments(timeout_seconds=60)
                    print(f"✅ End key request completed successfully")
                except (NetworkError, InvalidResponse, ErrorResponse) as e:
                    print(f"❌ Error with End key request: {e}")
                    # Raise exception to stop scraping
                    raise e

                # Increase threshold by 10 for next cycle
                self.comments_threshold += 10
                print(f"📈 Increased comment threshold to {self.comments_threshold}")

            return True

        return False

    def _is_reply_element(self, element_text: str) -> bool:
        """Check if element is related to replies"""
        element_text_lower = element_text.lower().strip()

        # More flexible patterns to catch "View 1 reply"
        # Check for "View 1 reply" with flexible whitespace
        if re.search(r"view\s*1\s*reply", element_text_lower):
            print(f"🔍 Found 'View 1 reply' pattern: {element_text.strip()}")
            return True

        # Check for "1 reply" without "view"
        if re.search(r"\b1\s*reply\b", element_text_lower):
            print(f"🔍 Found '1 reply' pattern: {element_text.strip()}")
            return True

        # Check for "View X replies" patterns (plural)
        if re.search(r"view\s*\d+\s*replies", element_text_lower):
            print(f"🔍 Found 'View X replies' pattern: {element_text.strip()}")
            return True

        # Check for "X replies" without "view"
        if re.search(r"\b\d+\s*replies\b", element_text_lower):
            print(f"🔍 Found 'X replies' pattern: {element_text.strip()}")
            return True

        # Check for "View all X replies" patterns
        if re.search(r"view\s*all\s*\d+\s*repl(?:y|ies)", element_text_lower):
            print(f"🔍 Found 'View all X replies' pattern: {element_text.strip()}")
            return True

        # Check for "View more replies" patterns (without specific numbers)
        if re.search(r"view\s+more\s+replies", element_text_lower):
            print(f"🔍 Found 'View more replies' pattern: {element_text.strip()}")
            return True

        # Check for "Author replied" patterns
        if "replied" in element_text_lower and len(element_text.strip()) < 100:
            print(f"🔍 Found 'Author replied' pattern: {element_text.strip()}")
            return True

        return False

    def _is_view_more_comments_element(self, element_text: str) -> bool:
        """Check if element is 'View more comments' or 'View 1 more comment'"""
        element_text_lower = element_text.lower().strip()

        # Check for "View more comments"
        if re.search(r"view\s+more\s+comments?", element_text_lower):
            print(f"🔍 Found 'View more comments' pattern: {element_text.strip()}")
            return True

        # Check for "View 1 more comment"
        if re.search(r"view\s+1\s+more\s+comment", element_text_lower):
            print(f"🔍 Found 'View 1 more comment' pattern: {element_text.strip()}")
            return True

        # Check for "View X more comments" (with numbers)
        if re.search(r"view\s+\d+\s+more\s+comments?", element_text_lower):
            print(f"🔍 Found 'View X more comments' pattern: {element_text.strip()}")
            return True

        return False

    def _check_comment_stop_condition(self, element_text: str) -> bool:
        """For regular posts and groups: stop when we find 'All comments' or 'Newest' element (secondary to universal Most relevant check)"""
        element_text_lower = element_text.lower().strip()

        if (
            self.scrape_comments_type.lower() in element_text_lower
            and self.is_video_url
        ):
            if self.scrape_comments_type_counter == 0:
                self.scrape_comments_type_counter += 1
                print("📊 Found 'scrape_comments_type' element first time.")
                return False
            else:
                print(
                    "📊 Found 'scrape_comments_type' element 2nd time. Scraping ended"
                )
                return True

        # Check for "All comments" element using startswith to handle unicode characters like feff
        if "all comments" in element_text_lower:
            print(
                "🎯 Found 'All comments' element (with possible unicode) - reached end of regular/group post comments"
            )
            return True

        if "most relevant" in element_text_lower:
            print(
                "📊 Found 'Most relevant' element - reached end of comments (cycled back to beginning)"
            )
            return True

        # Check for "Newest" element using exact match to handle unicode characters like feff
        if "newest" in element_text_lower:
            print(
                f"🎯 Found 'Newest' element - reached end of regular/group post comments"
            )
            return True

        if "comment" == element_text_lower:
            if (self.is_live_video_url and self.comment_button_counter == 0):
                print("Comment button found for the first time in live video, skipping")
                self.comment_button_counter += 1
            else:
                print(
                    "📊 Found 'Comment' element - reached end of comments (cycled back to beginning)"
                )
                return True

        if "reload page" == element_text_lower:
            print(
                "📊 Warning: Found 'Reload Page' element - Possibly got rate limit. Stopping scrapping for this post"
            )
            return True

        if "go to feed" == element_text_lower:
            print(
                "📊 Warning: Found 'Go to Feed' element - Possibly the post is deleted. Stopping scrapping for this post"
            )
            return True

        return False

    def _should_stop_navigation(self, element_text: str, element_handled: bool) -> bool:
        """Check if we should stop navigation - universal and post-type specific conditions"""

        if self._check_comment_stop_condition(element_text):
            return True

        if self.tabs_since_last_like >= 200:
            print(
                f"🚫 No 'Like' element found in last {self.tabs_since_last_like} tabs - reached end of content, stopping navigation"
            )
            return True

        # Then check post-type specific conditions
        if self.is_reel_url:
            return self._should_stop_reel_navigation(element_text)
        elif self.is_video_url:
            return self._should_stop_video_navigation(element_text)

    def _should_stop_reel_navigation(self, element_text: str) -> bool:
        """For reels: stop when we find 'Reels' element (secondary to universal Most relevant check)"""
        element_text_lower = element_text.lower().strip()

        # Debug log for Reels detection
        if "reels" in element_text_lower:
            print(
                f"🔍 DEBUG: Reels detection - element_text_lower: '{element_text_lower}' (length: {len(element_text_lower)})"
            )

        # Check for "Reels" element to indicate end of comments
        if "reels" == element_text_lower:
            print(f"🎯 Found exact 'Reels' element - reached end of reel comments")
            return True

        return False

    def _should_stop_video_navigation(self, element_text: str) -> bool:
        """For videos: stop when we find second 'Share' element (secondary to universal Most relevant check)"""
        element_text_lower = element_text.lower().strip()

        # Check for "Share" element
        if "share" == element_text_lower:
            if (self.is_live_video_url and self.share_button_counter == 0):
                print("Share button found for the first time in live video, skipping")
                self.share_button_counter += 1
            else:
                print("🎯 Share found - reached end of video comments")
                return True

        return False

    def _process_response(self, response_body: str, url: str):
        """Process GraphQL response for comments or replies"""
        try:
            # Check for direct comment feed response structure (edges format)
            if self._is_direct_comment_feed_response(response_body):
                print("📝 Found direct comment feed response")
                self._process_direct_comment_and_replies_feed_response(response_body)
                return

            # Check for reply response structure
            if self._is_reply_response(response_body):
                print("🔗 Found reply response")
                self._process_reply_response(response_body)
                return

        except Exception as e:
            print(f"❌ Error processing response: {e}")

    def _is_reply_response(self, response_body: str) -> bool:
        """Check if response contains reply data"""
        return (
            "replies_connection" in response_body
            and '"__typename":"Feedback"' in response_body
            and "edges" in response_body
        )

    def _is_direct_comment_feed_response(self, response_body: str) -> bool:
        """Check if response contains direct comment feed data with edges"""
        return (
            '"__typename":"Feedback"' in response_body
            and '"comment_rendering_instance_for_feed_location"' in response_body
            and '"edges"' in response_body
            and '"node"' in response_body
        )

    def _process_reply_response(self, response_body: str):
        """Process reply response with replies_connection.edges structure"""
        try:
            data = json.loads(response_body)
            node = data.get("data", {}).get("node", {})

            if node.get("__typename") != "Feedback":
                return

            replies_connection = node.get("replies_connection", {})
            edges = replies_connection.get("edges", [])

            print(f"📊 Processing {len(edges)} replies...")

            for edge in edges:
                reply_node = edge.get("node", {})
                if not reply_node:
                    continue

                # Extract reply data
                reply_comment = self._extract_comment_from_node(reply_node)
                if reply_comment:
                    # Do immediate parent-child mapping and add to scraped_comments
                    self._add_comment_with_immediate_mapping(reply_comment)
                    self.comment_counter += 1
                    print(f"✅ Added reply: {reply_comment.comment_text[:50]}...")

                    # Print complete reply dataclass as we scrape
                    print("\n" + "=" * 60)
                    print(
                        f"🔗 NEW REPLY SCRAPED #{self.comment_counter} (parent_node_id: {reply_comment._parent_node_id})"
                    )
                    print("=" * 60)
                    self._print_comment_details(reply_comment, indent=0)
                    print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error processing reply response: {e}")

    def _process_direct_comment_and_replies_feed_response(self, response_body: str):
        """Process direct comment feed response with data.node.comment_rendering_instance_for_feed_location.comments.edges structure"""
        try:
            decoder = json.JSONDecoder()
            data, index = decoder.raw_decode(response_body)
            node = data.get("data", {}).get("node", {})

            if node.get("__typename") != "Feedback":
                return

            # Navigate to comments edges
            comment_rendering = node.get(
                "comment_rendering_instance_for_feed_location", {}
            )
            comments_data = comment_rendering.get("comments", {})
            edges = comments_data.get("edges", [])

            print(f"📊 Processing {len(edges)} direct comments from feed...")

            for edge in edges:
                comment_node = edge.get("node", {})
                if not comment_node:
                    continue

                # Extract comment data from node
                comment = self._extract_comment_from_node(comment_node)
                if comment:
                    # Do immediate parent-child mapping and add to scraped_comments
                    self._add_comment_with_immediate_mapping(comment)
                    self.comment_counter += 1

                    print(f"✅ Added direct comment: {comment.comment_text[:50]}...")

                    # Print complete comment dataclass as we scrape
                    print("\n" + "=" * 60)
                    print(f"📝 NEW DIRECT COMMENT SCRAPED #{self.comment_counter}")
                    print("=" * 60)
                    self._print_comment_details(comment, indent=0)
                    print("=" * 60 + "\n")

                    # Process replies from direct comments
                    comment_feedback = comment_node.get("feedback", {})
                    replies_connection = (
                        comment_feedback.get("replies_connection", {})
                        if comment_feedback
                        else {}
                    )
                    print("Searching for replies in direct comemnt")
                    if replies_connection:
                        print("Direct comment has replies. Processing replies")
                        reply_data = {"data": {"node": comment_feedback}}
                        reply_data = json.dumps(reply_data)
                        self._process_reply_response(reply_data)

        except Exception as e:
            print(f"❌ Error processing direct comment feed response: {e}")

    def _extract_reactions_from_node(self, node: dict) -> Reactions:
        """Extract reactions from node.feedback.top_reactions"""
        try:
            # Initialize reaction counts
            reaction_counts = {
                "like": 0,
                "love": 0,
                "haha": 0,
                "wow": 0,
                "sad": 0,
                "angry": 0,
                "care": 0,
            }

            # Get feedback data
            feedback = node.get("feedback", {})
            if not feedback:
                return Reactions()

            # Extract from top_reactions.edges
            top_reactions = feedback.get("top_reactions", {})
            edges = top_reactions.get("edges", [])

            for edge in edges:
                reaction_node = edge.get("node", {})
                reaction_id = reaction_node.get("id", "")
                reaction_count = edge.get("reaction_count", 0)

                # Map reaction ID to reaction name
                reaction_name = REACTION_ID_MAPPING.get(reaction_id)
                if reaction_name:
                    reaction_counts[reaction_name] = reaction_count
                    print(
                        f"✅ Mapped reaction {reaction_id} -> {reaction_name}: {reaction_count}"
                    )
                else:
                    print(
                        f"⚠️ Unknown reaction ID: {reaction_id} with count: {reaction_count}"
                    )

            # Calculate total
            total_reactions = sum(reaction_counts.values())

            return Reactions(
                Total=total_reactions if total_reactions > 0 else None,
                Like=reaction_counts["like"] if reaction_counts["like"] > 0 else None,
                Love=reaction_counts["love"] if reaction_counts["love"] > 0 else None,
                Haha=reaction_counts["haha"] if reaction_counts["haha"] > 0 else None,
                Wow=reaction_counts["wow"] if reaction_counts["wow"] > 0 else None,
                Sad=reaction_counts["sad"] if reaction_counts["sad"] > 0 else None,
                Angry=reaction_counts["angry"]
                if reaction_counts["angry"] > 0
                else None,
                Care=reaction_counts["care"] if reaction_counts["care"] > 0 else None,
            )

        except Exception as e:
            print(f"❌ Error extracting reactions from node: {e}")
            return Reactions()

    def _add_comment_with_immediate_mapping(self, comment: Comment):
        """Add comment to scraped_comments and do immediate parent-child mapping"""
        try:
            # Always add to scraped_comments first
            self.scraped_comments.append(comment)

            # Store in node_id mapping for future parent-child lookups
            if comment._internal_node_id:
                self.node_id_to_comment[comment._internal_node_id] = comment
                print(
                    f"🗂️ Stored comment in mapping: {comment._internal_node_id} -> {comment.comment_id}"
                )

            # Check if this comment has a parent and try to attach immediately
            if (
                comment._reply_to_node_id
                and comment._reply_to_node_id in self.node_id_to_comment
            ):
                reply_to_comment = self.node_id_to_comment[comment._reply_to_node_id]
                comment.reply_to = reply_to_comment.comment_id

            # Check if this comment has a parent and try to attach immediately
            if (
                comment._parent_node_id
                and comment._parent_node_id in self.node_id_to_comment
            ):
                # Found parent - attach this comment as a reply
                parent_comment = self.node_id_to_comment[comment._parent_node_id]
                parent_comment.comments_replies.append(comment)
                comment.parent = parent_comment.comment_id

                print(
                    f"🔗 IMMEDIATE MAPPING: Attached reply {comment.comment_id} to parent {parent_comment.comment_id}"
                )
                # print(f"📊 Parent {parent_comment.comment_id} now has {parent_comment.total_replies} replies")
            else:
                if comment._parent_node_id:
                    print(
                        f"⏳ DEFERRED MAPPING: Comment {comment.comment_id} waiting for parent {comment._parent_node_id}"
                    )
                else:
                    print(f"🌱 ROOT COMMENT: {comment.comment_id} has no parent")

        except Exception as e:
            print(
                f"❌ Error in immediate mapping for comment {comment.comment_id}: {e}"
            )

    def _extract_comment_from_node(self, node: dict) -> Optional[Comment]:
        """Extract comment data from a node (used for replies)"""
        try:
            # Basic comment data
            comment_id = node.get("legacy_fbid", "")
            internal_node_id = node.get("id", "")
            text = node.get("body", {}).get("text", "") if node.get("body") else ""

            # Get comment URL from comment_action_links[0].comment.url
            comment_url = ""
            action_links = node.get("comment_action_links", [])
            if action_links and len(action_links) > 0:
                comment_link = action_links[0].get("comment", {})
                comment_url = comment_link.get("url", "")

            # Profile picture URL from node.user.profile_picture.uri (same as direct comments)
            profile_pic_url = ""
            user_data = node.get("user", {})
            if user_data:
                profile_pic_data = user_data.get("profile_picture", {})
                if profile_pic_data:
                    profile_pic_url = profile_pic_data.get("uri", "")

            # Time
            created_time = node.get("created_time")
            comment_time = None
            if created_time:
                try:
                    comment_time = datetime.fromtimestamp(created_time, tz=timezone.utc)
                except:
                    comment_time = None

            # Extract reactions from node.feedback.top_reactions
            reactions = self._extract_reactions_from_node(node)

            # Author data
            author_data = node.get("author", {})

            # Get user gender from author.gender
            user_gender = author_data.get("gender", "")

            # Download profile picture and get local path
            profile_pic_path = (
                self._download_profile_picture(
                    profile_pic_url, author_data.get("id", "")
                )
                if profile_pic_url
                else ""
            )

            author = Author(
                name=author_data.get("name", ""),
                author_id=author_data.get("id", ""),
                url=author_data.get("url", ""),
                profile_image_url=profile_pic_url,
                profile_image_path=profile_pic_path,
            )

            # Get attachment URL from node.attachments[0].style_type_renderer.attachment.media.image.uri
            attachment_url = ""
            image_accessibility_caption = None
            attachments = node.get("attachments", [])
            if attachments and len(attachments) > 0:
                attachment = attachments[0]
                style_type_renderer = attachment.get("style_type_renderer", {})
                if style_type_renderer:
                    attachment_data = style_type_renderer.get("attachment", {})
                    media = attachment_data.get("media", {})
                    image_accessibility_caption = attachment_data.get("accessibility_caption")
                    image = media.get("image", {})
                    attachment_url = image.get("uri", "")

            # Download attachment if available
            attachment_path = (
                self._download_comment_attachment(attachment_url, comment_id)
                if attachment_url
                else ""
            )

            # Parent node detection - check comment_direct_parent.id first, then comment_parent.id
            parent_node_id = None
            reply_to_node_id = None
            direct_parent = node.get("comment_direct_parent", {})
            if direct_parent and direct_parent.get("id"):
                reply_to_node_id = direct_parent.get("id")
            parent = node.get("comment_parent", {})
            if parent and parent.get("id"):
                parent_node_id = parent.get("id")
            else:
                parent_node_id = reply_to_node_id

            comment_feedback = node.get("feedback", {})
            replies_fields = comment_feedback.get("replies_fields", {})
            total_replies_count = replies_fields.get("total_count", None)

            # Create comment
            comment = Comment(
                comment_id=comment_id,
                url=comment_url,
                user_pro_pic_path=profile_pic_path,
                comment_time=comment_time,
                user_id=author.author_id,
                author=author,
                user_name=author.name,
                image_accessibility_caption=image_accessibility_caption,
                user_profile_url=author.url,
                user_gender=user_gender,
                comment_text=text,
                reactions=reactions,
                total_replies=total_replies_count,
                comment_attachment_path=attachment_path,
                comments_replies=[],
                reply_to=self.facebook_post_data.get("post_id", "root")
                if not parent_node_id
                else None,
                parent=self.facebook_post_data.get("post_id", "root")
                if not parent_node_id
                else None,
                _internal_node_id=internal_node_id,
                _parent_node_id=parent_node_id,
                _reply_to_node_id=reply_to_node_id,
                user_pro_pic_url=profile_pic_url,
            )

            return comment

        except Exception as e:
            print(f"❌ Error extracting comment from node: {e}")
            return None

    def _download_profile_picture(self, url: str, user_id: str) -> str:
        """Download profile picture and return local path"""
        try:
            if not url or not user_id:
                return ""

            # Use global profile pictures directory
            profile_pics_dir = os.path.join(
                self.facebook_data_base,
                "source_attachments",
                "profile_pictures_from_comments",
            )

            # Generate filename
            filename = f"{user_id}.jpg"
            file_path = os.path.join(profile_pics_dir, filename)

            # Skip if already downloaded
            if os.path.exists(file_path):
                return file_path

            # Download the image
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"📸 Downloaded profile picture: {filename}")
            return file_path

        except Exception as e:
            print(f"❌ Error downloading profile picture for {user_id}: {e}")
            return ""

    def _download_comment_attachment(self, url: str, comment_id: str) -> str:
        """Download comment attachment and return local path"""
        try:
            if not url or not comment_id:
                return ""

            # Use global comment attachments directory
            attachments_dir = os.path.join(
                self.facebook_data_base, "comment_attachments"
            )

            # Generate filename with extension from URL
            from urllib.parse import urlparse

            parsed = urlparse(url)
            path_parts = parsed.path.split(".")
            extension = path_parts[-1] if len(path_parts) > 1 else "jpg"
            filename = f"{comment_id}_attachment.{extension}"
            file_path = os.path.join(attachments_dir, filename)

            # Skip if already downloaded
            if os.path.exists(file_path):
                return file_path

            # Download the attachment
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"📎 Downloaded attachment: {filename}")
            return file_path

        except Exception as e:
            print(f"❌ Error downloading attachment for {comment_id}: {e}")
            return ""

    def _create_facebook_post(self) -> FacebookPost:
        """Create FacebookPost with all scraped comments and replies"""
        try:
            # Attach replies to parent comments
            # self._attach_replies_to_parents()

            total_comments_from_post = self.facebook_post_data.get(
                "total_comments", None
            )
            percent_comments = None
            # commenting percent comments as this will be handled by the data api
            # if total_comments_from_post is not None and total_comments_from_post != 0:
            #     percent_comments = self.comment_counter / total_comments_from_post
            # if total_comments_from_post is not None and total_comments_from_post == 0:
            #     percent_comments = 0
            # Use provided facebook_post_data fields when available, otherwise use defaults
            facebook_post = FacebookPost(
                post_id=self.facebook_post_data.get("post_id"),
                source=self.facebook_post_data.get("source", "Facebook"),
                post_url=self.facebook_post_data.get("post_url", self.target_url),
                post_title=self.facebook_post_data.get("post_title", ""),
                posted_at=self.facebook_post_data.get("posted_at"),
                post_text=self.facebook_post_data.get("post_text", ""),
                reactions=self.facebook_post_data.get("reactions", Reactions()),
                author=self.facebook_post_data.get(
                    "author", Author(name="", author_id="", url="")
                ),
                metadata=self.facebook_post_data.get("metadata"),
                type=self.facebook_post_data.get("type"),
                checksum=self.facebook_post_data.get("checksum"),
                total_comments=total_comments_from_post,
                total_comments_scraped=self.comment_counter,
                total_shares=self.facebook_post_data.get("total_shares"),
                total_views=self.facebook_post_data.get("total_views"),
                virality_score=self.facebook_post_data.get("virality_score"),
                percent_comments=percent_comments,
                comments=[
                    c for c in self.scraped_comments if c._parent_node_id is None
                ],
                featured_images_path=self.facebook_post_data.get(
                    "featured_images_path", []
                ),
                platform=self.facebook_post_data.get("platform", "F"),
                screenshot_path=self.screenshot_path,
            )

            print(
                f"✅ Created FacebookPost with {len(self.scraped_comments)} top-level comments ({self.comment_counter} total including nested replies)"
            )

            # Save FacebookPost to JSON before returning
            self._save_facebook_post_to_json(facebook_post)

            # Print complete comment structure after scraping
            # self._print_complete_comment_structure()

            return facebook_post

        except Exception as e:
            print(f"❌ Error creating FacebookPost: {e}")
            raise e

    def _save_facebook_post_to_json(self, facebook_post: FacebookPost):
        """Save FacebookPost dataclass to JSON file"""
        try:
            import string
            from dataclasses import asdict

            # Create output directory path
            output_dir = os.path.join(
                self.facebook_data_base, "scraped_data_output", "manual"
            )

            # Generate filename with datetime and random chars
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            random_chars = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            filename = f"{timestamp}_{random_chars}.json"
            output_path = os.path.join(output_dir, filename)

            # Convert FacebookPost dataclass to dictionary
            post_dict = asdict(facebook_post)

            # Convert datetime objects to ISO format strings for JSON serialization
            def convert_datetime_to_str(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime_to_str(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime_to_str(item) for item in obj]
                else:
                    return obj

            post_dict = convert_datetime_to_str(post_dict)

            # Save to JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(post_dict, f, indent=2, ensure_ascii=False)

            print(f"💾 FacebookPost saved to JSON: {filename}")

        except Exception as e:
            print(f"❌ Error saving FacebookPost to JSON: {e}")

    def _attach_replies_to_parents(self):
        """Handle any remaining unmapped comments with multiple mapping attempts"""
        try:
            print(
                "🔗 Starting comprehensive final mapping for remaining orphaned comments..."
            )

            # Step 1: Rebuild complete node_id mapping in case we missed any
            print("🔄 Rebuilding complete node_id mapping...")
            for comment in self.scraped_comments:
                if (
                    comment._internal_node_id
                    and comment._internal_node_id not in self.node_id_to_comment
                ):
                    self.node_id_to_comment[comment._internal_node_id] = comment
                    print(
                        f"🗂️ Added missing mapping: {comment._internal_node_id} -> {comment.comment_id}"
                    )

            # Step 2: Multiple mapping passes to handle nested reply chains
            max_passes = 3  # Allow up to 3 passes for deeply nested replies
            for pass_num in range(1, max_passes + 1):
                print(f"🔄 Final mapping pass #{pass_num}...")

                mapped_this_pass = 0
                orphaned_comments = []

                for comment in self.scraped_comments:
                    # Only process comments that have parent_node_id but are still marked as root
                    if comment._parent_node_id and comment.parent == "root":
                        if comment._parent_node_id in self.node_id_to_comment:
                            # Found parent - do the mapping
                            parent_comment = self.node_id_to_comment[
                                comment._parent_node_id
                            ]
                            parent_comment.comments_replies.append(comment)
                            comment.parent = parent_comment.comment_id
                            mapped_this_pass += 1
                            print(
                                f"🔗 FINAL MAPPING (Pass {pass_num}): Attached reply {comment.comment_id} to parent {parent_comment.comment_id}"
                            )
                        else:
                            orphaned_comments.append(comment)

                print(
                    f"   Pass #{pass_num}: Mapped {mapped_this_pass} previously orphaned comments"
                )

                # If no new mappings were made, no need for more passes
                if mapped_this_pass == 0:
                    print(f"   No new mappings in pass #{pass_num} - stopping early")
                    break

            # Step 3: Final statistics
            root_comments = []
            reply_comments = []
            truly_orphaned = []

            for comment in self.scraped_comments:
                if comment._parent_node_id and comment.parent == "root":
                    # Still orphaned after all attempts
                    truly_orphaned.append(comment)
                    print(
                        f"⚠️ TRULY ORPHANED: Comment {comment.comment_id} (parent_node_id: {comment._parent_node_id} not found after {max_passes} passes)"
                    )
                elif comment.parent == "root":
                    # True root comment (no parent_node_id)
                    root_comments.append(comment)
                else:
                    # Successfully mapped reply
                    reply_comments.append(comment)

            print(f"✅ Comprehensive final mapping completed:")
            print(f"   Root comments: {len(root_comments)}")
            print(f"   Successfully mapped replies: {len(reply_comments)}")
            print(f"   Truly orphaned replies: {len(truly_orphaned)}")
            print(f"   Total comments: {len(self.scraped_comments)}")

            if truly_orphaned:
                print(
                    f"💡 Truly orphaned replies will appear as top-level comments in output"
                )

        except Exception as e:
            print(f"❌ Error in comprehensive final mapping: {e}")

    def _capture_initial_screenshot(self):
        """Capture screenshot after page load but before scraping starts"""
        try:
            # Create screenshots directory path
            screenshots_dir = os.path.join(self.facebook_data_base, "screenshots")

            # Generate filename with datetime and random chars
            from datetime import datetime
            import string

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            random_chars = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            screenshot_filename = f"{timestamp}-{random_chars}.png"
            screenshot_path = os.path.join(screenshots_dir, screenshot_filename)

            # Capture screenshot
            self.driver.save_screenshot(screenshot_path)
            print(f"📸 Initial screenshot captured: {screenshot_filename}")

            # Store screenshot path for later use in FacebookPost
            self.screenshot_path = screenshot_path

            return screenshot_path

        except Exception as e:
            print(f"❌ Error capturing initial screenshot: {e}")
            return None

    def _wait_and_log(self, action: str, min_sec: int, max_sec: int):
        """Wait for random time and log the action"""
        wait_time = random.randint(min_sec, max_sec)
        print(f"⏳ {action}: waiting {wait_time} seconds...")
        time.sleep(wait_time)

    def _print_complete_comment_structure(self):
        """Print complete comment dataclass structure with all replies"""
        try:
            print("\n" + "=" * 100)
            print("📋 COMPLETE COMMENT STRUCTURE WITH REPLIES")
            print("=" * 100)

            # Separate main comments from replies
            main_comments = [
                c for c in self.scraped_comments if c._parent_node_id is None
            ]
            reply_comments = [
                c for c in self.scraped_comments if c._parent_node_id is not None
            ]

            print(f"📊 SUMMARY:")
            print(
                f"   Total Comments (from scrapped variable): {len(self.scraped_comments)} (from comment counter): {self.comment_counter}"
            )
            print(f"   Main Comments: {len(main_comments)}")
            print(f"   Reply Comments: {len(reply_comments)}")

            # Print each main comment with its replies
            for i, comment in enumerate(main_comments, 1):
                print(f"💬 MAIN COMMENT #{i}:")
                print("-" * 80)
                self._print_comment_details(comment, indent=0)

                # Print replies for this comment
                if comment.comments_replies:
                    print(f"   🔗 REPLIES ({len(comment.comments_replies)}):")
                    for j, reply in enumerate(comment.comments_replies, 1):
                        print(f"      ↳ REPLY #{j}:")
                        self._print_comment_details(reply, indent=2)

                        # Check for nested replies (replies to replies)
                        if reply.comments_replies:
                            print(
                                f"         🔗 NESTED REPLIES ({len(reply.comments_replies)}):"
                            )
                            for k, nested_reply in enumerate(reply.comments_replies, 1):
                                print(f"            ↳ NESTED REPLY #{k}:")
                                self._print_comment_details(nested_reply, indent=3)

                print("-" * 80)
                print()

            # Print any orphaned replies (replies without found parents)
            orphaned_replies = [
                c
                for c in self.scraped_comments
                if c._parent_node_id and c.parent == "root"
            ]
            if orphaned_replies:
                print(f"⚠️ ORPHANED REPLIES ({len(orphaned_replies)}):")
                print("-" * 80)
                for i, reply in enumerate(orphaned_replies, 1):
                    print(
                        f"   🔗 ORPHANED REPLY #{i} (parent_node_id: {reply._parent_node_id}):"
                    )
                    self._print_comment_details(reply, indent=1)
                print("-" * 80)
                print()

            print("=" * 100)
            print("📋 END OF COMPLETE COMMENT STRUCTURE")
            print("=" * 100 + "\n")

        except Exception as e:
            print(f"❌ Error printing comment structure: {e}")

    def _deduplicate_comments(self):
        already_existed_comment_ids: List[str] = []
        deduplicated_comments: List[Comment] = []
        for comment in self.scraped_comments:
            if comment.comment_id in already_existed_comment_ids:
                continue
            else:
                deduplicated_comments.append(comment)
                already_existed_comment_ids.append(comment.comment_id)

        # Sort comments by comment_time (newest first)
        deduplicated_comments = sorted(
            deduplicated_comments,
            key=lambda c: c.comment_time.timestamp() if c.comment_time else 0,
            reverse=True
        )

        self.scraped_comments = deduplicated_comments

    def _print_comment_details(self, comment: Comment, indent: int = 0):
        """Print complete Comment dataclass with proper indentation"""
        try:
            prefix = "    " * indent

            print(f"{prefix}📋 COMPLETE COMMENT DATACLASS:")
            print(f"{prefix}comment_id: {comment.comment_id}")
            print(f"{prefix}url: {comment.url}")
            print(f"{prefix}user_pro_pic_path: {comment.user_pro_pic_path}")
            print(f"{prefix}comment_time: {comment.comment_time}")
            print(f"{prefix}user_id: {comment.user_id}")
            print(
                f"{prefix}author: Author(name='{comment.author.name}', author_id='{comment.author.author_id}', url='{comment.author.url}')"
            )
            print(f"{prefix}user_name: {comment.user_name}")
            print(f"{prefix}user_profile_url: {comment.user_profile_url}")
            print(f"{prefix}user_gender: {comment.user_gender}")
            print(f"{prefix}comment_text: {comment.comment_text}")
            print(
                f"{prefix}reactions: Reactions(Total={comment.reactions.Total}, Sad={comment.reactions.Sad}, Love={comment.reactions.Love}, Wow={comment.reactions.Wow}, Like={comment.reactions.Like}, Haha={comment.reactions.Haha}, Angry={comment.reactions.Angry}, Care={comment.reactions.Care})"
            )
            print(f"{prefix}total_replies: {comment.total_replies}")
            print(f"{prefix}comment_attachment_path: {comment.comment_attachment_path}")
            print(
                f"{prefix}comments_replies: [{len(comment.comments_replies)} replies]"
            )
            print(f"{prefix}parent: {comment.parent}")
            print(f"{prefix}internal_node_id: {comment._internal_node_id}")
            print(f"{prefix}parent_node_id: {comment._parent_node_id}")
            print(f"{prefix}user_pro_pic_url: {comment.user_pro_pic_url}")

        except Exception as e:
            print(f"{prefix}❌ Error printing comment details: {e}")
