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
    role: str = Field(default="delivery")  # delivery or verification
    delivery_targets_json: str = Field(default="[]")  # JSON list of final target platforms

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


class ScoutNodeModel(SQLModel, table=True):
    """Reusable listening/source node."""
    __tablename__ = "scout_nodes"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str
    config_json: str
    schedule_cron: Optional[str] = None
    last_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentNodeModel(SQLModel, table=True):
    """Reusable transform/generation node."""
    __tablename__ = "agent_nodes"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    intent: str = Field(default="scouting")
    prompt_template: Optional[str] = None
    config_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChannelNodeModel(SQLModel, table=True):
    """Reusable output/delivery node."""
    __tablename__ = "channel_nodes"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    platforms: str = Field(default="[]")
    telegram_review: bool = Field(default=False)
    config_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FlowModel(SQLModel, table=True):
    """Workflow linking scout, agent, and channel nodes."""
    __tablename__ = "flows"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    scout_node_id: int = Field(foreign_key="scout_nodes.id")
    agent_node_id: int = Field(foreign_key="agent_nodes.id")
    channel_node_id: int = Field(foreign_key="channel_nodes.id")
    legacy_scout_id: Optional[int] = Field(default=None, foreign_key="scouts.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FlowScoutLinkModel(SQLModel, table=True):
    """Links multiple scout nodes into one flow."""
    __tablename__ = "flow_scout_links"

    id: Optional[int] = Field(default=None, primary_key=True)
    flow_id: int = Field(foreign_key="flows.id")
    scout_node_id: int = Field(foreign_key="scout_nodes.id")
    position: int = Field(default=0)


class FlowChannelLinkModel(SQLModel, table=True):
    """Links multiple channel nodes into one flow."""
    __tablename__ = "flow_channel_links"

    id: Optional[int] = Field(default=None, primary_key=True)
    flow_id: int = Field(foreign_key="flows.id")
    channel_node_id: int = Field(foreign_key="channel_nodes.id")
    position: int = Field(default=0)

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
