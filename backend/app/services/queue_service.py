"""Queue service — manages state transitions and publishes events."""

import json
from datetime import datetime

import redis
from app.config import settings


def publish_status(profile_id: str, url: str, status: str, name: str = None):
    """Publish a status change event to Redis pub/sub for WebSocket broadcast."""
    r = redis.Redis.from_url(settings.REDIS_URL)
    try:
        r.publish(
            "queue_updates",
            json.dumps(
                {
                    "event": "status_change",
                    "data": {
                        "id": profile_id,
                        "url": url,
                        "status": status,
                        "name": name,
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                    },
                }
            ),
        )
    finally:
        r.close()
