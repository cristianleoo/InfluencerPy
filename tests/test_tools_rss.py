import pytest
from unittest.mock import patch, MagicMock
from influencerpy.tools.rss_tool import rss

def test_rss_fetch_success():
    """Test fetching RSS feed successfully."""
    mock_feed = MagicMock()
    mock_feed.entries = [
        {
            "title": "Test Article",
            "link": "http://example.com/article",
            "published": "2023-01-01",
            "summary": "Summary of article",
            "id": "1"
        }
    ]
    
    with patch("feedparser.parse", return_value=mock_feed):
        result = rss(action="fetch", url="http://example.com/feed", max_entries=1)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Test Article"
        assert result[0]["link"] == "http://example.com/article"

def test_rss_fetch_empty():
    """Test fetching empty RSS feed."""
    mock_feed = MagicMock()
    mock_feed.entries = []
    
    with patch("feedparser.parse", return_value=mock_feed):
        result = rss(action="fetch", url="http://example.com/feed")
        assert isinstance(result, list)
        assert len(result) == 0

def test_rss_invalid_action():
    """Test invalid action."""
    result = rss(action="invalid", url="http://example.com/feed")
    assert isinstance(result, dict)
    assert "error" in result
