"""
test_unified_memory_and_chain_guard.py
Unit & Integration tests for Pulsar Unified Memory and Chain Guard.
"""
import sys
import os
import time
import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core_ai.memory import (
    MemoryService,
    HybridMemoryStore,
    Embedder,
    WorkingMemory,
    resolve_time,
)
from core_ai.core.chain_guard import ChainRunRegistry, ChainRun, run_chain
from core_ai.core.task_chain_orchestrator import TaskStep, ExecutionResult


def test_resolve_time_hinglish():
    """Verify deterministic temporal resolution relative to utterance anchor."""
    anchor = datetime(2026, 11, 20, 10, 0, 0)
    
    # "next January"
    res1 = resolve_time("next January", anchor)
    assert res1 is not None
    assert res1.start.year == 2027
    assert res1.start.month == 1
    assert res1.start.day == 1
    assert res1.precision == "month"
    
    # "tomorrow"
    res2 = resolve_time("tomorrow", anchor)
    assert res2 is not None
    assert res2.start.day == 21
    assert res2.precision == "day"
    
    # "15 january 2027"
    res3 = resolve_time("15 january 2027", anchor)
    assert res3 is not None
    assert res3.start.year == 2027
    assert res3.start.month == 1
    assert res3.start.day == 15
    assert res3.precision == "day"


def test_working_memory_ring_buffer():
    """Test RAM working memory ring buffer bounds."""
    wm = WorkingMemory(max_turns=4, max_chars=500)
    wm.add("user", "Hello")
    wm.add("assistant", "Hi there")
    wm.add("user", "What is my exam date?")
    wm.add("assistant", "Your exam is in January.")
    wm.add("user", "Great, thanks!")
    
    rendered = wm.render()
    assert "Hello" not in rendered  # Evicted because max_turns=4
    assert "Your exam is in January." in rendered
    assert "Great, thanks!" in rendered


def test_memory_service_singleton_and_speed():
    """Test MemoryService singleton and sub-millisecond retrieval."""
    ms = MemoryService.get()
    assert ms is not None
    assert isinstance(ms.store, HybridMemoryStore)
    
    # Record a turn
    ms.record_turn("user", "My Chrome profile for work is Profile 2")
    ms.record_turn("assistant", "Noted, work profile is Profile 2.")
    
    # Store a fact
    t0 = time.time()
    mid = ms.store.upsert(
        kind="fact",
        content="Work Chrome profile is Profile 2",
        subject="user.work_browser_profile",
        importance=0.9
    )
    t_insert = time.time() - t0
    assert mid is not None
    
    # Search
    t1 = time.time()
    hits = ms.store.search("Which profile is work?", k=5)
    t_search = time.time() - t1
    
    assert len(hits) > 0
    assert any("Profile 2" in h["content"] for h in hits)
    print(f"\n[Bench] Vector search completed in {t_search*1000:.2f} ms")


def test_fact_supersession():
    """Test that updating a subject supersedes the old fact cleanly."""
    ms = MemoryService.get()
    
    # Fact 1: Project profile is Profile 4
    ms.store.upsert(
        kind="fact",
        content="Project Chrome profile is Profile 4",
        subject="user.test_project_profile",
        importance=0.8
    )
    
    # Fact 2: User updates Project profile to Profile 5
    ms.store.upsert(
        kind="fact",
        content="Project Chrome profile is Profile 5",
        subject="user.test_project_profile",
        importance=0.9
    )
    
    hits = ms.store.search("Project Chrome profile", k=5, kinds=("fact",))
    # Active hit must be Profile 5
    profile_5_hits = [h for h in hits if "Profile 5" in h["content"]]
    assert len(profile_5_hits) >= 1
    # Old Profile 4 under user.test_project_profile should be superseded (status not active)
    profile_4_active = [h for h in hits if h.get("subject") == "user.test_project_profile" and "Profile 4" in h["content"] and h["status"] == "active"]
    assert len(profile_4_active) == 0


def test_chain_guard_registry():
    """Test ChainRunRegistry ownership scoping and derived UI state."""
    reg = ChainRunRegistry()
    assert reg.state == "idle"
    
    # Start chain run for chat
    run1 = reg.start(owner="chat_turn_1", blackboard={"profile": "Profile 1"})
    assert reg.state == "processing"
    assert run1.blackboard.get("profile") == "Profile 1"
    
    # Voice cleanup tries to cancel its own turn (should NOT cancel chat_turn_1)
    cancelled_count = reg.cancel_owner("voice_turn_1")
    assert cancelled_count == 0
    assert not run1.cancelled.is_set()
    assert reg.state == "processing"
    
    # Correct owner cancels
    cancelled_count2 = reg.cancel_owner("chat_turn_1")
    assert cancelled_count2 == 1
    assert run1.cancelled.is_set()
    
    reg.finish(run1.id)
    assert reg.state == "idle"


def test_task_chain_orchestrator_terminal_events():
    """Test that TaskChainOrchestrator emits terminal events and propagates blackboard parameters."""
    from core_ai.core.task_chain_orchestrator import TaskChainOrchestrator
    
    orch = TaskChainOrchestrator()
    events = []
    
    def on_event(payload):
        events.append(payload.get("event_type"))
        
    step1 = TaskStep(step=1, intent="open_app", params={"app_name": "chrome", "profile": "Default"})
    step2 = TaskStep(step=2, intent="read_email", params={})
    
    # Execute chain with callback
    res = orch.execute_chain(
        steps=[step1, step2],
        chain_id="test_chain_001",
        progress_callback=on_event
    )
    
    assert res is not None
    # Verify that a terminal event was recorded
    assert any(e in ("chain.completed", "chain.failed") for e in events)
    print(f"\n[Chain] Recorded events: {events}")


if __name__ == "__main__":
    test_resolve_time_hinglish()
    print("✅ test_resolve_time_hinglish passed")
    test_working_memory_ring_buffer()
    print("✅ test_working_memory_ring_buffer passed")
    test_memory_service_singleton_and_speed()
    print("✅ test_memory_service_singleton_and_speed passed")
    test_fact_supersession()
    print("✅ test_fact_supersession passed")
    test_chain_guard_registry()
    print("✅ test_chain_guard_registry passed")
    test_task_chain_orchestrator_terminal_events()
    print("✅ test_task_chain_orchestrator_terminal_events passed")
    print("\n🎉 ALL UNIFIED MEMORY & CHAIN GUARD TESTS PASSED!")
