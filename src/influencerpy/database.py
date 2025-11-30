from sqlmodel import SQLModel, create_engine, Session
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

# Database Setup
sqlite_file_name = "influencerpy.db"
sqlite_path = CONFIG_DIR / sqlite_file_name
sqlite_url = f"sqlite:///{sqlite_path}"

# Use Postgres
# TODO: Move credentials to config/env
# postgres_url = "postgresql://influencerpy:password@localhost:5432/influencerpy"

engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
