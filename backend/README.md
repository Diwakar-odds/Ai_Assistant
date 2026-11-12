# ⚙️ PULSAR Backend Services & Architecture

## 📌 Overview
The **Pulsar Backend** is a high-performance Python application providing REST endpoints, Server-Sent Events (SSE) streaming, WebSocket telemetry, multi-agent dispatching, and hardware-accelerated local AI management.

* **Primary Runner:** [`backend/modern_web_backend.py`](file:///d:/Projects/Ai_Assistant/backend/modern_web_backend.py)
* **Root Orchestrator:** [`modern_web_backend.py`](file:///d:/Projects/Ai_Assistant/modern_web_backend.py)
* **CLI Entrypoint:** [`main.py`](file:///d:/Projects/Ai_Assistant/main.py)
* **Port:** `http://localhost:5000` (Default REST & WebSocket Gateway)

---

## 🏗️ Directory Layout

```text
backend/
├── modern_web_backend.py       # Main HTTP server & WebSocket event loop
├── routes/                     # Modular API Blueprints
│   ├── agent_routes.py         # Multi-Agent task dispatch & lifecycle (/api/agents/*)
│   ├── auth_routes.py          # PIN login, JWT tokens & User profile (/api/auth/*, /api/user/*)
│   ├── chain_routes.py         # Multi-agent Chain-of-Actions DAGs (/api/chain/*)
│   ├── chat_routes.py          # Conversational LLM & SSE streaming (/api/chat/*)
│   ├── common.py               # Shared helpers, JWT guards & rate limiters
│   ├── file_routes.py          # File upload & document processing (/api/files/*)
│   ├── learning_routes.py      # Memory & knowledge graph API (/api/learning/*)
│   ├── local_ai_routes.py      # Ollama & local model management (/api/local-ai/*)
│   ├── settings_routes.py      # Model selection & API keys (/api/settings/*)
│   ├── system_routes.py        # CPU, RAM & GPU telemetry (/api/system/*)
│   ├── taskbar_routes.py       # Live desktop taskbar analysis (/api/taskbar/*)
│   └── web_routes.py           # Selenium web browsing controller (/api/web/*)
├── logs/                       # Backend execution & telemetry logs
├── screenshots/                # Automated failure & visual audit screenshots
└── utils/                      # Low-level helpers & Windows UTF-8 bootstrap
```

---

## 🚀 Quickstart & Setup

### 1. Activate Environment
Ensure you have activated the root Python virtual environment:
```powershell
# In Windows PowerShell:
.\venv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r config/requirements/requirements.txt
```

### 3. Launch Backend Standalone
```powershell
python backend/modern_web_backend.py
```
* Or use the root launcher which runs both backend and frontend concurrently:
```powershell
python modern_web_backend.py
```

---

## 🔑 Key Environment Variables (`.env`)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ADMIN_PIN` | *Required* | 4-8 digit numeric PIN for authenticating UI sessions. |
| `ADMIN_PASSWORD` | `admin123` | Master password (change immediately in production). |
| `JWT_SECRET_KEY` | *Generated* | Cryptographic secret for signing JWT Bearer tokens. |
| `GEMINI_API_KEY` | - | Google Gemini AI Studio API key. |
| `OPENAI_API_KEY` | - | OpenAI API key for GPT-4o fallback. |
| `ENABLE_VOICE` | `true` | Initializes Vosk, Whisper, and TTS audio pipelines. |
| `ENABLE_MULTIMODAL` | `true` | Enables OCR and vision capture services. |
| `LAZY_INIT` | `true` | Defers heavy AI weights loading until first requested. |

---

## 🧪 Testing Backend Services
Run unit and integration test suites:
```powershell
pytest tests/ -v
```
To run route-specific tests:
```powershell
pytest tests/test_agent_api.py -v
```

---

## 📚 Related Documentation
* [14 Multi-Agent Cores Specification](file:///d:/Projects/Ai_Assistant/docs/agents/)
* [Subsystem Capabilities & Architecture](file:///d:/Projects/Ai_Assistant/docs/capabilities/)
* [API Reference](file:///d:/Projects/Ai_Assistant/docs/api/)
