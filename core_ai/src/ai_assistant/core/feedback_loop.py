import logging
import json
from typing import Dict, Any, List
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class FeedbackLoop:
    """
    Feedback Loop System for AI Learning.
    Collects user feedback, analyzes it, and feeds it back to the AI models for improvement.
    """

    def __init__(self, data_dir: str = "data/feedback"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_file = self.data_dir / "chain_feedback.json"
        self._load_feedback()

    def _load_feedback(self):
        self.feedback_data: List[Dict[str, Any]] = []
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    self.feedback_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load feedback data: {e}")

    def _save_feedback(self):
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feedback data: {e}")

    def collect_feedback(self, chain_id: str, rating: int, comments: str, user_id: str = "default") -> bool:
        """User rating/feedback collection (1-5 stars)"""
        if not 1 <= rating <= 5:
            logger.warning(f"Invalid rating value: {rating}. Must be between 1 and 5.")
            return False
            
        feedback_entry = {
            "chain_id": chain_id,
            "user_id": user_id,
            "rating": rating,
            "comments": comments,
            "timestamp": time.time(),
            "analyzed": False
        }
        
        self.feedback_data.append(feedback_entry)
        self._save_feedback()
        logger.info(f"Collected feedback for chain {chain_id}: Rating {rating}/5")
        
        # Trigger async analysis if rating is low
        if rating <= 3:
            self._trigger_analysis(feedback_entry)
            
        return True

    def _trigger_analysis(self, feedback_entry: Dict[str, Any]):
        """Trigger analysis for poor ratings"""
        logger.info(f"Triggering analysis for low-rated chain {feedback_entry['chain_id']}")
        # In a real scenario, this would send an event to a background worker
        pass

    def analyze_feedback(self) -> Dict[str, Any]:
        """Feedback analysis to find common issues"""
        unanalyzed = [f for f in self.feedback_data if not f.get("analyzed", False)]
        
        if not unanalyzed:
            return {"status": "no_new_data"}
            
        average_rating = sum(f["rating"] for f in unanalyzed) / len(unanalyzed)
        low_ratings = len([f for f in unanalyzed if f["rating"] <= 3])
        
        # Mark as analyzed
        for f in unanalyzed:
            f["analyzed"] = True
        self._save_feedback()
        
        return {
            "status": "success",
            "entries_analyzed": len(unanalyzed),
            "average_rating": average_rating,
            "critical_issues": low_ratings
        }

    def trigger_model_improvement(self) -> bool:
        """Model improvement based on feedback"""
        # This would interface with the fine-tuning module or update the prompt context
        logger.info("Triggering model improvement routine based on accumulated feedback.")
        analysis = self.analyze_feedback()
        if analysis["status"] == "success" and analysis["critical_issues"] > 0:
            logger.info("Adjusting system prompts/parameters to mitigate recurring issues.")
            return True
        return False
