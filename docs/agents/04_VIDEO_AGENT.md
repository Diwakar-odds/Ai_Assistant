# 🎬 04: Video Agent (`video-001`)

## 📌 Overview
The **Video Agent** is a multi-modal desktop and multimedia agent. It handles video file processing (trimming, clipping, audio stripping, subtitle generation), speech-to-text video transcription via `faster-whisper`, video thumbnail generation, and external desktop GUI video editor control (such as Adobe Premiere Pro, DaVinci Resolve, CapCut, or Filmora) backed by visual verification and workflow training.

* **Agent ID:** `video-001`
* **Canonical Name:** Video Agent
* **Category:** `video`
* **Aliases:** `video`, `video-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/video/video_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/video/video_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`video`, `movie`, `clip`, `trim`, `cut`, `transcribe`, `subtitle`, `caption`, `premiere`, `davinci`, `filmora`, `capcut`, `thumbnail`, `extract audio`, `control app`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `edit_video` / `create_video` | `_edit_video(task)` | Trims video clips, adjusts playback speeds, and cuts timestamps. | `moviepy` |
| `transcribe_video` | `_transcribe_video(task)` | Transcribes spoken audio within video files into timed text. | `faster-whisper` / `whisper` |
| `add_subtitles` | `_transcribe_video(task)` | Formats speech transcription into `.srt` / `.vtt` timed subtitle files. | Whisper Segment Timestamps |
| `extract_audio` | `_extract_audio(task)` | Strips video tracks to produce standalone high-quality `.mp3` / `.wav` audio. | `moviepy.audio` |
| `create_thumbnail` | `_create_thumbnail(task)` | Captures key frames at specific timestamps and generates video covers. | OpenCV (`cv2`) / Pillow |
| `control_external_app` | `_control_app(task)` | Automates external desktop video suites via GUI coordinates or hotkeys. | `AppControllerFactory` & `VisualVerifier` |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "input_file": "D:/Projects/Ai_Assistant/data/sample_video.mp4",
  "start_time": 10.5,
  "end_time": 45.0,
  "timestamp": 12.0,
  "app_name": "capcut | premiere | davinci | filmora",
  "action": "open | import_media | export | cut",
  "output_format": "mp4 | srt | mp3 | png"
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/thumbnail_video_12s.png",
    artifacts=["D:/Projects/Ai_Assistant/outputs/thumbnail_video_12s.png"],
    data={
        "timestamp": 12.0,
        "width": 1920,
        "height": 1080,
        "output_path": "D:/Projects/Ai_Assistant/outputs/thumbnail_video_12s.png",
        "message": "Thumbnail generated from video at 12.0s."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Lazy Module Loading:** Heavy multimedia packages (`moviepy`, `cv2`, `faster-whisper`) are loaded lazily upon first invocation to ensure instantaneous startup times for the AI Assistant.
* **Visual Verification Loop:** When controlling external desktop software, the agent invokes [`VisualVerifier`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/video/visual_verifier.py) to capture screen patches and verify that dialog boxes or timeline sliders actually moved before proceeding.
* **Whisper Fallback:** Attempts `faster-whisper` GPU/CPU CTranslate2 acceleration first; if unavailable, seamlessly falls back to standard OpenAI `whisper`.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("video-001")

task = Task(
    task_id="vid_thumb_01",
    description="Create a thumbnail from video at 15 seconds",
    params={
        "input_file": "D:/Videos/demo.mp4",
        "timestamp": 15.0
    }
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
  "agent_id": "video-001",
  "description": "Extract audio track from meeting recording",
  "params": {
    "input_file": "D:/Videos/meeting.mp4",
    "output_format": "mp3"
  }
}
```
