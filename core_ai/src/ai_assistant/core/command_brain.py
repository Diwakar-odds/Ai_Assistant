"""
Executive Brain — Central Command Intelligence
The 'thinking layer' between ALL input sources and ALL execution systems.

Responsibilities:
1. Receive ALL commands from ALL sources (voice, chat, API)
2. Classify: Executive (stop/cancel) vs Task vs Conversational
3. Decide relatedness: Is this related to something running? (Intent-based, NOT time-based)
4. Route: Merge into active chain, start parallel chain, or cancel
5. Track: Know what's running, what's queued, what's done
"""

import logging
import threading
import time
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from ai_assistant.core.command_models import (
    TimestampedCommand, CommandClassification, CommandSource,
    CommandPriority, BrainState, ManagedChain, BrainResponse,
    EXECUTIVE_STOP_KEYWORDS, EXECUTIVE_PAUSE_KEYWORDS,
    EXECUTIVE_RESUME_KEYWORDS, SEQUENTIAL_KEYWORDS,
    MODIFICATION_KEYWORDS,
)

logger = logging.getLogger(__name__)

# Known app names for relatedness detection
KNOWN_APPS = {
    'chrome', 'firefox', 'edge', 'brave', 'opera', 'safari',  # browsers
    'whatsapp', 'telegram', 'discord', 'slack', 'teams', 'signal',  # messaging
    'notepad', 'word', 'excel', 'powerpoint', 'vscode', 'code',  # productivity
    'spotify', 'vlc', 'youtube', 'music',  # media
    'explorer', 'file manager', 'files',  # file management
    'settings', 'control panel',  # system
    'calculator', 'paint', 'photos', 'camera',  # utilities
}

BROWSER_APPS = {'chrome', 'firefox', 'edge', 'brave', 'opera', 'safari'}

# Actions that imply "do this in the current app"
CONTEXT_DEPENDENT_INTENTS = {
    'search', 'type', 'write', 'send', 'click', 'scroll',
    'go to', 'navigate', 'play', 'pause', 'skip', 'forward',
    'download', 'upload', 'attach', 'share',
}


class ExecutiveBrain:
    """
    Central command processor.
    
    Decision flow for each incoming command:
    1. Is this an executive command (stop/cancel/pause)? → Handle immediately
    2. Does this modify a pending/active chain? ("no wait, use Firefox") → Modify
    3. Is this related to an active chain? → Merge/append
    4. Is this independent? → Start new parallel chain
    5. Is this conversational? → Route to chat handler
    """
    
    def __init__(self):
        self._state = BrainState.IDLE
        self._active_chains: Dict[str, ManagedChain] = {}
        self._completed_chains: Dict[str, ManagedChain] = {}
        self._lock = threading.Lock()
        
        # Chain manager (lazy loaded)
        self._chain_manager = None
        self._context_manager = None
        
        # Callbacks for real-time updates
        self._status_callbacks: List = []
        
        logger.info("🧠 Executive Brain initialized")
    
    @property
    def state(self) -> BrainState:
        return self._state
    
    @property
    def active_chain_count(self) -> int:
        return len(self._active_chains)
    
    def _get_chain_manager(self):
        """Lazy-load ChainOfActionsManager"""
        if self._chain_manager is None:
            try:
                from ai_assistant.core.chain_of_actions_manager import ChainOfActionsManager
                self._chain_manager = ChainOfActionsManager()
            except ImportError:
                logger.error("ChainOfActionsManager not available")
        return self._chain_manager
    
    def _get_context_manager(self):
        """Lazy-load ContextManager"""
        if self._context_manager is None:
            try:
                from ai_assistant.core.conversation_context import get_context_manager
                self._context_manager = get_context_manager()
            except ImportError:
                logger.error("ContextManager not available")
        return self._context_manager
    
    # ===== MAIN ENTRY POINT =====
    
    def receive_command(self, command: str, source: str = 'chat') -> BrainResponse:
        """
        Single entry point for ALL commands from ALL sources.
        
        Args:
            command: The user's command text
            source: Where the command came from ('voice', 'chat', 'api', 'websocket')
            
        Returns:
            BrainResponse describing what action was taken
        """
        source_enum = CommandSource(source) if source in [s.value for s in CommandSource] else CommandSource.CHAT
        priority = CommandPriority.VOICE if source_enum == CommandSource.VOICE else CommandPriority.CHAT
        
        ts_command = TimestampedCommand(
            text=command,
            timestamp=time.time(),
            source=source_enum,
            priority=priority
        )
        
        logger.info(f"🧠 Brain received: '{command}' from {source} (priority: {priority.name})")
        
        # Background memory extraction (Commitments & Graph)
        def _background_extraction(cmd_text):
            try:
                from ai_assistant.core.commitment_tracker import CommitmentTracker
                tracker = CommitmentTracker()
                tracker.extract_and_store(cmd_text)
            except Exception as e:
                logger.error(f"Background extraction failed: {e}")
        
        # Only extract from chat/voice, not API calls unless they are explicit commands
        if source_enum in [CommandSource.VOICE, CommandSource.CHAT]:
            threading.Thread(target=_background_extraction, args=(command,), daemon=True).start()
        
        # Step 1: Classify the command
        classification = self._classify_command(command)
        ts_command.classification = classification
        logger.info(f"   Classification: {classification.value}")
        
        # Step 2: Route based on classification
        if classification in [
            CommandClassification.EXECUTIVE_STOP,
            CommandClassification.EXECUTIVE_PAUSE,
            CommandClassification.EXECUTIVE_RESUME,
        ]:
            return self._handle_executive(classification, command)
        
        if classification == CommandClassification.TASK_MODIFY:
            return self._handle_modification(command, ts_command)
        
        if classification == CommandClassification.CONVERSATIONAL:
            return BrainResponse(
                action_taken='chatting',
                message='Routing to chat handler',
                active_chains=list(self._active_chains.keys())
            )
        
        # Step 3: For TASK_NEW / TASK_RELATED — check relatedness to active chains
        if classification in [CommandClassification.TASK_NEW, CommandClassification.TASK_RELATED]:
            return self._handle_task(command, ts_command)
        
        # Fallback
        return BrainResponse(
            action_taken='chatting',
            message='Could not determine intent, routing to chat',
            active_chains=list(self._active_chains.keys())
        )
    
    # ===== CLASSIFICATION =====
    
    def _classify_command(self, command: str) -> CommandClassification:
        """
        Classify a command using the unified IntentRouter.
        """
        from ai_assistant.ai.intent_router import IntentRouter
        router = IntentRouter() # Singleton
        
        # We need to map our semantic IntentResult to CommandClassification
        intent_result = router.route(command)
        
        # 1. Check for specific Modification/Sequential keywords first since they apply to active chains
        cmd_lower = command.lower().strip()
        for keyword in MODIFICATION_KEYWORDS:
            if cmd_lower.startswith(keyword) or keyword in cmd_lower[:30]:
                return CommandClassification.TASK_MODIFY
                
        for keyword in SEQUENTIAL_KEYWORDS:
            if cmd_lower.startswith(keyword) or f' {keyword} ' in f' {cmd_lower} ':
                return CommandClassification.TASK_RELATED

        # 2. Map IntentRouter outputs
        if intent_result:
            intent_name = intent_result.intent_name
            # Executive intents might be mapped directly if we passed 'action' in parameters
            if intent_result.tier == 1 and intent_result.parameters.get("action") == "stop":
                return CommandClassification.EXECUTIVE_STOP
            elif intent_result.tier == 1 and intent_result.parameters.get("action") == "pause":
                return CommandClassification.EXECUTIVE_PAUSE
            elif intent_result.tier == 1 and intent_result.parameters.get("action") == "resume":
                return CommandClassification.EXECUTIVE_RESUME
            
            # Info queries and conversational fall back to CONVERSATIONAL in the command brain
            if intent_name == "info_query" or intent_name == "conversational":
                return CommandClassification.CONVERSATIONAL
                
            # If it's a known system intent, treat it as a new task
            system_intents = [
                'open_app', 'close_app', 'search_web', 'play_media', 'volume_control',
                'system_control', 'battery_status', 'list_running_apps', 'bluetooth_toggle',
                'create_document', 'create_folder', 'open_settings', 'analyze_screen',
                'download_media', 'task_automation', 'file_operation'
            ]
            if intent_name in system_intents:
                return CommandClassification.TASK_NEW
                
        # 3. Default fallback
        # If router returned None, it means it's pure conversation
        return CommandClassification.CONVERSATIONAL
    
    # ===== EXECUTIVE HANDLERS =====
    
    def _handle_executive(self, classification: CommandClassification, 
                          command: str) -> BrainResponse:
        """Handle executive commands (stop/pause/resume)"""
        
        if classification == CommandClassification.EXECUTIVE_STOP:
            return self._cancel_all_active(command)
        
        elif classification == CommandClassification.EXECUTIVE_PAUSE:
            return self._pause_all_active()
        
        elif classification == CommandClassification.EXECUTIVE_RESUME:
            return self._resume_all_active()
        
        return BrainResponse(action_taken='error', message='Unknown executive command', success=False)
    
    def _cancel_all_active(self, reason: str = '') -> BrainResponse:
        """Cancel all active chains"""
        with self._lock:
            cancelled_ids = []
            for chain_id, managed in list(self._active_chains.items()):
                managed.cancel()
                cancelled_ids.append(chain_id)
                self._completed_chains[chain_id] = managed
            
            for cid in cancelled_ids:
                self._active_chains.pop(cid, None)
            
            self._state = BrainState.IDLE
        
        # Also cancel via context manager
        ctx = self._get_context_manager()
        if ctx:
            try:
                from ai_assistant.core.conversation_context import ExecutionState
                ctx.clear_task_chain()
                ctx.set_state(ExecutionState.IDLE)
            except Exception:
                pass
        
        count = len(cancelled_ids)
        logger.info(f"🛑 Cancelled {count} active chain(s): {cancelled_ids}")
        
        return BrainResponse(
            action_taken='cancelled',
            message=f"Cancelled {count} active task(s)." if count else "Nothing was running.",
            active_chains=[]
        )
    
    def _pause_all_active(self) -> BrainResponse:
        """Pause all active chains"""
        self._state = BrainState.PAUSED
        
        ctx = self._get_context_manager()
        if ctx:
            try:
                from ai_assistant.core.conversation_context import ExecutionState
                ctx.set_state(ExecutionState.PAUSED)
            except Exception:
                pass
        
        logger.info("⏸️ All chains paused")
        return BrainResponse(
            action_taken='paused',
            message='Execution paused.',
            active_chains=list(self._active_chains.keys())
        )
    
    def _resume_all_active(self) -> BrainResponse:
        """Resume paused chains"""
        self._state = BrainState.EXECUTING
        
        ctx = self._get_context_manager()
        if ctx:
            try:
                from ai_assistant.core.conversation_context import ExecutionState
                ctx.set_state(ExecutionState.EXECUTING)
            except Exception:
                pass
        
        logger.info("▶️ Execution resumed")
        return BrainResponse(
            action_taken='resumed',
            message='Execution resumed.',
            active_chains=list(self._active_chains.keys())
        )
    
    # ===== TASK HANDLING =====
    
    def _handle_task(self, command: str, ts_cmd: TimestampedCommand) -> BrainResponse:
        """Handle a task command — decide merge vs parallel"""
        
        # Check if related to any active chain
        related_chain_id = self._find_related_chain(command)
        
        if related_chain_id:
            # Merge/append to the related chain
            logger.info(f"   🔗 Related to chain {related_chain_id} — merging")
            return self._append_to_chain(related_chain_id, command, ts_cmd)
        else:
            # Independent — start new parallel chain
            logger.info(f"   🆕 Independent command — starting new chain")
            return self._start_new_chain(command, ts_cmd)
    
    def _find_related_chain(self, command: str) -> Optional[str]:
        """
        Determine if a command is related to any active chain using intent analysis.
        
        Rules (checked in order):
        1. Sequential keywords ("then", "phir") → always related to most recent chain
        2. Same app context → related
        3. Implied context (no explicit app, but active chain has one) → related
        4. Different explicit app → NOT related (parallel)
        5. Conversational → NOT related
        """
        if not self._active_chains:
            return None
        
        cmd_lower = command.lower()
        
        # Rule 1: Sequential keywords → always related to latest chain
        for keyword in SEQUENTIAL_KEYWORDS:
            if keyword in cmd_lower:
                # Find most recent chain
                latest = max(self._active_chains.values(), key=lambda c: c.created_at)
                return latest.chain_id
        
        # Extract app from command
        command_app = self._extract_app_name(cmd_lower)
        command_has_context_action = any(intent in cmd_lower for intent in CONTEXT_DEPENDENT_INTENTS)
        
        for chain_id, managed in self._active_chains.items():
            chain_app = managed.app_context
            
            if not chain_app:
                continue
            
            # Rule 2: Same app → related
            if command_app and command_app == chain_app:
                return chain_id
            
            # Rule 2b: Both are browsers → related (e.g., active=chrome, cmd="go to YouTube")
            if chain_app in BROWSER_APPS and command_app in BROWSER_APPS:
                return chain_id
            
            # Rule 2c: Browser action + URL/website → related to browser chain
            if chain_app in BROWSER_APPS and self._is_web_action(cmd_lower):
                return chain_id
            
            # Rule 3: No explicit app in command + context-dependent action → related
            if not command_app and command_has_context_action:
                return chain_id
        
        # Rule 4: Different app or no match → not related
        return None
    
    def _extract_app_name(self, cmd_lower: str) -> Optional[str]:
        """Extract app name from a command string"""
        # Check for known app names
        for app in KNOWN_APPS:
            if app in cmd_lower:
                return app
        
        # Check for "open X" pattern
        open_patterns = [
            r'open\s+(\w+)',
            r'launch\s+(\w+)',
            r'start\s+(\w+)',
            r'(\w+)\s+kholo',
            r'(\w+)\s+open\s+karo',
        ]
        
        for pattern in open_patterns:
            match = re.search(pattern, cmd_lower)
            if match:
                app = match.group(1).lower()
                if app not in ['the', 'a', 'an', 'my', 'this', 'that', 'it']:
                    return app
        
        return None
    
    def _is_web_action(self, cmd_lower: str) -> bool:
        """Check if command implies a web/browser action"""
        web_indicators = [
            'search', 'google', 'youtube', 'website', 'url',
            'browse', 'navigate', 'go to', 'visit',
            '.com', '.org', '.net', 'http', 'www',
        ]
        return any(indicator in cmd_lower for indicator in web_indicators)
    
    def _append_to_chain(self, chain_id: str, command: str,
                         ts_cmd: TimestampedCommand) -> BrainResponse:
        """Append a related command to an existing chain"""
        managed = self._active_chains.get(chain_id)
        if not managed:
            return self._start_new_chain(command, ts_cmd)
        
        # The chain manager handles appending actions to a running chain
        manager = self._get_chain_manager()
        if manager and chain_id in manager.active_chains:
            try:
                import asyncio
                chain = manager.active_chains[chain_id]
                
                # Decompose the new command and add actions to existing chain
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Create a temp chain just for decomposition
                temp_chain = loop.run_until_complete(manager.create_chain(command))
                new_actions = loop.run_until_complete(manager.decompose_command(temp_chain))
                
                # Add actions to the active chain
                chain.actions.extend(new_actions)
                
                # Clean up temp
                manager.active_chains.pop(temp_chain.id, None)
                loop.close()
                
                logger.info(f"   ➕ Added {len(new_actions)} actions to chain {chain_id}")
                
                return BrainResponse(
                    action_taken='merged',
                    message=f"Added to running task: {command}",
                    chain_id=chain_id,
                    active_chains=list(self._active_chains.keys())
                )
            except Exception as e:
                logger.error(f"Failed to append to chain: {e}")
                # Fallback: start new chain
                return self._start_new_chain(command, ts_cmd)
        
        return self._start_new_chain(command, ts_cmd)
    
    def _start_new_chain(self, command: str, 
                         ts_cmd: TimestampedCommand) -> BrainResponse:
        """Start a new independent chain"""
        import asyncio
        
        self._state = BrainState.EXECUTING
        
        manager = self._get_chain_manager()
        if not manager:
            return BrainResponse(
                action_taken='error',
                message='Chain manager not available',
                success=False
            )
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            chain = loop.run_until_complete(manager.create_chain(command))
            loop.close()
        except Exception as e:
            logger.error(f"Failed to create chain: {e}")
            return BrainResponse(
                action_taken='error',
                message=f'Failed to create chain: {e}',
                success=False
            )
        
        # Extract app context for relatedness tracking
        app_context = self._extract_app_name(command.lower())
        
        # Create managed chain with cancellation support
        cancel_event = threading.Event()
        managed = ManagedChain(
            chain_id=chain.id,
            command=command,
            cancel_event=cancel_event,
            source=ts_cmd.source,
            created_at=time.time(),
            app_context=app_context
        )
        
        # Start execution in background thread
        def run_chain_bg():
            try:
                import asyncio as _asyncio
                new_loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(new_loop)
                
                async def _execute():
                    await manager.decompose_command(chain)
                    await manager.identify_executors(chain)
                    report = await manager.execute_chain(chain.id)
                    await manager.notify_completion(report)
                    return report
                
                new_loop.run_until_complete(_execute())
                new_loop.close()
                
            except Exception as e:
                logger.error(f"Chain execution error: {e}")
            finally:
                # Move from active to completed
                with self._lock:
                    self._completed_chains[chain.id] = self._active_chains.pop(chain.id, managed)
                    if not self._active_chains:
                        self._state = BrainState.IDLE
        
        thread = threading.Thread(target=run_chain_bg, name=f"brain-chain-{chain.id}", daemon=True)
        managed.thread = thread
        
        with self._lock:
            self._active_chains[chain.id] = managed
        
        thread.start()
        
        action = 'parallel' if len(self._active_chains) > 1 else 'executing'
        logger.info(f"🚀 Started chain {chain.id} ({action}): {command}")
        
        return BrainResponse(
            action_taken=action,
            message=f"Started: {command}",
            chain_id=chain.id,
            active_chains=list(self._active_chains.keys())
        )
    
    def _handle_modification(self, command: str, 
                             ts_cmd: TimestampedCommand) -> BrainResponse:
        """Handle command modifications ("no wait, use Firefox instead")"""
        if not self._active_chains:
            # Nothing to modify, treat as new task
            # Strip modification keywords
            clean_cmd = command
            for keyword in MODIFICATION_KEYWORDS:
                clean_cmd = clean_cmd.replace(keyword, '').strip()
            if clean_cmd:
                return self._start_new_chain(clean_cmd, ts_cmd)
            return BrainResponse(
                action_taken='error',
                message='Nothing to modify',
                success=False
            )
        
        # Cancel the most recent chain and start the modified version
        latest = max(self._active_chains.values(), key=lambda c: c.created_at)
        latest.cancel()
        
        with self._lock:
            self._completed_chains[latest.chain_id] = self._active_chains.pop(latest.chain_id)
        
        # Extract the actual command from the modification
        clean_cmd = command
        for keyword in MODIFICATION_KEYWORDS:
            clean_cmd = clean_cmd.replace(keyword, '').strip()
        
        if clean_cmd:
            logger.info(f"✏️ Modified: cancelled '{latest.command}', starting '{clean_cmd}'")
            return self._start_new_chain(clean_cmd, ts_cmd)
        
        return BrainResponse(
            action_taken='cancelled',
            message=f"Cancelled: {latest.command}",
            active_chains=list(self._active_chains.keys())
        )
    
    # ===== STATUS & MONITORING =====
    
    def get_status(self) -> Dict[str, Any]:
        """Get current brain status"""
        return {
            'state': self._state.value,
            'active_chains': [m.to_dict() for m in self._active_chains.values()],
            'completed_count': len(self._completed_chains),
            'total_active': len(self._active_chains),
        }
    
    def cancel_chain(self, chain_id: str) -> bool:
        """Cancel a specific chain by ID"""
        with self._lock:
            managed = self._active_chains.get(chain_id)
            if managed:
                managed.cancel()
                self._completed_chains[chain_id] = self._active_chains.pop(chain_id)
                if not self._active_chains:
                    self._state = BrainState.IDLE
                logger.info(f"🛑 Cancelled chain {chain_id}")
                return True
        return False
    
    def is_busy(self) -> bool:
        """Check if any chains are currently active"""
        return len(self._active_chains) > 0
    
    def get_active_chain_ids(self) -> List[str]:
        """Get IDs of all active chains"""
        return list(self._active_chains.keys())
    
    def on_status_change(self, callback):
        """Register a callback for brain status changes"""
        self._status_callbacks.append(callback)
    
    def _notify_status(self):
        """Notify all registered callbacks of status change"""
        status = self.get_status()
        for cb in self._status_callbacks:
            try:
                cb(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")


# ===== Singleton =====

_brain: Optional[ExecutiveBrain] = None
_brain_lock = threading.Lock()

def get_executive_brain() -> ExecutiveBrain:
    """Get singleton ExecutiveBrain instance"""
    global _brain
    if _brain is None:
        with _brain_lock:
            if _brain is None:
                _brain = ExecutiveBrain()
    return _brain
