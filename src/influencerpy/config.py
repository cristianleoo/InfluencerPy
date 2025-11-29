import yaml
from pathlib import Path
from typing import Dict, Any, Union

# Determine project root (assuming src/influencerpy structure)
PACKAGE_ROOT = Path(__file__).parent.resolve()
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
CONFIG_DIR = PROJECT_ROOT / ".influencerpy"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_CONFIG = {
    "ai": {
        "default_provider": "gemini",
        "providers": {
            "gemini": {
                "default_model": "gemini-2.5-flash"
            },
            "anthropic": {
                "default_model": "claude-4.5-sonnet"
            }
        },
        "search": {
            "provider": "gemini",
            "model": "gemini-2.5-flash-lite"
        }
    }
}

class ConfigManager:
    """Manages application configuration via config.yaml."""
    
    def __init__(self, config_path: Union[str, Path] = None):
        self.config_path = Path(config_path or CONFIG_FILE)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load config from file or return defaults."""
        if not self.config_path.exists():
            return DEFAULT_CONFIG
        
        try:
            with self.config_path.open("r") as f:
                return yaml.safe_load(f) or DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG

    def save_config(self):
        """Save current config to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w") as f:
            yaml.dump(self._config, f, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation (e.g. 'ai.default_provider')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """Set a config value using dot notation and save."""
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_config()

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def ensure_config_exists(self):
        """Create config file if it doesn't exist."""
        if not self.config_path.exists():
            self.save_config()
