"""
Integration module for task chain orchestration in backend.
Connects the multi-step execution system to chat/voice endpoints.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Try to import orchestrator (will use if available)
try:
    from ai_assistant.core.task_chain_orchestrator import get_orchestrator
    ORCHESTRATOR_AVAILABLE = True
    logger.info("✅ Task Chain Orchestrator available")
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning("Task Chain Orchestrator not available")


def should_use_orchestrator(command: str) -> bool:
    """
    Determine if command should use multi-step orchestration.
    
    Indicators:
    - Contains sequential keywords (फिर, then, and, etc.)
    - Has commas separating multiple actions
    - Mentions multiple apps
    """
    if not ORCHESTRATOR_AVAILABLE:
        return False
    
    # Sequential keywords
    sequential_keywords = [
        'फिर', 'phir', 'then',
        'और फिर', 'aur phir', 'and then',
        'और', 'aur', 'and',
        'के बाद', 'ke baad', 'after',
    ]
    
    command_lower = command.lower()
    
    # Check for sequential keywords
    for keyword in sequential_keywords:
        if keyword in command_lower:
            return True
    
    # Check for comma-separated commands
    if ',' in command:
        return True
    
    return False


def process_with_orchestrator(command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process command using task chain orchestrator.
    
    Args:
        command: User command
        context: Additional context (optional)
    
    Returns:
        Dict with execution result
    """
    if not ORCHESTRATOR_AVAILABLE:
        return {
            'orche strated': False,
            'error': 'Orchestrator not available',
            'fallback': True
        }
    
    try:
        orchestrator = get_orchestrator()
        
        logger.info(f"🔗 Executing multi-step command via orchestrator: {command}")
        
        # Execute command
        result = orchestrator.execute_command(command)
        
        # Format response
        if result.success:
            message = f"✅ Completed {result.steps_completed} steps successfully!\n\n"
            
            # Add details about what was done
            for i, step_result in enumerate(result.results, 1):
                intent = step_result.get('intent', 'unknown')
                if step_result.get('success'):
                    message += f"{i}. {intent} ✓\n"
                else:
                    message += f"{i}. {intent} ✗ ({step_result.get('error', 'failed')})\n"
            
            return {
                'orchestrated': True,
                'success': True,
                'response': message.strip(),
                'steps_completed': result.steps_completed,
                'total_steps': result.total_steps,
                'results': result.results
            }
        else:
            error_msg = f"❌ Failed at step {result.steps_completed + 1}/{result.total_steps}"
            if result.error:
                error_msg += f": {result.error}"
            
            return {
                'orchestrated': True,
                'success': False,
                'response': error_msg,
                'error': result.error,
                'steps_completed': result.steps_completed,
                'total_steps': result.total_steps
            }
    
    except Exception as e:
        logger.error(f"Orchestrator execution failed: {e}", exc_info=True)
        return {
            'orchestrated': True,
            'success': False,
            'error': str(e),
            'fallback': True
        }


def get_orchestrator_status() -> Dict[str, Any]:
    """Get current orchestrator status."""
    if not ORCHESTRATOR_AVAILABLE:
        return {
            'available': False,
            'message': 'Task Chain Orchestrator not loaded'
        }
    
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_current_status()
        
        return {
            'available': True,
            'status': status
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }
