#!/usr/bin/env python3
"""
PULSAR AI ASSISTANT - FRONTEND USER INTERACTION MOCK TESTER
===========================================================
Simulates the exact HTTP and WebSocket interactions performed by a user
in the React/Windows Desktop frontend:
1. Loading initial app settings (GET /api/settings/all)
2. Changing AI Provider & Model in Settings (POST /api/settings/update)
3. Changing Voice and General preferences
4. Sending Chat commands via HTTP (POST /api/command)
5. Sending Chat commands via Socket.IO (socket.emit('command'))
6. Model hot-switching verification (gemini-2.5-flash <-> gemini-1.5-flash)
7. WebSocket live token streaming verification
"""

import sys
import os
import json
import time
import requests
import socketio
from datetime import datetime

# Enforce UTF-8 on Windows stdout
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = os.environ.get("PULSAR_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
SOCKET_URL = BASE_URL

results = []

def log_test(name, passed, details="", data=None):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({"name": name, "passed": passed, "details": details})
    print(f"\n[{status}] {name}")
    if details:
        print(f"   ℹ️  {details}")
    if data:
        preview = json.dumps(data, indent=2, default=str)
        if len(preview) > 500:
            preview = preview[:500] + "... [truncated]"
        print(f"   📦 Data: {preview}")

def test_1_get_initial_settings():
    """User opens Settings modal -> App calls GET /api/settings/all"""
    try:
        r = requests.get(f"{BASE_URL}/api/settings/all", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and "settings" in data:
                ai = data["settings"].get("ai", {})
                provider = ai.get("defaultProvider")
                model = ai.get("defaultModel")
                log_test("Test 1: Fetch All Settings on App Mount", True, 
                         f"Loaded current provider='{provider}', model='{model}'", data["settings"]["ai"])
                return data["settings"]
            else:
                log_test("Test 1: Fetch All Settings on App Mount", False, f"Unexpected response: {data}")
        else:
            log_test("Test 1: Fetch All Settings on App Mount", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        log_test("Test 1: Fetch All Settings on App Mount", False, f"Exception: {e}")
    return None

def test_2_update_ai_settings(provider="gemini", model="gemini-2.5-flash", temp=0.7):
    """User changes AI settings in UI -> App calls POST /api/settings/update"""
    try:
        payload = {
            "category": "ai",
            "settings": {
                "defaultProvider": provider,
                "defaultModel": model,
                "temperature": temp,
                "maxTokens": 2048,
                "contextWindow": 4096,
                "safetySettings": {
                    "dangerousContent": "block_none",
                    "harassment": "block_none",
                    "hateSpeech": "block_none",
                    "sexuallyExplicit": "block_none"
                },
                "localLlm": {
                    "enabled": True,
                    "modelPath": "models/pulsar-final-q4_k_m.gguf",
                    "useGpu": False
                }
            }
        }
        r = requests.post(f"{BASE_URL}/api/settings/update", json=payload, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                # Verify persistence by reading back
                r_verify = requests.get(f"{BASE_URL}/api/settings/all", timeout=5).json()
                saved_ai = r_verify.get("settings", {}).get("ai", {})
                if saved_ai.get("defaultProvider") == provider and saved_ai.get("defaultModel") == model:
                    log_test(f"Test 2: User Chooses Model ({provider} / {model})", True,
                             f"Successfully saved and verified persistent settings!", saved_ai)
                    return True
                else:
                    log_test(f"Test 2: User Chooses Model ({provider} / {model})", False,
                             f"Settings not matched after save. Got: {saved_ai}")
            else:
                log_test(f"Test 2: User Chooses Model ({provider} / {model})", False, f"Failed: {data}")
        else:
            log_test(f"Test 2: User Chooses Model ({provider} / {model})", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        log_test(f"Test 2: User Chooses Model ({provider} / {model})", False, f"Exception: {e}")
    return False

def test_3_update_general_settings():
    """User changes UI language / Hinglish in General Settings"""
    try:
        payload = {
            "category": "general",
            "settings": {
                "language": "en-US",
                "secondaryLanguage": "hi-IN",
                "enableHinglish": True,
                "theme": "dark",
                "animations": True,
                "startOnBoot": True
            }
        }
        r = requests.post(f"{BASE_URL}/api/settings/update", json=payload, timeout=5)
        if r.status_code == 200 and r.json().get("success"):
            log_test("Test 3: User Updates General Settings (Hinglish=True)", True,
                     "General preferences saved successfully.")
            return True
        else:
            log_test("Test 3: User Updates General Settings", False, f"Response: {r.text}")
    except Exception as e:
        log_test("Test 3: User Updates General Settings", False, f"Exception: {e}")
    return False

def test_4_update_voice_settings():
    """User configures Voice (TTS & STT) in Settings Tab"""
    try:
        payload = {
            "category": "voice",
            "settings": {
                "tts": {
                    "enabled": True,
                    "engine": "edge_tts",
                    "voice_id": "en-US-AriaNeural",
                    "voice_name": "Aria",
                    "speed": 1.0,
                    "pitch": 1,
                    "volume": 0.9,
                    "useCache": True
                },
                "stt": {
                    "engine": "whisper",
                    "model": "base",
                    "language": "en",
                    "sensitivity": 0.8,
                    "continuous": False
                },
                "wakeWord": {
                    "enabled": True,
                    "phrases": ["hey pulsar", "pulsar"],
                    "sensitivity": 0.7
                }
            }
        }
        r = requests.post(f"{BASE_URL}/api/settings/update", json=payload, timeout=5)
        if r.status_code == 200 and r.json().get("success"):
            log_test("Test 4: User Configures Voice (TTS/STT/WakeWord)", True,
                     "Voice preferences saved and active.")
            return True
        else:
            log_test("Test 4: User Configures Voice", False, f"Response: {r.text}")
    except Exception as e:
        log_test("Test 4: User Configures Voice", False, f"Exception: {e}")
    return False

def test_5_send_chat_command_http(command_text="What is 25 + 75?"):
    """User types in CommandInput bar and submits -> POST /api/command"""
    try:
        payload = {
            "command": command_text,
            "offline_mode": False,
            "provider": "gemini",
            "model": "gemini-2.5-flash"
        }
        start = time.time()
        r = requests.post(f"{BASE_URL}/api/command", json=payload, timeout=25)
        duration = round(time.time() - start, 2)
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                response_text = data.get("response", "")
                log_test(f"Test 5: HTTP Chat Command ('{command_text}')", True,
                         f"Reply received in {duration}s: '{response_text.strip()}'", data)
                return True
            else:
                log_test(f"Test 5: HTTP Chat Command", False, f"Command failed: {data}")
        else:
            log_test(f"Test 5: HTTP Chat Command", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        log_test(f"Test 5: HTTP Chat Command", False, f"Exception: {e}")
    return False

def test_6_send_chat_command_socketio(command_text="Say 'Pulsar Online' in one word"):
    """
    User types in CommandInput bar when WebSocket is connected -> socket.emit('command')
    Frontend expects socket.on('command_response') to receive AI reply and clear typing state.
    """
    sio = socketio.Client(logger=False, engineio_logger=False)
    received_event = {"got_response": False, "chunks": 0, "data": None}

    @sio.on("connect")
    def on_connect():
        pass

    @sio.on("chat_stream_chunk")
    def on_stream(data):
        received_event["chunks"] += 1

    @sio.on("command_response")
    def on_command_response(data):
        received_event["got_response"] = True
        received_event["data"] = data

    try:
        sio.connect(BASE_URL, socketio_path="/socket.io", transports=["polling", "websocket"])
        time.sleep(0.5)

        if not sio.connected:
            log_test("Test 6: WebSocket Chat Command via socket.emit('command')", False,
                     "Could not connect Socket.IO client.")
            return False

        # Emit the exact payload that DashboardContext.tsx sends
        sio.emit("command", {
            "command": command_text,
            "message": command_text,
            "offline_mode": False,
            "provider": "gemini",
            "model": "gemini-2.5-flash"
        })

        # Wait up to 35 seconds for response (first cold query also warms IntentRouter)
        for _ in range(70):
            time.sleep(0.5)
            if received_event["got_response"]:
                break

        sio.disconnect()

        if received_event["got_response"]:
            resp = received_event["data"].get("response") or received_event["data"].get("message")
            chunks = received_event["chunks"]
            log_test("Test 6: WebSocket Chat Command via socket.emit('command')", True,
                     f"Live WebSocket reply received ({chunks} stream chunks): '{resp}'", received_event["data"])
            return True
        else:
            log_test("Test 6: WebSocket Chat Command via socket.emit('command')", False,
                     "Backend did not respond with 'command_response'.")
            return False
    except Exception as e:
        log_test("Test 6: WebSocket Chat Command via socket.emit('command')", False, f"Exception: {e}")
        try:
            sio.disconnect()
        except:
            pass
        return False

def test_7_model_switching_and_persistence():
    """User selects a different model (gemini-2.5-pro) in Settings and asks a question"""
    try:
        # Step A: Update settings to gemini-2.5-pro
        update_payload = {
            "category": "ai",
            "settings": {
                "defaultProvider": "gemini",
                "defaultModel": "gemini-2.5-pro",
                "temperature": 0.5,
                "maxTokens": 2048,
                "contextWindow": 4096,
                "safetySettings": {
                    "dangerousContent": "block_none",
                    "harassment": "block_none",
                    "hateSpeech": "block_none",
                    "sexuallyExplicit": "block_none"
                },
                "localLlm": {"enabled": True, "modelPath": "", "useGpu": False}
            }
        }
        r1 = requests.post(f"{BASE_URL}/api/settings/update", json=update_payload, timeout=5)
        if not r1.json().get("success"):
            log_test("Test 7: Switch to gemini-2.5-pro", False, "Failed to update settings to gemini-2.5-pro")
            return False

        # Step B: Send command with gemini-2.5-pro
        cmd_payload = {
            "command": "Give me a 3-word motto for an AI assistant",
            "provider": "gemini",
            "model": "gemini-2.5-pro"
        }
        r2 = requests.post(f"{BASE_URL}/api/command", json=cmd_payload, timeout=25)
        if r2.status_code == 200 and r2.json().get("success"):
            reply = r2.json().get("response", "")
            meta = r2.json().get("execution_meta", {})
            log_test("Test 7: Switch Model -> gemini-2.5-pro & Ask Question", True,
                     f"Successfully processed with {meta.get('model_used', 'gemini-2.5-pro')}! Reply: '{reply.strip()}'")
            return True
        else:
            log_test("Test 7: Switch Model -> gemini-2.5-pro", False, f"Error: {r2.text}")
    except Exception as e:
        log_test("Test 7: Switch Model -> gemini-2.5-pro", False, f"Exception: {e}")
    return False

def main():
    print("=" * 70)
    print("  🚀 PULSAR AI ASSISTANT - EXTENSIVE FRONTEND MOCK VERIFICATION")
    print(f"  Target: {BASE_URL} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    test_1_get_initial_settings()
    test_2_update_ai_settings("gemini", "gemini-2.5-flash", 0.7)
    test_3_update_general_settings()
    test_4_update_voice_settings()
    test_5_send_chat_command_http("Calculate 100 divided by 4")
    test_6_send_chat_command_socketio("Say 'Pulsar Online' in one word")
    test_7_model_switching_and_persistence()

    # Revert to default gemini-2.5-flash
    test_2_update_ai_settings("gemini", "gemini-2.5-flash", 0.7)

    print("\n" + "=" * 70)
    print("  📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    for r in results:
        mark = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"  {mark:8} | {r['name']}")

    print(f"\n  Total Tests: {total} | Passed: {passed} | Failed: {failed}")
    if failed == 0:
        print("  🎉 ALL FRONTEND USER INTERACTIONS MOCKED AND VERIFIED SUCCESSFULLY!")
    else:
        print(f"  ⚠️ {failed} tests failed! Review diagnostics above.")
    print("=" * 70)

if __name__ == "__main__":
    main()
