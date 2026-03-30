from fastapi import APIRouter

from app.api.profiles import router as profiles_router
from app.api.queue import router as queue_router
from app.api.external import router as external_router

api_router = APIRouter()

api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
api_router.include_router(queue_router, prefix="/queue", tags=["queue"])
api_router.include_router(external_router, prefix="/external", tags=["external"])
