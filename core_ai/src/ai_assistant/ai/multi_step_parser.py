"""
Multi-Step Command Parser
Breaks down complex commands into sequential sub-tasks.
Handles English, Hindi, and Hinglish.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """Represents a single step in a task chain."""
    step: int
    intent: str
    params: Dict[str, Any]
    dependencies: List[int] = None
    original_text: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class MultiStepCommandParser:
    """
    Parses complex, multi-step commands into sequential tasks.
    
    Examples:
        "WhatsApp खोलो, मॉम को message करो"
        → [open_app(WhatsApp), send_message(Mom)]
        
        "YouTube open करो, video play करो, 20 minutes skip करो"
        → [open_app(YouTube), play_video(), skip_time(20min)]
    """
    
    def __init__(self):
        """Initialize parser with patterns."""
        # Sequential keywords that indicate multiple steps
        self.sequential_keywords = [
            'फिर', 'phir', 'then',
            'और फिर', 'aur phir', 'and then',
            'और', 'aur', 'and',
            'के बाद', 'ke baad', 'after',
            'फिर से', 'phir se', 'again',
            'बाद में', 'baad me', 'later'
        ]
        
        # Common action patterns
        self.action_patterns = {
            'open_app': [
                r'(\w+)\s+(खोलो|kholo|open|start|चालू करो|launch)',
                r'(खोलो|kholo|open)\s+(\w+)',
            ],
            'send_message': [
                r'(\w+)\s+को\s+(message|भेजो|send|बोल दो)',
                r'(message|भेजो|send)\s+(?:to\s+)?(\w+)',
            ],
            'type_text': [
                r'(?:type|लिखो|likho)\s+(.+)',
                r'(.+)\s+लिखो',
            ],
            'play_video': [
                r'(video|वीडियो)\s+(play|चलाओ|chalao)',
                r'(play|चलाओ)\s+(video|वीडियो)',
            ],
            'skip_time': [
                r'(\d+)\s+(minutes?|mins?|मिनट)\s+(skip|आगे बढ़ाओ|forward)',
                r'(skip|आगे बढ़ाओ)\s+(\d+)\s+(minutes?|mins?|मिनट)',
            ],
        }
        
        # Import existing intent recognizer
        try:
            from ai_assistant.ai.intent_recognizer import IntentRecognizer
            self.intent_recognizer = IntentRecognizer()
        except ImportError:
            self.intent_recognizer = None
            logger.warning("Intent recognizer not available")
    
    def is_multi_step(self, command: str) -> bool:
        """Check if command contains multiple steps."""
        command_lower = command.lower()
        
        # Check for sequential keywords
        for keyword in self.sequential_keywords:
            if keyword in command_lower:
                return True
        
        # Check for comma-separated commands
        if ',' in command:
            return True
        
        return False
    
    def split_into_steps(self, command: str) -> List[str]:
        """
        Split command into individual step strings.
        
        Args:
            command: Full command string
        
        Returns:
            List of command strings, one per step
        """
        steps = []
        
        # First try splitting by sequential keywords
        remaining = command
        for keyword in self.sequential_keywords:
            if keyword in remaining.lower():
                # Split by this keyword
                parts = re.split(rf'\s+{re.escape(keyword)}\s+', remaining, flags=re.IGNORECASE)
                steps.extend([p.strip() for p in parts if p.strip()])
                break
        
        # If no sequential keywords, try comma separation
        if not steps:
            parts = command.split(',')
            steps = [p.strip() for p in parts if p.strip()]
        
        # If still nothing, it's a single step
        if not steps:
            steps = [command.strip()]
        
        return steps
    
    def parse_single_step(self, step_text: str, step_number: int) -> TaskStep:
        """
        Parse a single command step.
        
        Args:
            step_text: Text of this step
            step_number: Step number (1-indexed)
        
        Returns:
            TaskStep object
        """
        # Use intent recognizer if available
        if self.intent_recognizer:
            result = self.intent_recognizer.parse_command(step_text)
            
            return TaskStep(
                step=step_number,
                intent=result.get('intent', 'unknown'),
                params={
                    'app_name': result.get('app_name'),
                    'text': step_text,
                    **result
                },
                original_text=step_text
            )
        
        # Fallback: Simple pattern matching
        intent = 'unknown'
        params = {'text': step_text}
        
        # Try to match known patterns
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, step_text, re.IGNORECASE)
                if match:
                    intent = action
                    params['matched_pattern'] = pattern
                    params['matches'] = match.groups()
                    break
            if intent != 'unknown':
                break
        
        return TaskStep(
            step=step_number,
            intent=intent,
            params=params,
            original_text=step_text
        )
    
    def infer_dependencies(self, steps: List[TaskStep]) -> List[TaskStep]:
        """
        Infer dependencies between steps.
        
        For example:
        - "send_message" depends on app being open
        - "skip_time" depends on video being played
        """
        for i, step in enumerate(steps):
            dependencies = []
            
            # send_message depends on previous open_app
            if step.intent in ['send_message', 'type_text']:
                # Find last open_app step
                for j in range(i - 1, -1, -1):
                    if steps[j].intent == 'open_app':
                        dependencies.append(steps[j].step)
                        break
            
            # skip_time depends on play_video
            if step.intent == 'skip_time':
                for j in range(i - 1, -1, -1):
                    if steps[j].intent == 'play_video':
                        dependencies.append(steps[j].step)
                        break
            
            step.dependencies = dependencies
        
        return steps
    
    def parse_command(self, command: str) -> List[TaskStep]:
        """
        Parse a command into task steps.
        
        Args:
            command: Full command string
        
        Returns:
            List of TaskStep objects
        
        Example:
            >>> parser.parse_command("WhatsApp खोलो, मॉम को message करो")
            [
                TaskStep(step=1, intent='open_app', params={'app_name': 'whatsapp'}),
                TaskStep(step=2, intent='send_message', params={'contact': 'मॉम'}, dependencies=[1])
            ]
        """
        logger.info(f"Parsing command: {command}")
        
        # Check if multi-step
        if not self.is_multi_step(command):
            # Single step
            step = self.parse_single_step(command, 1)
            return [step]
        
        # Multi-step: split and parse each
        step_texts = self.split_into_steps(command)
        logger.debug(f"Split into {len(step_texts)} steps: {step_texts}")
        
        steps = []
        for i, step_text in enumerate(step_texts, start=1):
            step = self.parse_single_step(step_text, i)
            steps.append(step)
        
        # Infer dependencies
        steps = self.infer_dependencies(steps)
        
        logger.info(f"Parsed {len(steps)} steps with dependencies")
        return steps
    
    def extract_message_content(self, command: str) -> Optional[str]:
        """
        Extract message content from command.
        
        Looks for patterns like:
        - "message करो कि <content>"
        - "बोल दो कि <content>"
        """
        patterns = [
            r'(?:message|भेजो|send).*?(?:कि|ki|that)\s+(.+)',
            r'(?:बोल|bol|tell).*?(?:कि|ki|that)\s+(.+)',
            r'(?:message|भेजो|send)\s+["\'](.+?)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_contact_name(self, command: str) -> Optional[str]:
        """Extract contact/recipient name from command."""
        patterns = [
            r'(\w+)\s+को\s+(?:message|भेजो|send)',
            r'(?:message|भेजो|send)\s+(?:to\s+)?(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def enhance_step_params(self, step: TaskStep, full_command: str) -> TaskStep:
        """
        Enhance step parameters with extracted information.
        
        For example, extract message content and contact for send_message intent.
        """
        if step.intent == 'send_message':
            # Extract contact
            contact = self.extract_contact_name(step.original_text)
            if contact:
                step.params['contact'] = contact
            
            # Extract message content
            message = self.extract_message_content(full_command)
            if message:
                step.params['message'] = message
        
        return step


# Convenience function
def parse_multi_step_command(command: str) -> List[TaskStep]:
    """Parse a multi-step command into task steps."""
    parser = MultiStepCommandParser()
    return parser.parse_command(command)
