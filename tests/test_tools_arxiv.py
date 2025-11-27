import pytest
from unittest.mock import patch, MagicMock
from influencerpy.tools.arxiv_tool import arxiv_search, get_arxiv_id_from_url, get_top_paper_url

def test_get_arxiv_id_from_url():
    assert get_arxiv_id_from_url("https://huggingface.co/papers/2310.12345") == "2310.12345"
    assert get_arxiv_id_from_url("https://arxiv.org/abs/2310.12345") == "2310.12345"

@patch('influencerpy.tools.arxiv_tool.requests.get')
def test_get_top_paper_url(mock_get):
    mock_response = MagicMock()
    mock_response.content = b'<html><article><a href="/papers/2310.12345">Paper</a></article></html>'
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    url = get_top_paper_url()
    assert url == "https://huggingface.co/papers/2310.12345"

@patch('influencerpy.tools.arxiv_tool.arxiv.Search')
def test_arxiv_search(mock_search):
    mock_result = MagicMock()
    mock_result.title = "Test Paper"
    author1 = MagicMock()
    author1.name = "Author One"
    author2 = MagicMock()
    author2.name = "Author Two"
    mock_result.authors = [author1, author2]
    mock_result.published.strftime.return_value = "2023-10-27"
    mock_result.entry_id = "http://arxiv.org/abs/2310.12345"
    mock_result.summary = "This is a test abstract."
    
    mock_search_instance = MagicMock()
    mock_search_instance.results.return_value = iter([mock_result])
    mock_search.return_value = mock_search_instance
    
    result = arxiv_search("test query")
    
    assert "**Title:** Test Paper" in result
    assert "**Authors:** Author One, Author Two" in result
    assert "**Published:** 2023-10-27" in result
    assert "**Arxiv ID:** 2310.12345" in result
    assert "**Abstract:**\nThis is a test abstract." in result

@patch('influencerpy.tools.arxiv_tool.arxiv.Search')
def test_arxiv_search_no_results(mock_search):
    mock_search_instance = MagicMock()
    mock_search_instance.results.return_value = iter([])
    mock_search.return_value = mock_search_instance
    
    result = arxiv_search("nonexistent paper")
    assert "No results found on Arxiv." in result
