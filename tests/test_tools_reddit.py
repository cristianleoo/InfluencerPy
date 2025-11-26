import pytest
from unittest.mock import patch, MagicMock
from influencerpy.tools.reddit import reddit

def test_reddit_tool_success():
    """Test reddit tool with successful API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Test Post",
                        "permalink": "/r/test/comments/123/test_post/",
                        "selftext": "Content",
                        "score": 100,
                        "num_comments": 50,
                        "author": "tester",
                        "created_utc": 1600000000
                    }
                }
            ]
        }
    }
    
    with patch("requests.get", return_value=mock_response) as mock_get:
        result = reddit(subreddit="test", limit=1)
        
        mock_get.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Test Post"
        assert result[0]["url"] == "https://www.reddit.com/r/test/comments/123/test_post/"
        assert result[0]["source"] == "r/test"

def test_reddit_tool_404():
    """Test reddit tool when subreddit is not found."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    with patch("requests.get", return_value=mock_response):
        result = reddit(subreddit="invalid_sub")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

def test_reddit_tool_rate_limit():
    """Test reddit tool when rate limited."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    
    with patch("requests.get", return_value=mock_response):
        result = reddit(subreddit="test")
        assert isinstance(result, dict)
        assert "error" in result
        assert "Rate limit" in result["error"]

