from fastapi import APIRouter

from app.services.profile_service import profile_service

router = APIRouter()


@router.get("/status")
async def get_queue_status():
    """Get current queue summary counts."""
    return await profile_service.get_queue_status()
