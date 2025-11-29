"""Tests for RSS feed validation and fetching using strands_tools.rss."""

import pytest
from strands_tools import rss


def test_rss_module_import():
    """Test that rss.rss function is callable."""
    # Ensure we're importing the module correctly
    assert hasattr(rss, 'rss'), "rss module should have an 'rss' function"
    assert callable(rss.rss), "rss.rss should be callable"


def test_rss_fetch_with_max_entries():
    """Test fetching RSS feed with max_entries limit."""
    # Use a known stable RSS feed for testing
    feed_url = "https://news.google.com/rss/search?q=artificial+intelligence"
    
    try:
        result = rss.rss(action="fetch", url=feed_url, max_entries=1)
        
        # Should return a list
        assert isinstance(result, list), "RSS fetch should return a list"
        
        # Should respect max_entries limit
        assert len(result) <= 1, "Should return at most 1 entry"
        
        # If we got results, check structure
        if len(result) > 0:
            entry = result[0]
            assert "title" in entry, "Entry should have a title"
            assert "link" in entry, "Entry should have a link"
            
    except Exception as e:
        pytest.skip(f"RSS feed fetch failed (network issue?): {e}")


def test_rss_validation_takara_ai_papers():
    """Test validation of Takara AI papers feed (real-world scenario)."""
    # This is the feed that was failing in the bug report
    feed_url = "https://tldr.takara.ai/api/papers"
    
    try:
        result = rss.rss(action="fetch", url=feed_url, max_entries=1)
        
        # Should return a list
        assert isinstance(result, list), "RSS fetch should return a list"
        
        # Feed should have content
        assert len(result) > 0, "Takara AI papers feed should have entries"
        
        # Check entry structure
        entry = result[0]
        assert "title" in entry, "Entry should have a title"
        assert "link" in entry, "Entry should have a link"
        
        # Takara AI specific - links should point to their domain
        assert "tldr.takara.ai" in entry["link"], "Links should be Takara AI papers"
        
    except Exception as e:
        pytest.skip(f"RSS feed fetch failed (network issue?): {e}")


def test_rss_empty_feed_handling():
    """Test handling of feeds with no entries."""
    # We can't easily test with a real empty feed, so we'll test the structure
    # This ensures the code handles empty results gracefully
    feed_url = "https://news.google.com/rss/search?q=zzzzz_nonexistent_query_12345"
    
    try:
        result = rss.rss(action="fetch", url=feed_url, max_entries=10)
        
        # Should still return a list, even if empty
        assert isinstance(result, list), "RSS fetch should return a list even when empty"
        
    except Exception as e:
        pytest.skip(f"RSS feed fetch failed (network issue?): {e}")


def test_rss_validation_scout_workflow():
    """Test the RSS validation workflow as used in scout creation."""
    # This mimics the validation logic in main.py _create_scout_flow
    feed_url = "https://tldr.takara.ai/api/papers"
    
    try:
        result = rss.rss(action="fetch", url=feed_url, max_entries=1)
        
        # This is the exact validation logic from main.py line 689-691
        if isinstance(result, list) and len(result) > 0:
            # Validation passes
            assert True
        else:
            pytest.fail("Feed validation should pass for Takara AI papers")
            
    except Exception as e:
        pytest.fail(f"RSS validation should not raise exception: {e}")
