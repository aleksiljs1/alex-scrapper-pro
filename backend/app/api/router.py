from fastapi import APIRouter

from app.api.profiles import router as profiles_router
from app.api.queue import router as queue_router

api_router = APIRouter()

api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
api_router.include_router(queue_router, prefix="/queue", tags=["queue"])
