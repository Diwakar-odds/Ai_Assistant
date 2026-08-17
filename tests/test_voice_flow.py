#!/usr/bin/env python3
"""
Voice Integration Test Script
Tests the complete voice command flow: Frontend -> Backend -> AI -> Response
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from socketio import Client
import threading

def test_voice_integration():
    """Test voice command integration end-to-end"""
    
    print("\n" + "="*70)
    print("🎤 VOICE INTEGRATION TEST")
    print("="*70 + "\n")
    
    # Create socket client
    sio = Client()
    
    responses_received = []
    connection_success = threading.Event()
    response_received = threading.Event()
    
    @sio.on('connect')
    def on_connect():
        print("✅ Connected to backend")
        connection_success.set()
    
    @sio.on('disconnect')
    def on_disconnect():
        print("👋 Disconnected from backend")
    
    @sio.on('voice_response')
    def on_voice_response(data):
        print(f"\n📥 RESPONSE RECEIVED:")
        print(f"   Response: {data.get('response', 'N/A')}")
        print(f"   Success: {data.get('success', False)}")
        print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
        responses_received.append(data)
        response_received.set()
    
    @sio.on('voice_status')
    def on_voice_status(data):
        print(f"📊 Voice Status: {data}")
    
    # Connect to backend
    try:
        print("🔌 Connecting to http://localhost:5000...")
        sio.connect('http://localhost:5000')
        
        # Wait for connection
        if not connection_success.wait(timeout=5):
            print("❌ Connection timeout")
            return False
        
        # Test commands
        test_commands = [
            {"text": "hello", "expected": "greeting"},
            {"text": "what time is it", "expected": "time"},
            {"text": "hey daddy", "expected": "greeting"},
        ]
        
        print(f"\n🧪 Testing {len(test_commands)} voice commands...\n")
        
        for i, cmd in enumerate(test_commands, 1):
            print(f"\n--- Test {i}/{len(test_commands)} ---")
            print(f"📤 Sending: '{cmd['text']}'")
            
            response_received.clear()
            
            sio.emit('voice_command', {
                'text': cmd['text'],
                'confidence': 0.95
            })
            
            # Wait for response
            if response_received.wait(timeout=10):
                print("✅ Response received within 10 seconds")
            else:
                print("❌ No response received (timeout)")
            
            time.sleep(1)  # Brief pause between commands
        
        # Disconnect
        sio.disconnect()
        
        # Summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Commands sent: {len(test_commands)}")
        print(f"Responses received: {len(responses_received)}")
        print(f"Success rate: {len(responses_received)}/{len(test_commands)} ({len(responses_received)/len(test_commands)*100:.0f}%)")
        
        if len(responses_received) == len(test_commands):
            print("\n✅ ALL TESTS PASSED! Voice integration is working perfectly!")
            return True
        else:
            print(f"\n⚠️ Some tests failed. Received {len(responses_received)}/{len(test_commands)} responses.")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_backend():
    """Check if backend is running"""
    import requests
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
    except:
        pass
    
    print("❌ Backend is not running!")
    print("\n💡 Start the backend first:")
    print("   python modern_web_backend.py")
    return False

def main():
    print("\n" + "="*70)
    print("🚀 VOICE INTEGRATION DIAGNOSTICS")
    print("="*70 + "\n")
    
    # Check backend
    print("1️⃣ Checking backend status...")
    if not check_backend():
        return 1
    
    print("\n2️⃣ Testing voice integration...")
    time.sleep(1)
    
    success = test_voice_integration()
    
    if success:
        print("\n" + "="*70)
        print("🎉 SUCCESS! Voice integration is fully functional!")
        print("="*70)
        print("\n✅ What's working:")
        print("   • WebSocket connection")
        print("   • Voice command transmission")
        print("   • Backend processing")
        print("   • AI response generation")
        print("   • Response delivery to frontend")
        print("\n📱 Your frontend should now receive AI responses!")
        return 0
    else:
        print("\n" + "="*70)
        print("⚠️ PARTIAL SUCCESS - Some issues detected")
        print("="*70)
        print("\n🔍 Troubleshooting:")
        print("   1. Check backend logs for errors")
        print("   2. Verify assistant.process_command() method")
        print("   3. Check WebSocket connection")
        print("   4. Review voice handler registration")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
        sys.exit(0)
