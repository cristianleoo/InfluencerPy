import pytest
from unittest.mock import patch, MagicMock
from influencerpy.tools.http_tool import http_request

def test_http_request_success():
    """Test successful HTTP request."""
    mock_response = MagicMock()
    mock_response.content = b"<html><body><p>Test Content</p></body></html>"
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(url="http://example.com")
        
        assert isinstance(result, dict)
        assert result["url"] == "http://example.com"
        assert "Test Content" in result["content"]

def test_http_request_failure():
    """Test HTTP request failure."""
    with patch("requests.get", side_effect=Exception("Network Error")):
        result = http_request(url="http://example.com")
        assert isinstance(result, dict)
        assert "error" in result
        assert "Network Error" in result["error"]
