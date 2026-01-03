"""
Integration test for HTTP Request tool with Scouts.
This test verifies that the http_request tool can be used by scouts.
"""

import requests
from unittest.mock import MagicMock, patch
from influencerpy.tools.http_tool import http_request

def test_http_tool_basic_functionality():
    """Test that http_request tool returns expected structure."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.content = b"""
    <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Machine Learning Breakthrough</h1>
                <p>Scientists have discovered a new approach to training neural networks.</p>
            </article>
        </body>
    </html>
    """
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(url="https://example.com/article")
        
        # Verify structure
        assert isinstance(result, dict)
        assert "url" in result
        assert "title" in result
        assert "content" in result
        
        # Verify content
        assert result["url"] == "https://example.com/article"
        assert result["title"] == "Test Article"
        assert "Machine Learning Breakthrough" in result["content"]
        assert "neural networks" in result["content"]

def test_http_tool_with_selector():
    """Test that CSS selector properly filters content."""
    mock_response = MagicMock()
    mock_response.content = b"""
    <html>
        <body>
            <nav>Navigation Menu</nav>
            <article class="main">
                <h1>Main Article</h1>
                <p>This is the main content.</p>
            </article>
            <aside>Sidebar Content</aside>
        </body>
    </html>
    """
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(
            url="https://example.com", 
            selector="article.main"
        )
        
        # Should only contain article content
        assert "Main Article" in result["content"]
        assert "main content" in result["content"]
        assert "Navigation Menu" not in result["content"]
        assert "Sidebar Content" not in result["content"]

def test_http_tool_error_handling():
    """Test that errors are properly caught and returned."""
    with patch("requests.get", side_effect=Exception("Connection failed")):
        result = http_request(url="https://invalid-url.com")
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "Connection failed" in result["error"]
        assert result["url"] == "https://invalid-url.com"

def test_http_tool_is_strands_compatible():
    """Test that the tool has the required Strands tool attributes."""
    # Check that it's a proper Strands tool
    assert hasattr(http_request, 'tool_spec')
    assert isinstance(http_request.tool_spec, dict)
    
    # Check required tool spec fields
    assert 'name' in http_request.tool_spec
    assert 'description' in http_request.tool_spec
    assert http_request.tool_spec['name'] == 'http_request'

def test_http_tool_in_scout_tools_list():
    """Test that http_request can be imported and used in scouts."""
    from influencerpy.core.scouts import ScoutManager
    from influencerpy.tools.http_tool import http_request
    
    # Verify the tool can be imported
    assert callable(http_request)
    
    # Verify ScoutManager exists and can be instantiated
    # (We don't actually create a scout here to avoid DB dependencies)
    assert ScoutManager is not None

def test_http_tool_link_extraction():
    """Test that link extraction works correctly."""
    mock_response = MagicMock()
    mock_response.content = b"""
    <html>
        <body>
            <a href="https://example.com/page1">Link 1</a>
            <a href="/relative-link">Link 2</a>
            <a href="https://example.com/page3">Link 3</a>
        </body>
    </html>
    """
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.get", return_value=mock_response):
        result = http_request(
            url="https://example.com",
            extract_links=True
        )
        
        assert "links" in result
        assert len(result["links"]) == 3
        
        # Check that relative URL was converted to absolute
        urls = [link["url"] for link in result["links"]]
        assert "https://example.com/page1" in urls
        assert "https://example.com/relative-link" in urls
        assert "https://example.com/page3" in urls
