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
        # Auto-start global emergency stop hotkey listener
        try:
            from ai_assistant.core.emergency_stop import start_emergency_stop_listener
            start_emergency_stop_listener()
        except Exception as _es_err:
            logger.debug(f"Could not auto-start emergency stop listener: {_es_err}")
    
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
    
    def receive_command(
        self,
        command: str,
        source: str = 'chat',
        turn_id: Optional[int] = None,
        speak: bool = True,
        provider_preference: Optional[str] = None,
        offline_mode: Optional[bool] = None,
    ) -> BrainResponse:
        """
        Single entry point for ALL commands from ALL sources.

        Args:
            command: The user's command text
            source: Where the command came from ('voice', 'chat', 'api', 'websocket')
            turn_id: Optional lifecycle turn token for pre/post report coordination
            speak: Whether unified TTS is enabled for this turn
            provider_preference: Optional per-request provider override
            offline_mode: Optional per-request offline flag

        Returns:
            BrainResponse describing what action was taken
        """
        self._active_turn_id = turn_id
        self._active_turn_speak = bool(speak)
        self._request_provider_override = provider_preference
        self._request_offline_override = offline_mode

        if source in ('voice', 'companion', 'whisper', 'webui_voice'):
            try:
                from ai_assistant.core.speech_text_crisper import crisp_speech_transcript
                crisped_cmd = crisp_speech_transcript(command)
                if crisped_cmd:
                    command = crisped_cmd
            except Exception:
                pass

        source_enum = CommandSource(source) if source in [s.value for s in CommandSource] else CommandSource.CHAT
        priority = CommandPriority.VOICE if source_enum == CommandSource.VOICE else CommandPriority.CHAT
        
        ts_command = TimestampedCommand(
            text=command,
            timestamp=time.time(),
            source=source_enum,
            priority=priority
        )
        
        logger.info(f"🧠 Brain received: '{command}' from {source} (priority: {priority.name})")

        # Step 0: Check Executive Stop / Pause / Resume first!
        cmd_strip = command.strip().lower()
        # Check Pending Task Chain Recovery (Zero LLM calls, deterministic recovery)
        try:
            from ai_assistant.core.task_chain_orchestrator import get_chain_recovery_manager
            recovery_mgr = get_chain_recovery_manager()
            if recovery_mgr.has_pending_recovery():
                if recovery_mgr.is_affirmative(command):
                    rec_result = recovery_mgr.execute_recovery()
                    rec_ok = bool(rec_result.get("success", False))
                    rec_msg = rec_result.get("response", "")
                    logger.info(f"🧠 [RECOVERY] Executed pending chain recovery: success={rec_ok}")
                    return BrainResponse(
                        action_taken='completed',
                        message=rec_msg,
                        success=rec_ok,
                        active_chains=list(self._active_chains.keys()),
                    )
                elif recovery_mgr.is_negative(command):
                    recovery_mgr.clear()
                    logger.info("🧠 [RECOVERY] User rejected pending recovery. Cleared state.")
                    return BrainResponse(
                        action_taken='completed',
                        message="ठीक है, वैकल्पिक टास्क रद्द कर दिया गया है।",
                        success=True,
                        active_chains=list(self._active_chains.keys()),
                    )
        except Exception as rec_err:
            logger.debug(f"Recovery check skipped in ExecutiveBrain: {rec_err}")

        media_indicators = {
            "song", "songs", "music", "playback", "audio", "video", "videos",
            "track", "tracks", "gaana", "gana", "player", "spotify", "youtube"
        }
        has_media_target = any(re.search(rf'\b{w}\b', cmd_strip) for w in media_indicators)

        if not has_media_target:
            if (
                cmd_strip in ("stop", "emergency stop", "halt", "cancel chain", "abort", "halt all actions")
                or any(kw == cmd_strip or cmd_strip.startswith(f"{kw} ") for kw in EXECUTIVE_STOP_KEYWORDS)
            ):
                res = self._cancel_all_active(command)
                res.action_taken = 'stop'
                return res

            if (
                cmd_strip in ("pause", "pause chain", "hold on", "pause all")
                or any(kw == cmd_strip or cmd_strip.startswith(f"{kw} ") for kw in EXECUTIVE_PAUSE_KEYWORDS)
            ):
                if self._active_chains:
                    res = self._pause_all_active()
                    res.action_taken = 'pause'
                    return res

            if (
                cmd_strip in ("resume", "resume chain", "continue chain", "resume all")
                or any(kw == cmd_strip or cmd_strip.startswith(f"{kw} ") for kw in EXECUTIVE_RESUME_KEYWORDS)
            ):
                if self._active_chains:
                    res = self._resume_all_active()
                    res.action_taken = 'resume'
                    return res

        # Fast Voice / Mode Control interception (Zero LLM calls)
        try:
            from ai_assistant.core.local_command_normalizer import (
                parse_voice_control_command,
                execute_voice_control_command,
            )
            vc_parsed = parse_voice_control_command(command)
            if vc_parsed:
                vc_res = execute_voice_control_command(vc_parsed)
                return BrainResponse(
                    action_taken='completed',
                    message=vc_res.get('response', ''),
                    success=bool(vc_res.get('success', True)),
                    active_chains=list(self._active_chains.keys()),
                )
        except Exception as vc_err:
            logger.debug(f"Voice control check skipped in ExecutiveBrain: {vc_err}")

        # Background memory extraction (Commitments & Graph)
        def _background_extraction(cmd_text):
            commitment_keywords = ["remind", "promise", "deadline", "by tomorrow", "schedule", "task", "meeting", "submit", "deliver", "kal", "parso", "yaad", "bhul mat"]
            if any(kw in cmd_text.lower() for kw in commitment_keywords):
                try:
                    from ai_assistant.core.commitment_tracker import CommitmentTracker
                    tracker = CommitmentTracker()
                    tracker.extract_and_store(cmd_text)
                except Exception as e:
                    logger.error(f"Background extraction failed: {e}")

        # Only extract from chat/voice, not API calls unless they are explicit commands
        if source_enum in [CommandSource.VOICE, CommandSource.CHAT]:
            threading.Thread(target=_background_extraction, args=(command,), daemon=True).start()

        # Bare contextual follow-up resolution (e.g., "off कर दो" right after "Bluetooth on कर दो")
        if not self._active_chains:
            try:
                from ai_assistant.core.local_command_normalizer import resolve_contextual_toggle_command
                resolved_toggle = resolve_contextual_toggle_command(command, self._get_context_manager())
                if resolved_toggle:
                    t_intent, t_params = resolved_toggle
                    enable = bool(t_params.get('enable', False))
                    state_word = 'on' if enable else 'off'
                    if t_intent == 'wifi_toggle':
                        command = f"turn {state_word} wifi"
                    elif t_intent == 'bluetooth_toggle':
                        command = f"turn {state_word} bluetooth"
                    elif t_intent == 'dark_mode_toggle':
                        command = "dark mode on" if enable else "dark mode off"
                    ts_command.text = command
                    logger.info(f"🧠 Resolved contextual bare toggle to: '{command}'")
            except Exception as ctx_err:
                logger.debug(f"Contextual toggle resolution skipped: {ctx_err}")

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
        from ai_assistant.core.local_command_normalizer import (
            word_boundary_contains,
            contains_any_sequential_keyword,
        )

        router = IntentRouter() # Singleton

        # We need to map our semantic IntentResult to CommandClassification
        intent_result = router.route(
            command,
            provider_override=getattr(self, '_request_provider_override', None),
            offline_mode=getattr(self, '_request_offline_override', None),
        )
        self._last_routed_intent = intent_result

        # 1. Whole-token checks for Modification / Sequential keywords
        cmd_lower = command.lower().strip()
        head_snippet = " ".join(cmd_lower.split()[:5])
        if self._active_chains or intent_result is None:
            for keyword in MODIFICATION_KEYWORDS:
                if word_boundary_contains(head_snippet, keyword):
                    return CommandClassification.TASK_MODIFY

        if self._active_chains and contains_any_sequential_keyword(command, SEQUENTIAL_KEYWORDS):
            return CommandClassification.TASK_RELATED

        # 2. Map IntentRouter outputs
        if intent_result:
            intent_name = intent_result.intent_name
            # Executive intents apply only to non-media/system commands
            non_executive_intents = {
                'media_control', 'play_media', 'play_video', 'volume_control',
                'system_control', 'wifi_toggle', 'bluetooth_toggle', 'dark_mode_toggle',
            }
            if intent_name not in non_executive_intents:
                if intent_result.tier == 1 and intent_result.parameters.get("action") == "stop":
                    return CommandClassification.EXECUTIVE_STOP
                elif intent_result.tier == 1 and intent_result.parameters.get("action") == "pause":
                    if self._active_chains:
                        return CommandClassification.EXECUTIVE_PAUSE
                    return CommandClassification.TASK_NEW
                elif intent_result.tier == 1 and intent_result.parameters.get("action") == "resume":
                    if self._active_chains:
                        return CommandClassification.EXECUTIVE_RESUME
                    return CommandClassification.TASK_NEW

            # Info queries and conversational fall back to CONVERSATIONAL in the command brain
            if intent_name == "info_query" or intent_name == "conversational":
                return CommandClassification.CONVERSATIONAL

            # If it's a known system intent, treat it as a new task
            system_intents = [
                'open_app', 'close_app', 'search_web', 'youtube_search', 'youtube_history',
                'play_media', 'play_video', 'media_control', 'send_message', 'volume_control',
                'set_brightness', 'brightness_control', 'dark_mode_toggle',
                'system_control', 'battery_status', 'list_running_apps', 'check_taskbar',
                'bluetooth_toggle', 'wifi_toggle', 'create_document', 'create_folder',
                'find_file', 'open_folder', 'open_explorer', 'skip_time',
                'open_settings', 'analyze_screen', 'download_media', 'task_automation',
                'file_operation', 'switch_model', 'settings_control',
            ]
            if intent_name in system_intents:
                return CommandClassification.TASK_NEW

        # 3. Default fallback
        # If router returned None, it means it's pure conversation
        return CommandClassification.CONVERSATIONAL
    
    # ===== EXECUTIVE HANDLERS =====

    @classmethod
    def handle_executive(cls, classification: CommandClassification = CommandClassification.EXECUTIVE_STOP,
                         command: str = 'stop', emit_notice: bool = True) -> BrainResponse:
        """
        Universal class and instance entry point for executive commands.
        Can be invoked directly:
            CommandBrain.handle_executive(CommandClassification.EXECUTIVE_STOP)
            get_executive_brain().handle_executive(CommandClassification.EXECUTIVE_STOP)
        """
        brain = get_executive_brain()
        return brain._handle_executive(classification, command, emit_notice=emit_notice)

    def _handle_executive(self, classification: CommandClassification, 
                          command: str, emit_notice: bool = True) -> BrainResponse:
        """Handle executive commands (stop/pause/resume)"""
        
        if classification == CommandClassification.EXECUTIVE_STOP:
            return self._cancel_all_active(command, emit_notice=emit_notice)
        
        elif classification == CommandClassification.EXECUTIVE_PAUSE:
            return self._pause_all_active()
        
        elif classification == CommandClassification.EXECUTIVE_RESUME:
            return self._resume_all_active()
        
        return BrainResponse(action_taken='error', message='Unknown executive command', success=False)
    
    def _cancel_all_active(self, reason: str = '', emit_notice: bool = True) -> BrainResponse:
        """Cancel all active chains, halt TaskChainOrchestrator, and release inputs"""
        with self._lock:
            cancelled_ids = []
            for chain_id, managed in list(self._active_chains.items()):
                managed.cancel()
                cancelled_ids.append(chain_id)
                self._completed_chains[chain_id] = managed
            
            for cid in cancelled_ids:
                self._active_chains.pop(cid, None)
            
            self._state = BrainState.IDLE
        
        # 1. Halt TaskChainOrchestrator immediately
        try:
            from ai_assistant.core.task_chain_orchestrator import get_orchestrator
            get_orchestrator().emergency_stop(reason=reason or "Executive Stop triggered")
        except Exception as orch_e:
            logger.warning(f"Orchestrator emergency stop warning: {orch_e}")

        # 2. Forcibly release OS inputs (mouse and modifier keys)
        try:
            from ai_assistant.core.emergency_stop import release_system_inputs
            release_system_inputs()
        except Exception:
            pass

        # 3. Clear context manager state & pending recovery
        try:
            from ai_assistant.core.task_chain_orchestrator import get_chain_recovery_manager
            get_chain_recovery_manager().clear()
        except Exception:
            pass

        ctx = self._get_context_manager()
        if ctx:
            try:
                from ai_assistant.core.conversation_context import ExecutionState
                ctx.clear_task_chain()
                ctx.set_state(ExecutionState.IDLE)
            except Exception:
                pass

        # 4. Cancel active lifecycle turns & optionally broadcast stop signal via Socket.IO
        try:
            from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
            get_lifecycle_coordinator().cancel_all(reason=reason or 'executive_stop')
        except Exception:
            pass
        if emit_notice:
            try:
                import sys
                from datetime import datetime
                if 'voice_service' in sys.modules or 'backend.voice_service' in sys.modules:
                    try:
                        from voice_service import safe_emit
                    except ImportError:
                        from backend.voice_service import safe_emit
                    safe_emit('emergency_stop', {'reason': reason or 'Emergency Stop', 'timestamp': datetime.now().isoformat()})
                    safe_emit('command_response', {
                        'success': False,
                        'response': f"🛑 Stop command executed: Live tasks halted immediately. {reason}".strip(),
                        'command': 'stop',
                        'source': 'executive_stop',
                        'timestamp': datetime.now().isoformat(),
                        'skip_tts': True
                    })
            except Exception as emit_e:
                logger.debug(f"Emit stop notice: {emit_e}")
        
        count = len(cancelled_ids)
        logger.info(f"🛑 Cancelled {count} active chain(s): {cancelled_ids}")
        
        return BrainResponse(
            action_taken='cancelled',
            message=f"Cancelled {count} active task(s)." if count else "Emergency stop executed. All active tasks halted.",
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

        # Rule 1: Whole-word sequential keywords → always related to latest chain
        from ai_assistant.core.local_command_normalizer import contains_any_sequential_keyword
        if contains_any_sequential_keyword(command, SEQUENTIAL_KEYWORDS):
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
    
    def _get_agent_coordinator(self):
        if not hasattr(self, '_coordinator'):
            from ai_assistant.core.multi_agent_coordinator import MultiAgentCoordinator
            from ai_assistant.agents.registry import AgentRegistry
            from ai_assistant.agents.loader import AgentLoader
            
            registry = AgentRegistry()
            AgentLoader.register_agent_definitions(registry)
            self._coordinator = MultiAgentCoordinator(registry)
        return self._coordinator

    def _start_new_chain(self, command: str, ts_cmd: TimestampedCommand) -> BrainResponse:
        import threading
        chain_id = f"chain_{int(time.time() * 1000)}_{len(self._completed_chains) + len(self._active_chains) + 1}"
        managed = ManagedChain(
            chain_id=chain_id,
            command=command,
            source=ts_cmd.source,
            created_at=time.time(),
        )
        with self._lock:
            self._active_chains[chain_id] = managed
            self._state = BrainState.EXECUTING

        src_str = ts_cmd.source.value if hasattr(ts_cmd.source, 'value') else str(ts_cmd.source or 'chat')
        turn_id = getattr(self, '_active_turn_id', None)
        speak_flag = getattr(self, '_active_turn_speak', True)

        coordinator = None
        pre_msg = None
        try:
            from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator, should_speak_for_request
            coordinator = get_lifecycle_coordinator()
            if turn_id is None:
                speak_flag = should_speak_for_request({'source': src_str}, default_for_chat=speak_flag)
                turn_id = coordinator.begin_turn(command=command, source=src_str, speak=speak_flag)
            else:
                speak_flag = bool(speak_flag) and should_speak_for_request({'source': src_str}, force=speak_flag)
            routed = getattr(ts_command, 'intent_result', None) or getattr(self, '_last_routed_intent', None)
            real_intent = routed.intent_name if routed else 'task_chain_orchestrator'
            real_target = str(routed.parameters.get('target') or routed.parameters.get('query') or '') if routed and routed.parameters else ''
            pre_msg = coordinator.emit_pre_report(
                turn_id,
                command,
                intent=real_intent,
                target=real_target,
                source=src_str,
                speak=speak_flag,
            )
        except Exception as lc_err:
            logger.debug(f"Pre-report hook skipped in ExecutiveBrain: {lc_err}")

        def run_execution():
            import sys
            from datetime import datetime

            success = False
            response_msg = ""

            try:
                if managed.is_cancelled:
                    return
                if coordinator is not None and turn_id is not None and not coordinator.is_turn_active(turn_id):
                    return
                # 1. Primary execution engine: TaskChainOrchestrator
                from ai_assistant.core.task_chain_orchestrator import get_orchestrator
                orchestrator = get_orchestrator()
                res = orchestrator.execute_command(command, skip_override_check=True)

                success = bool(res.success)
                details = []
                for r in res.results:
                    if isinstance(r, dict):
                        res_val = r.get('result')
                        if isinstance(res_val, dict) and res_val.get('message'):
                            details.append(str(res_val['message']))
                        elif isinstance(res_val, str) and res_val.strip():
                            details.append(res_val.strip())
                if success:
                    response_msg = " | ".join(details) if details else (res.message or "Command executed successfully")
                else:
                    response_msg = res.error or res.message or (" | ".join(details) if details else "Command execution failed")
            except Exception as orch_e:
                logger.error(f"TaskChainOrchestrator error: {orch_e}")
                response_msg = f"Execution error: {orch_e}"
            finally:
                with self._lock:
                    popped = self._active_chains.pop(chain_id, None)
                    if popped:
                        self._completed_chains[chain_id] = popped
                    if not self._active_chains and self._state == BrainState.EXECUTING:
                        self._state = BrainState.IDLE

            if managed.is_cancelled:
                return

            if coordinator is not None:
                try:
                    formatted_msg, was_active = coordinator.complete_turn(
                        turn_id,
                        command,
                        response_msg,
                        success=success,
                        intent=real_intent,
                        source=real_intent,
                        speak=speak_flag,
                        emit_response=False,
                    )
                    if not was_active:
                        return
                    final_text = formatted_msg or response_msg
                    ai_msg_id = None
                    sess_id = None
                    boot_id = None
                    try:
                        try:
                            from utils.chat_session_store import get_session_store
                        except ImportError:
                            from backend.utils.chat_session_store import get_session_store
                        store = get_session_store()
                        ai_msg_id = store.next_message_id('chain_ai')
                        sess_id = store.get_current_session().get('id')
                        boot_id = store.get_boot_id()
                        store.record_message(
                            'ai',
                            final_text,
                            source='task_chain_orchestrator',
                            is_voice=False,
                            message_id=ai_msg_id,
                            intent='task_chain_orchestrator',
                            success=success,
                            activity_kind=('action' if success else 'error'),
                            activity_title=('Action completed' if success else 'Action failed'),
                            expected_session_id=sess_id,
                        )
                    except Exception:
                        pass

                    sio = coordinator._get_socketio()
                    if sio is not None:
                        try:
                            sio.emit('command_response', {
                                'success': bool(success),
                                'response': final_text,
                                'command': command,
                                'source': 'task_chain_orchestrator',
                                'chain_id': chain_id,
                                'message_id': ai_msg_id,
                                'session_id': sess_id,
                                'boot_id': boot_id,
                                'skip_tts': True,
                                'timestamp': datetime.now().isoformat(),
                            })
                        except Exception:
                            pass
                    return
                except Exception as comp_err:
                    logger.debug(f"Coordinator complete_turn fallback: {comp_err}")

            # Fallback if lifecycle coordinator unavailable
            ai_msg_id = None
            sess_id = None
            boot_id = None
            try:
                try:
                    from utils.chat_session_store import get_session_store
                except ImportError:
                    from backend.utils.chat_session_store import get_session_store
                store = get_session_store()
                ai_msg_id = store.next_message_id('chain_ai')
                sess_id = store.get_current_session().get('id')
                boot_id = store.get_boot_id()
                store.record_message(
                    'ai',
                    response_msg,
                    source='task_chain_orchestrator',
                    is_voice=False,
                    message_id=ai_msg_id,
                    intent='task_chain_orchestrator',
                    success=success,
                    activity_kind=('action' if success else 'error'),
                    activity_title=('Action completed' if success else 'Action failed'),
                    expected_session_id=sess_id,
                )
            except Exception:
                pass
            try:
                vs_mod = sys.modules.get('voice_service') or sys.modules.get('backend.voice_service')
                if vs_mod is not None:
                    update_ov = getattr(vs_mod, 'update_overlay_state', None)
                    sched_idle = getattr(vs_mod, '_schedule_overlay_idle', None)
                    safe_emit = getattr(vs_mod, 'safe_emit', None)

                    if callable(update_ov):
                        if not success:
                            snap = update_ov(state='error', error_message=response_msg, source='task_chain_orchestrator')
                            if callable(sched_idle):
                                sched_idle(3.5, snap['updated_at'])
                        else:
                            update_ov(state='idle', source='task_chain_orchestrator')

                    if callable(safe_emit):
                        safe_emit('command_response', {
                            'success': success,
                            'response': response_msg,
                            'command': command,
                            'chain_id': chain_id,
                            'source': 'task_chain_orchestrator',
                            'message_id': ai_msg_id,
                            'session_id': sess_id,
                            'boot_id': boot_id,
                            'timestamp': datetime.now().isoformat(),
                            'skip_tts': True,
                        })
            except Exception as emit_e:
                logger.error(f"Failed to emit execution result: {emit_e}")

        t = threading.Thread(target=run_execution, daemon=True)
        managed.thread = t
        t.start()

        return BrainResponse(
            action_taken='executing',
            message=pre_msg or f"Executing: {command}",
            chain_id=chain_id,
            active_chains=[chain_id],
            success=True,
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


# ===== Compatibility Alias =====
CommandBrain = ExecutiveBrain
