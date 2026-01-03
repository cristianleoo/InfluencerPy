import pytest
import requests
from unittest.mock import patch, MagicMock
from influencerpy.tools.http_tool import http_request

def test_http_request_success():
    """Test successful HTTP request."""
    mock_response = MagicMock()
    mock_response.content = b"<html><head><title>Test Page</title></head><body><p>Test Content</p></body></html>"
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(url="http://example.com")
        
        assert isinstance(result, dict)
        assert result["url"] == "http://example.com"
        assert "Test Content" in result["content"]
        assert result["title"] == "Test Page"

def test_http_request_with_selector():
    """Test HTTP request with CSS selector."""
    mock_response = MagicMock()
    mock_response.content = b"""
    <html>
        <body>
            <article>Article Content</article>
            <div class="sidebar">Sidebar Content</div>
        </body>
    </html>
    """
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(url="http://example.com", selector="article")
        
        assert isinstance(result, dict)
        assert "Article Content" in result["content"]
        assert "Sidebar Content" not in result["content"]

def test_http_request_with_links():
    """Test HTTP request with link extraction."""
    mock_response = MagicMock()
    mock_response.content = b"""
    <html>
        <body>
            <a href="https://example.com/page1">Link 1</a>
            <a href="/page2">Link 2</a>
        </body>
    </html>
    """
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(url="http://example.com", extract_links=True)
        
        assert isinstance(result, dict)
        assert "links" in result
        assert len(result["links"]) == 2
        assert result["links"][0]["url"] == "https://example.com/page1"

def test_http_request_failure():
    """Test HTTP request failure."""
    with patch("requests.get", side_effect=Exception("Network Error")):
        result = http_request(url="http://example.com")
        assert isinstance(result, dict)
        assert "error" in result
        assert "Network Error" in result["error"]

def test_http_request_timeout():
    """Test HTTP request timeout."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        result = http_request(url="http://example.com")
        assert isinstance(result, dict)
        assert "error" in result
        assert "timed out" in result["error"].lower()
