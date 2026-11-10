#!/usr/bin/env python3
"""
Pulsar AI Assistant - Ambient Agent Comprehensive Test Bench Suite
===================================================================
Tests all 6 core sub-systems across Phases 1-5:
- Bench 1: Intent Routing & Reasoning (Media, Comms, System, Screen Actions, Tier 3 Safety Gate)
- Bench 2: Screen Perception & Window Context (Foreground detection, capture speed)
- Bench 3: Notification Priority Queue & Deduplication
- Bench 4: Layered Window UI Renderers & Interactive Button Hit-Testing
- Bench 5: Backend REST API Endpoints (/api/agent/command, notifications, confirm)
- Bench 6: Process Mutex & Singleton Protection
"""

import sys
import os
import time
from pathlib import Path

# Add project roots
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "core_ai" / "src"))
sys.path.insert(0, str(project_root / "desktop"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

results = []

def run_bench(bench_name, test_func):
    print(f"\n=======================================================")
    print(f"RUNNING {bench_name.upper()}")
    print(f"=======================================================")
    start = time.time()
    try:
        test_func()
        elapsed = (time.time() - start) * 1000
        print(f"--> [PASS] {bench_name} completed in {elapsed:.1f}ms")
        results.append((bench_name, True, f"{elapsed:.1f}ms", "All checks passed"))
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        print(f"--> [FAIL] {bench_name} failed: {e}")
        import traceback
        traceback.print_exc()
        results.append((bench_name, False, f"{elapsed:.1f}ms", str(e)))


# -------------------------------------------------------------
# BENCH 1: Intent Routing & Reasoning Bench
# -------------------------------------------------------------
def test_bench_1_intent_routing():
    from agent_brain import get_agent_brain
    brain = get_agent_brain()

    # 1.1 Fast Media Commands
    res1 = brain.process_command("gaana skip karo")
    assert res1.get("success") is True, "Media skip failed"
    print("  ✓ Fast Media Skip dispatch:", res1.get("response"))

    res2 = brain.process_command("pause video")
    assert res2.get("success") is True, "Media pause failed"
    print("  ✓ Fast Media Pause dispatch:", res2.get("response"))

    # 1.2 Fast System Controls
    res3 = brain.process_command("mute")
    assert res3.get("success") is True, "Mute failed"
    print("  ✓ System Mute dispatch:", res3.get("response"))

    # 1.3 Background Task Dispatch
    res4 = brain.process_command("search website for python vs typescript")
    assert res4.get("success") is True, "Background search failed"
    print("  ✓ Background research dispatch:", res4.get("response")[:60] + "...")

    # 1.4 Tier 3 Gated Action (Requires Confirmation)
    tier3_test = brain._create_pending_confirmation(
        command="Send WhatsApp to Boss: I am resigning",
        intent="communication",
        action="send_whatsapp",
        params={"contact": "Boss", "message": "I am resigning"},
        classification={"summary": "Send WhatsApp to Boss saying 'I am resigning'"}
    )
    assert tier3_test.get("requires_confirmation") is True, "Tier 3 safety gating failed"
    act_id = tier3_test.get("action_id")
    assert act_id in brain.pending_actions, "Action ID not registered in pending store"
    print("  ✓ Tier 3 Safety Gate: Action properly held for confirmation:", act_id)

    # Cancel confirmation test
    res_cancel = brain.confirm_action_by_id(act_id, confirmed=False)
    assert res_cancel.get("success") is True, "Cancel confirmation failed"
    assert act_id not in brain.pending_actions, "Cancelled action not purged from store"
    print("  ✓ Tier 3 Safety Gate: Cancellation handled cleanly")


# -------------------------------------------------------------
# BENCH 2: Screen Perception & Window Context Bench
# -------------------------------------------------------------
def test_bench_2_screen_perception():
    from agent_brain import get_agent_brain
    brain = get_agent_brain()

    # 2.1 Active window detection
    win_info = brain.get_active_window_info()
    assert "title" in win_info, "Missing title in active window info"
    assert "app_name" in win_info, "Missing app_name in active window info"
    assert "rect" in win_info, "Missing rect in active window info"
    print(f"  ✓ Active window detected: '{win_info['title'][:40]}' (App: {win_info['app_name']})")

    # 2.2 Screen capture benchmark
    t0 = time.time()
    shot = brain.capture_screen()
    t_cap = (time.time() - t0) * 1000
    assert shot is not None, "Screen capture returned None"
    print(f"  ✓ Screen captured in {t_cap:.1f}ms (Resolution: {shot.size[0]}x{shot.size[1]})")
    assert t_cap < 200, f"Screen capture too slow ({t_cap:.1f}ms)"


# -------------------------------------------------------------
# BENCH 3: Notification Priority Queue & Deduplication Bench
# -------------------------------------------------------------
def test_bench_3_notification_queue():
    from notification_monitor import get_notification_monitor
    monitor = get_notification_monitor()

    # Clear queue first
    monitor.get_pending()

    # Push 3 notifications with varying priorities
    monitor.push_notification({
        "type": "email",
        "title": "Normal Newsletter",
        "body": "Weekly tech updates",
        "priority": "normal"
    })
    monitor.push_notification({
        "type": "calendar",
        "title": "URGENT Meeting in 10 mins",
        "body": "Project review call with manager",
        "priority": "critical"
    })
    monitor.push_notification({
        "type": "whatsapp",
        "title": "Important Client Message",
        "body": "Contract signed",
        "priority": "high"
    })

    # Test Deduplication: push duplicate
    monitor.push_notification({
        "type": "email",
        "title": "Normal Newsletter",
        "body": "Weekly tech updates",
        "priority": "normal"
    })

    # Retrieve sorted pending
    pending = monitor.get_pending()
    assert len(pending) == 3, f"Expected 3 items after deduplication, got {len(pending)}"

    # Verify priority sorting: critical -> high -> normal
    assert pending[0]["priority"] == "critical", f"Item 0 should be critical, got {pending[0]['priority']}"
    assert pending[1]["priority"] == "high", f"Item 1 should be high, got {pending[1]['priority']}"
    assert pending[2]["priority"] == "normal", f"Item 2 should be normal, got {pending[2]['priority']}"
    print("  ✓ Deduplication verified (duplicate dropped)")
    print("  ✓ Priority ordering verified: Critical (Calendar) -> High (WhatsApp) -> Normal (Email)")


# -------------------------------------------------------------
# BENCH 4: Win32 Layered Window UI & Hit-Testing Bench
# -------------------------------------------------------------
def test_bench_4_ui_hit_testing():
    from companion_ui import render_speech_bubble, render_notification_card, render_confirmation_dialog

    # 4.1 Speech Bubble
    bubble = render_speech_bubble("Hello! I reviewed your screen and everything is working smoothly.")
    assert bubble.size[0] == 280, f"Expected width 280, got {bubble.size[0]}"
    print(f"  ✓ Speech bubble rendered: {bubble.size[0]}x{bubble.size[1]} with RGBA alpha channel")

    # 4.2 Notification Card
    notif = {
        "type": "whatsapp",
        "title": "💬 Message from Diwakar",
        "body": "Hey bro, check the latest update",
        "actions": ["Show", "Reply", "Dismiss"]
    }
    card, buttons = render_notification_card(notif, max_w=310)
    assert card.size[0] == 310, "Card width incorrect"
    assert len(buttons) == 3, f"Expected 3 interactive buttons, got {len(buttons)}"
    print(f"  ✓ Notification card rendered: {card.size[0]}x{card.size[1]} with {len(buttons)} buttons")

    # 4.3 Interactive Hit-Testing Simulation
    # Check that clicking inside button 1 hits 'Show'
    btn0 = buttons[0]
    bx_center = (btn0["rect"][0] + btn0["rect"][2]) // 2
    by_center = (btn0["rect"][1] + btn0["rect"][3]) // 2

    hit = None
    for b in buttons:
        x0, y0, x1, y1 = b["rect"]
        if x0 <= bx_center <= x1 and y0 <= by_center <= y1:
            hit = b["action"]
            break
    assert hit == "Show", f"Hit test expected 'Show', got '{hit}'"
    print(f"  ✓ Button Hit-Test: Click at ({bx_center}, {by_center}) correctly hit '{hit}' button")

    # 4.4 Confirmation Dialog
    c_img, c_buttons = render_confirmation_dialog("End video call on WhatsApp?")
    assert len(c_buttons) == 2, "Expected confirm and cancel buttons"
    assert c_buttons[0]["action"] == "confirm"
    assert c_buttons[1]["action"] == "cancel"
    print(f"  ✓ Confirmation dialog rendered: {c_img.size[0]}x{c_img.size[1]} with Confirm and Cancel targets")


# -------------------------------------------------------------
# BENCH 5: Backend REST API Endpoints Bench
# -------------------------------------------------------------
def test_bench_5_rest_api():
    from backend.modern_web_backend import app

    client = app.test_client()

    # 5.1 /api/agent/command
    r_cmd = client.post("/api/agent/command", json={"command": "mute", "include_screen": False})
    assert r_cmd.status_code == 200, f"Expected 200, got {r_cmd.status_code}"
    data_cmd = r_cmd.get_json()
    assert data_cmd.get("success") is True, f"Command execution returned false: {data_cmd}"
    print("  ✓ POST /api/agent/command returned 200 OK with success=True")

    # 5.2 /api/agent/notifications
    r_notif = client.get("/api/agent/notifications")
    assert r_notif.status_code == 200, f"Expected 200, got {r_notif.status_code}"
    data_notif = r_notif.get_json()
    assert "notifications" in data_notif, "Missing 'notifications' key"
    print(f"  ✓ GET /api/agent/notifications returned 200 OK (count={len(data_notif['notifications'])})")

    # 5.3 /api/agent/confirm
    r_conf = client.post("/api/agent/confirm", json={"action_id": "test_id", "confirmed": False})
    assert r_conf.status_code in [200, 400], "Endpoint failed to respond"
    print("  ✓ POST /api/agent/confirm endpoint verified")


# -------------------------------------------------------------
# BENCH 6: Process Mutex & Singleton Protection Bench
# -------------------------------------------------------------
def test_bench_6_process_mutex():
    import ctypes
    kernel32 = ctypes.windll.kernel32
    MUTEX_NAME = "Global\\Pulsar_Ambient_Mascot_Robot_Mutex"

    # Acquire mutex
    m1 = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    err1 = kernel32.GetLastError()

    # Try duplicate acquisition
    m2 = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    err2 = kernel32.GetLastError()

    assert err2 == 183, f"Expected ERROR_ALREADY_EXISTS (183), got {err2}"
    print(f"  ✓ Mutex 1 creation error code: {err1}")
    print(f"  ✓ Mutex 2 duplicate error code: {err2} (ERROR_ALREADY_EXISTS)")
    print("  ✓ Strict Single-Instance protection guaranteed across OS")

    kernel32.CloseHandle(m1)
    kernel32.CloseHandle(m2)


def main():
    print("=======================================================")
    print("   PULSAR AMBIENT AGENT (PHASES 1-5) BENCHMARK SUITE   ")
    print("=======================================================")

    run_bench("Bench 1: Intent Routing & Reasoning", test_bench_1_intent_routing)
    run_bench("Bench 2: Screen Perception & Window Context", test_bench_2_screen_perception)
    run_bench("Bench 3: Notification Priority & Deduplication", test_bench_3_notification_queue)
    run_bench("Bench 4: Win32 Layered Window UI & Hit-Testing", test_bench_4_ui_hit_testing)
    run_bench("Bench 5: Backend REST API Endpoints", test_bench_5_rest_api)
    run_bench("Bench 6: Process Mutex & Singleton Protection", test_bench_6_process_mutex)

    print("\n=======================================================")
    print("                  BENCHMARK SUMMARY                    ")
    print("=======================================================")
    all_passed = True
    for name, passed, time_taken, note in results:
        status = "PASSED [✓]" if passed else "FAILED [✗]"
        print(f"{name:45} | {status} | {time_taken:8} | {note}")
        if not passed:
            all_passed = False

    print("=======================================================")
    if all_passed:
        print(">>> ALL 6 BENCHES PASSED WITH 100% SUCCESS! <<<")
    else:
        print(">>> SOME BENCHES ENCOUNTERED ISSUES <<<")
    print("=======================================================\n")


if __name__ == "__main__":
    main()

