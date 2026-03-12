from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.profile import (
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileStatus,
)
from app.services.profile_service import profile_service
from app.services.queue_service import publish_status
from app.utils.helpers import normalize_fb_url

router = APIRouter()


@router.post("", response_model=ProfileCreateResponse)
async def create_profile(request: ProfileCreateRequest):
    """Submit a Facebook profile URL to scrape."""
    url, slug = normalize_fb_url(request.url)

    # Check duplicate
    existing = await profile_service.get_by_url(url)
    if existing:
        status = existing.get("status")
        if status == ProfileStatus.FINISHED.value:
            # Return existing finished profile
            return ProfileCreateResponse(
                id=existing["id"],
                url=existing["url"],
                status=status,
                created_at=existing["created_at"]
                if isinstance(existing["created_at"], str)
                else existing["created_at"].isoformat(),
            )
        elif status in (ProfileStatus.QUEUED.value, ProfileStatus.PROCESSING.value):
            # Already in queue
            return ProfileCreateResponse(
                id=existing["id"],
                url=existing["url"],
                status=status,
                created_at=existing["created_at"]
                if isinstance(existing["created_at"], str)
                else existing["created_at"].isoformat(),
            )
        elif status == ProfileStatus.FAILED.value:
            # Re-queue failed profile
            await profile_service.update_status(existing["id"], ProfileStatus.QUEUED.value)
            # Dispatch celery task
            from app.tasks.scrape_task import scrape_profile

            task = scrape_profile.delay(existing["id"], url)
            await profile_service.update_celery_task_id(existing["id"], task.id)
            publish_status(existing["id"], url, ProfileStatus.QUEUED.value)
            return ProfileCreateResponse(
                id=existing["id"],
                url=existing["url"],
                status=ProfileStatus.QUEUED.value,
                created_at=existing["created_at"]
                if isinstance(existing["created_at"], str)
                else existing["created_at"].isoformat(),
            )

    # Create new profile
    doc = await profile_service.create(url, slug)

    # Dispatch Celery scrape task
    from app.tasks.scrape_task import scrape_profile

    task = scrape_profile.delay(doc["id"], url)
    await profile_service.update_celery_task_id(doc["id"], task.id)

    # Publish queued event
    publish_status(doc["id"], url, ProfileStatus.QUEUED.value)

    return ProfileCreateResponse(
        id=doc["id"],
        url=url,
        status=ProfileStatus.QUEUED.value,
        created_at=doc["created_at"]
        if isinstance(doc["created_at"], str)
        else doc["created_at"].isoformat(),
    )


@router.get("")
async def list_profiles(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or URL"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords to match across all text fields"),
    district: Optional[str] = Query(None, description="Filter by district"),
    division: Optional[str] = Query(None, description="Filter by division"),
    upazila: Optional[str] = Query(None, description="Filter by upazila"),
    country: Optional[str] = Query(None, description="Filter by country"),
    college: Optional[str] = Query(None, description="Filter by college/university name"),
    high_school: Optional[str] = Query(None, description="Filter by high school name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List all profiles with optional filters and pagination."""
    return await profile_service.list_profiles(
        status=status,
        search=search,
        keywords=keywords,
        district=district,
        division=division,
        upazila=upazila,
        country=country,
        college=college,
        high_school=high_school,
        page=page,
        limit=limit,
    )


@router.get("/by-url")
async def get_profile_by_url(url: str = Query(..., description="Facebook profile URL")):
    """Get a profile by its Facebook URL."""
    normalized_url, _ = normalize_fb_url(url)
    doc = await profile_service.get_by_url(normalized_url)
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return doc


@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    """Get full profile by MongoDB _id."""
    doc = await profile_service.get_by_id(profile_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return doc


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile."""
    deleted = await profile_service.delete(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True}
