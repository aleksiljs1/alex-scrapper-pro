from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class ProfileStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    FINISHED = "finished"
    FAILED = "failed"


# ─── About Tab Models ────────────────────────────────────────

class AboutFieldEntity(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    profile_url: Optional[str] = None
    is_verified: bool = False
    typename: Optional[str] = None


class AboutField(BaseModel):
    text: Optional[str] = None
    field_type: Optional[str] = None
    entities: List[AboutFieldEntity] = []
    details: List[str] = []
    icon_url: Optional[str] = None


class AboutSection(BaseModel):
    section_type: Optional[str] = None
    title: Optional[str] = None
    fields: List[AboutField] = []


class AboutTab(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    sections: List[AboutSection] = []


# ─── Scraped Profile Data (raw from scraper) ─────────────────

class ScrapedProfileData(BaseModel):
    """Profile data as stored in MongoDB (raw scraped format)."""
    profile_id: Optional[str] = None
    name: Optional[str] = None
    profile_url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    profile_picture_path: Optional[str] = None
    cover_photo_url: Optional[str] = None
    cover_photo_path: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    followers_count: Optional[int] = None
    friends_count: Optional[int] = None
    work: List[Any] = []
    education: List[Any] = []
    current_city: Optional[Any] = None
    hometown: Optional[Any] = None
    relationship_status: Optional[str] = None
    intro_items: List[str] = []
    about_details: dict = {}
    about_tabs: List[AboutTab] = []
    joined_facebook: Optional[str] = None
    profile_updated: Optional[str] = None


# ─── Final Profile Format (EXAMPLE_PROFILE.json) ─────────────

class WorkItem(BaseModel):
    organization: Optional[str] = None
    designation: Optional[str] = None
    details: List[str] = []


class EducationItem(BaseModel):
    institution: Optional[str] = None
    type: Optional[str] = None
    field_of_study: Optional[str] = None
    details: List[str] = []


class LocationInfo(BaseModel):
    upazila: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None
    country: Optional[str] = None


class BirthdayInfo(BaseModel):
    birthday: Optional[str] = None
    birthdate: Optional[str] = None
    birth_year: Optional[str] = None


class PartnerInfo(BaseModel):
    name: Optional[str] = None
    profile_url: Optional[str] = None


class RelationshipItem(BaseModel):
    status: Optional[str] = None
    partner_info: Optional[PartnerInfo] = None
    details: List[str] = []


class FamilyMember(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    profile_url: Optional[str] = None


class NamesInfo(BaseModel):
    nicknames: List[str] = []
    name_pronunciation: Optional[str] = None


class FinalProfile(BaseModel):
    """The final formatted profile for database storage (EXAMPLE_PROFILE.json format)."""
    profile_id: Optional[str] = None
    name: Optional[str] = None
    profile_url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    profile_picture_path: Optional[str] = None
    cover_photo_url: Optional[str] = None
    cover_photo_path: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    followers_count: Optional[int] = None
    friends_count: Optional[int] = None
    work: List[WorkItem] = []
    education: List[EducationItem] = []
    current_city: Optional[LocationInfo] = None
    hometown: Optional[LocationInfo] = None
    birthday_info: Optional[BirthdayInfo] = None
    relationship: List[RelationshipItem] = []
    family_members: List[FamilyMember] = []
    gender: Optional[str] = None
    language_skills: List[str] = []
    names: Optional[NamesInfo] = None
    intro_items: List[str] = []
    scraped_at: Optional[str] = None


# ─── API Request/Response Models ─────────────────────────────

class ProfileCreateRequest(BaseModel):
    url: str


class ProfileCreateResponse(BaseModel):
    id: str
    url: str
    status: ProfileStatus
    created_at: str


class ProfileDocument(BaseModel):
    """Full profile document as stored in MongoDB."""
    id: str = Field(alias="_id")
    url: str
    url_slug: str
    status: ProfileStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    scraped_at: Optional[str] = None
    celery_task_id: Optional[str] = None
    json_file_path: Optional[str] = None
    profile: Optional[dict] = None
    scraped_data: Optional[dict] = None

    class Config:
        populate_by_name = True


class ProfileListResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    pages: int


class QueueStatusResponse(BaseModel):
    queued: int
    processing: int
    finished: int
    failed: int
