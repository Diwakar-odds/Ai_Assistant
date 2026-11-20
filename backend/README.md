# ⚙️ PULSAR Backend Services & Architecture

## 📌 Overview
The **Pulsar Backend** is a high-performance Python application providing REST endpoints, Server-Sent Events (SSE) streaming, WebSocket telemetry, multi-agent dispatching, local GGUF AI management, and backward-compatible service forwarders.

* **Primary Runner:** [`backend/modern_web_backend.py`](file:///d:/Projects/Ai_Assistant/backend/modern_web_backend.py)
* **Root Orchestrator:** [`web.py`](file:///d:/Projects/Ai_Assistant/web.py) (legacy alias: `modern_web_backend.py`)
* **Pulsar Headless Core:** [`pulsar/core/server.py`](file:///d:/Projects/Ai_Assistant/pulsar/core/server.py)
* **Default Port:** `http://localhost:5000` (REST & WebSocket Gateway)

---

## 🏗️ Directory Layout

```text
backend/
├── modern_web_backend.py       # Main HTTP server, Blueprint registry & WebSocket event loop
├── agent_brain.py              # Backward-compatible forwarder -> services/agent_brain.py
├── voice_service.py            # Backward-compatible forwarder -> services/voice_service.py
├── telemetry_dashboard.py       # Backward-compatible forwarder -> services/telemetry_dashboard.py
├── settings_manager.py         # Backward-compatible forwarder -> services/settings_manager.py
├── notification_monitor.py     # Backward-compatible forwarder -> services/notification_monitor.py
├── routes/                     # Modular API Blueprints
│   ├── agent_routes.py         # Multi-Agent task dispatch & lifecycle (/api/agents/*)
│   ├── auth_routes.py          # PIN login, JWT tokens & User profile (/api/auth/*, /api/user/*)
│   ├── chain_routes.py         # Multi-agent Chain-of-Actions DAGs (/api/chain/*)
│   ├── chat_routes.py          # Conversational LLM & SSE streaming (/api/chat/*)
│   ├── common.py               # Shared helpers, JWT guards & rate limiters
│   ├── file_routes.py          # File upload & document processing (/api/files/*)
│   ├── learning_routes.py      # Memory & knowledge graph API (/api/learning/*)
│   ├── local_ai_routes.py      # GGUF local model discovery & VRAM status (/api/local-ai/*)
│   ├── settings_routes.py      # Model selection & API keys (/api/settings/*)
│   ├── system_routes.py        # CPU, RAM, GPU & health telemetry (/api/system/*)
│   ├── taskbar_routes.py       # Live desktop taskbar analysis (/api/taskbar/*)
│   └── web_routes.py           # Selenium web browsing controller (/api/web/*)
├── services/                   # High-Level Business Logic Services
│   ├── agent_brain.py          # Central coordinator interfacing with core_ai
│   ├── app_integration_api.py  # External application integration bridge
│   ├── learning_api.py         # Knowledge graph and episodic memory query engine
│   ├── notification_monitor.py # Windows action center notification listener
│   ├── settings_manager.py     # Persistent settings serializer (%APPDATA%\PulsarAI\config\)
│   ├── telemetry_dashboard.py  # Real-time metrics aggregator
│   └── voice_service.py        # IPC forwarder to audio worker
├── templates/                  # Diagnostic web dashboards (companion.html)
└── utils/                      # Low-Level Utilities
    ├── chat_session_store.py   # Multi-session conversation persistence & export
    ├── tool_schemas.py         # OpenAI/Gemini compatible tool definitions
    └── logging_config.py       # Rotating log file handlers
```

---

## 🚀 Quickstart & Setup

### 1. Activate Environment
```powershell
.\venv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r config/requirements/requirements.txt
```

### 3. Launch Backend Standalone
```powershell
# Fast root launcher (starts backend + serves frontend)
python web.py

# Or launch backend directly:
python backend/modern_web_backend.py
```

---

## 🔑 Key Environment Variables (`.env`)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ADMIN_PIN` | *Required* | 4-8 digit numeric PIN for authenticating UI sessions. |
| `ADMIN_PASSWORD` | `admin123` | Master password (change immediately in production). |
| `JWT_SECRET_KEY` | *Auto-Generated* | Cryptographic secret for signing JWT Bearer tokens. |
| `GEMINI_API_KEY` | - | Google Gemini AI Studio API key. |
| `OPENAI_API_KEY` | - | OpenAI API key for GPT-4o fallback. |
| `ENABLE_VOICE` | `true` | Initializes Vosk, Faster-Whisper, and TTS audio pipelines. |
| `ENABLE_WEB_GROUNDING` | `true` | Enables real-time background search grounding. |
| `LAZY_INIT` | `true` | Defers heavy AI model loading until first requested. |
| `PULSAR_PORT` | `5000` | Backend REST/WebSocket listening port. |

---

## 🧪 Testing Backend Services

Run backend test suites:
```powershell
# Run all backend route and service tests
pytest tests/test_agent_api.py -v
pytest tests/test_chat_routes.py -v
pytest tests/test_system_routes.py -v
```

---

## 📚 Related Documentation
* [14 Multi-Agent Cores Specification](file:///d:/Projects/Ai_Assistant/docs/agents/)
* [Subsystem Capabilities & Architecture](file:///d:/Projects/Ai_Assistant/docs/capabilities/)
* [API Reference](file:///d:/Projects/Ai_Assistant/docs/api/)
* [Enterprise Zero-Hardcoded Storage](file:///d:/Projects/Ai_Assistant/docs/architecture/STORAGE_AND_PATHS_ARCHITECTURE.md)
