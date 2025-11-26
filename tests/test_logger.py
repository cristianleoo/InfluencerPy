import pytest
import logging
import time
from pathlib import Path
from influencerpy.logger import get_app_logger, get_scout_logger

@pytest.fixture
def mock_logs_dir(monkeypatch, tmp_path):
    """Mock LOGS_DIR to use a temporary directory."""
    monkeypatch.setattr("influencerpy.logger.LOGS_DIR", tmp_path)
    return tmp_path

def test_app_logger(mock_logs_dir):
    """Test application logger creation and file writing."""
    # Reset logger handlers to force re-creation with new path
    logger = logging.getLogger("test_app")
    for h in list(logger.handlers):
        logger.removeHandler(h)
        
    logger = get_app_logger("test_app")
    logger.info("Test app log")
    
    # Check directory structure
    app_dir = mock_logs_dir / "app"
    assert app_dir.exists()
    
    log_file = app_dir / "app.log"
    assert log_file.exists()
    
    with open(log_file, "r") as f:
        content = f.read()
        assert "Test app log" in content

def test_scout_logger(mock_logs_dir):
    """Test scout logger creation and timestamped files."""
    scout_name = "TestScout"
    logger = get_scout_logger(scout_name)
    logger.info("Test scout log")
    
    # Check directory structure
    scout_dir = mock_logs_dir / "scouts" / scout_name
    assert scout_dir.exists()
    
    # Find log file (timestamped)
    log_files = list(scout_dir.glob("*.log"))
    assert len(log_files) == 1
    
    with open(log_files[0], "r") as f:
        content = f.read()
        assert "Test scout log" in content

def test_scout_logger_multiple_runs(mock_logs_dir):
    """Test that multiple runs create multiple files."""
    scout_name = "MultiRunScout"
    
    # Run 1
    logger1 = get_scout_logger(scout_name)
    logger1.info("Run 1")
    
    # Ensure timestamp difference (files are named by second)
    time.sleep(1.1)
    
    # Run 2
    logger2 = get_scout_logger(scout_name)
    logger2.info("Run 2")
    
    scout_dir = mock_logs_dir / "scouts" / scout_name
    log_files = list(scout_dir.glob("*.log"))
    assert len(log_files) == 2
