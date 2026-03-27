import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from influencerpy.config import CONFIG_DIR, PROJECT_ROOT

PID_FILE = PROJECT_ROOT / "bot.pid"
BOT_LOG_FILE = CONFIG_DIR / "bot-service.log"


def is_bot_running() -> bool:
    """Check whether the Telegram bot and scheduler service is active."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def stop_bot_process(wait_seconds: float = 3.0) -> bool:
    """Stop the background bot process if it is running."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        PID_FILE.unlink(missing_ok=True)
        return False

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if not is_bot_running():
            PID_FILE.unlink(missing_ok=True)
            return True
        time.sleep(0.2)

    return False


def start_bot_process() -> bool:
    """Start the background bot process if it is not already running."""
    if is_bot_running():
        return False

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    BOT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with BOT_LOG_FILE.open("a", encoding="utf-8") as log_file:
        subprocess.Popen(
            [sys.executable, "-m", "influencerpy.web.bot_runner"],
            cwd=str(PROJECT_ROOT),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )

    return True
