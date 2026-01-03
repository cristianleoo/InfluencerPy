from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel
from influencerpy.types.models import Platform

class PostModel(SQLModel, table=True):
    """Database model for posts."""
    __tablename__ = "posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    platform: str
    status: str = Field(default="draft")  # draft, scheduled, posted, failed
    scheduled_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    posted_at: Optional[datetime] = None
    external_id: Optional[str] = None
    scout_id: Optional[int] = Field(default=None, foreign_key="scouts.id")

class NewsItemModel(SQLModel, table=True):
    """Database model for seen news items."""
    __tablename__ = "news_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str = Field(unique=True)
    summary: Optional[str] = None
    source: str
    seen_at: datetime = Field(default_factory=datetime.utcnow)
    is_processed: bool = Field(default=False)

class ScoutModel(SQLModel, table=True):
    """Database model for Scouts (configured tools)."""
    __tablename__ = "scouts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    type: str  # search, subreddit, rss
    config_json: str  # JSON string of params
    intent: str = Field(default="scouting")  # "scouting" or "generation" - determines output format
    platforms: str = Field(default="[]")  # JSON list of platforms ["x", "linkedin", etc.] - only used for generation
    telegram_review: bool = Field(default=False)  # Enable Telegram approval workflow
    prompt_template: Optional[str] = None
    schedule_cron: Optional[str] = None
    last_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ScoutFeedbackModel(SQLModel, table=True):
    """Database model for user feedback on Scout results."""
    __tablename__ = "scout_feedback"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    scout_id: int = Field(foreign_key="scouts.id")
    content_url: str
    action: str  # approved, rejected
    feedback_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ScoutCalibrationModel(SQLModel, table=True):
    """Database model for Scout calibration feedback."""
    __tablename__ = "scout_calibrations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    scout_id: int = Field(foreign_key="scouts.id")
    content_item_url: str
    generated_draft: str
    user_feedback: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# from pgvector.sqlalchemy import Vector

class ContentEmbedding(SQLModel, table=True):
    """Database model for content embeddings."""
    __tablename__ = "content_embeddings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content_hash: str = Field(index=True)  # Fast exact match check
    embedding_json: str  # Stored as JSON string of floats
    source_type: str  # 'retrieved' or 'generated'
    created_at: datetime = Field(default_factory=datetime.utcnow)

