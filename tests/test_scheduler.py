import pytest
from unittest.mock import MagicMock, patch
from influencerpy.core.scheduler import ScoutScheduler
from influencerpy.database import ScoutModel

def test_scheduler_load_jobs():
    """Test loading jobs from scouts."""
    mock_scout = ScoutModel(
        name="Test Scout",
        type="rss",
        config_json="{}",
        schedule_cron="0 9 * * *"
    )
    mock_scout.id = 1
    
    with patch("influencerpy.core.scouts.ScoutManager.list_scouts", return_value=[mock_scout]):
        scheduler = ScoutScheduler()
        scheduler.scheduler = MagicMock()
        
        scheduler.load_jobs()
        
        # Verify add_job was called
        scheduler.scheduler.add_job.assert_called_once()
        args, kwargs = scheduler.scheduler.add_job.call_args
        assert kwargs["id"] == "scout_1"
        assert kwargs["name"] == "Run Scout: Test Scout"

def test_scheduler_start_stop():
    """Test start and stop methods."""
    with patch("influencerpy.core.scouts.ScoutManager.list_scouts", return_value=[]):
        scheduler = ScoutScheduler()
        scheduler.scheduler = MagicMock()
        scheduler.scheduler.running = False
        
        scheduler.start()
        scheduler.scheduler.start.assert_called_once()
        
        scheduler.scheduler.running = True
        scheduler.stop()
        scheduler.scheduler.shutdown.assert_called_once()
