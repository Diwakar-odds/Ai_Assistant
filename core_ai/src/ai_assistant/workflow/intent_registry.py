# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Intent Registry for mapping natural language intents to workflow templates.
Scans workflow templates directory and builds intent mappings.
"""

import os
import yaml
import glob
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class IntentMapping:
    """Represents a mapping from intent to workflow template."""
    intent: str
    entities: List[str]
    workflow_path: str
    description: str = ""
    confidence: float = 1.0

class IntentRegistry:
    """Registry for mapping natural language intents to workflow templates."""
    
    def __init__(self, templates_dir: str = None):
        """
        Initialize the intent registry.
        
        Args:
            templates_dir: Directory containing workflow template YAML files.
                          Defaults to src/ai_assistant/workflow/templates/
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(current_dir, "templates")
        
        self.templates_dir = templates_dir
        self.intent_mappings: Dict[str, IntentMapping] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all workflow templates from the templates directory."""
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Warning: Templates directory not found: {self.templates_dir}")
            return
        
        # Find all YAML files in templates directory
        pattern = os.path.join(self.templates_dir, "*.yaml")
        yaml_files = glob.glob(pattern)
        
        for yaml_file in yaml_files:
            try:
                self._load_template_file(yaml_file)
            except Exception as e:
                logger.warning(f"Warning: Failed to load template {yaml_file}: {e}")
    
    def _load_template_file(self, filepath: str):
        """Load a single workflow template file and extract intent information."""
        with open(filepath, 'r', encoding='utf-8') as f:
            template_data = yaml.safe_load(f)
        
        # Support both root-level and metadata-nested schemas
        metadata = template_data.get('metadata', {})
        intent = template_data.get('intent') or metadata.get('intent')
        entities = template_data.get('entities') or metadata.get('entities', [])
        description = template_data.get('description') or metadata.get('description', '')
        
        if intent:
            # Create intent mapping
            mapping = IntentMapping(
                intent=intent,
                entities=entities,
                workflow_path=filepath,
                description=description
            )
            
            # Use upper and lowercase versions
            self.intent_mappings[intent] = mapping
            self.intent_mappings[intent.lower()] = mapping
            
            # Also add any aliases if present
            aliases = template_data.get('aliases') or metadata.get('aliases', [])
            for alias in aliases:
                self.intent_mappings[alias] = mapping
                self.intent_mappings[alias.lower()] = mapping
    
    def get_intent_mapping(self, intent: str) -> Optional[IntentMapping]:
        """
        Get the intent mapping for a given intent string.
        
        Args:
            intent: The intent string to look up
            
        Returns:
            IntentMapping if found, None otherwise
        """
        return self.intent_mappings.get(intent.lower().strip())
    
    def get_all_intents(self) -> List[str]:
        """Get a list of all registered intents."""
        return list(self.intent_mappings.keys())
    
    def reload_templates(self):
        """Reload all template files."""
        self.intent_mappings.clear()
        self._load_templates()

# Global instance for easy access
intent_registry = IntentRegistry()