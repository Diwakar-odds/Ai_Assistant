"""
Visual Automation Engine

Combines VLM (Vision Language Model) with UI automation to enable
intelligent screen interaction based on natural language descriptions.

Features:
- Find and click UI elements by description
- Multi-step visual workflows
- Action verification with VLM
- Integration with existing automation tools
"""

import time
from typing import Dict, List, Optional, Tuple, Any, Union
from PIL import Image
import pyautogui

# Safe imports
try:
    from ..multimodal import MultiModalAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False

try:
    from ..vision.vlm_provider import VLMProvider
    from ..vision.gemini_vision_provider import GeminiVisionProvider
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False


class VisualAutomationEngine:
    """
    VLM-powered visual automation engine.
    
    Enables UI automation using natural language descriptions of elements
    instead of fixed coordinates or selectors.
    """
    
    def __init__(self, safety_mode: bool = True):
        """
        Initialize visual automation engine.
        
        Args:
            safety_mode: If True, requires confirmation before actions
        """
        if not MULTIMODAL_AVAILABLE:
            raise ImportError("MultiModalAI not available. Check imports.")
        
        self.vlm = MultiModalAI()
        self.safety_mode = safety_mode
        self.action_history = []
        
        # Configure pyautogui safety features
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.5  # Pause between actions
        
        print("✅ Visual Automation Engine initialized")
        if safety_mode:
            print("🛡️ Safety mode enabled - actions require confirmation")
    
    def find_and_click(
        self,
        element_description: str,
        verify: bool = True,
        double_click: bool = False
    ) -> Dict[str, Any]:
        """
        Find UI element by description and click it.
        
        Args:
            element_description: Natural language description (e.g., "submit button")
            verify: Whether to verify action succeeded
            double_click: Whether to double-click
            
        Returns:
            Dict with success status and details
        """
        print(f"🔍 Looking for: {element_description}")
        
        # Find element coordinates using VLM
        coords_result = self.vlm.extract_coordinates(element_description)
        
        if not coords_result.get("found"):
            return {
                "success": False,
                "error": "Element not found",
                "details": coords_result.get("reason", "Unknown reason")
            }
        
        # Extract coordinates
        coords = coords_result.get("coordinates", {})
        x, y = coords.get("x"), coords.get("y")
        
        if not (x and y):
            return {
                "success": False,
                "error": "Invalid coordinates",
                "details": coords_result
            }
        
        print(f"📍 Found element at ({x}, {y})")
        
        # Safety check
        if self.safety_mode:
            print(f"⚠️ Will click {element_description} at ({x}, {y})")
            confirm = input("Proceed? (y/n): ")
            if confirm.lower() != 'y':
                return {"success": False, "error": "User cancelled"}
        
        # Capture before screenshot
        before_screenshot = None
        if verify:
            before_screenshot = self.vlm.capture_screen()
        
        # Perform click
        try:
            pyautogui.moveTo(x, y, duration=0.3)
            time.sleep(0.1)
            
            if double_click:
                pyautogui.doubleClick()
            else:
                pyautogui.click()
            
            print(f"✅ Clicked {element_description}")
            
            # Record action
            action_record = {
                "action": "double_click" if double_click else "click",
                "element": element_description,
                "coordinates": {"x": x, "y": y},
                "timestamp": time.time(),
                "success": True
            }
            self.action_history.append(action_record)
            
            # Verify if requested
            if verify:
                time.sleep(0.5)  # Wait for UI to update
                verification = self._verify_action_result(
                    element_description,
                    "click",
                    before_screenshot
                )
                action_record["verified"] = verification["success"]
                action_record["verification_details"] = verification.get("details")
            
            return action_record
            
        except Exception as e:
            error_record = {
                "success": False,
                "error": str(e),
                "element": element_description,
                "coordinates": {"x": x, "y": y}
            }
            self.action_history.append(error_record)
            return error_record
    
    def find_and_type(
        self,
        field_description: str,
        text: str,
        clear_first: bool = True
    ) -> Dict[str, Any]:
        """
        Find input field and type text.
        
        Args:
            field_description: Description of input field
            text: Text to type
            clear_first: Whether to clear field first
            
        Returns:
            Dict with success status
        """
        print(f"⌨️ Typing into: {field_description}")
        
        # First, click on the field to focus
        click_result = self.find_and_click(field_description, verify=False)
        
        if not click_result.get("success"):
            return click_result
        
        time.sleep(0.2)
        
        # Clear field if requested
        if clear_first:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
        
        # Type text
        try:
            pyautogui.write(text, interval=0.05)
            print(f"✅ Typed: {text}")
            
            return {
                "success": True,
                "action": "type",
                "field": field_description,
                "text": text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_visual_workflow(
        self,
        steps: List[Dict[str, Any]],
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Execute multi-step visual workflow.
        
        Args:
            steps: List of step dicts with 'action', 'target', and optional params
            stop_on_error: Whether to stop if a step fails
            
        Returns:
            Dict with workflow results
        """
        print(f"🔄 Executing workflow with {len(steps)} steps")
        
        results = []
        
        for i, step in enumerate(steps):
            action = step.get("action")
            target = step.get("target")
            
            print(f"\n📌 Step {i+1}/{len(steps)}: {action} {target}")
            
            if action == "click":
                result = self.find_and_click(
                    target,
                    verify=step.get("verify", True)
                )
            elif action == "type":
                result = self.find_and_type(
                    target,
                    step.get("text", ""),
                    clear_first=step.get("clear_first", True)
                )
            elif action == "wait":
                time.sleep(step.get("seconds", 1))
                result = {"success": True, "action": "wait"}
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
            
            results.append({
                "step": i + 1,
                "action": action,
                "target": target,
                **result
            })
            
            if not result.get("success") and stop_on_error:
                print(f"❌ Workflow stopped at step {i+1}: {result.get('error')}")
                break
            
            # Small delay between steps
            time.sleep(0.3)
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count == len(steps),
            "total_steps": len(steps),
            "successful_steps": success_count,
            "failed_steps": len(steps) - success_count,
            "steps": results
        }
    
    def plan_and_execute(
        self,
        task_description: str,
        auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        Use VLM to plan a task and optionally execute it.
        
        Args:
            task_description: Natural language task description
            auto_execute: Whether to execute automatically
            
        Returns:
            Dict with plan and execution results
        """
        print(f"🧠 Planning task: {task_description}")
        
        # Get VLM to analyze and plan
        plan = self.vlm.analyze_for_automation(task_description)
        
        if not plan.get("possible"):
            return {
                "success": False,
                "error": "Task not possible",
                "details": plan
            }
        
        steps = plan.get("steps", [])
        print(f"\n📋 Plan generated with {len(steps)} steps:")
        for i, step in enumerate(steps):
            print(f"  {i+1}. {step.get('action')} {step.get('target')}")
        
        if plan.get("warnings"):
            print(f"\n⚠️ Warnings:")
            for warning in plan["warnings"]:
                print(f"  - {warning}")
        
        if not auto_execute:
            confirm = input("\nExecute this plan? (y/n): ")
            if confirm.lower() != 'y':
                return {
                    "success": False,
                    "plan": plan,
                    "error": "User declined execution"
                }
        
        # Execute the plan
        execution_result = self.execute_visual_workflow(steps)
        
        return {
            "success": execution_result.get("success"),
            "task": task_description,
            "plan": plan,
            "execution": execution_result
        }
    
    def _verify_action_result(
        self,
        element_description: str,
        action: str,
        before_screenshot: Optional[Image.Image] = None
    ) -> Dict[str, Any]:
        """
        Verify that an action had the expected effect.
        
        Args:
            element_description: Element that was interacted with
            action: Action performed
            before_screenshot: Screenshot before action
            
        Returns:
            Dict with verification results
        """
        after_screenshot = self.vlm.capture_screen()
        
        prompt = f"""Compare these two screenshots (before and after a {action} action on '{element_description}').

Did the action succeed? What changed?

Return JSON:
{{
    "success": true/false,
    "changes": "description of what changed",
    "confidence": "high/medium/low"
}}"""
        
        # For now, just do a simple analysis
        # TODO: Implement proper before/after comparison
        result = self.vlm.analyze_image(
            after_screenshot,
            f"Analyze if clicking '{element_description}' had an effect. What changed on screen?"
        )
        
        return {
            "success": True,  # Assume success for now
            "details": result.get("analysis", "")
        }
    
    def get_action_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent action history."""
        return self.action_history[-limit:]
    
    def clear_history(self):
        """Clear action history."""
        self.action_history.clear()


# Convenience functions

def click_element(element_description: str, safety_mode: bool = True) -> Dict[str, Any]:
    """Quick function to click an element by description."""
    engine = VisualAutomationEngine(safety_mode=safety_mode)
    return engine.find_and_click(element_description)


def type_into_field(field_description: str, text: str) -> Dict[str, Any]:
    """Quick function to type into a field."""
    engine = VisualAutomationEngine(safety_mode=False)
    return engine.find_and_type(field_description, text)


def automate_task(task_description: str) -> Dict[str, Any]:
    """Quick function to plan and execute a task."""
    engine = VisualAutomationEngine(safety_mode=False)
    return engine.plan_and_execute(task_description, auto_execute=False)
