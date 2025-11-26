import pytest
from influencerpy.config import ConfigManager

def test_load_defaults(config_manager):
    """Test that defaults are loaded if config file is empty/missing."""
    # Note: config_manager fixture creates a file with some content.
    # Let's create a new manager which should load that content.
    manager = ConfigManager()
    assert manager.get("ai.default_provider") == "gemini"

def test_get_value(config_manager):
    manager = ConfigManager()
    assert manager.get("ai.default_provider") == "gemini"
    assert manager.get("non.existent.key", "default") == "default"

def test_set_value(config_manager):
    manager = ConfigManager()
    manager.set("ai.default_provider", "anthropic")
    assert manager.get("ai.default_provider") == "anthropic"
    
    # Verify persistence
    manager2 = ConfigManager()
    assert manager2.get("ai.default_provider") == "anthropic"

def test_nested_set(config_manager):
    manager = ConfigManager()
    manager.set("new.nested.key", "value")
    assert manager.get("new.nested.key") == "value"
