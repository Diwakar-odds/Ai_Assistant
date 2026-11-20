# 🌌 PULSAR Standalone Windows Companion Engine (`pulsar/`)

Welcome to the **Pulsar Standalone Subsystem** documentation. This directory implements the production-grade, dual-mode Windows desktop architecture (Paradigm B) that separates the GUI host process from the heavy headless AI & audio runtime.

---

## 📌 Architectural Blueprint: Strict Paradigm B Separation

Pulsar is split into two completely isolated operating processes managed under the Windows OS kernel:

```
+-----------------------------------------------------------------------------------+
|                               Windows 10 / 11 Kernel                              |
+-----------------------------------------------------------------------------------+
       |                                                               |
       v                                                               v
+---------------------------------------+       +-----------------------------------+
|       Native Host Process (GUI)       |       |   Headless Core Subprocess (AI)   |
|   `Pulsar.exe` or `python -m pulsar`  |       |   `Pulsar.exe --core-subprocess`  |
+---------------------------------------+       +-----------------------------------+
| - PySide6 / QtWebEngine Dashboard     |       | - FastAPI / Uvicorn Server (5000) |
| - Floating 4D Particle Orb Overlay    |       | - GGUF CPU/GPU Intent Routing     |
|   (WS_EX_LAYERED, Click-Through)      |  IPC  | - Offline Faster-Whisper STT      |
| - Screen-Share Stealth Mode Exclusion | <===> | - EdgeTTS & KittenTTS Synthesis   |
|   (SetWindowDisplayAffinity)          | HTTP/ | - Windows Audio Ducking (pycaw)   |
| - System Tray Menu & Notification     | Token | - Watchdog Process Supervisor     |
| - Win32 Job Object Process Guard      |       | - Tiered Web Intelligence Subsys  |
| - Global Mutex Single-Instance Lock   |       | - Swarm Meta-Planner & DAG Memory |
+---------------------------------------+       +-----------------------------------+
```

### 🔒 The Strict Invariant Rule
1. **Host Mode Invariant**: The Host process **NEVER** imports `torch`, `llama_cpp`, `faster_whisper`, `sounddevice`, or backend ML libraries. This guarantees instantaneous application startup (<1 second), low RAM footprint (<60 MB idle), and 100% UI fluidity.
2. **Core Mode Invariant**: The Core subprocess **NEVER** imports `PySide6`, `QtWebEngine`, or GUI toolkits. It runs strictly headless with zero display dependency.

---

## 📂 Subsystem Directory Structure

```text
pulsar/
├── __init__.py                 # Subsystem version and package markers
├── frozen_entry.py             # PyInstaller Paradigm B dual-mode binary entrypoint
├── logging_setup.py            # Rotating file logging configured for %APPDATA%\Pulsar\logs
├── audio/                      # Zero-GUI Headless Audio Processing
│   ├── __init__.py
│   ├── mic_stream.py           # PyAudio stream capture, ring buffer, device selection
│   └── worker.py               # Speech recognition worker, VAD, wake-word matching
├── core/                       # Headless Core Backend Server
│   ├── __init__.py
│   ├── __main__.py             # Entrypoint for --core-subprocess execution
│   ├── orb_state.py            # Shared thread-safe 4D Orb state machine
│   ├── routes_health.py        # Token-authenticated REST health & telemetry routes
│   ├── server.py               # FastAPI/Uvicorn server orchestration
│   ├── watchdog.py             # Process watchdog terminating Core on parent death
│   └── static/
│       └── orb.html            # WebGL / Three.js 4D particle orb interactive canvas
└── host/                       # Native PySide6 Host & Windows Shell Supervisor
    ├── __init__.py
    ├── __main__.py             # Entrypoint for Host GUI & System Tray launch
    ├── console_ui.py           # Terminal status HUD & live colored logs
    ├── core_supervisor.py      # Subprocess lifecycle manager & token generator
    ├── dashboard_window.py     # Main application dashboard window (PySide6 WebEngine)
    ├── job_object.py           # Win32 Kernel Job Object ensuring zero orphan processes
    ├── orb_window.py           # Layered, transparent, click-through 4D floating orb
    ├── tray_app.py             # Windows Notification Area (System Tray) menu
    └── windows_integration.py  # Win32 screen-share stealth, autostart, & shortcuts
```

---

## 🚀 How to Run & Developer Commands

### 1. Development Mode (Python virtualenv)
```powershell
# Activate venv
.\venv\Scripts\activate

# Launch full desktop companion (Host + Core Supervisor + Tray + Orb)
python -m pulsar.host

# Launch Host minimized to tray with floating 4D Orb active
python -m pulsar.host --tray

# Launch Headless Core independently (for API/integration testing)
python -m pulsar.core
```

### 2. Standalone Release Mode (`Pulsar.exe`)
When packaged with `scripts/build_distributable_release.py`:
```powershell
# Standard launch: Opens Dashboard + System Tray + 4D Floating Orb
Pulsar.exe

# Stealth background launch: Starts minimized in System Tray
Pulsar.exe --tray

# Core-only subprocess (internal use by host supervisor)
Pulsar.exe --core-subprocess --parent-pid <PID> --port 5000 --token <SECRET>
```

---

## 🛠️ Key Technical Modules Deep Dive

### 1. Win32 Kernel Job Object (`pulsar/host/job_object.py`)
In legacy applications, killing a GUI window often leaves background AI processes (like heavy llama-cpp or whisper models) running invisibly in Task Manager, consuming gigabytes of RAM.
* **Solution**: `pulsar/host/job_object.py` registers the child Core subprocess inside a **Win32 Kernel Job Object** configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
* **Guarantee**: If the Host crashes, is closed, or terminated in Task Manager, Windows OS kernel **automatically and immediately terminates the Core subprocess**. No orphaned processes can ever survive.

### 2. Screen-Share Stealth Mode Exclusion (`pulsar/host/windows_integration.py`)
When you are on Microsoft Teams, Zoom, Discord, or OBS screen shares, you might not want the floating 4D Orb or confidential AI widgets to be visible to other attendees.
* **Implementation**: Uses the Windows Win32 API `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`.
* **Outcome**: The Orb and companion overlay are completely invisible to screen recording and screen sharing tools, while remaining fully visible and interactive on your physical monitor.

### 3. Floating 4D Particle Orb Overlay (`pulsar/host/orb_window.py` & `pulsar/core/static/orb.html`)
* **Layered Windowing**: Uses `WS_EX_LAYERED` and `WS_EX_TRANSPARENT` styles with a transparent WebEngine profile to render a fluid, hardware-accelerated Three.js 4D particle mesh.
* **State Synchronization**: The Orb reflects real-time operational states via `pulsar/core/orb_state.py`:
  - `idle`: Gentle pulsing blue particle cloud.
  - `listening`: Expanded responsive green waveform reacting to microphone audio volume.
  - `thinking`: Swirling golden galaxy state during LLM generation.
  - `speaking`: Dynamic magenta harmonic oscillation synced with TTS audio output.
  - `error`: Warning red flare.
* **Interactive Controls**: Right-click to toggle listening, double-click to summon the main dashboard, drag to place anywhere on multi-monitor setups.

### 4. Zero-GUI Audio Worker (`pulsar/audio/worker.py` & `mic_stream.py`)
* Captures 16kHz 16-bit mono PCM stream with PyAudio via an asynchronous ring buffer.
* Employs WebRTC Voice Activity Detection (VAD) to ignore background silence.
* Implements offline wake-word detector ("Hey Pulsar", "Pulsar", "Assistant").
* Coordinates with `core_ai/voice/audio_ducking.py` to duck Windows system sound before speaking.

### 5. Single-Instance Mutex Protection (`pulsar/host/__main__.py`)
Uses `CreateMutexW(None, True, "Local\\PulsarAIAssistant_Host_Mutex")` to prevent duplicate processes from launching and fighting over audio devices or port 5000. If an instance is already running, subsequent launches bring the existing dashboard window to the foreground.

---

## 🩺 Health & Diagnostic Endpoints

The headless core exposes token-gated management routes on port 5000:

| Method | Endpoint | Query / Header | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | `token` or `X-Pulsar-Token` | Returns system status, uptime, and engine state |
| `GET` | `/orb` | None | Serves the Three.js 4D particle canvas |
| `GET` | `/api/orb/state` | None | Returns active orb state, audio energy level, and latency |
| `POST` | `/api/orb/state` | `token`, `{"state": "listening"}` | Manually forces orb state transition |
| `POST` | `/shutdown` | `token` | Gracefully closes core server and frees model weights |

---

## 🔍 Developer Troubleshooting & Breakpoint Checklist

1. **Port 5000 Conflict**:
   - *Symptom*: Core fails to start with `OSError: [Errno 10048] address already in use`.
   - *Remedy*: Check for leftover Python processes via `Get-Process python` or set `PULSAR_PORT=5050` in `.env`.
2. **Microphone Device Unavailable**:
   - *Symptom*: Audio worker logs `PyAudio input stream overflow / device busy`.
   - *Remedy*: Verify microphone permissions in Windows Settings -> Privacy -> Microphone. `mic_stream.py` falls back to default OS recording device.
3. **Invalid Token Error**:
   - *Symptom*: HTTP 403 Forbidden on health endpoints.
   - *Remedy*: The Host generates a cryptographic token at boot and passes it via `--token` argument. In manual curl tests, pass the matching token.
