import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time
from contextlib import asynccontextmanager


# Pydantic models for request/response data
class PendingRequest(BaseModel):
    id: str
    type: str
    url: str
    requestBody: str
    timestamp: int
    completed: bool = False
    response: Optional[Any] = None
    status: Optional[int] = None
    responseBody: Optional[str] = None
    completedAt: Optional[int] = None
    isValid: Optional[bool] = None


class ResponseData(BaseModel):
    id: int
    requestId: str
    requestType: str
    url: str
    requestBody: str
    responseBody: str
    status: int
    timestamp: int


class RequestUpdate(BaseModel):
    requestId: str
    status: int
    responseBody: str
    isValid: bool


class RequestTracker:
    """Singleton class to track requests and responses"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize tracking lists and counters"""
        self.pending_requests: List[PendingRequest] = []
        self.tracked_responses: List[ResponseData] = []
        self.response_count = 0
        self.max_pending_requests = 100
        self.max_tracked_responses = 100
        self._lock = threading.Lock()

    def add_pending_request(self, request: PendingRequest) -> None:
        """Add a pending request to the list"""
        with self._lock:
            self.pending_requests.append(request)
            # Remove oldest if limit exceeded
            if len(self.pending_requests) > self.max_pending_requests:
                self.pending_requests.pop(0)

    def update_request_response(
        self, request_id: str, status: int, response_body: str, is_valid: bool
    ) -> bool:
        """Update a pending request with response data"""
        with self._lock:
            for i, req in enumerate(self.pending_requests):
                if req.id == request_id:
                    req.completed = True
                    req.status = status
                    req.responseBody = response_body
                    req.completedAt = int(time.time() * 1000)
                    req.isValid = is_valid

                    # If valid response, also add to tracked responses
                    if status == 200 and is_valid:
                        self.response_count += 1
                        response_data = ResponseData(
                            id=self.response_count,
                            requestId=req.id,
                            requestType=req.type,
                            url=req.url,
                            requestBody=req.requestBody,
                            responseBody=response_body,
                            status=status,
                            timestamp=int(time.time() * 1000),
                        )
                        self.tracked_responses.append(response_data)

                        # Remove oldest if limit exceeded
                        if len(self.tracked_responses) > self.max_tracked_responses:
                            self.tracked_responses.pop(0)

                    return True
            return False

    def get_pending_requests(self) -> List[Dict]:
        """Get all pending requests"""
        with self._lock:
            return [req.model_dump() for req in self.pending_requests]

    def get_tracked_responses(self) -> List[Dict]:
        """Get and clear tracked responses"""
        with self._lock:
            responses = [resp.model_dump() for resp in self.tracked_responses]
            self.tracked_responses.clear()
            return responses

    def wait_for_request(
        self,
        request_type: str,
        start_time_ms: int,
        detection_timeout_ms: int,
        total_timeout_ms: int,
    ) -> Dict:
        """Wait for a specific request type to be triggered and completed"""
        detection_end = start_time_ms + detection_timeout_ms
        total_end = start_time_ms + total_timeout_ms
        target_request = None

        # Phase 1: Detection phase
        while time.time() * 1000 < detection_end:
            with self._lock:
                for req in reversed(self.pending_requests):
                    if req.type == request_type and req.timestamp >= start_time_ms:
                        target_request = req
                        break

            if target_request:
                break

            time.sleep(0.2)

        if not target_request:
            return {"success": True, "reason": "no_request_needed"}

        # Phase 2: Wait for completion
        while time.time() * 1000 < total_end:
            with self._lock:
                for req in self.pending_requests:
                    if req.id == target_request.id:
                        if req.completed:
                            if req.status != 200:
                                return {
                                    "success": False,
                                    "error": {
                                        "type": "ErrorResponse",
                                        "message": f"Non-200 response for {request_type}: status {req.status}",
                                    },
                                }
                            if not req.isValid:
                                return {
                                    "success": False,
                                    "error": {
                                        "type": "InvalidResponse",
                                        "message": f"No valid response found for {request_type}",
                                    },
                                }
                            return {
                                "success": True,
                                "reason": "completed",
                                "requestId": req.id,
                            }
                        break

            time.sleep(0.5)

        return {
            "success": False,
            "error": {
                "type": "NetworkError",
                "message": f"Request {request_type} did not complete within timeout",
            },
        }

    def clear_all(self):
        """Clear all tracked data"""
        with self._lock:
            self.pending_requests.clear()
            self.tracked_responses.clear()
            self.response_count = 0


# Create global tracker instance
tracker = RequestTracker()


# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Request Tracker Server starting...")
    yield
    # Shutdown
    print("🛑 Request Tracker Server shutting down...")
    tracker.clear_all()


app = FastAPI(lifespan=lifespan)

# Configure CORS to allow requests from any origin (Facebook)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/track/pending")
async def track_pending_request(request: PendingRequest):
    """Endpoint to track a new pending request"""
    try:
        tracker.add_pending_request(request)
        return {"status": "success", "message": f"Request {request.id} tracked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/track/response")
async def track_response(update: RequestUpdate):
    """Endpoint to update a pending request with response data"""
    try:
        success = tracker.update_request_response(
            update.requestId, update.status, update.responseBody, update.isValid
        )
        if success:
            return {
                "status": "success",
                "message": f"Request {update.requestId} updated",
            }
        else:
            return {
                "status": "error",
                "message": f"Request {update.requestId} not found",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pending")
async def get_pending_requests():
    """Get all pending requests"""
    return tracker.get_pending_requests()


@app.get("/responses")
async def get_tracked_responses():
    """Get and clear tracked responses"""
    return tracker.get_tracked_responses()


@app.post("/wait")
async def wait_for_request(
    request_type: str,
    start_time_ms: int,
    detection_timeout_ms: int = 2000,
    total_timeout_ms: int = 60000,
):
    """Wait for a specific request type to complete"""
    try:
        # Run blocking wait in thread pool to not block async loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            tracker.wait_for_request,
            request_type,
            start_time_ms,
            detection_timeout_ms,
            total_timeout_ms,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
async def clear_all_data():
    """Clear all tracked data"""
    tracker.clear_all()
    return {"status": "success", "message": "All data cleared"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "pending_requests": len(tracker.pending_requests),
        "tracked_responses": len(tracker.tracked_responses),
        "response_count": tracker.response_count,
    }


def run_server(host: str = "127.0.0.1", port: int = 8888):
    """Run the FastAPI server"""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
