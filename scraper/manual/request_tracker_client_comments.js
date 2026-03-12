// Helper function to send data to FastAPI server
async function sendToTracker(endpoint, data) {
  try {
    const response = await fetch(`${TRACKER_SERVER_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    return await response.json();
  } catch (error) {
    console.error(`❌ Error sending to tracker server ${endpoint}:`, error);
    return null;
  }
}

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

    // Debug: Log all XHR GraphQL request bodies
    console.log(
      "🔍 DEBUG: XHR GraphQL request body preview: " +
      bodyStr.substring(0, 200) +
      "..."
    );

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

    // Track specific comment-related requests
    let requestType = null;

    // Check for various formats of CommentsListComponentsPaginationQuery
    if (
      bodyStr.includes("fb_api_req_friendly_name:CommentsListComponentsPaginationQuery") ||
      bodyStr.includes("fb_api_req_friendly_name%3ACommentsListComponentsPaginationQuery") ||
      bodyStr.includes("CommentsListComponentsPaginationQuery")
    ) {
      requestType = "VIEW_MORE_COMMENTS";
      console.log("🎯 DEBUG: Detected VIEW_MORE_COMMENTS request");
    }
    // Check for various formats of CommentListComponentsRootQuery
    else if (
      bodyStr.includes("fb_api_req_friendly_name:CommentListComponentsRootQuery") ||
      bodyStr.includes("fb_api_req_friendly_name%3ACommentListComponentsRootQuery") ||
      bodyStr.includes("CommentListComponentsRootQuery")
    ) {
      requestType = "COMMENT_SORT_CHANGE";
      console.log("🎯 DEBUG: Detected COMMENT_SORT_CHANGE request");
    }
    // Check for various formats of Depth1CommentsListPaginationQuery
    else if (
      bodyStr.includes("fb_api_req_friendly_name:Depth1CommentsListPaginationQuery") ||
      bodyStr.includes("fb_api_req_friendly_name%3ADepth1CommentsListPaginationQuery") ||
      bodyStr.includes("Depth1CommentsListPaginationQuery")
    ) {
      requestType = "VIEW_REPLIES_DEPTH1";
      console.log("🎯 DEBUG: Detected VIEW_REPLIES_DEPTH1 request");
    }
    // Check for various formats of Depth2CommentsListPaginationQuery
    else if (
      bodyStr.includes("fb_api_req_friendly_name:Depth2CommentsListPaginationQuery") ||
      bodyStr.includes("fb_api_req_friendly_name%3ADepth2CommentsListPaginationQuery") ||
      bodyStr.includes("Depth2CommentsListPaginationQuery")
    ) {
      requestType = "VIEW_REPLIES_DEPTH2";
      console.log("🎯 DEBUG: Detected VIEW_REPLIES_DEPTH2 request");
    }

    if (requestType) {
      console.log("📡 Tracking " + requestType + " GraphQL request...");

      // Generate unique request ID
      const requestId = "req_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);

      // Create pending request data
      const pendingRequest = {
        id: requestId,
        type: requestType,
        url: this._scraperBotUrl,
        requestBody: bodyStr,
        timestamp: Date.now(),
        completed: false,
        response: null
      };

      // Send to FastAPI server
      sendToTracker('/track/pending', pendingRequest).then(result => {
        if (result && result.status === 'success') {
          console.log("✅ Sent pending request to tracker: " + requestId);
        }
      });

      // Store request info for response tracking
      this._scraperBotRequestId = requestId;
      this._scraperBotRequestType = requestType;
      this._scraperBotRequestBody = bodyStr;
      this._scraperBotRequestUrl = this._scraperBotUrl;

      console.log("🔄 Created pending request: " + requestId + " (" + requestType + ")");

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
            const responseText = this.responseText || "";
            const hasValidContent =
              responseText.includes("comment") ||
              responseText.includes("Comment") ||
              responseText.includes("feedback") ||
              responseText.includes("Feedback") ||
              responseText.includes('__typename":"Feedback"');

            // Send response update to FastAPI server
            const updateData = {
              requestId: this._scraperBotRequestId,
              status: this.status,
              responseBody: this.responseText,
              isValid: hasValidContent
            };

            sendToTracker('/track/response', updateData).then(result => {
              if (result && result.status === 'success') {
                console.log(
                  "✅ Sent response update to tracker for " +
                  this._scraperBotRequestType +
                  " request #" +
                  this._scraperBotRequestId
                );
              }
            });

            if (this.status === 200) {
              if (hasValidContent) {
                console.log(
                  "✅ Valid response for " +
                  this._scraperBotRequestType +
                  " request #" +
                  this._scraperBotRequestId
                );
              } else {
                console.log(
                  "❌ Invalid response for " +
                  this._scraperBotRequestType +
                  " request #" +
                  this._scraperBotRequestId +
                  " (no comment data)"
                );
              }
            } else {
              console.log(
                "❌ Error response for " +
                this._scraperBotRequestType +
                " request #" +
                this._scraperBotRequestId +
                " (status: " +
                this.status +
                ")"
              );
            }
          } catch (err) {
            console.log(
              "⚠️ Error processing response for request #" +
              this._scraperBotRequestId +
              ":",
              err
            );
          }
        }
      };
    }
  }

  // Continue with normal requests
  return originalXHRSend.apply(this, [data]);
};

// Function to wait for request completion (calls FastAPI server)
window.scraperBotWaitForRequest = async function (
  requestType,
  startTimeMs,
  detectionTimeoutMs,
  totalTimeoutMs
) {
  try {
    const response = await fetch(`${TRACKER_SERVER_URL}/wait?request_type=${requestType}&start_time_ms=${startTimeMs}&detection_timeout_ms=${detectionTimeoutMs}&total_timeout_ms=${totalTimeoutMs}`, {
      method: 'POST'
    });
    const result = await response.json();

    if (result.success) {
      return result;
    } else {
      throw result.error;
    }
  } catch (error) {
    console.error("❌ Error waiting for request:", error);
    throw {
      type: "NetworkError",
      message: "Failed to communicate with tracker server"
    };
  }
};

console.log("✅ Request tracking with FastAPI server enabled - will send all tracked requests to " + TRACKER_SERVER_URL);
