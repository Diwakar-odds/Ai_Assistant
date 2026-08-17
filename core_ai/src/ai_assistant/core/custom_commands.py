import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CustomCommandManager:
    def __init__(self, data_dir: str = "data"):
        self.config_path = Path(data_dir) / "custom_commands.json"
        self.aliases = {}
        self._load_commands()

    def _load_commands(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.aliases = json.load(f)
            except Exception as e:
                logger.error(f"Error loading custom commands: {e}")
                self.aliases = {}
        else:
            self.aliases = {
                "start my day": ["open browser", "open mail", "show news"],
                "focus mode": ["close browser", "open vscode", "play lo-fi music"]
            }
            self._save_commands()

    def _save_commands(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving custom commands: {e}")

    def add_alias(self, alias: str, commands: list):
        self.aliases[alias.lower()] = commands
        self._save_commands()
        return True

    def remove_alias(self, alias: str):
        alias_lower = alias.lower()
        if alias_lower in self.aliases:
            del self.aliases[alias_lower]
            self._save_commands()
            return True
        return False

    def resolve_command(self, user_input: str) -> list:
        """Returns a list of commands. If it's an alias, returns the mapped commands."""
        lower_input = user_input.lower().strip()
        if lower_input in self.aliases:
            return self.aliases[lower_input]
        return [user_input]
