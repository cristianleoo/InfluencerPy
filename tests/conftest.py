import pytest
import os
import tempfile
from sqlmodel import SQLModel, create_engine, Session
from influencerpy.config import ConfigManager

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="config_manager")
def config_manager_fixture(monkeypatch):
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write("ai:\n  default_provider: gemini\n")
        tmp_path = tmp.name
        
    # Patch the global CONFIG_FILE variable
    monkeypatch.setattr("influencerpy.config.CONFIG_FILE", tmp_path)
    
    yield tmp_path
    
    # Cleanup
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("X_API_KEY", "test_x_key")
