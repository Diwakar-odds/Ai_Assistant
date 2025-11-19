#!/usr/bin/env python3
"""
Test Enhanced Chat Features
Tests all integrated AI features and chat capabilities
"""

import requests
import json
import time
import base64
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5001"
TEST_TOKEN = None  # Will get from login

def test_login():
    """Test authentication and get token"""
    global TEST_TOKEN
    
    login_data = {
        "username": "admin",
        "password": "changeme123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            TEST_TOKEN = data.get("access_token")
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

def get_headers():
    """Get headers with authentication"""
    if TEST_TOKEN:
        return {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        }
    else:
        return {"Content-Type": "application/json"}

def test_features_status():
    """Test available features"""
    print("\n🔍 Testing Available Features...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/features")
        if response.status_code == 200:
            features = response.json()
            print("✅ Features Status:")
            for feature, status in features.items():
                if isinstance(status, dict):
                    print(f"  📁 {feature}:")
                    for sub_feature, sub_status in status.items():
                        status_icon = "✅" if sub_status else "❌"
                        print(f"    {status_icon} {sub_feature}")
                else:
                    status_icon = "✅" if status else "❌"
                    print(f"  {status_icon} {feature}")
            return True
        else:
            print(f"❌ Features test failed: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Features test error: {e}")
        return False

def test_enhanced_chat():
    """Test enhanced chat endpoint"""
    print("\n💬 Testing Enhanced Chat...")
    
    test_messages = [
        {
            "message": "Hello! What can you help me with?",
            "context": {"session_id": "test_session_1"}
        },
        {
            "message": "Open Chrome browser for me",
            "context": {"session_id": "test_session_1"}
        },
        {
            "message": "What's the weather like today?",
            "context": {"session_id": "test_session_1"}
        },
        {
            "message": "Play some music",
            "context": {"session_id": "test_session_1"}
        },
        {
            "message": "मुझे आज का मौसम बताओ",  # Hindi test
            "context": {"session_id": "test_session_1"}
        },
        {
            "message": "Show me system status",
            "context": {"session_id": "test_session_1"}
        }
    ]
    
    for i, test_data in enumerate(test_messages, 1):
        print(f"\n  Test {i}: '{test_data['message']}'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json=test_data,
                headers=get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"    ✅ Response: {data['response'][:100]}...")
                print(f"    🔧 Features used: {', '.join(data.get('features_used', []))}")
                print(f"    😊 Mood: {data.get('mood', 'unknown')}")
                print(f"    🗣️ Language: {data.get('detected_language', 'unknown')}")
                print(f"    📝 Type: {data.get('message_type', 'unknown')}")
                
                suggestions = data.get('suggestions', [])
                if suggestions:
                    print(f"    💡 Suggestions: {len(suggestions)} available")
                    
            else:
                print(f"    ❌ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            
        time.sleep(1)  # Rate limiting

def test_context_creation():
    """Test conversation context creation"""
    print("\n📝 Testing Conversation Context...")
    
    context_data = {
        "name": "Test Conversation",
        "topic": "Feature Testing",
        "initial_message": "Starting feature test conversation"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/context",
            json=context_data,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Context created: {data.get('context_id')}")
            print(f"   Name: {data.get('name')}")
            print(f"   Topic: {data.get('topic')}")
            return data.get('context_id')
        else:
            print(f"❌ Context creation failed: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Context creation error: {e}")
        return None

def test_suggestions():
    """Test AI suggestions"""
    print("\n💡 Testing AI Suggestions...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/chat/suggestions",
            headers=get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get('suggestions', [])
            print(f"✅ Got {len(suggestions)} suggestions")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"   {i}. {suggestion}")
        else:
            print(f"❌ Suggestions test failed: {response.json()}")
    except Exception as e:
        print(f"❌ Suggestions test error: {e}")

def test_screen_analysis():
    """Test screen analysis"""
    print("\n📸 Testing Screen Analysis...")
    
    analysis_data = {
        "prompt": "What applications are currently visible on the screen?"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/screen/analyze",
            json=analysis_data,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Screen analysis: {data.get('analysis', '')[:100]}...")
        else:
            print(f"❌ Screen analysis failed: {response.json()}")
    except Exception as e:
        print(f"❌ Screen analysis error: {e}")

def test_language_detection():
    """Test language detection"""
    print("\n🌍 Testing Language Detection...")
    
    test_texts = [
        "Hello, how are you today?",
        "नमस्ते, आप कैसे हैं?",
        "Chrome browser खोलो",
        "Play some music यार"
    ]
    
    for text in test_texts:
        try:
            response = requests.post(
                f"{BASE_URL}/api/language/detect",
                json={"text": text},
                headers=get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ '{text[:30]}...' -> {data.get('detected_language')} "
                      f"(confidence: {data.get('confidence', 0):.2f})")
            else:
                print(f"❌ Language detection failed for: {text}")
        except Exception as e:
            print(f"❌ Language detection error: {e}")

def test_memory_system():
    """Test memory system"""
    print("\n🧠 Testing Memory System...")
    
    # Test saving to memory
    memory_data = {
        "category": "test",
        "content": "Testing enhanced chat memory system with all features"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/memory/save",
            json=memory_data,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            print("✅ Memory save successful")
            
            # Test searching memory
            response = requests.get(
                f"{BASE_URL}/api/memory/search?query=enhanced chat",
                headers=get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"✅ Memory search found {len(results)} results")
                for result in results[:2]:
                    print(f"   - {str(result)[:50]}...")
            else:
                print(f"❌ Memory search failed: {response.json()}")
        else:
            print(f"❌ Memory save failed: {response.json()}")
    except Exception as e:
        print(f"❌ Memory test error: {e}")

def test_automation_workflows():
    """Test automation workflows"""
    print("\n🤖 Testing Automation Workflows...")
    
    try:
        # Get available workflows
        response = requests.get(
            f"{BASE_URL}/api/automation/workflows",
            headers=get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            workflows = data.get('workflows', [])
            print(f"✅ Found {len(workflows)} available workflows")
            
            for workflow in workflows[:3]:
                print(f"   - {workflow}")
                
            # Try to execute a simple workflow if available
            if workflows:
                test_workflow = workflows[0] if isinstance(workflows[0], str) else workflows[0].get('name', '')
                if test_workflow:
                    try:
                        response = requests.post(
                            f"{BASE_URL}/api/automation/execute",
                            json={"workflow_name": test_workflow},
                            headers=get_headers()
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            print(f"✅ Workflow executed: {data.get('result', '')[:50]}...")
                        else:
                            print(f"❌ Workflow execution failed: {response.json()}")
                    except Exception as e:
                        print(f"❌ Workflow execution error: {e}")
        else:
            print(f"❌ Workflows test failed: {response.json()}")
    except Exception as e:
        print(f"❌ Workflows test error: {e}")

def main():
    """Run all tests"""
    print("🚀 Enhanced Chat Feature Testing")
    print("=" * 50)
    
    # Try to login first
    if test_login():
        time.sleep(1)
    else:
        print("⚠️ Running tests without authentication")
    
    # Run all tests
    tests = [
        test_features_status,
        test_enhanced_chat,
        test_context_creation,
        test_suggestions,
        test_screen_analysis,
        test_language_detection,
        test_memory_system,
        test_automation_workflows
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with error: {e}")
        
        time.sleep(2)  # Rate limiting between tests
    
    print("\n" + "=" * 50)
    print(f"🏁 Testing Complete: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All features working perfectly!")
    elif passed >= total * 0.7:
        print("🟡 Most features working - some issues detected")
    else:
        print("❌ Multiple issues detected - check configuration")

if __name__ == "__main__":
    main()