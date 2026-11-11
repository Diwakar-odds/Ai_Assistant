import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrainingMode:
    """Allows 'training' the video agent by defining and saving reusable action workflows."""

    def __init__(self, profile_name: str = "custom_workflow"):
        self.profile_name = profile_name
        self.actions: List[Dict] = []

    def add_action(self, action_type: str, params: Dict) -> None:
        """Add an action to the current training session."""
        self.actions.append({
            "timestamp": time.time(),
            "type": action_type,
            "params": params,
        })
        logger.debug("Recorded action: %s - %s", action_type, params)

    def save_workflow(
        self,
        filename: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> str:
        """Save the trained workflow to disk under agents/video/workflows (or output_dir)."""
        if not filename:
            safe_profile = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in self.profile_name)
            filename = f"workflow_{safe_profile}.json"

        base_dir = Path(output_dir).resolve() if output_dir else (Path(__file__).resolve().parent / "workflows")
        base_dir.mkdir(parents=True, exist_ok=True)
        output_path = base_dir / Path(filename).name

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({"profile": self.profile_name, "actions": self.actions}, fh, indent=2)

        logger.info("Workflow saved to: %s", output_path)
        return str(output_path)

    @staticmethod
    def load_workflow(filename: str) -> List[Dict]:
        if filename and os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("actions", [])
        return []
