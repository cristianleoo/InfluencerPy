import pytest
from unittest.mock import patch, MagicMock
import os
from influencerpy.tools.image_generation import generate_image_stability

@patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"})
def test_generate_image_success():
    """Test successful image generation."""
    mock_tool_use = {
        "input": {"prompt": "test prompt"},
        "toolUseId": "test_id"
    }
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "finish_reason": "SUCCESS",
        "image": "SGVsbG8=" # "Hello" in base64
    }
    mock_response.raise_for_status.return_value = None
    
    with patch("requests.post", return_value=mock_response):
        result = generate_image_stability(mock_tool_use)
        
        assert result["status"] == "success"
        assert result["toolUseId"] == "test_id"
        assert "image" in result["content"][1]

def test_generate_image_no_key():
    """Test missing API key."""
    mock_tool_use = {"input": {"prompt": "test"}}
    
    # Ensure no key in env
    with patch.dict(os.environ, {}, clear=True):
        result = generate_image_stability(mock_tool_use)
        assert result["status"] == "error"
        assert "STABILITY_API_KEY" in result["content"][0]["text"]
