import pytest
from unittest.mock import MagicMock, patch
from influencerpy.providers.gemini import GeminiProvider

@patch("influencerpy.providers.gemini.Agent")
@patch("influencerpy.providers.gemini.GeminiModel")
def test_gemini_generate(mock_model, mock_agent):
    # Setup mocks
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    mock_agent_instance.return_value = "Generated content"
    
    provider = GeminiProvider(model_id="gemini-test")
    result = provider.generate("Test prompt")
    
    assert result == "Generated content"
    
    # Verify Agent was initialized with callback_handler
    args, kwargs = mock_agent.call_args
    assert "callback_handler" in kwargs
    
    mock_agent_instance.assert_called_once_with("Test prompt")
