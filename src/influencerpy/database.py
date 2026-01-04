import logging
from sqlmodel import SQLModel, create_engine, Session, text
from influencerpy.config import CONFIG_DIR
from influencerpy.types.schema import (
    PostModel,
    NewsItemModel,
    ScoutModel,
    ScoutFeedbackModel,
    ScoutCalibrationModel,
    ContentEmbedding,
)
from influencerpy.types.rss import RSSFeedModel, RSSEntryModel

logger = logging.getLogger(__name__)

# Database Setup
sqlite_file_name = "influencerpy.db"
sqlite_path = CONFIG_DIR / sqlite_file_name
sqlite_url = f"sqlite:///{sqlite_path}"

# Use Postgres
# TODO: Move credentials to config/env
# postgres_url = "postgresql://influencerpy:password@localhost:5432/influencerpy"

engine = create_engine(sqlite_url)

def _migrate_rss_entries_add_processed_fields():
    """Add is_processed and processed_at fields to rss_entries table for existing databases."""
    try:
        with Session(engine) as session:
            # Check if columns already exist
            result = session.exec(text("PRAGMA table_info(rss_entries)"))
            columns = [row[1] for row in result] if result else []
            
            if "is_processed" not in columns:
                logger.info("Adding is_processed column to rss_entries table...")
                session.exec(text(
                    "ALTER TABLE rss_entries ADD COLUMN is_processed BOOLEAN DEFAULT 0"
                ))
                session.exec(text(
                    "CREATE INDEX IF NOT EXISTS idx_rss_entries_is_processed ON rss_entries(is_processed)"
                ))
                logger.info("✓ Added is_processed column")
            
            if "processed_at" not in columns:
                logger.info("Adding processed_at column to rss_entries table...")
                session.exec(text(
                    "ALTER TABLE rss_entries ADD COLUMN processed_at DATETIME"
                ))
                logger.info("✓ Added processed_at column")
            
            session.commit()
    except Exception as e:
        # This is OK if table doesn't exist yet (new database) or migration already applied
        logger.debug(f"Migration check: {e}")

def create_db_and_tables():
    """Create database tables and run migrations."""
    # Create tables first (will create all columns for new databases)
    SQLModel.metadata.create_all(engine)
    
    # Run migration for existing databases (idempotent - safe to call multiple times)
    _migrate_rss_entries_add_processed_fields()

def get_session():
    with Session(engine) as session:
        yield session
