import asyncio
import json
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import api_router
from app.api.websocket import ws_router
from app.db.mongodb import connect_db, close_db
from app.ws.manager import manager


async def redis_subscriber():
    """Background task: subscribe to Redis pub/sub and broadcast to WebSocket clients."""
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("queue_updates")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await manager.broadcast(data)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("queue_updates")
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_db()
    task = asyncio.create_task(redis_subscriber())
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await close_db()


app = FastAPI(
    title="Facebook Profile Scraper API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
