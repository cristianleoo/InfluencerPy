import logging
from sqlmodel import SQLModel, create_engine, Session, select, text
from influencerpy.config import CONFIG_DIR
from influencerpy.types.schema import (
    AgentNodeModel,
    ChannelNodeModel,
    FlowChannelLinkModel,
    FlowScoutLinkModel,
    PostModel,
    NewsItemModel,
    FlowModel,
    ScoutModel,
    ScoutNodeModel,
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


def _get_table_columns(session: Session, table_name: str) -> list[str]:
    result = session.exec(text(f"PRAGMA table_info({table_name})"))
    return [row[1] for row in result] if result else []


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


def _migrate_scouts_add_intent_field():
    """Add intent column to older scouts tables."""
    try:
        with Session(engine) as session:
            columns = _get_table_columns(session, "scouts")
            if "intent" not in columns:
                logger.info("Adding intent column to scouts table...")
                session.exec(
                    text("ALTER TABLE scouts ADD COLUMN intent VARCHAR DEFAULT 'scouting'")
                )
                session.exec(
                    text("UPDATE scouts SET intent = 'scouting' WHERE intent IS NULL")
                )
                session.commit()
    except Exception as e:
        logger.debug(f"Scout intent migration check: {e}")


def _migrate_flows_from_legacy_scouts():
    """Bootstrap reusable node tables from existing combined scouts."""
    try:
        with Session(engine) as session:
            legacy_scouts = session.exec(select(ScoutModel)).all()
            if not legacy_scouts:
                return

            existing_flow_legacy_ids = {
                flow.legacy_scout_id
                for flow in session.exec(select(FlowModel)).all()
                if flow.legacy_scout_id is not None
            }

            created = False
            for scout in legacy_scouts:
                if scout.id in existing_flow_legacy_ids:
                    continue

                config_json = scout.config_json or "{}"
                scout_node = ScoutNodeModel(
                    name=f"{scout.name} Scout",
                    type=scout.type,
                    config_json=config_json,
                    schedule_cron=scout.schedule_cron,
                    last_run=scout.last_run,
                )
                agent_node = AgentNodeModel(
                    name=f"{scout.name} Agent",
                    intent=scout.intent,
                    prompt_template=scout.prompt_template,
                    config_json=config_json,
                )
                channel_node = ChannelNodeModel(
                    name=f"{scout.name} Channel",
                    platforms=scout.platforms,
                    telegram_review=scout.telegram_review,
                )
                session.add(scout_node)
                session.add(agent_node)
                session.add(channel_node)
                session.flush()

                flow = FlowModel(
                    name=scout.name,
                    scout_node_id=scout_node.id,
                    agent_node_id=agent_node.id,
                    channel_node_id=channel_node.id,
                    legacy_scout_id=scout.id,
                )
                session.add(flow)
                session.flush()
                session.add(
                    FlowScoutLinkModel(
                        flow_id=flow.id,
                        scout_node_id=scout_node.id,
                        position=0,
                    )
                )
                session.add(
                    FlowChannelLinkModel(
                        flow_id=flow.id,
                        channel_node_id=channel_node.id,
                        position=0,
                    )
                )
                created = True

            if created:
                session.commit()
    except Exception as e:
        logger.debug(f"Flow bootstrap migration check: {e}")


def _migrate_flow_channel_links():
    """Backfill multi-channel link rows for existing flows."""
    try:
        with Session(engine) as session:
            existing_flow_ids = {
                link.flow_id
                for link in session.exec(select(FlowChannelLinkModel)).all()
            }
            created = False
            for flow in session.exec(select(FlowModel)).all():
                if flow.id in existing_flow_ids:
                    continue
                session.add(
                    FlowChannelLinkModel(
                        flow_id=flow.id,
                        channel_node_id=flow.channel_node_id,
                        position=0,
                    )
                )
                created = True
            if created:
                session.commit()
    except Exception as e:
        logger.debug(f"Flow channel link migration check: {e}")


def create_db_and_tables():
    """Create database tables and run migrations."""
    # Create tables first (will create all columns for new databases)
    SQLModel.metadata.create_all(engine)
    
    # Run migration for existing databases (idempotent - safe to call multiple times)
    _migrate_rss_entries_add_processed_fields()
    _migrate_scouts_add_intent_field()
    _migrate_flows_from_legacy_scouts()
    _migrate_flow_channel_links()

def get_session():
    with Session(engine) as session:
        yield session
