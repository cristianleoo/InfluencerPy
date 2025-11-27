import pytest
import json
from unittest.mock import MagicMock, patch
from influencerpy.core.scouts import ScoutManager
from influencerpy.database import ScoutModel

def test_create_scout(session, config_manager):
    manager = ScoutManager()
    # Override session with test session
    manager.session = session
    
    config = {"query": "test query"}
    scout = manager.create_scout(
        name="Test Scout",
        type="search",
        config=config
    )
    
    assert scout.id is not None
    assert scout.name == "Test Scout"
    assert json.loads(scout.config_json) == config

def test_get_scout(session, config_manager):
    manager = ScoutManager()
    manager.session = session
    
    manager.create_scout("Find Me", "rss", {})
    scout = manager.get_scout("Find Me")
    assert scout is not None
    assert scout.name == "Find Me"

def test_update_scout(session, config_manager):
    manager = ScoutManager()
    manager.session = session
    
    scout = manager.create_scout("Update Me", "rss", {})
    updated = manager.update_scout(scout, name="Updated Name")
    
    assert updated.name == "Updated Name"
    assert manager.get_scout("Update Me") is None
    assert manager.get_scout("Updated Name") is not None

def test_delete_scout(session, config_manager):
    manager = ScoutManager()
    manager.session = session
    
    scout = manager.create_scout("Delete Me", "rss", {})
    manager.delete_scout(scout)
    
    assert manager.get_scout("Delete Me") is None

def test_create_scout_with_platform(session, config_manager):
    """Test creating a scout with platforms configured."""
    manager = ScoutManager()
    manager.session = session
    
    config = {"query": "AI news"}
    scout = manager.create_scout(
        name="Auto-Post Scout",
        type="search",
        config=config,
        platforms=["x"],
        telegram_review=False
    )
    
    assert scout.id is not None
    assert scout.name == "Auto-Post Scout"
    assert json.loads(scout.platforms) == ["x"]
    assert scout.telegram_review == False

def test_create_scout_without_platform(session, config_manager):
    """Test creating a scout without platforms (manual mode)."""
    manager = ScoutManager()
    manager.session = session
    
    config = {"query": "Manual scout"}
    scout = manager.create_scout(
        name="Manual Scout",
        type="search",
        config=config,
        platforms=[],
        telegram_review=False
    )
    
    assert scout.id is not None
    assert scout.name == "Manual Scout"
    assert json.loads(scout.platforms) == []
    assert scout.telegram_review == False

def test_create_scout_with_telegram_review(session, config_manager):
    """Test creating a scout with Telegram review enabled."""
    manager = ScoutManager()
    manager.session = session
    
    config = {"query": "Review scout"}
    scout = manager.create_scout(
        name="Telegram Review Scout",
        type="search",
        config=config,
        platforms=["x"],
        telegram_review=True
    )
    
    assert scout.id is not None
    assert scout.name == "Telegram Review Scout"
    assert json.loads(scout.platforms) == ["x"]
    assert scout.telegram_review == True

@patch("influencerpy.core.scouts.get_scout_logger")
@patch("influencerpy.core.scouts.Agent")
@patch("strands.models.gemini.GeminiModel")
def test_run_scout_with_agent(mock_model, mock_agent, mock_logger, session, config_manager):
    """Test run_scout with agent execution."""
    manager = ScoutManager()
    manager.session = session
    
    # Setup mocks
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    
    # Mock agent response
    mock_response = """
    ```json
    [
        {
            "title": "Test Article",
            "url": "http://example.com",
            "summary": "Summary",
            "sources": ["source1"]
        }
    ]
    ```
    """
    mock_agent_instance.return_value = mock_response
    
    # Create scout with tools
    config = {
        "query": "AI",
        "tools": ["google_search"],
        "generation_config": {"provider": "gemini", "model_id": "gemini-test"}
    }
    scout = manager.create_scout("Agent Scout", "search", config)
    
    # Run scout
    items = manager.run_scout(scout)
    
    # Verify
    assert len(items) == 1
    assert items[0].title == "Test Article"
    assert items[0].url == "http://example.com"
    
    # Verify logger usage
    mock_logger.assert_called_with("Agent Scout")
    
    # Verify Agent initialization
    mock_agent.assert_called_once()
    args, kwargs = mock_agent.call_args
    assert "tools" in kwargs
    assert len(kwargs["tools"]) == 1 # google_search
    
    # Verify callback_handler (updated from NullConversationManager)
    assert "callback_handler" in kwargs

@patch("influencerpy.core.scouts.get_scout_logger")
@patch("influencerpy.core.scouts.Agent")
@patch("strands.models.gemini.GeminiModel")
def test_run_reddit_scout(mock_model, mock_agent, mock_logger, session, config_manager):
    """Test running a scout configured with reddit tool."""
    manager = ScoutManager()
    manager.session = session
    
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    mock_agent_instance.return_value = "[]" # Empty response is fine, checking init
    
    config = {
        "subreddits": ["arcteryx"],
        "tools": ["reddit"]
    }
    scout = manager.create_scout("Reddit Scout", "reddit", config)
    
    manager.run_scout(scout)
    
    # Verify agent tools
    args, kwargs = mock_agent.call_args
    tools = kwargs["tools"]
    # Verify reddit tool is present
    tool_names = [t.tool_name for t in tools]
    assert "reddit" in tool_names

@patch("influencerpy.core.scouts.get_scout_logger")
@patch("influencerpy.core.scouts.Agent")
@patch("strands.models.gemini.GeminiModel")
def test_run_arxiv_scout(mock_model, mock_agent, mock_logger, session, config_manager):
    """Test running a scout configured with arxiv tool."""
    manager = ScoutManager()
    manager.session = session
    
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    mock_agent_instance.return_value = "[]" 
    
    config = {
        "query": "LLM Agents",
        "tools": ["arxiv"]
    }
    scout = manager.create_scout("Arxiv Scout", "arxiv", config)
    
    manager.run_scout(scout)
    
    # Verify agent tools
    args, kwargs = mock_agent.call_args
    tools = kwargs["tools"]
    # Verify arxiv tool is present
    tool_names = [t.tool_name for t in tools]
    assert "arxiv_search" in tool_names
