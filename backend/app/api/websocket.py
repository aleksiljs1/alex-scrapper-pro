from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import manager

ws_router = APIRouter()


@ws_router.websocket("/ws/queue-status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time queue status updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; wait for messages (ping/pong handled by framework)
            data = await websocket.receive_text()
            # Echo back or ignore — client doesn't need to send meaningful data
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
