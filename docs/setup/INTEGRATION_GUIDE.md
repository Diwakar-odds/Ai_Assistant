# Integration Guide: Enable Multi-Step Commands in Chat/Voice

## ✅ What's Ready

**Built Components:**
- Multi-step parser ✅
- Context manager ✅
- Task orchestrator ✅
- App controller ✅
- Integration module ✅

## 🔌 How to Enable

### Option 1: Quick Integration (Recommended)

**Just add 3 lines to your chat/voice handler!**

```python
# In your chat processing function
from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator

def handle_command(command_text):
    # Check if multi-step
    if should_use_orchestrator(command_text):
        result = process_with_orchestrator(command_text)
        
        if result['success']:
            return result['response']
        elif result.get('fallback'):  
            # Fallback to normal processing
            pass  # Continue to existing logic
        else:
            return f"Error: {result['error']}"
    
    # Normal single-step processing
    # ... your existing code ...
```

### Option 2: Backend Integration

**Add to `/api/chat` endpoint:**

```python
# In modern_web_backend.py, line ~2477

# BEFORE processing
from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator

# Inside api_chat() function, after line 2476:
if should_use_orchestrator(message):
    orch_result = process_with_orchestrator(message, context)
    
    if orch_result['success']:
        return jsonify({
            "message": message,
            "response": orch_result['response'],
            "orchestrated": True,
            "steps": orch_result['steps_completed'],
            "timestamp": datetime.now().isoformat()
        })
    elif not orch_result.get('fallback'):
        return jsonify({
            "error": orch_result['error'],
            "orchestrated": True
        }), 500
    # else: fallback to existing processing below
```

### Option 3: Voice Integration

**Add to voice command handler:**

```python
# In your voice processing code
from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator

def handle_voice_command(transcribed_text):
    if should_use_orchestrator(transcribed_text):
        result = process_with_orchestrator(transcribed_text)
        
        if result['success']:
            speak(result['response'])  # Your TTS function
            return
    
    # Normal voice command handling
    # ... existing code ...
```

---

## 📋 Full Integration Example

Here's a complete example:

```python
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat endpoint with multi-step support"""
    try:
        data = request.get_json()
        message = data['message']
        context = data.get('context', {})
        
        # === NEW: Multi-step orchestration ===
        from ai_assistant.integrations.orchestrator_integration import (
            should_use_orchestrator, 
            process_with_orchestrator
        )
        
        if should_use_orchestrator(message):
            logger.info(f"🔗 Using orchestrator for: {message}")
            
            result = process_with_orchestrator(message, context)
            
            if result['success']:
                return jsonify({
                    "response": result['response'],
                    "orchestrated": True,
                    "steps_completed": result['steps_completed'],
                    "timestamp": datetime.now().isoformat()
                })
            elif not result.get('fallback'):
                # Hard error, don't fallback
                return jsonify({
                    "error": result['error'],
                    "orchestrated": True
                }), 500
            else:
                logger.warning("Orchestrator failed, using fallback")
                # Continue to normal processing below
        # === END: Multi-step orchestration ===
        
        # Normal single-step processing
        response = assistant.process_command(message)
        
        return jsonify({
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## 🧪 Testing

### Test Commands

```javascript
// Test 1: Simple multi-step
POST /api/chat
{
  "message": "Notepad खोलो, Hello लिखो"
}

// Test 2: Three steps
POST /api/chat
{
  "message": "Calculator खोलो फिर Notepad खोलो फिर Chrome खोलो"
}

// Test 3: Context-aware
POST /api/chat
{"message": "WhatsApp खोलो"}

POST /api/chat  // Second command, no app specified!
{"message": "message करो"}  // Uses WhatsApp from context
```

### Expected Response

```json
{
  "response": "✅ Completed 2 steps successfully!\n\n1. open_app ✓\n2. type_text ✓",
  "orchestrated": true,
  "steps_completed": 2,
  "timestamp": "2026-01-01T22:30:00"
}
```

---

## ⚡ Quick Start (Minimal Changes)

**Don't want to modify backend? Use this wrapper:**

```python
# In your existing command handler (wherever it is)
def process_any_command(command_text):
    """
    Your existing function.
    Just wrap it with orchestrator check!
    """
    # NEW: 5 lines added
    from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator
    
    if should_use_orchestrator(command_text):
        result = process_with_orchestrator(command_text)
        if result['success']:
            return result['response']
    # END: New code
    
    # Your existing code continues unchanged
    # ... all your current logic ...
```

**That's it!** Multi-step commands now work!

---

## 📊 Status Check

**Check if orchestrator is loaded:**

```python
from ai_assistant.integrations.orchestrator_integration import get_orchestrator_status

status = get_orchestrator_status()
print(status)
# {'available': True, 'status': {...}}
```

**Add status endpoint** (optional):

```python
@app.route('/api/orchestrator/status')
def api_orchestrator_status():
    from ai_assistant.integrations.orchestrator_integration import get_orchestrator_status
    return jsonify(get_orchestrator_status())
```

---

## ✅ Summary

**To enable multi-step commands:**

1. Import integration module ✅
2. Add `if should_use_orchestrator()` check ✅
3. Call `process_with_orchestrator()` ✅
4. Done! 🎉

**Minimal code:** 3-5 lines
**Impact:** Full multi-step support
**Backward compatible:** ✅ (falls back to normal)

---

## 🎯 Next Steps After Integration

1. **Test with chat UI**
2. **Test with voice commands**
3. **Monitor execution logs**
4. **Add more intents** (optional)
5. **Enable learning system** (optional)

**Your users can now say:**
- "WhatsApp खोलो, मॉम को message करो"
- "Notepad open करो, text लिखो, फिर save करो"
- Any multi-step workflow!

🚀 **System is ready to use!**
