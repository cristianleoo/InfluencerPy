from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class Platform(str, Enum):
    X = "x"
    # TELEGRAM = "telegram"

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    ARTICLE = "article"

@dataclass
class ContentItem:
    """Represents a raw item fetched from a source (e.g., a news article)."""
    source_id: str
    title: str
    url: str
    summary: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def display_title(self) -> str:
        return f"[{self.published_at.strftime('%Y-%m-%d')}] {self.title}"

@dataclass
class PostDraft:
    """Represents a piece of content ready to be posted."""
    content: str
    platforms: List[Platform]
    media_urls: List[str] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    reply_to_id: Optional[str] = None
