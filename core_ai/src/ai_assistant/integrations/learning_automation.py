"""
Learning-Enhanced Automation Wrapper
Wraps automation tools with learning capabilities

This module provides intelligent wrappers around automation functions
that learn from usage patterns and improve over time.
"""

import time
import logging
from typing import Any, Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import learning integration
try:
    from ai_assistant.integrations.learning_integration import get_learning_assistant
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    logger.warning("Learning integration not available")


def with_learning(func: Callable) -> Callable:
    """
    Decorator to add learning capabilities to automation functions
    Logs execution for learning and provides intelligent suggestions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not LEARNING_AVAILABLE:
            # Run without learning
            return func(*args, **kwargs)
        
        start_time = time.time()
        success = False
        result = None
        error = None
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            success = True
            return result
            
        except Exception as e:
            error = str(e)
            raise
            
        finally:
            # Log the execution for learning
            try:
                execution_time = time.time() - start_time
                assistant = get_learning_assistant()
                
                # Create command string
                func_name = func.__name__
                args_str = ', '.join(str(a) for a in args[:2])  # First 2 args only
                command = f"{func_name}({args_str})"
                
                # Log the execution
                assistant.log_command_execution(
                    command=command,
                    output=str(result) if result else str(error),
                    success=success,
                    execution_time=execution_time
                )
                
                # Update context
                assistant.update_context({
                    'last_command': func_name,
                    'last_success': success
                })
                
            except Exception as e:
                logger.error(f"Failed to log learning data: {e}")
    
    return wrapper


def get_smart_suggestion(current_task: str) -> Optional[str]:
    """Get smart suggestion based on current task"""
    if not LEARNING_AVAILABLE:
        return None
    
    try:
        assistant = get_learning_assistant()
        recommendations = assistant.get_workflow_suggestions(current_task)
        if recommendations:
            return recommendations[0].get('workflow')
    except Exception as e:
        logger.error(f"Failed to get suggestion: {e}")
    
    return None


def predict_next_action(command_history: list) -> Optional[str]:
    """Predict next action based on command history"""
    if not LEARNING_AVAILABLE or not command_history:
        return None
    
    try:
        assistant = get_learning_assistant()
        return assistant.predict_next_command(
            recent_commands=command_history[-5:],
            recent_outputs=[],
            context=assistant.current_context
        )
    except Exception as e:
        logger.error(f"Failed to predict action: {e}")
    
    return None


def enhance_voice_recognition(transcription: str, confidence: float) -> str:
    """Enhance voice recognition using adaptive learning"""
    if not LEARNING_AVAILABLE:
        return transcription
    
    try:
        assistant = get_learning_assistant()
        assistant.log_voice_recognition(transcription, None, confidence)
        
        # Could apply corrections based on learned patterns here
        return transcription
        
    except Exception as e:
        logger.error(f"Voice enhancement error: {e}")
        return transcription


def log_automation_workflow(workflow_name: str, steps: list, success: bool):
    """Log complete automation workflow for learning"""
    if not LEARNING_AVAILABLE:
        return
    
    try:
        assistant = get_learning_assistant()
        assistant.log_command_execution(
            command=f"workflow:{workflow_name}",
            output=f"Steps: {len(steps)}",
            success=success,
            execution_time=sum(s.get('time', 0) for s in steps)
        )
    except Exception as e:
        logger.error(f"Workflow logging error: {e}")


# Example usage:
# from ai_assistant.integrations.learning_automation import with_learning
# 
# @with_learning
# def my_automation_function(arg1, arg2):
#     # Your automation code here
#     return result
