#!/usr/bin/env python3
"""
Streaming Chat Test Client
Tests the new streaming endpoints and WebSocket handlers.
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import requests
import json
import time

BASE_URL = "http://localhost:5000"


def test_streaming_endpoint():
    """Test the /api/chat/stream endpoint"""
    print("\n" + "="*70)
    print("🧪 TEST: Streaming Endpoint (/api/chat/stream)")
    print("="*70)
    
    try:
        print("\n📨 Sending request to /api/chat/stream...")
        print("💬 Message: 'What is Python programming?'")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/stream",
            json={
                "message": "What is Python programming?",
                "session_id": "test_session"
            },
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        print("\n📡 Receiving stream...")
        tokens = 0
        full_response = ""
        
        for line in response.iter_lines():
            if line:
                try:
                    # Parse Server-Sent Events format
                    if line.startswith(b'data: '):
                        data = json.loads(line[6:].decode('utf-8'))
                        
                        if 'token' in data:
                            token = data['token']
                            tokens = data['count']
                            print(token, end='', flush=True)
                        
                        elif 'done' in data:
                            print(f"\n\n✅ Stream complete!")
                            print(f"   Tokens: {data['tokens']}")
                            print(f"   Duration: {data['duration']}s")
                            print(f"   Speed: {data.get('tokens_per_second', 0):.1f} tok/s")
                            return True
                        
                        elif 'error' in data:
                            print(f"\n❌ Error: {data['error']}")
                            return False
                except json.JSONDecodeError:
                    print(f"⚠️ Could not parse: {line}")
        
        print("\n⚠️ Stream ended without completion signal")
        return False
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error: Is the server running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_endpoint():
    """Test the chat_stream WebSocket endpoint"""
    print("\n" + "="*70)
    print("🧪 TEST: WebSocket Endpoint (chat_stream)")
    print("="*70)
    
    try:
        import socketio
        
        print("\n📡 Connecting to WebSocket...")
        
        sio = socketio.Client()
        
        # Store received data
        received_tokens = []
        completion_received = False
        
        @sio.event
        def connect():
            print("✅ Connected to server")
            print("📨 Sending chat message...")
            sio.emit('chat_stream', {
                'message': 'Explain quantum computing in simple terms',
                'session_id': 'test_ws_session'
            })
        
        @sio.on('chat_token')
        def on_token(data):
            token = data.get('token', '')
            print(token, end='', flush=True)
            received_tokens.append(token)
        
        @sio.on('chat_complete')
        def on_complete(data):
            nonlocal completion_received
            completion_received = True
            print(f"\n\n✅ Stream complete!")
            print(f"   Tokens: {data['tokens']}")
            print(f"   Duration: {data['duration']}s")
            print(f"   Speed: {data.get('tokens_per_second', 0):.1f} tok/s")
            sio.disconnect()
        
        @sio.on('chat_stream_error')
        def on_error(data):
            print(f"\n❌ Error: {data['error']}")
            sio.disconnect()
        
        # Connect
        sio.connect(BASE_URL, wait_timeout=10)
        
        # Wait for completion
        sio.wait()
        
        if completion_received and received_tokens:
            print(f"✅ WebSocket test passed! Received {len(received_tokens)} tokens")
            return True
        else:
            print("⚠️ WebSocket test incomplete")
            return False
        
    except ImportError:
        print("⚠️ python-socketio not installed: pip install python-socketio")
        return None
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 STREAMING CHAT - ENDPOINT TESTS")
    print("="*70)
    print("\n⚠️  Make sure the backend is running:")
    print("   python modern_web_backend.py")
    print("\nStarting tests in 2 seconds...")
    time.sleep(2)
    
    results = {}
    
    # Test 1: REST API Streaming
    results['REST Streaming'] = test_streaming_endpoint()
    
    # Test 2: WebSocket Streaming
    ws_result = test_websocket_endpoint()
    if ws_result is not None:
        results['WebSocket'] = ws_result
    else:
        print("\n⏭️  Skipping WebSocket test (socketio not installed)")
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All streaming tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
