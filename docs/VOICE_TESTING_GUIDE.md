# Voice System Testing Guide

## Quick Start

### 1. Start Backend Server

```bash
cd f:\bn\assitant
python -m ai_assistant.services.modern_web_backend
```

### 2. Run Test Suite

```bash
python tests\test_voice_system.py
```

### 3. Expected Output

```
==============================================================
VOICE SYSTEM TEST SUITE
==============================================================

📋 Testing P0: Critical Fixes
🧪 Testing: P0.1: Voice List Endpoint
✅ PASSED: P0.1: Voice List Endpoint

📋 Testing P1: High Priority Features
🧪 Testing: P1.5: Caching - First Request
✅ PASSED: P1.5: Caching - First Request

...

==============================================================
TEST RESULTS
==============================================================
Passed: 11/11
Failed: 0/11
Success Rate: 100.0%
==============================================================
```

## Manual Testing Checklist

### Frontend Component Testing

- [ ] Navigate to Voice Assistant page
- [ ] Verify VoiceControls displays correctly (mic button, waveform)
- [ ] Click mic button - should toggle listening state
- [ ] Expand VoiceSettings - should show 12 voices
- [ ] Click voice preview - should play audio
- [ ] Second preview of same voice should be instant (<100ms)
- [ ] CommandHistory should display past commands
- [ ] Clear history button should work

### API Testing

```bash
# Test voice list
curl http://localhost:5000/api/voice/list

# Test preview (first time - slow)
curl -X POST http://localhost:5000/api/voice/preview \
  -H "Content-Type: application/json" \
  -d '{"voice_id": "en-US-AriaNeural"}'

# Test preview (second time - fast, cached)
curl -X POST http://localhost:5000/api/voice/preview \
  -H "Content-Type: application/json" \
  -d '{"voice_id": "en-US-AriaNeural"}'

# Test cache stats
curl http://localhost:5000/api/voice/cache/stats

# Test rate limiting (run 12 times quickly)
for i in {1..12}; do
  curl -X POST http://localhost:5000/api/voice/preview \
    -H "Content-Type: application/json" \
    -d '{"voice_id": "en-US-AriaNeural"}' &
done
# Should see 429 errors after 10 requests
```

## Performance Validation

### Caching Performance

Expected results:
- First preview: 2-3 seconds
- Cached preview: <100ms (20-30x faster)
- Cache hit rate: >50% in production

### Rate Limiting

Expected results:
- 10 requests/minute allowed
- 11th request returns HTTP 429
- Frontend handles gracefully

### Component Performance

Expected results:
- VoiceInterface: 362 lines (down from 823)
- Main component re-renders: Minimal
- Sub-component isolation: Good

## Troubleshooting

### Test Failures

**"Backend server is not running"**
- Start server: `python -m ai_assistant.services.modern_web_backend`

**"404 Not Found on /api/voice/vad/detect"**
- voice_processing_api blueprint might not be registered
- Check modern_web_backend.py for registration

**"503 Service Unavailable"**
- Edge-TTS or dependencies not installed
- Run: `pip install edge-tts`

**Rate limiting test passes too easily**
- Requests might be too slow
- Try parallel requests with `&` in bash

### Performance Issues

**Cache not working**
- Check `/api/voice/cache/stats` shows hits
- Verify voice_id and text match exactly

**Previews still slow**
- First request always slow (normal)
- Check "cached": true in response
- Consider running prewarm_voice_cache()

## All 12 Optimizations Status

✅ P0.1: Blueprint registration  
✅ P0.2: Error handling  
✅ P0.3: Duplicate removal  
✅ P1.4: Component splitting  
✅ P1.5: Preview caching  
✅ P1.6: Async recognition  
✅ P2.7: VAD integration  
✅ P2.8: Noise reduction  
✅ P2.9: Rate limiting  
✅ P3.10: Silero VAD framework  
✅ P3.11: Voice cloning framework  
✅ P3.12: Diarization framework  

**Implementation Status: 100% Complete**
