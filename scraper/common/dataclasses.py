from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Author:
    name: str
    author_id: str  # Changed from 'id' to 'author_id'
    url: str
    profile_image_path: Optional[str] = None
    profile_image_url: Optional[str] = None


@dataclass
class Reactions:
    Total: Optional[int] = None
    Sad: Optional[int] = None
    Love: Optional[int] = None
    Wow: Optional[int] = None
    Like: Optional[int] = None
    Haha: Optional[int] = None
    Angry: Optional[int] = None
    Care: Optional[int] = None


@dataclass
class Comment:
    comment_id: str  # Changed from 'id' to 'comment_id'
    url: str
    user_pro_pic_path: str
    comment_time: Optional[datetime]
    user_id: str
    author: Author
    user_name: str
    user_profile_url: str
    user_gender: str
    comment_text: str
    reactions: Reactions
    total_replies: int
    comment_attachment_path: Optional[str]
    comments_replies: List["Comment"] = field(default_factory=list)
    parent: str = "root"
    reply_to: Optional[str] = None
    # New fields for improved tracking
    _internal_node_id: Optional[str] = None  # Store node.id for parent-child mapping
    _parent_node_id: Optional[str] = None  # Store parent's node.id for replies
    _reply_to_node_id: Optional[str] = None # Author is replying to this node.id
    user_pro_pic_url: Optional[str] = None  # Store profile picture URL before download
    image_accessibility_caption: str | None = None

@dataclass
class FacebookPost:
    post_id: str  # Changed from 'id' to 'post_id'
    source: str
    post_url: str
    post_title: str
    posted_at: Optional[datetime]
    post_text: str
    reactions: Reactions
    author: Author
    type: Optional[str]
    checksum: Optional[str]
    total_comments: Optional[int]
    total_shares: Optional[int]
    total_views: Optional[int]
    virality_score: Optional[float]
    attached_post: 'FacebookPost | None' = None
    percent_comments: float | None = None
    comments: List[Comment] = field(default_factory=list)
    featured_images_path: List[str] = field(default_factory=list)
    platform: str = "F"
    metadata: Dict = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    total_comments_scraped: Optional[int] = (
        0  # Total scraped comments including all nested replies
    )
    image_accessibility_captions: list[str] = field(default_factory=list[str])

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {"source": {}, "group": {}, "post": {}, "author": {}}
