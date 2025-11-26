import logging
import sys
import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from influencerpy.config import CONFIG_DIR

# Ensure logs directory exists
LOGS_DIR = CONFIG_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def _get_formatter() -> logging.Formatter:
    return logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    Deprecated: Use get_app_logger or get_scout_logger instead.
    """
    return get_app_logger(name)

def get_app_logger(name: str = "app") -> logging.Logger:
    """
    Get the application logger.
    Logs to .influencerpy/logs/app/app.log (rotated).
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        return logger
        
    app_logs_dir = LOGS_DIR / "app"
    app_logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = app_logs_dir / "app.log"
    
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(_get_formatter())
    logger.addHandler(file_handler)
    
    return logger

def get_scout_logger(scout_name: str) -> logging.Logger:
    """
    Get a logger for a specific scout run.
    Logs to .influencerpy/logs/scouts/{scout_name}/{timestamp}.log
    
    WARNING: This modifies the logger handlers. Do not use for concurrent runs of the same scout in the same process.
    """
    logger_name = f"scout.{scout_name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to ensure we log to the new timestamped file
    for h in list(logger.handlers):
        logger.removeHandler(h)
        
    # Create scout logs directory
    safe_name = "".join(c for c in scout_name if c.isalnum() or c in ('_', '-', '.'))
    scout_logs_dir = LOGS_DIR / "scouts" / safe_name
    scout_logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = scout_logs_dir / f"{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(_get_formatter())
    logger.addHandler(file_handler)
    
    return logger
