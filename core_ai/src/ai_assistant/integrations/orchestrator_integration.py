"""
Integration module for task chain orchestration in backend.
Routes ALL commands through the Executive Brain.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Try to import the Executive Brain (primary)
try:
    from ai_assistant.core.command_brain import get_executive_brain
    BRAIN_AVAILABLE = True
    logger.info("✅ Executive Brain available")
except ImportError:
    BRAIN_AVAILABLE = False
    logger.warning("Executive Brain not available")

# Fallback: direct orchestrator (legacy)
try:
    from ai_assistant.core.task_chain_orchestrator import get_orchestrator
    ORCHESTRATOR_AVAILABLE = True
    logger.info("✅ Task Chain Orchestrator available (fallback)")
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning("Task Chain Orchestrator not available")


def should_use_orchestrator(command: str) -> bool:
    """
    Determine if command should use multi-step orchestration.
    
    With the Brain available, ALL commands go through the brain
    (which internally decides single vs multi-step). But we still
    check keywords to hint to the caller that orchestration might be needed.
    """
    if not BRAIN_AVAILABLE and not ORCHESTRATOR_AVAILABLE:
        return False
    
    # Sequential keywords
    sequential_keywords = [
        'फिर', 'phir', 'then',
        'और फिर', 'aur phir', 'and then',
        'और', 'aur', 'and',
        'के बाद', 'ke baad', 'after',
    ]
    
    command_lower = command.lower()
    
    for keyword in sequential_keywords:
        if keyword in command_lower:
            return True
    
    if ',' in command:
        return True
    
    return False


def process_with_orchestrator(command: str, context: Dict[str, Any] = None,
                              source: str = 'chat') -> Dict[str, Any]:
    """
    Process command — routes through Executive Brain if available,
    falls back to direct orchestrator otherwise.
    
    Args:
        command: User command
        context: Additional context (optional)
        source: Command source ('voice', 'chat', 'api')
    
    Returns:
        Dict with execution result
    """
    # === Primary: Executive Brain ===
    if BRAIN_AVAILABLE:
        try:
            brain = get_executive_brain()
            
            logger.info(f"🧠 Routing through Executive Brain: {command} (source: {source})")
            
            response = brain.receive_command(command, source=source)
            
            if response.action_taken == 'chatting':
                # Brain says this is conversational, not a task
                return {
                    'orchestrated': False,
                    'success': False,
                    'fallback': True,
                    'brain_action': 'chatting'
                }
            
            if response.action_taken in ['executing', 'parallel', 'merged']:
                return {
                    'orchestrated': True,
                    'success': True,
                    'response': f"🧠 {response.message}",
                    'brain_action': response.action_taken,
                    'chain_id': response.chain_id,
                    'active_chains': response.active_chains,
                    'steps_completed': 0,
                    'total_steps': 0,
                }
            
            if response.action_taken == 'cancelled':
                return {
                    'orchestrated': True,
                    'success': True,
                    'response': f"🛑 {response.message}",
                    'brain_action': 'cancelled',
                    'steps_completed': 0,
                    'total_steps': 0,
                }
            
            if response.action_taken in ['paused', 'resumed']:
                return {
                    'orchestrated': True,
                    'success': True,
                    'response': f"{'⏸️' if response.action_taken == 'paused' else '▶️'} {response.message}",
                    'brain_action': response.action_taken,
                    'steps_completed': 0,
                    'total_steps': 0,
                }
            
            # Unknown action
            return {
                'orchestrated': True,
                'success': response.success,
                'response': response.message,
                'brain_action': response.action_taken,
            }
            
        except Exception as e:
            logger.error(f"Executive Brain failed, falling back: {e}", exc_info=True)
            # Fall through to legacy orchestrator
    
    # === Fallback: Direct Orchestrator (legacy) ===
    if not ORCHESTRATOR_AVAILABLE:
        return {
            'orchestrated': False,
            'error': 'Orchestrator not available',
            'fallback': True
        }
    
    try:
        orchestrator = get_orchestrator()
        
        logger.info(f"🔗 Executing multi-step command via orchestrator: {command}")
        
        result = orchestrator.execute_command(command)
        
        if result.success:
            message = f"✅ Completed {result.steps_completed} steps successfully!\n\n"
            
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
    """Get current brain/orchestrator status."""
    if BRAIN_AVAILABLE:
        try:
            brain = get_executive_brain()
            return {
                'available': True,
                'engine': 'executive_brain',
                'status': brain.get_status()
            }
        except Exception as e:
            pass
    
    if ORCHESTRATOR_AVAILABLE:
        try:
            orchestrator = get_orchestrator()
            status = orchestrator.get_current_status()
            return {
                'available': True,
                'engine': 'legacy_orchestrator',
                'status': status
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }
    
    return {
        'available': False,
        'message': 'No orchestration engine loaded'
    }
