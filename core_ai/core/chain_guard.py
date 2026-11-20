"""
chain_guard.py - ownership-scoped chain runs with guaranteed terminal events.

Root cause of the frozen spinner: a GLOBAL execution state ("IDLE"/"PROCESSING") is written by whoever
finishes last (e.g. voice-turn cleanup), so it can flip to IDLE while a chain is still mid-way; the orchestrator
then sees "cancelled" and returns without ever emitting chain.completed / chain.failed.

Fix: (1) every run has an id and an owner, (2) cleanup may only cancel runs its own turn owns,
(3) UI state is DERIVED from live runs (never stored), (4) terminal events are emitted in `finally`.
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable


@dataclass
class ChainRun:
    owner: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    cancelled: threading.Event = field(default_factory=threading.Event)
    blackboard: dict = field(default_factory=dict)      # resolved entities shared between waves


class ChainRunRegistry:
    def __init__(self):
        self._runs: dict[str, ChainRun] = {}
        self._lock = threading.Lock()

    def start(self, owner: str, blackboard: dict | None = None) -> ChainRun:
        run = ChainRun(owner, blackboard=dict(blackboard or {}))
        with self._lock:
            self._runs[run.id] = run
        return run

    def finish(self, run_id: str) -> None:
        with self._lock:
            self._runs.pop(run_id, None)

    def cancel_owner(self, owner: str) -> int:
        """Voice/turn cleanup calls this with ITS OWN owner id - it can never touch another turn's chain."""
        with self._lock:
            mine = [r for r in self._runs.values() if r.owner == owner]
        for r in mine:
            r.cancelled.set()
        return len(mine)

    @property
    def state(self) -> str:                              # derived, never assigned
        with self._lock:
            return "processing" if self._runs else "idle"


async def run_chain(registry: ChainRunRegistry, owner: str, waves: list,
                    execute_wave: Callable[[object, ChainRun], Awaitable[None]],
                    emit: Callable[..., None], blackboard: dict | None = None,
                    wave_timeout: float = 180.0) -> str:
    """`blackboard` should be filled at PLAN time (e.g. {"chrome_profile": "Profile 1"} from memory),
    so step 2 never depends on what turn-level context survived."""
    run = registry.start(owner, blackboard)
    emit("chain.started", run_id=run.id)
    status, error, i = "completed", None, -1
    try:
        for i, wave in enumerate(waves):
            if run.cancelled.is_set():
                status, error = "cancelled", "cancelled by owner"
                break
            emit("chain.wave.started", run_id=run.id, wave=i)
            await asyncio.wait_for(execute_wave(wave, run), wave_timeout)
    except asyncio.TimeoutError:
        status, error = "failed", f"wave {i} timed out after {wave_timeout}s"
    except asyncio.CancelledError:
        status, error = "cancelled", "task cancelled"
        raise
    except Exception as e:                               # noqa: BLE001 - must always reach the finally
        status, error = "failed", repr(e)
    finally:
        registry.finish(run.id)
        try:
            emit("chain.completed" if status == "completed" else "chain.failed",
                 run_id=run.id, status=status, error=error)
            emit("state.changed", state=registry.state)
        except Exception:
            pass
    return status
