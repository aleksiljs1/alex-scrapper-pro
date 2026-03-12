# Server-Based Request Tracking Implementation

## Overview
This implementation replaces the browser-based JavaScript memory storage with a FastAPI server that tracks network requests and responses. This solves the memory leak issue where JavaScript arrays would grow indefinitely and not get garbage collected.

## Architecture

### Components

1. **FastAPI Server (`request_tracker_server.py`)**
   - Runs on localhost:8888 (configurable)
   - Manages request/response tracking in Python memory
   - Provides REST endpoints for tracking operations
   - Automatic cleanup and memory management

2. **JavaScript Client (`request_tracker_client.js`)**
   - Intercepts XMLHttpRequest calls
   - Sends request data to FastAPI server
   - No longer stores data in browser memory

3. **Updated Scraper (`comment_scraper.py`)**
   - Starts FastAPI server in background thread
   - Configurable to use server tracking or fallback to JS-only
   - Fetches tracked responses from server instead of browser

## Benefits

### Memory Management
- **Before**: JavaScript arrays grew indefinitely in browser memory
- **After**: Python server manages memory with proper garbage collection
- Lists are limited to 100 items with automatic cleanup of oldest entries

### Performance
- Reduced browser memory footprint
- Better handling of long-running scraping sessions
- Server can process and filter data more efficiently

### Reliability
- Separation of concerns: browser handles navigation, server handles data
- Automatic fallback to JS-only mode if server fails
- Clear error handling and recovery

## API Endpoints

### POST `/track/pending`
Track a new pending request
```json
{
  "id": "req_12345",
  "type": "VIEW_MORE_COMMENTS",
  "url": "https://...",
  "requestBody": "...",
  "timestamp": 1234567890
}
```

### POST `/track/response`
Update a pending request with response data
```json
{
  "requestId": "req_12345",
  "status": 200,
  "responseBody": "...",
  "isValid": true
}
```

### GET `/responses`
Get and clear all tracked responses
Returns array of response objects

### POST `/wait`
Wait for a specific request type to complete
Query parameters:
- `request_type`: Type of request to wait for
- `start_time_ms`: Start time in milliseconds
- `detection_timeout_ms`: Detection phase timeout
- `total_timeout_ms`: Total timeout

### POST `/clear`
Clear all tracked data

### GET `/health`
Health check endpoint

## Usage

### Basic Usage
```python
from comment_scraper import TabBasedCommentScraper

# With server tracking (default)
scraper = TabBasedCommentScraper(
    driver=driver,
    target_url=url,
    use_server_tracking=True,
    server_port=8888
)

# Without server tracking (JS-only fallback)
scraper = TabBasedCommentScraper(
    driver=driver,
    target_url=url,
    use_server_tracking=False
)
```

### Running the Server Standalone
```python
from request_tracker_server import run_server
run_server(host="127.0.0.1", port=8888)
```

## Configuration

### Server Settings
- `server_port`: Port for FastAPI server (default: 8888)
- `max_pending_requests`: Maximum pending requests to track (default: 100)
- `max_tracked_responses`: Maximum responses to store (default: 100)

### Automatic Fallback
The system automatically falls back to JavaScript-only tracking if:
- Server fails to start
- Server becomes unresponsive
- JavaScript client file is missing

## Testing

Run the test script to verify both modes:
```bash
# Test both modes
python test_server_tracking.py

# Test server mode only
python test_server_tracking.py --server

# Test JS-only mode
python test_server_tracking.py --js-only
```

## Memory Comparison

### JavaScript-Only Mode
- Arrays grow without limit
- No garbage collection during session
- Memory usage: O(n) where n = total requests
- Browser slowdown after extended use

### Server-Based Mode
- Fixed maximum array size (100 items)
- Automatic cleanup of old entries
- Memory usage: O(1) constant
- No browser performance degradation

## Error Handling

1. **Server Start Failure**: Automatic fallback to JS-only mode
2. **Communication Errors**: Graceful degradation with error logging
3. **Response Validation**: Both client and server validate responses
4. **Timeout Management**: Configurable timeouts with proper error reporting

## Future Improvements

1. **Persistence**: Add optional database backing for request history
2. **Analytics**: Real-time monitoring dashboard
3. **Compression**: Compress large response bodies
4. **Rate Limiting**: Add request throttling capabilities
5. **WebSocket**: Replace polling with WebSocket for real-time updates