"""Tests for RSS entry processing and tracking functionality."""

import pytest
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel, select

from influencerpy.types.rss import RSSFeedModel, RSSEntryModel
from influencerpy.tools.rss import RSSManager

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def test_session():
    """Create a test database session."""
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def rss_manager(test_session, monkeypatch):
    """Create an RSS manager with mocked session."""
    manager = RSSManager()
    
    # Mock get_session to return our test session
    def mock_get_session():
        yield test_session
    
    monkeypatch.setattr("influencerpy.tools.rss.get_session", mock_get_session)
    return manager


@pytest.fixture
def sample_feed(test_session):
    """Create a sample RSS feed in the database."""
    feed = RSSFeedModel(
        url="https://example.com/feed.xml",
        title="Test Feed",
        scout_id=1,
        update_interval=60
    )
    test_session.add(feed)
    test_session.commit()
    test_session.refresh(feed)
    return feed


@pytest.fixture
def sample_entries(test_session, sample_feed):
    """Create sample RSS entries in the database."""
    entries = []
    for i in range(5):
        entry = RSSEntryModel(
            feed_id=sample_feed.id,
            entry_id=f"entry_{i}",
            title=f"Test Entry {i}",
            link=f"https://example.com/entry{i}",
            published=datetime.utcnow(),
            summary=f"Summary for entry {i}",
            is_processed=False
        )
        test_session.add(entry)
        entries.append(entry)
    
    test_session.commit()
    for entry in entries:
        test_session.refresh(entry)
    
    return entries


def test_new_entries_have_is_processed_false(sample_entries):
    """Test that new entries are created with is_processed=False."""
    for entry in sample_entries:
        assert entry.is_processed is False
        assert entry.processed_at is None


def test_read_feed_returns_only_unprocessed(rss_manager, test_session, sample_feed, sample_entries):
    """Test that read_feed only returns unprocessed entries by default."""
    # Mark some entries as processed
    sample_entries[0].is_processed = True
    sample_entries[1].is_processed = True
    test_session.add(sample_entries[0])
    test_session.add(sample_entries[1])
    test_session.commit()
    
    # Read feed with default only_unprocessed=True
    result = rss_manager.read_feed(sample_feed.id, max_entries=10, only_unprocessed=True)
    
    assert "entries" in result
    assert len(result["entries"]) == 3  # Only 3 unprocessed entries
    
    # Verify returned entries are unprocessed ones
    returned_titles = {entry["title"] for entry in result["entries"]}
    assert "Test Entry 0" not in returned_titles
    assert "Test Entry 1" not in returned_titles
    assert "Test Entry 2" in returned_titles
    assert "Test Entry 3" in returned_titles
    assert "Test Entry 4" in returned_titles


def test_read_feed_returns_all_when_only_unprocessed_false(rss_manager, test_session, sample_feed, sample_entries):
    """Test that read_feed returns all entries when only_unprocessed=False."""
    # Mark some entries as processed
    sample_entries[0].is_processed = True
    sample_entries[1].is_processed = True
    test_session.add(sample_entries[0])
    test_session.add(sample_entries[1])
    test_session.commit()
    
    # Read feed with only_unprocessed=False
    result = rss_manager.read_feed(sample_feed.id, max_entries=10, only_unprocessed=False)
    
    assert "entries" in result
    assert len(result["entries"]) == 5  # All entries


def test_read_all_feeds_filters_unprocessed(rss_manager, test_session, sample_feed, sample_entries):
    """Test that read_all_feeds filters unprocessed entries."""
    # Mark some entries as processed
    sample_entries[0].is_processed = True
    sample_entries[1].is_processed = True
    test_session.add(sample_entries[0])
    test_session.add(sample_entries[1])
    test_session.commit()
    
    # Read all feeds
    results = rss_manager.read_all_feeds(scout_id=1, max_entries_per_feed=10, only_unprocessed=True)
    
    assert len(results) == 1  # One feed
    assert results[0]["entry_count"] == 3  # Only unprocessed entries


def test_mark_processed_updates_entries(rss_manager, test_session, sample_entries):
    """Test that mark_processed correctly updates entries."""
    entry_ids = [sample_entries[0].id, sample_entries[1].id, sample_entries[2].id]
    
    # Mark entries as processed
    result = rss_manager.mark_processed(entry_ids)
    
    assert result["status"] == "success"
    assert result["marked_count"] == 3
    
    # Verify entries are marked by querying fresh from database
    updated_entries = []
    for entry_id in entry_ids:
        entry = test_session.get(RSSEntryModel, entry_id)
        updated_entries.append(entry)
    
    assert updated_entries[0].is_processed is True
    assert updated_entries[1].is_processed is True
    assert updated_entries[2].is_processed is True
    assert updated_entries[0].processed_at is not None
    assert updated_entries[1].processed_at is not None
    assert updated_entries[2].processed_at is not None


def test_mark_processed_ignores_invalid_ids(rss_manager, test_session):
    """Test that mark_processed handles invalid entry IDs gracefully."""
    # Try to mark non-existent entries
    result = rss_manager.mark_processed([9999, 9998, 9997])
    
    assert result["status"] == "success"
    assert result["marked_count"] == 0  # No entries marked


def test_reset_processed_status(rss_manager, test_session, sample_feed, sample_entries):
    """Test that reset_processed_status resets entries."""
    # Mark all entries as processed
    entry_ids = []
    for entry in sample_entries:
        entry.is_processed = True
        entry.processed_at = datetime.utcnow()
        test_session.add(entry)
        entry_ids.append(entry.id)
    test_session.commit()
    
    # Reset processed status
    result = rss_manager.reset_processed_status(feed_id=sample_feed.id)
    
    assert result["status"] == "success"
    assert result["reset_count"] == 5
    
    # Verify entries are reset by querying fresh from database
    for entry_id in entry_ids:
        entry = test_session.get(RSSEntryModel, entry_id)
        assert entry.is_processed is False
        assert entry.processed_at is None


def test_reset_processed_status_all_feeds(rss_manager, test_session, sample_feed, sample_entries):
    """Test that reset_processed_status can reset all feeds."""
    # Create another feed with entries
    feed2 = RSSFeedModel(
        url="https://example.com/feed2.xml",
        title="Test Feed 2",
        scout_id=1,
        update_interval=60
    )
    test_session.add(feed2)
    test_session.commit()
    test_session.refresh(feed2)
    
    entry2 = RSSEntryModel(
        feed_id=feed2.id,
        entry_id="entry_feed2",
        title="Test Entry Feed 2",
        link="https://example.com/entry_feed2",
        published=datetime.utcnow(),
        is_processed=True,
        processed_at=datetime.utcnow()
    )
    test_session.add(entry2)
    test_session.commit()
    
    # Mark all entries in feed 1 as processed
    for entry in sample_entries:
        entry.is_processed = True
        entry.processed_at = datetime.utcnow()
        test_session.add(entry)
    test_session.commit()
    
    # Reset all feeds (no feed_id specified)
    result = rss_manager.reset_processed_status()
    
    assert result["status"] == "success"
    assert result["reset_count"] == 6  # 5 from feed1 + 1 from feed2


def test_entries_include_id_for_marking(rss_manager, test_session, sample_feed, sample_entries):
    """Test that read operations include entry IDs for marking as processed."""
    result = rss_manager.read_feed(sample_feed.id, max_entries=10)
    
    assert "entries" in result
    for entry in result["entries"]:
        assert "id" in entry, "Entry should include ID for marking as processed"
        assert isinstance(entry["id"], int)


def test_workflow_read_mark_read_again(rss_manager, test_session, sample_feed, sample_entries):
    """Test the complete workflow: read -> mark processed -> read again."""
    # Step 1: Read unprocessed entries
    result1 = rss_manager.read_feed(sample_feed.id, max_entries=10, only_unprocessed=True)
    assert len(result1["entries"]) == 5
    
    # Step 2: Mark first 3 as processed
    entry_ids = [result1["entries"][i]["id"] for i in range(3)]
    mark_result = rss_manager.mark_processed(entry_ids)
    assert mark_result["marked_count"] == 3
    
    # Step 3: Read again - should only get 2 unprocessed entries
    result2 = rss_manager.read_feed(sample_feed.id, max_entries=10, only_unprocessed=True)
    assert len(result2["entries"]) == 2
    
    # Step 4: Mark remaining as processed
    entry_ids = [result2["entries"][i]["id"] for i in range(2)]
    mark_result = rss_manager.mark_processed(entry_ids)
    assert mark_result["marked_count"] == 2
    
    # Step 5: Read again - should get no entries
    result3 = rss_manager.read_feed(sample_feed.id, max_entries=10, only_unprocessed=True)
    assert len(result3["entries"]) == 0


def test_read_all_feeds_excludes_feeds_with_no_unprocessed(rss_manager, test_session, sample_feed, sample_entries):
    """Test that read_all_feeds excludes feeds with no unprocessed entries."""
    # Mark all entries as processed
    for entry in sample_entries:
        entry.is_processed = True
        test_session.add(entry)
    test_session.commit()
    
    # Read all feeds - should return empty list
    results = rss_manager.read_all_feeds(scout_id=1, only_unprocessed=True)
    assert len(results) == 0  # No feeds with unprocessed entries
