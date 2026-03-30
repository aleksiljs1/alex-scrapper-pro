"""
External Integration API
------------------------
Dedicated endpoints for external apps to submit Facebook profile URLs for
scraping and retrieve the results (status + location).

POST /api/external/scrape   — submit a URL, get profile_id + status back
GET  /api/external/result/{profile_id} — poll for status + location
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.profile import ProfileStatus
from app.services.profile_service import profile_service
from app.utils.helpers import normalize_fb_url

router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    url: str


class LocationCity(BaseModel):
    upazila: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None
    country: Optional[str] = None


class LocationResult(BaseModel):
    current_city: Optional[LocationCity] = None
    hometown: Optional[LocationCity] = None
    raw: Optional[str] = None


class ScrapeResponse(BaseModel):
    profile_id: str
    url: str
    status: str
    name: Optional[str] = None
    location: Optional[LocationResult] = None
    error: Optional[str] = None
    assigned_bot: Optional[str] = None
    bot_vnc_url: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_location(doc: dict) -> Optional[LocationResult]:
    """Extract location from a finished profile document."""
    profile = doc.get("profile") or {}
    if not profile:
        return None

    current_city = profile.get("current_city")
    hometown = profile.get("hometown")

    # Pull a human-readable raw string from intro_items
    raw = None
    for item in profile.get("intro_items", []):
        if "Lives in" in item or "From" in item:
            raw = item
            break

    if not current_city and not hometown and not raw:
        return None

    return LocationResult(
        current_city=LocationCity(**current_city) if current_city else None,
        hometown=LocationCity(**hometown) if hometown else None,
        raw=raw,
    )


_BOT_VNC_PORTS = {
    "scraper-bot-1": 9091,
    "scraper-bot-2": 9092,
    "scraper-bot-3": 9093,
    "scraper-bot-4": 9094,
    "scraper-bot-5": 9095,
    "scraper-bot-6": 9096,
    "scraper-bot-7": 9097,
    "scraper-bot-8": 9098,
}


def _doc_to_response(doc: dict) -> ScrapeResponse:
    status = doc.get("status", "unknown")
    profile = doc.get("profile") or {}
    assigned_bot = doc.get("assigned_bot")

    bot_vnc_url = None
    if assigned_bot and assigned_bot in _BOT_VNC_PORTS:
        bot_vnc_url = f"http://100.64.132.90:{_BOT_VNC_PORTS[assigned_bot]}"

    location = None
    if status == ProfileStatus.FINISHED:
        location = _build_location(doc)

    return ScrapeResponse(
        profile_id=doc["id"],
        url=doc.get("url", ""),
        status=status,
        name=profile.get("name") if status == ProfileStatus.FINISHED else None,
        location=location,
        error=doc.get("error_message") if status == ProfileStatus.FAILED else None,
        assigned_bot=assigned_bot,
        bot_vnc_url=bot_vnc_url,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_profile(request: ScrapeRequest):
    """
    Submit a Facebook profile URL for scraping.

    - If the profile is new → queues a scrape, returns status "queued"
    - If already queued or processing → returns current status
    - If already finished → returns status "finished" + location immediately
    - If previously failed → re-queues it, returns status "queued"
    """
    url, slug = normalize_fb_url(request.url)

    existing = await profile_service.get_by_url(url)

    if existing:
        status = existing.get("status")

        if status == ProfileStatus.FINISHED:
            return _doc_to_response(existing)

        if status in (ProfileStatus.QUEUED, ProfileStatus.PROCESSING):
            return _doc_to_response(existing)

        if status == ProfileStatus.FAILED:
            # Re-queue
            await profile_service.update_status(existing["id"], ProfileStatus.QUEUED.value)
            from app.tasks.scrape_task import scrape_profile as celery_scrape
            task = celery_scrape.delay(existing["id"], url)
            await profile_service.update_celery_task_id(existing["id"], task.id)
            refreshed = await profile_service.get_by_id(existing["id"])
            return _doc_to_response(refreshed)

    # New profile
    doc = await profile_service.create(url, slug)
    from app.tasks.scrape_task import scrape_profile as celery_scrape
    task = celery_scrape.delay(doc["id"], url)
    await profile_service.update_celery_task_id(doc["id"], task.id)
    refreshed = await profile_service.get_by_id(doc["id"])
    return _doc_to_response(refreshed)


@router.get("/result/{profile_id}", response_model=ScrapeResponse)
async def get_result(profile_id: str):
    """
    Poll for the scrape result by profile_id.

    Returns status + location. Poll every 10 seconds until status is
    "finished" or "failed". Typical scrape takes 1–3 minutes.
    """
    doc = await profile_service.get_by_id(profile_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _doc_to_response(doc)
