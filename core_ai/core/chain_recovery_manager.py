"""
Canonical re-export for ChainRecoveryManager from task_chain_orchestrator.
Maintains a single shared singleton instance across the entire application.
"""
from ai_assistant.core.task_chain_orchestrator import (
    ChainRecoveryManager,
    PendingRecovery,
    get_chain_recovery_manager,
)

__all__ = [
    "ChainRecoveryManager",
    "PendingRecovery",
    "get_chain_recovery_manager",
]
