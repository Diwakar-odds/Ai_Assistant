# 🎧 12: Audio Agent (`audio-001`)

## 📌 Overview
The **Audio Agent** performs high-fidelity audio engineering and speech processing. It synthesizes multi-chord procedural background music tracks (Lo-Fi, Ambient, Upbeat, Cinematic) using NumPy and the standard wave library, generates sound effects (SFX), performs noise reduction on noisy WAV files (`noisereduce` + spectral gating), performs Neural Text-to-Speech (TTS), and transcribes speech into text via Whisper.

* **Agent ID:** `audio-001`
* **Canonical Name:** Audio Agent
* **Category:** `audio`
* **Aliases:** `audio`, `audio_01`, `audio-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/audio/audio_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/audio/audio_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`music`, `song`, `melody`, `beat`, `lofi`, `sound effect`, `sfx`, `clean audio`, `remove noise`, `denoise`, `transcribe audio`, `synthesize`, `speech`, `audio track`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `generate_music` | `_generate_music(task)` | Synthesizes multi-chord procedural WAV background tracks (Lo-Fi, Ambient, Cinematic). | NumPy + `wave` |
| `generate_sfx` | `_generate_sfx(task)` | Creates retro chimes, alerts, laser swooshes, and UI sound effects procedurally. | Mathematical waveform synthesis |
| `clean_audio` | `_clean_audio(task)` | Reduces background noise and hums from speech recordings. | `noisereduce` / spectral gate |
| `text_to_speech` | `_text_to_speech(task)` | Synthesizes human-like voice audio files from text scripts. | `edge-tts` / `pyttsx3` / Kitten TTS |
| `transcribe_audio` | `_transcribe_audio(task)` | Transcribes spoken audio files into accurate text transcripts. | `faster-whisper` / `whisper` |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "genre": "lofi | ambient | upbeat | cinematic",
  "duration": 5.0,
  "sample_rate": 22050,
  "sfx_type": "chime | alert | laser | beep",
  "input_file": "D:/Projects/Ai_Assistant/data/noisy_recording.wav",
  "text": "Pulsar audio systems operating at peak fidelity.",
  "output_path": "D:/Projects/Ai_Assistant/outputs/bg_music.wav"
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/music_lofi_5s.wav",
    artifacts=["D:/Projects/Ai_Assistant/outputs/music_lofi_5s.wav"],
    data={
        "genre": "lofi",
        "duration": 5.0,
        "sample_rate": 22050,
        "output_path": "D:/Projects/Ai_Assistant/outputs/music_lofi_5s.wav",
        "message": "Generated lofi music track (5.0s, 22050Hz) at D:/Projects/Ai_Assistant/outputs/music_lofi_5s.wav"
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Zero External Dependencies for Music:** Procedural music and sound effects are computed using pure mathematical harmonics ($f(t) = A \sin(2\pi f t)$ with exponential decay envelope) via NumPy and standard Python libraries—meaning they generate 100% offline with zero cloud tokens.
* **Noise Reduction Fallback:** If `noisereduce` is not installed, the agent runs a native high-pass / low-pass amplitude attenuation filter rather than failing the task.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("audio-001")

task = Task(
    task_id="audio_music_01",
    description="Generate a 4-second ambient music track",
    params={"genre": "ambient", "duration": 4.0}
)
result = await agent.execute(task)
print(result.output_path)
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "audio-001",
  "description": "Clean audio recording noise",
  "params": {
    "input_file": "D:/Recordings/speech.wav"
  }
}
```
