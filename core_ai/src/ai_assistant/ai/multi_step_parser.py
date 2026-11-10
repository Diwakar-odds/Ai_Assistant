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
        
        # Import unified intent router
        try:
            from ai_assistant.ai.intent_router import IntentRouter
            self.intent_router = IntentRouter()
        except Exception as e:
            self.intent_router = None
            logger.warning(f"Intent router not available in multi_step_parser: {e}")
    
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
        """
        steps = []
        
        # First try splitting by sequential keywords (longest first to avoid partial matches)
        sorted_keywords = sorted(self.sequential_keywords, key=len, reverse=True)
        for keyword in sorted_keywords:
            pattern = rf'\s+\b{re.escape(keyword)}\b\s+'
            if re.search(pattern, command, re.IGNORECASE):
                parts = re.split(pattern, command, flags=re.IGNORECASE)
                steps.extend([p.strip() for p in parts if p.strip()])
                break
        
        # If no sequential keywords, try comma separation
        if not steps and ',' in command:
            parts = command.split(',')
            steps = [p.strip() for p in parts if p.strip()]
        
        # If still nothing, it's a single step
        if not steps:
            steps = [command.strip()]
        
        return steps

    def infer_dependencies(self, steps: List[TaskStep]) -> List[TaskStep]:
        """Infer dependencies between sequential steps."""
        for i in range(1, len(steps)):
            steps[i].dependencies = [steps[i - 1].step]
        return steps
    
    def parse_single_step(self, step_text: str, step_number: int) -> TaskStep:
        """
        Parse a single command step using IntentRouter with regex fallback.
        """
        step_text_clean = step_text.strip()
        
        # 1. Try unified IntentRouter first
        if getattr(self, 'intent_router', None):
            try:
                res = self.intent_router.route(step_text_clean)
                if res and res.intent_name and res.intent_name not in ['conversational', 'info_query']:
                    params = dict(res.parameters or {})
                    params['text'] = step_text_clean
                    if 'target' in params and 'app_name' not in params:
                        params['app_name'] = params['target']
                    return TaskStep(
                        step=step_number,
                        intent=res.intent_name,
                        params=params,
                        original_text=step_text_clean
                    )
            except Exception as e:
                logger.debug(f"Intent router in parse_single_step fallback: {e}")
        
        # 2. Fallback: Simple pattern matching
        intent = 'unknown'
        params = {'text': step_text_clean}
        
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, step_text_clean, re.IGNORECASE)
                if match:
                    intent = action
                    groups = match.groups()
                    params['matched_pattern'] = pattern
                    params['matches'] = groups
                    if action == 'open_app':
                        kw_words = {'kholo', 'khojo', 'open', 'start', 'launch', 'chalu', 'chalu karo'}
                        cands = [g for g in groups if g and g.lower().strip() not in kw_words]
                        if cands:
                            params['app_name'] = cands[0].strip()
                            params['target'] = cands[0].strip()
                    elif action == 'send_message':
                        kw_words = {'message', 'bhejo', 'send', 'bol do'}
                        cands = [g for g in groups if g and g.lower().strip() not in kw_words]
                        if cands:
                            params['contact'] = cands[0].strip()
                    break
            if intent != 'unknown':
                break
        
        return TaskStep(
            step=step_number,
            intent=intent,
            params=params,
            original_text=step_text_clean
        )


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
            step = self.enhance_step_params(step, command)
            steps.append(step)
        
        # Forward profile context from earlier open_app steps to dependent search/media steps
        inherited_profile = None
        for s in steps:
            if s.intent == 'open_app' and s.params.get('profile'):
                inherited_profile = s.params['profile']
            elif inherited_profile and s.intent in ['youtube_search', 'search_web', 'play_media', 'play_video', 'youtube_history']:
                if 'profile' not in s.params or not s.params['profile']:
                    s.params['profile'] = inherited_profile

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
        """
        if step.intent == 'send_message':
            contact = self.extract_contact_name(step.original_text)
            if contact:
                step.params['contact'] = contact
            message = self.extract_message_content(full_command)
            if message:
                step.params['message'] = message

        elif step.intent == 'open_app':
            target = step.params.get('target') or step.params.get('app_name') or ''
            for p in ['rancho', 'diwakar saurashtra', 'saurashtra', 'diwakar', 'rajat', 'kit']:
                if p in target.lower():
                    step.params['profile'] = p
                    step.params['target'] = p.title()
                    step.params['app_name'] = p.title()
                    break

        elif step.intent in ['youtube_search', 'search_web']:
            q = step.params.get('query') or ''
            if q:
                cleaned = re.sub(r'^(?:for|of)\s+', '', q, flags=re.IGNORECASE)
                cleaned = re.sub(r'\b(on\s+youtube|in\s+youtube|youtube\s+pe|youtube\s+par)\b', '', cleaned, flags=re.IGNORECASE).strip()
                step.params['query'] = cleaned

        return step


# Convenience function
def parse_multi_step_command(command: str) -> List[TaskStep]:
    """Parse a multi-step command into task steps."""
    parser = MultiStepCommandParser()
    return parser.parse_command(command)
