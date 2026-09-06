# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
AI-Powered Task Planner Module

Decomposes natural language commands into executable action sequences.
Uses LLM (Gemini/GPT) to understand user intent and create step-by-step plans.

Example:
    "Open YouTube, go to history and clear history of one month"
    
    Becomes:
    1. BROWSER_NAVIGATE to youtube.com
    2. BROWSER_CLICK on profile icon
    3. BROWSER_CLICK on "History"
    4. BROWSER_CLICK on "Clear watch history"
    5. BROWSER_SELECT timeframe "Last month"
    6. BROWSER_CLICK on "Clear"
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

# Import LLM providers
from ai_assistant.ai.llm_provider import LLMFactory

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of executable actions"""
    # Browser actions
    BROWSER_NAVIGATE = "browser_navigate"
    BROWSER_CLICK = "browser_click"
    BROWSER_TYPE = "browser_type"
    BROWSER_SELECT = "browser_select"
    BROWSER_SCROLL = "browser_scroll"
    BROWSER_SCREENSHOT = "browser_screenshot"
    
    # Application actions
    APP_OPEN = "app_open"
    APP_CLOSE = "app_close"
    APP_FOCUS = "app_focus"
    APP_INTERACT = "app_interact"
    
    # System actions
    KEY_PRESS = "key_press"
    MOUSE_CLICK = "mouse_click"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    
    # Data actions
    OCR_EXTRACT = "ocr_extract"
    READ_TEXT = "read_text"
    COPY_TO_CLIPBOARD = "copy_to_clipboard"
    
    # Communication actions
    SEND_MESSAGE = "send_message"
    SEND_EMAIL = "send_email"
    
    # AI actions
    TRANSLATE = "translate"
    SUMMARIZE = "summarize"
    ANALYZE_IMAGE = "analyze_image"


@dataclass
class Action:
    """Represents a single executable action"""
    id: str
    type: ActionType
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # IDs of actions that must complete first
    optional: bool = False  # Can fail without stopping execution
    timeout: int = 30  # Seconds
    retry_count: int = 0
    max_retries: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['type'] = self.type.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Create from dictionary"""
        data['type'] = ActionType(data['type'])
        return cls(**data)


@dataclass
class TaskPlan:
    """Complete execution plan for a task"""
    id: str
    original_command: str
    actions: List[Action]
    created_at: datetime = field(default_factory=datetime.now)
    estimated_duration: int = 0  # Seconds
    safety_level: str = "safe"  # "safe", "moderate", "dangerous"
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'original_command': self.original_command,
            'actions': [a.to_dict() for a in self.actions],
            'created_at': self.created_at.isoformat(),
            'estimated_duration': self.estimated_duration,
            'safety_level': self.safety_level,
            'requires_confirmation': self.requires_confirmation,
            'metadata': self.metadata
        }


class PlanValidator:
    """Validates task plans for safety and feasibility"""
    
    # Dangerous keywords that require confirmation
    DANGER_KEYWORDS = [
        'delete', 'remove', 'clear', 'uninstall', 'format',
        'reset', 'erase', 'wipe', 'destroy', 'kill'
    ]
    
    # Blacklisted domains for safety
    BLACKLISTED_DOMAINS = [
        'malware', 'phishing', 'hack', 'crack'
    ]
    
    @staticmethod
    def validate_plan(plan: TaskPlan) -> tuple[bool, str]:
        """
        Validate a task plan for safety and feasibility
        
        Returns:
            (is_valid, message)
        """
        # Check for dangerous operations using basic keywords and PermissionSystem
        command_lower = plan.original_command.lower()
        
        for keyword in PlanValidator.DANGER_KEYWORDS:
            if keyword in command_lower:
                plan.safety_level = "dangerous"
                plan.requires_confirmation = True
                return True, f"⚠️ This action involves '{keyword}' and requires confirmation"
                
        try:
            from ai_assistant.core.permission_system import get_permission_system
            perm_sys = get_permission_system()
            if perm_sys.require_confirmation(command_lower):
                plan.safety_level = "dangerous"
                plan.requires_confirmation = True
                return True, "⚠️ This action is categorized as high risk and requires confirmation"
        except ImportError:
            pass
        
        # Check for blacklisted domains
        for domain in PlanValidator.BLACKLISTED_DOMAINS:
            if domain in command_lower:
                return False, f" Œ Operation blocked: contains blacklisted term '{domain}'"
        
        # Check action count (prevent infinite loops)
        if len(plan.actions) > 50:
            return False, "Œ Too many actions (>50). Please simplify the command."
        
        # Check for circular dependencies
        if PlanValidator._has_circular_dependencies(plan.actions):
            return False, "Œ Circular dependencies detected in action plan"
        
        return True, "… Plan validated successfully"
    
    @staticmethod
    def _has_circular_dependencies(actions: List[Action]) -> bool:
        """Check for circular dependencies"""
        action_ids = {a.id for a in actions}
        
        def has_cycle(action_id: str, visited: set, stack: set) -> bool:
            visited.add(action_id)
            stack.add(action_id)
            
            # Find action
            action = next((a for a in actions if a.id == action_id), None)
            if not action:
                return False
            
            for dep_id in action.dependencies:
                if dep_id not in action_ids:
                    continue
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, stack):
                        return True
                elif dep_id in stack:
                    return True
            
            stack.remove(action_id)
            return False
        
        visited = set()
        for action in actions:
            if action.id not in visited:
                if has_cycle(action.id, visited, set()):
                    return True
        return False


class TaskPlanner:
    """
    AI-powered task planner
    
    Uses LLM to decompose natural language into executable actions
    """
    
    def __init__(self, llm_provider: str = "gemini"):
        """
        Initialize task planner
        
        Args:
            llm_provider: "gemini" or "openai"
        """
        self.llm = LLMFactory.create(llm_provider)
        self.validator = PlanValidator()
        logger.info(f"… TaskPlanner initialized with {llm_provider}")
    
    def create_plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """
        Create execution plan from natural language command
        
        Args:
            command: Natural language command
            context: Optional context (user preferences, current state, etc.)
        
        Returns:
            TaskPlan object
        """
        logger.info(f" Planning task: {command}")
        
        # Generate plan using LLM
        actions = self._generate_actions(command, context)
        
        # Create plan object
        plan = TaskPlan(
            id=self._generate_plan_id(),
            original_command=command,
            actions=actions,
            estimated_duration=sum(a.timeout for a in actions),
            metadata={'context': context or {}}
        )
        
        # Validate plan
        is_valid, message = self.validator.validate_plan(plan)
        if not is_valid:
            raise ValueError(f"Invalid plan: {message}")
        
        logger.info(f"… Created plan with {len(actions)} actions - {message}")
        return plan
    
    def generate_repair_actions(self, failed_action: Action, error_message: str, vlm_analysis: str) -> List[Action]:
        """
        Generate remedial actions to fix a failed step.
        
        Args:
            failed_action: The action that failed
            error_message: Technical error or VLM verification failure
            vlm_analysis: Visual description of the screen
            
        Returns:
            List of new Action objects to insert
        """
        prompt = f"""You are an Expert AI Repair Agent. An action failed during execution. 
Your goal is to provide a few specific actions to fix the situation so the original goal can be verified.

**Context:**
- Failed Action: {failed_action.description} (Type: {failed_action.type.value})
- Parameters: {json.dumps(failed_action.parameters)}
- Error/Failure: {error_message}
- Visual Analysis (What the AI sees): "{vlm_analysis}"

**Instructions:**
1. Analyze why it failed (e.g., popup blocking, element not found, forgot to save).
2. Generate 1 to 3 corrective actions.
3. Return ONLY the JSON list of actions.

**Available Actions:** same as standard plan (BROWSER_CLICK, APP_INTERACT, KEY_PRESS, WAIT, etc.)

**Example:**
If failed to "Type into search" because "Search bar not active", fix might be:
[
  {{"type": "BROWSER_CLICK", "description": "Click search bar to focus", "parameters": {{"element_description": "search input"}}}},
  {{"type": "BROWSER_TYPE", "description": "Retype query", "parameters": {{"text": "{failed_action.parameters.get('text', '')}"}}}}
]
"""
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.llm.generate_response(messages)
            actions = self._parse_llm_response(response, f"Fix {failed_action.description}")
            logger.info(f"›  Generated {len(actions)} repair actions")
            return actions
        except Exception as e:
            logger.error(f"Failed to generate repairs: {e}")
            return []

    def _generate_actions(self, command: str, context: Optional[Dict[str, Any]]) -> List[Action]:
        """Generate actions using LLM"""
        
        # Create prompt for LLM
        prompt = self._create_planning_prompt(command, context)
        
        # Get response from LLM
        try:
            # Construct message for generate_response
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_response(messages)
            logger.debug(f"LLM Response: {response}")
            
            # Parse response into actions
            actions = self._parse_llm_response(response, command)
            return actions
            
        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            # Fallback to simple planning
            return self._fallback_planning(command)
    
    def _create_planning_prompt(self, command: str, context: Optional[Dict[str, Any]]) -> str:
        """Create prompt for LLM to generate task plan"""
        
        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context, indent=2)}"
        
        prompt = f"""You are an AI task planner. Break down the following command into a sequence of executable actions.

**User Command:** "{command}"{context_str}

**Available Action Types:**
- BROWSER_NAVIGATE: Navigate to a URL (params: url)
- BROWSER_CLICK: Click an element (params: element_description, selector)
- BROWSER_TYPE: Type text into an input (params: text, element_description)
- APP_OPEN: Open an application (params: app_name)
- APP_INTERACT: Interact with app (params: action_description)
- SYSTEM_TYPE: Type text globally/in active window (params: text)
- SYSTEM_PRESS: Press key like 'enter', 'win' (params: key)
- WAIT: Wait for duration (params: seconds)

**Examples:**
Command: "Open notepad and write hello world"
[
  {{"type": "APP_OPEN", "description": "Open Notepad", "parameters": {{"app_name": "notepad"}}}},
  {{"type": "WAIT", "description": "Wait for app", "parameters": {{"seconds": 2}}}},
  {{"type": "SYSTEM_TYPE", "description": "Type text", "parameters": {{"text": "hello world"}}}}
]

Command: "Search youtube for cats"
[
  {{"type": "BROWSER_NAVIGATE", "description": "Go to YouTube", "parameters": {{"url": "youtube.com"}}}},
  {{"type": "BROWSER_TYPE", "description": "Type search query", "parameters": {{"text": "cats", "element_description": "search box"}}}},
  {{"type": "BROWSER_CLICK", "description": "Click search", "parameters": {{"element_description": "search button"}}}}
]

Command: "Open youtube and clear my one week history"
[
  {{"type": "BROWSER_NAVIGATE", "description": "Go to YouTube", "parameters": {{"url": "youtube.com"}}}},
  {{"type": "BROWSER_CLICK", "description": "Click History", "parameters": {{"element_description": "History"}}}},
  {{"type": "BROWSER_CLICK", "description": "Click Clear History", "parameters": {{"element_description": "Clear all watch history"}}}},
  {{"type": "WAIT", "description": "Wait for confirmation", "parameters": {{"seconds": 1}}}},
  {{"type": "BROWSER_CLICK", "description": "Confirm clear", "parameters": {{"element_description": "Clear watch history"}}}}
]

**Instructions:**
1. Break down composite commands (like "open X and do Y") into separate actions.
2. Ensure app names are clean (e.g. "notepad", not "notepad and write...").
3. Use WAIT between opening apps and typing.
3. Add dependencies where actions must execute in order
4. Be specific with element descriptions (e.g., "History button in dropdown menu")
5. Return ONLY a valid JSON array of actions

**JSON Format:**
```json
[
  {{
    "id": "action_1",
    "type": "BROWSER_NAVIGATE",
    "description": "Navigate to YouTube homepage",
    "parameters": {{"url": "https://www.youtube.com"}},
    "dependencies": []
  }},
  {{
    "id": "action_2",
    "type": "BROWSER_CLICK",
    "description": "Click on profile icon",
    "parameters": {{"element_description": "profile icon in top-right corner"}},
    "dependencies": ["action_1"]
  }}
]
```

**Generate the action plan now:**"""
        
        return prompt
    
    def _parse_llm_response(self, response: str, original_command: str) -> List[Action]:
        """Parse LLM response into Action objects"""
        
        # Extract JSON from response
        json_str = self._extract_json(response)
        
        try:
            actions_data = json.loads(json_str)
            
            if not isinstance(actions_data, list):
                raise ValueError("Response is not a list of actions")
            
            actions = []
            for i, action_data in enumerate(actions_data):
                # Ensure required fields
                if 'type' not in action_data:
                    logger.warning(f"Action {i} missing 'type', skipping")
                    continue
                
                # Convert type string to ActionType enum
                try:
                    type_str = action_data['type'].lower()
                    # Handle common variations
                    if type_str == 'browser_navigate':
                        action_type = ActionType.BROWSER_NAVIGATE
                    elif type_str == 'browser_click':
                        action_type = ActionType.BROWSER_CLICK
                    # ... add generic lookup
                    else:
                        action_type = ActionType(type_str)
                except ValueError:
                    logger.warning(f"Unknown action type: {action_data['type']}, skipping")
                    continue
                
                action = Action(
                    id=action_data.get('id', f'action_{i+1}'),
                    type=action_type,
                    description=action_data.get('description', ''),
                    parameters=action_data.get('parameters', {}),
                    dependencies=action_data.get('dependencies', []),
                    optional=action_data.get('optional', False),
                    timeout=action_data.get('timeout', 30)
                )
                actions.append(action)
            
            return actions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"JSON string: {json_str}")
            return self._fallback_planning(original_command)
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response (handles markdown code blocks)"""
        
        # Try to find JSON in code blocks
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            return text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            return text[start:end].strip()
        
        # Try to find JSON array directly
        if '[' in text and ']' in text:
            start = text.find('[')
            # Find matching closing bracket
            bracket_count = 0
            for i in range(start, len(text)):
                if text[i] == '[':
                    bracket_count += 1
                elif text[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        return text[start:i+1]
        
        # Return as-is and let JSON parser fail
        return text.strip()
    
    def _fallback_planning(self, command: str) -> List[Action]:
        """
        Fallback planning when LLM fails
        Creates simple single-action plans
        """
        logger.warning("Using fallback planning")
        
        command_lower = command.lower()
        
        # Detect intent from keywords
        if 'open' in command_lower and ('youtube' in command_lower or 'browser' in command_lower):
            return [
                Action(
                    id='action_1',
                    type=ActionType.BROWSER_NAVIGATE,
                    description='Navigate to YouTube',
                    parameters={'url': 'https://www.youtube.com'}
                )
            ]
        
        elif 'whatsapp' in command_lower and ('message' in command_lower or 'send' in command_lower):
            # Extract contact name (basic)
            words = command.split()
            contact = "unknown"
            message = command
            
            return [
                Action(
                    id='action_1',
                    type=ActionType.APP_OPEN,
                    description='Open WhatsApp',
                    parameters={'app_name': 'WhatsApp'}
                ),
                Action(
                    id='action_2',
                    type=ActionType.SEND_MESSAGE,
                    description=f'Send message to {contact}',
                    parameters={'contact': contact, 'message': message, 'platform': 'whatsapp'},
                    dependencies=['action_1']
                )
            ]
        
        else:
            # Generic fallback
            return [
                Action(
                    id='action_1',
                    type=ActionType.WAIT,
                    description='Unable to parse command, waiting for clarification',
                    parameters={'seconds': 1}
                )
            ]
    
    @staticmethod
    def _generate_plan_id() -> str:
        """Generate unique plan ID"""
        import uuid
        return f"plan_{uuid.uuid4().hex[:8]}"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create planner
    planner = TaskPlanner()
    
    # Test commands
    test_commands = [
        "Open YouTube, go to history and clear history of one month",
        "Open sticky notes and read the notes",
        "Send a WhatsApp message to mom saying hello",
        "Translate this page and send summary to John"
    ]
    
    for cmd in test_commands:
        print(f"\n{'='*60}")
        print(f"Command: {cmd}")
        print('='*60)
        
        try:
            plan = planner.create_plan(cmd)
            print(f"\n… Plan created: {len(plan.actions)} actions")
            print(f"Safety level: {plan.safety_level}")
            print(f"Estimated duration: {plan.estimated_duration}s")
            
            for i, action in enumerate(plan.actions, 1):
                print(f"\n{i}. {action.type.value}")
                print(f"   Description: {action.description}")
                print(f"   Parameters: {action.parameters}")
                if action.dependencies:
                    print(f"   Dependencies: {action.dependencies}")
        
        except Exception as e:
            print(f"\nŒ Error: {e}")

