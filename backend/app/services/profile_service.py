import math
from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongodb import get_collection
from app.models.profile import ProfileStatus


def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document for JSON serialization."""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    if doc and "created_at" in doc and isinstance(doc["created_at"], datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if doc and "updated_at" in doc and isinstance(doc["updated_at"], datetime):
        doc["updated_at"] = doc["updated_at"].isoformat()
    return doc


class ProfileService:
    """CRUD operations for profiles collection."""

    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("profiles")
        return self._collection

    async def create(self, url: str, url_slug: str) -> dict:
        """Create a new profile document in queued status."""
        now = datetime.utcnow()
        doc = {
            "url": url,
            "url_slug": url_slug,
            "status": ProfileStatus.QUEUED.value,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
            "scraped_at": None,
            "celery_task_id": None,
            "json_file_path": None,
            "profile": None,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _serialize_doc(doc)

    async def get_by_id(self, profile_id: str) -> Optional[dict]:
        """Get a profile by its MongoDB _id."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(profile_id)})
        except Exception:
            return None
        if doc:
            return _serialize_doc(doc)
        return None

    async def get_by_url(self, url: str) -> Optional[dict]:
        """Get a profile by its Facebook URL."""
        doc = await self.collection.find_one({"url": url})
        if doc:
            return _serialize_doc(doc)
        return None

    @staticmethod
    def _regex_filter(value: str) -> dict:
        """Build a case-insensitive regex filter from a user string."""
        import re
        escaped = re.escape(value.strip())
        return {"$regex": escaped, "$options": "i"}

    async def list_profiles(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        keywords: Optional[str] = None,
        district: Optional[str] = None,
        division: Optional[str] = None,
        upazila: Optional[str] = None,
        country: Optional[str] = None,
        college: Optional[str] = None,
        high_school: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List profiles with flexible filters and pagination."""
        conditions: list[dict] = []

        # ── Status filter ──
        if status:
            conditions.append({"status": status})

        # ── Quick search (name / URL) ──
        if search:
            pat = self._regex_filter(search)
            conditions.append(
                {"$or": [
                    {"profile.name": pat},
                    {"url": pat},
                    {"url_slug": pat},
                ]}
            )

        # ── Location filters ──
        if district:
            pat = self._regex_filter(district)
            conditions.append(
                {"$or": [
                    {"profile.current_city.district": pat},
                    {"profile.hometown.district": pat},
                ]}
            )
        if division:
            pat = self._regex_filter(division)
            conditions.append(
                {"$or": [
                    {"profile.current_city.division": pat},
                    {"profile.hometown.division": pat},
                ]}
            )
        if upazila:
            pat = self._regex_filter(upazila)
            conditions.append(
                {"$or": [
                    {"profile.current_city.upazila": pat},
                    {"profile.hometown.upazila": pat},
                ]}
            )
        if country:
            pat = self._regex_filter(country)
            conditions.append(
                {"$or": [
                    {"profile.current_city.country": pat},
                    {"profile.hometown.country": pat},
                ]}
            )

        # ── Education filters ──
        if college:
            pat = self._regex_filter(college)
            conditions.append(
                {"profile.education": {
                    "$elemMatch": {
                        "institution": pat,
                        "type": {"$in": ["College", "University", None]},
                    }
                }}
            )
        if high_school:
            pat = self._regex_filter(high_school)
            conditions.append(
                {"profile.education": {
                    "$elemMatch": {
                        "institution": pat,
                        "type": "High School",
                    }
                }}
            )

        # ── Keywords (match across many text fields at once) ──
        if keywords:
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
            for kw in kw_list:
                pat = self._regex_filter(kw)
                conditions.append(
                    {"$or": [
                        {"profile.name": pat},
                        {"url": pat},
                        {"profile.bio": pat},
                        {"profile.category": pat},
                        {"profile.work.organization": pat},
                        {"profile.work.designation": pat},
                        {"profile.education.institution": pat},
                        {"profile.current_city.district": pat},
                        {"profile.current_city.division": pat},
                        {"profile.hometown.district": pat},
                        {"profile.hometown.division": pat},
                        {"profile.intro_items": pat},
                        {"profile.language_skills": pat},
                    ]}
                )

        query = {"$and": conditions} if conditions else {}

        total = await self.collection.count_documents(query)
        pages = math.ceil(total / limit) if total > 0 else 1
        skip = (page - 1) * limit

        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        items = []
        async for doc in cursor:
            items.append(_serialize_doc(doc))

        return {
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
        }

    async def update_status(
        self,
        profile_id: str,
        status: str,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Update the status of a profile."""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if error_message is not None:
            update_data["error_message"] = error_message
        update_data.update(kwargs)

        result = await self.collection.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": update_data},
        )
        return result.modified_count > 0

    async def update_celery_task_id(self, profile_id: str, task_id: str) -> bool:
        """Set the Celery task ID for a profile."""
        result = await self.collection.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": {"celery_task_id": task_id, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    async def delete(self, profile_id: str) -> bool:
        """Delete a profile by its MongoDB _id."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(profile_id)})
        except Exception:
            return False
        return result.deleted_count > 0

    async def get_queue_status(self) -> dict:
        """Get count of profiles by status."""
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        counts = {"queued": 0, "processing": 0, "finished": 0, "failed": 0}
        async for doc in self.collection.aggregate(pipeline):
            if doc["_id"] in counts:
                counts[doc["_id"]] = doc["count"]
        return counts


# Global singleton
profile_service = ProfileService()
