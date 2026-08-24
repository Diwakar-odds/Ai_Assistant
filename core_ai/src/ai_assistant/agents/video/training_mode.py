from typing import List, Dict
import time
import json
import os

class TrainingMode:
    """
    Allows 'training' the agent by defining workflows or recording actions.
    Future: Hook into keyboard hooks to record real-time (requires complex permissions).
    Current: Manual definition builder.
    """
    
    def __init__(self, profile_name: str = "custom_workflow"):
        self.profile_name = profile_name
        self.actions: List[Dict] = []
        
    def add_action(self, action_type: str, params: Dict):
        """Add an action to the current training session"""
        self.actions.append({
            "timestamp": time.time(),
            "type": action_type,
            "params": params
        })
        print(f"Recorded action: {action_type} - {params}")
        
    def save_workflow(self, filename: str = None):
        """Save the trained workflow to disk"""
        if not filename:
            filename = f"workflow_{self.profile_name}.json"
            
        output_path = os.path.abspath(os.path.join("ai_assistant", "agents", "video", "workflows", filename))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                "profile": self.profile_name,
                "actions": self.actions
            }, f, indent=2)
            
        print(f"Workflow saved to: {output_path}")
        return output_path

    @staticmethod
    def load_workflow(filename: str) -> List[Dict]:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                return data.get("actions", [])
        return []