from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class RSSFeedModel(SQLModel, table=True):
    """Database model for RSS feed subscriptions."""
    __tablename__ = "rss_feeds"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    title: Optional[str] = None
    scout_id: Optional[int] = Field(default=None, foreign_key="scouts.id") # Optional link to a specific scout
    added_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None
    update_interval: int = Field(default=60) # minutes
    
    # Authentication (stored as JSON string if needed, or separate fields)
    auth_json: Optional[str] = None
    headers_json: Optional[str] = None

    entries: List["RSSEntryModel"] = Relationship(back_populates="feed")

class RSSEntryModel(SQLModel, table=True):
    """Database model for RSS feed entries."""
    __tablename__ = "rss_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="rss_feeds.id")
    entry_id: str = Field(index=True) # Unique ID from the feed
    title: str
    link: str
    published: Optional[datetime] = None
    author: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    categories_json: Optional[str] = None # JSON list of categories
    
    feed: RSSFeedModel = Relationship(back_populates="entries")
    created_at: datetime = Field(default_factory=datetime.utcnow)

