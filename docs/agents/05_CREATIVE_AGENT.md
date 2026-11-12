# 🎨 05: Creative Agent (`creative-001`)

## 📌 Overview
The **Creative Agent** is responsible for synthesizing visual and spoken multimedia assets. It programmatically generates graphic layouts, banners, social media thumbnails, art placeholders, and image transformations using Pillow, as well as voiceover audio files using `edge-tts`, `pyttsx3`, or procedural waveform synthesis.

* **Agent ID:** `creative-001`
* **Canonical Name:** Creative Agent
* **Category:** `creative`
* **Aliases:** `creative`, `creative_01`, `creative-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/creative/creative_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/creative/creative_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`image`, `art`, `picture`, `thumbnail`, `photo`, `logo`, `banner`, `poster`, `voiceover`, `narrate`, `tts`, `design`, `layout`, `illustration`.  
*(Note: Excludes data charts and database queries, which route to Data Analyst Agent).*

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `generate_image` / `create_art` | `_handle_image_generation(task)` | Creates styled PNG banners and graphics with gradients and centered typography. | Pillow (`PIL.Image`, `ImageDraw`) |
| `design_layout` | `_handle_image_generation(task)` | Produces card layouts, thumbnail compositions, and title slides with metadata. | Pillow Layout Engine |
| `image_editing` | `_handle_image_editing(task)` | Resizes, crops, rotates, adds borders, blurs, or converts images to grayscale. | Pillow Image Filters |
| `generate_voiceover` | `_handle_audio_generation(task)` | Generates speech narration audio files from text descriptions or script inputs. | `edge-tts` / `pyttsx3` / Synth WAV |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "prompt": "Cyberpunk Neon Assistant Banner",
  "text": "PULSAR AI: Autonomous Desktop Intelligence",
  "size": "1280x720",
  "background": "gradient | dark | #1e1e2e",
  "image_path": "D:/Projects/Ai_Assistant/data/input.png",
  "action": "resize | grayscale | crop | blur",
  "voice": "en-US-GuyNeural",
  "script": "Welcome to Pulsar. All 14 multi-agent cores are online."
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/banner_creative_1280x720.png",
    artifacts=["D:/Projects/Ai_Assistant/outputs/banner_creative_1280x720.png"],
    data={
        "output_path": "D:/Projects/Ai_Assistant/outputs/banner_creative_1280x720.png",
        "size": [1280, 720],
        "format": "PNG",
        "message": "Generated creative graphic banner (1280x720)."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Autonomous Font Selection:** The agent automatically scans the Windows system fonts directory (`C:\Windows\Fonts`) for clean TTF fonts (e.g., `segoeui.ttf`, `arial.ttf`, `calibri.ttf`), seamlessly falling back to `ImageFont.load_default()` if custom fonts are missing.
* **Three-Tier Voiceover Fallback:**
  1. High-fidelity Microsoft Edge TTS (`edge-tts`).
  2. Local SAPI5 offline speech synthesizer (`pyttsx3`).
  3. Pure procedural sine-wave audio tone generator (`wave` + `struct`) to ensure non-crashing output.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("creative-001")

task = Task(
    task_id="creative_banner_01",
    description="Generate a banner image with text 'Welcome to Pulsar'",
    params={"text": "Welcome to Pulsar", "size": "1920x1080"}
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
  "agent_id": "creative-001",
  "description": "Generate voiceover narration for tutorial intro",
  "params": {
    "script": "This tutorial will guide you through connecting external agents."
  }
}
```
