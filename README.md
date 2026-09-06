<div align="center">
  <h1>🌌 PULSAR</h1>
  <p><strong>Native OS Automation via Agentic LLM</strong></p>
  <p><em>An Offline Multi-Modal LLM Assistant for Windows</em></p>
</div>

---

## Table of Contents
1. [Project Vision & Key Features](#1-project-vision--key-features)
2. [Quickstart Guide](#2-quickstart-guide)
3. [Environment Variables Reference](#3-environment-variables-reference)
4. [Security Model](#4-security-model)
5. [API Overview](#5-api-overview)
6. [Monorepo Architecture Deep Dive](#6-monorepo-architecture-deep-dive)
7. [The 27 Advanced Learning Systems](#7-the-27-advanced-learning-systems)
8. [Complete API Reference Guide](#8-complete-api-reference-guide)
9. [Automated Codebase Documentation](#9-automated-codebase-documentation)
10. [Desktop Integration & Automation](#10-desktop-integration--automation)
11. [Comprehensive Setup & Installation](#11-comprehensive-setup--installation)
12. [Executable Packaging Guide](#12-executable-packaging-guide)
13. [Troubleshooting & Known Issues](#13-troubleshooting--known-issues)

---

## 1. Project Vision & Key Features

PULSAR is not just another chatbot. It is a **native Operating System Automation Suite** designed to act as your personal AI desktop agent. Unlike traditional web-based LLMs that are sandboxed in a browser, PULSAR connects directly to your Windows OS to observe, learn, and execute complex workflows on your behalf.

### Key Capabilities (Why PULSAR?)
- **Native Windows Automation:** PULSAR can open apps, click buttons, type text, and manage your files directly.
- **100% Offline & Private:** Powered by a massive 2.5 million line custom fine-tuning dataset, it runs entirely on local models.
- **GGUF CPU-Inference Architecture:** We utilize a custom fine-tuned, 4-bit quantized Llama 3.1 8B Instruct model (Q4_K_M GGUF format) running natively via `llama-cpp-python` to process and classify user intents seamlessly without a GPU.
- **Multi-Modal Intelligence:** Features advanced computer vision (to read your screen) and voice integration (Whisper/TTS) so you can speak to it naturally.
- **Continuous Learning:** Built with 27 distinct machine learning paradigms (including Active Learning and Meta Learning) that adapt to your personal habits and slang (like Hinglish) over time.
- **Agentic Execution:** It breaks down complex goals into sub-tasks and uses multi-agent negotiation to find the best way to execute them.

PULSAR features over 700 specialized Python modules, 27 distinct machine learning paradigms, and a beautiful React frontend.

### Project JARVIS Upgrades (Phase 1 & 2 Complete)
Recent integrations have massive upgraded the assistant's autonomy and personality:
- **Audio-Based Emotion Tracking**: Calculates the intensity of your voice stream to guess if you are frustrated or calm before reading the text transcript.
- **Context-Switching Watcher**: Actively tracks your OS window states and prepares proactive suggestions if you suddenly switch contexts (e.g. from coding to browsing).
- **Proactive Diagnostics**: Scans for low disk space, expired backups, and API keys.
- **Trust-Scaling Personality Engine**: Seamlessly transitions from a formal, robotic AI (Low Trust) to a highly sarcastic companion who drops custom catchphrases (High Trust).
- **Continuous Dashboard**: Real-time React dashboard visualizing Self-Healing Engine logs and User DNA trust scores.
- **Zero-Dependency Long-Term Memory (RAG)**: A custom-built Retrieval-Augmented Generation system using SQLite `FTS5` full-text search to persist and recall past conversations with lightning speed and zero extra RAM footprint.
- **Optimized Voice Loop**: Supercharged real-time voice inference using `faster-whisper` and dynamic chunking for instantaneous transcription.

---

## 2. Quickstart Guide

> **Note**: PULSAR currently natively supports Windows.

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) (for running local LLMs)
- [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Add to your System PATH)
- C++ Build Tools (Required for compiling dependencies)

### Setup & Run
1. **Clone & Setup Environment**
   ```bash
   git clone <repo-url>
   cd Ai_Assistant
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   Create a `.env` file in the root directory (see Section 3 for reference).

3. **Start the Backend**
   ```bash
   python backend/modern_web_backend.py
   ```

4. **Start the Frontend**
   ```bash
   cd frontend/web-app
   npm install
   npm run dev
   ```

---

## 3. Environment Variables Reference

Create a `.env` file in the root directory.

| Variable | Requirement | Description |
|---|---|---|
| `OPENAI_API_KEY` | Optional | For falling back to OpenAI models if local LLM is unavailable. |
| `GOOGLE_GEMINI_API_KEY` | Optional | For utilizing Gemini models for visual and complex reasoning. |
| `ELEVEN_LABS_API_KEY` | Optional | For premium Text-To-Speech (TTS). |
| `PIN_HASH` | **Required** | Hashed PIN for authenticating critical endpoints and desktop controls. |
| `SECURITY_KEY` | **Required** | Secret key for encrypting local data. |
| `TESSERACT_PATH` | Optional | Path to Tesseract executable (if not in System PATH). |

---

## 4. Security Model

PULSAR takes security and privacy seriously:
- **Authentication**: High-risk actions (e.g., executing desktop commands) require PIN-based authentication.
- **Authorization**: Implements Role-Based Access Control (RBAC).
- **Data Privacy**: Local LLMs guarantee zero data leakage. When external APIs are used, extensive data anonymization and PII redaction occur.
- **Encryption**: Sensitive logs and user profiles are stored encrypted using the defined `SECURITY_KEY`.

---

## 5. API Overview

PULSAR exposes several REST endpoints for frontend integration. Detailed route information can be found in the API Reference below.

- **Authentication**: Most `/api/system/*` and `/api/app/*` routes require authentication via headers.
- **Data Exchange**: All endpoints accept and return `application/json` unless otherwise specified (like WebSocket events).

---

## 6. Monorepo Architecture Deep Dive

```text
Ai_Assistant/
├── backend/                   # Flask API Gateway & WebSockets
│   ├── blueprints/            # 11 Modular API Routes (Voice, Apps, Web, etc.)
│   └── modern_web_backend.py  # Main Server Entrypoint
├── core_ai/                   # The 27 Learning Systems & OS Automations
│   └── src/ai_assistant/
│       ├── agents/            # Multi-Agent Negotiators
│       ├── ai/                # Core ML Paradigms (Active Learning, Meta Learning, etc.)
│       ├── automation/        # Visual Automation & OS Scripts
│       └── voice/             # STT, TTS, and Speaker Diarization
├── desktop/                   # Native Windows Packaging
│   ├── build/                 # PyInstaller Temp Artifacts
│   ├── app_launcher.py        # PyWebView Native Window Renderer
│   └── build_exe.bat          # High-Optimization Exe Bundler
├── frontend/                  # React + Vite User Interface
│   └── web-app/
│       ├── src/components/    # Beautiful Tailwind/Lucide Components
│       └── package.json       # React Dependencies
├── scripts/                   # 70+ Development & Diagnostic Utilities
├── shared/                    # Centralized State & Storage
│   ├── config/                # App usage metrics & Discovery JSONs
│   └── data/                  # Neo4j/SQLite memory graphs & Training JSONLs
└── tests/                     # Massive Pytest Suite (Unit, E2E, Integration)
```

- **`frontend/`**: React 18, Vite, TypeScript, Tailwind-inspired CSS.
- **`backend/`**: Flask API Gateway, WebSockets, 11 Blueprints.
- **`core_ai/`**: The Brain (Learning systems, Automations, Voice).
- **`desktop/`**: Native wrappers using `pywebview` and `PyInstaller`.
- **`shared/`**: Databases (`memory.db`), user metrics, config files.
- **`scripts/`**: 70+ Development and diagnostic tools.
- **`tests/`**: Unit, E2E, Integration, and Feature tests.

---

## 🧠 3. The 27 Advanced Learning Systems
This project utilizes 27 distinct programmatic learning paradigms:

1. **Active Learning**:  Proactively queries the user.
2. **Advanced Feedback Learning**:  Reinforcement Learning from Human Feedback.
3. **Auto Learning Router**:  Meta-classifier for routing tasks.
4. **Contrastive Learning**:  Differentiates similar OS commands.
5. **Enhanced User Preference Learning**:  Time-decaying weighted cache.
6. **Federated Learning**:  Secure local weight deltas (LoRA).
7. **Meta Learning**:  Optimizes internal prompts.
8. **Multimodal Emotion Learning**:  Fuses audio sentiment with text.
9. **Self-Supervised Log Learning**:  Ingests background OS logs.
10. **Online Learning Trainer**:  Retrains local models.
11. **Contextual Memory Fading**:  Ebbinghaus forgetting curve.
12. **Semantic Knowledge Graphing**:  Extracts Triples for Neo4j/SQLite.
13. **Intent Drift Compensation**:  Adapts to user slang (Hinglish).
14. **Visual Taskbar Analysis**:  Scrapes desktop icon bounding boxes.
15. **Voice Accent Adaptation**:  Adjusts Whisper parameters.
16. **API Latency Optimization**:  Epsilon-Greedy bandit algorithm.
17. **Error State Recovery**:  Code Healing via traceback parsing.
18. **Cross-Session Continuity**:  Serializes conversation graphs.
19. **Behavioral Scheduling**:  Pre-warms applications via K-Means.
20. **Secure Data Pruning**:  Scrubs passwords/PII via NER.
21. **Automated App Discovery**:  Scans Windows Registry.
22. **Sentiment Analysis Tracking**:  30-day VADER sentiment tracking.
23. **Codebase Understanding**:  AST parsing of its own Monorepo.
24. **Multi-Agent Negotiation**:  Sub-agents debate execution plans.
25. **Hardware Constraint Learning**:  Monitors CPU/RAM via psutil.
26. **Custom Dataset Generation**:  Mathematically permutates prompts.
27. **Zero-Shot Transfer Application**:  Applies web scraping logic to docs.

---

## 📡 4. Complete API Reference Guide

### Extracted Flask Routes from `modern_web_backend.py`

| Route | Methods | Description |
|-------|---------|-------------|
| `/api/context` | GET | Backend API Endpoint |
| `/api/user/preferences` | GET | Backend API Endpoint |
| `/api/user/profile/status` | GET | Backend API Endpoint |
| `/api/user/profile/setup` | POST | Backend API Endpoint |
| `/api/user/preferences` | POST | Backend API Endpoint |
| `/api/status/initialization` | GET | Backend API Endpoint |
| `/` | GET | Backend API Endpoint |
| `/<path:path>` | GET | Backend API Endpoint |
| `/enhanced-chat` | GET | Backend API Endpoint |
| `/download` | GET | Backend API Endpoint |
| `/download/windows-app` | GET | Backend API Endpoint |
| `/test` | GET | Backend API Endpoint |
| `/api/auth/register` | POST | Backend API Endpoint |
| `/api/auth/login` | POST | Backend API Endpoint |
| `/api/auth/verify` | GET | Backend API Endpoint |
| `/api/status` | GET | Backend API Endpoint |
| `/api/learning/stats` | GET | Backend API Endpoint |
| `/dashboard` | GET | Backend API Endpoint |
| `/api/learning/dashboard` | GET | Backend API Endpoint |
| `/api/learning/databases` | GET | Backend API Endpoint |
| `/api/learning/database/<db_name>/<table_name>` | GET | Backend API Endpoint |
| `/api/learning/memory/search` | GET | Backend API Endpoint |
| `/api/learning/documentation` | GET | Backend API Endpoint |
| `/api/logs/recent` | GET | Backend API Endpoint |
| `/api/learning/stats/all` | GET | Backend API Endpoint |
| `/api/learning/smart-commands/predict` | POST | Backend API Endpoint |
| `/api/learning/context/generate` | POST | Backend API Endpoint |
| `/api/learning/workflow/recommend` | POST | Backend API Endpoint |
| `/api/learning/anomaly/detect` | POST | Backend API Endpoint |
| `/api/learning/causal/query` | POST | Backend API Endpoint |
| `/api/learning/knowledge-graph/query` | POST | Backend API Endpoint |
| `/api/learning/adaptive-voice/log` | POST | Backend API Endpoint |
| `/api/learning/rl/action` | POST | Backend API Endpoint |
| `/api/learning/system/<system_name>/stats` | GET | Backend API Endpoint |
| `/api/local-ai/status` | GET | Backend API Endpoint |
| `/api/chat` | POST | Backend API Endpoint |
| `/api/command` | POST | Backend API Endpoint |
| `/api/startup/sequence` | GET | Backend API Endpoint |
| `/api/startup/diagnostics` | GET | Backend API Endpoint |
| `/api/startup/briefing` | GET | Backend API Endpoint |
| `/api/enhanced/chat` | POST | Backend API Endpoint |
| `/api/enhanced/stats` | GET | Backend API Endpoint |
| `/api/enhanced/cache/clear` | POST | Backend API Endpoint |
| `/api/usage-analysis` | GET | Backend API Endpoint |
| `/api/usage-analysis/export` | POST | Backend API Endpoint |
| `/api/automation/verify` | POST | Backend API Endpoint |
| `/api/chat/stream` | POST | Backend API Endpoint |
| `/api/chat/sessions/<session_id>` | GET | Backend API Endpoint |
| `/api/chat/sessions/<session_id>` | DELETE | Backend API Endpoint |
| `/api/system/stats` | GET | Backend API Endpoint |
| `/api/weather` | GET | Backend API Endpoint |
| `/api/features` | GET | Backend API Endpoint |
| `/api/chat/context` | POST | Backend API Endpoint |
| `/api/chat/suggestions` | GET | Backend API Endpoint |
| `/api/multimodal/analyze` | POST | Backend API Endpoint |
| `/api/screen/analyze` | POST | Backend API Endpoint |
| `/api/automation/workflows` | GET | Backend API Endpoint |
| `/api/automation/execute` | POST | Backend API Endpoint |
| `/api/memory/save` | POST | Backend API Endpoint |
| `/api/memory/search` | GET | Backend API Endpoint |
| `/api/language/detect` | POST | Backend API Endpoint |
| `/api/language/translate` | POST | Backend API Endpoint |
| `/api/apps` | GET | Backend API Endpoint |
| `/api/apps/refresh` | POST | Backend API Endpoint |
| `/api/apps/launch` | POST | Backend API Endpoint |
| `/api/spotify/status` | GET | Backend API Endpoint |
| `/api/spotify/control` | POST | Backend API Endpoint |
| `/api/visual/question` | POST | Backend API Endpoint |
| `/api/activity` | GET | Backend API Endpoint |
| `/api/voice/history` | GET | Backend API Endpoint |
| `/api/voice/status` | GET | Backend API Endpoint |
| `/api/voice/start` | POST | Backend API Endpoint |
| `/api/voice/stop` | POST | Backend API Endpoint |
| `/api/voice/speak` | POST | Backend API Endpoint |
| `/api/voice/list` | GET | Backend API Endpoint |
| `/api/voice/preview` | POST | Backend API Endpoint |
| `/api/voice/process` | POST | Backend API Endpoint |
| `/api/language/hinglish` | POST | Backend API Endpoint |
| `/api/language/preference` | POST | Backend API Endpoint |
| `/api/language/preference` | GET | Backend API Endpoint |
| `/api/error/log` | POST | Backend API Endpoint |
| `/api/settings/save` | POST | Backend API Endpoint |
| `/api/settings/load` | GET | Backend API Endpoint |
| `/api/settings/all` | GET | Backend API Endpoint |
| `/api/settings/update` | POST | Backend API Endpoint |
| `/api/settings/reset` | POST | Backend API Endpoint |
| `/api/settings/export` | GET | Backend API Endpoint |
| `/api/settings/import` | POST | Backend API Endpoint |
| `/api/models/available` | GET | Backend API Endpoint |
| `/api/models/preference` | GET | Backend API Endpoint |
| `/api/models/preference` | POST | Backend API Endpoint |
| `/api/models/stats` | GET | Backend API Endpoint |
| `/api/models/compare` | POST | Backend API Endpoint |
| `/api/models/providers` | GET | Backend API Endpoint |
| `/api/local_ai/status` | GET | Backend API Endpoint |
| `/api/local_ai/chat` | POST | Backend API Endpoint |
| `/api/local_ai/reset` | POST | Backend API Endpoint |
| `/api/local_ai/stats` | GET | Backend API Endpoint |
| `/api/local_ai/load_model` | POST | Backend API Endpoint |
| `/api/local_ai/unload` | POST | Backend API Endpoint |
| `/api/files/organize` | POST | Backend API Endpoint |
| `/api/files/find-duplicates` | POST | Backend API Endpoint |
| `/api/files/search` | POST | Backend API Endpoint |
| `/api/files/batch-rename` | POST | Backend API Endpoint |
| `/api/files/analyze-directory` | POST | Backend API Endpoint |
| `/api/ocr/check-dependencies` | GET | Backend API Endpoint |
| `/api/ocr/extract-image` | POST | Backend API Endpoint |
| `/api/ocr/extract-pdf` | POST | Backend API Endpoint |
| `/api/ocr/analyze-document` | POST | Backend API Endpoint |
| `/api/ocr/extract-info` | POST | Backend API Endpoint |
| `/api/web/weather` | GET | Backend API Endpoint |
| `/api/web/news` | GET | Backend API Endpoint |
| `/api/web/stock` | GET | Backend API Endpoint |
| `/api/web/crypto` | GET | Backend API Endpoint |
| `/api/web/scrape` | POST | Backend API Endpoint |
| `/api/web/trending` | GET | Backend API Endpoint |
| `/api/taskbar/detect` | GET | Backend API Endpoint |
| `/api/taskbar/capabilities` | GET | Backend API Endpoint |
| `/api/taskbar/find-app` | POST | Backend API Endpoint |
| `/api/taskbar/running-apps` | GET | Backend API Endpoint |
| `/api/chains/create` | POST | Backend API Endpoint |
| `/api/chains/<chain_id>/resume` | POST | Backend API Endpoint |
| `/api/chains/<chain_id>` | GET | Backend API Endpoint |
| `/api/chains/history` | GET | Backend API Endpoint |
| `/unified` | GET | Backend API Endpoint |
| `/unified-dashboard` | GET | Backend API Endpoint |

---

## 📚 5. Automated Codebase Documentation

Below is the auto-generated AST documentation of all major Python modules in the system. This provides a deep dive into the inner workings of the AI.


### File: `core_ai\src\ai_assistant\agents\base_agent.py`
- **Class `BaseAgent`**: Base class for all AI agents
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\dispatcher.py`
- **Class `Dispatcher`**: Dispatches natural language commands to appropriate workflows.
  - **Function `__init__()`**: Signature: (self)
  - **Function `handle()`**: Process a natural language user input and dispatch to appropriate workflow.

### File: `core_ai\src\ai_assistant\agents\loader.py`
- **Class `AgentLoader`**: Helper to load agents into the registry using Lazy Loading
  - **Function `register_agent_definitions()`**: Register agent definitions (metadata + lazy factory) without instantiating
  - **Function `_load_productivity()`**: Signature: ()
  - **Function `_load_research()`**: Signature: ()
  - **Function `_load_writer()`**: Signature: ()
  - **Function `_load_video()`**: Signature: ()
  - **Function `_load_creative()`**: Signature: ()
  - **Function `_load_data()`**: Signature: ()
  - **Function `_load_database()`**: Signature: ()
  - **Function `_load_communication()`**: Signature: ()
  - **Function `_load_web()`**: Signature: ()
  - **Function `_load_student()`**: Signature: ()
  - **Function `_load_file()`**: Signature: ()
  - **Function `_load_audio()`**: Signature: ()
  - **Function `_load_deep_research()`**: Signature: ()
  - **Function `_load_autonomous()`**: Signature: ()

### File: `core_ai\src\ai_assistant\agents\models.py`
- **Class `AgentStatus`**: Core component.
- **Class `Task`**: Core component.
- **Class `TaskResult`**: Core component.
- **Class `VerificationResult`**: Core component.
- **Class `ProofreadResult`**: Core component.

### File: `core_ai\src\ai_assistant\agents\registry.py`
- **Class `AgentMetadata`**: Metadata for a lazy-loaded agent
- **Class `AgentRegistry`**: Manages all available agents and their capabilities with lazy loading support
  - **Function `__init__()`**: Signature: (self)
  - **Function `register_agent()`**: Register an already instantiated agent (legacy support)
  - **Function `register_agent_definition()`**: Register an agent definition for lazy loading
  - **Function `_register_capabilities()`**: Helper to map capabilities
  - **Function `get_agent()`**: Get agent by ID, instantiating if necessary
  - **Function `get_all_agents()`**: Get all currently ACTIVE agents
  - **Function `get_all_metadata()`**: Get metadata for ALL agents (active and standby)
  - **Function `find_agents_by_capability()`**: Find agent IDs that have a specific capability

### File: `core_ai\src\ai_assistant\agents\audio\audio_agent.py`
- **Class `AudioAgent`**: Handles specific audio tasks (Music, SFX, Audio Processing). Distinct from CreativeAgent (Speech) and VideoAgent (Editing).
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\communication\communication_agent.py`
- **Class `CommunicationAgent`**: Handles communications (Email, Messaging, Social).
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\core\autonomous_agent.py`
- **Class `AutonomousAgent`**: Replicates the 'hermes-agent' autonomous learning loop: 1. Observes conversations 2. Routes them to the LearningDataRouter for persistence 3. Propo...
  - **Function `__init__()`**: Signature: (self, agent_id, config)
  - **Function `passive_observe()`**: Can be called by the main chat loop to constantly feed data  into the agent without explicitly treating it as a task.

### File: `core_ai\src\ai_assistant\agents\creative\creative_agent.py`
- **Class `CreativeAgent`**: Agent responsible for generating creative assets: - Images (Thumbnails, B-Roll, Art) - Audio (Voiceovers, Sound Effects)
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\file\file_manager_agent.py`
- **Class `FileManagerAgent`**: Handles file organization and operations.
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\productivity\productivity_agent.py`
- **Class `ProductivityAgent`**: Handles office productivity tasks: Word, Excel, PowerPoint
  - **Function `__init__()`**: Signature: (self, agent_id, config)
  - **Function `_identify_task_type()`**: Signature: (self, task)

### File: `core_ai\src\ai_assistant\agents\research\deep_research_agent.py`
- **Class `DeepResearchAgent`**: Replicates the 'last30days-skill' workflow: 1. Topic Analysis 2. Parallel Web Search 3. LLM Synthesis
  - **Function `__init__()`**: Signature: (self, agent_id, config)
  - **Function `_generate_search_queries()`**: Use simple heuristics or LLM to generate targeted search queries
  - **Function `_scrape_text()`**: Helper to scrape text from a URL
  - **Function `_synthesize_results()`**: Use LLM to generate a final markdown brief

### File: `core_ai\src\ai_assistant\agents\research\research_agent.py`
- **Class `ResearchAgent`**: Handles web research, searching, and simple scraping.
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\student\student_agent.py`
- **Class `StudentAgent`**: Handles educational tasks (Math, Quizzes, Study).
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\video\gui_controller.py`
- **Class `AppControlInterface`**: Abstract interface for controlling external applications
- **Class `BaseGUIController`**: Generic GUI Controller using PyAutoGUI
- **Class `PremiereProController`**: Profile for Adobe Premiere Pro. Maps high-level actions to keyboard shortcuts.
- **Class `KnowledgeBaseController`**: Controller that loads keymaps dynamically from the Knowledge Base.
- **Class `AppControllerFactory`**: Core component.
  - **Function `focus_window()`**: Signature: (self, app_name)
  - **Function `send_hotkey()`**: Signature: (self, keys)
  - **Function `type_text()`**: Signature: (self, text)
  - **Function `click_at()`**: Signature: (self, x, y)
  - **Function `__init__()`**: Signature: (self, app_key)
  - **Function `_load_libs()`**: Signature: (self)
  - **Function `focus_window()`**: Signature: (self, app_name)
  - **Function `send_hotkey()`**: Signature: (self, keys)
  - **Function `type_text()`**: Signature: (self, text)
  - **Function `click_at()`**: Signature: (self, x, y)
  - **Function `execute_action()`**: Signature: (self, action_name)
  - **Function `perform_sequence()`**: Perform a common sequence of actions
  - **Function `__init__()`**: Signature: (self, app_key)
  - **Function `_load_kb()`**: Signature: (self)
  - **Function `execute_action()`**: Signature: (self, action_name)
  - **Function `get_controller()`**: Signature: (app_name)

### File: `core_ai\src\ai_assistant\agents\video\training_mode.py`
- **Class `TrainingMode`**: Allows 'training' the agent by defining workflows or recording actions. Future: Hook into keyboard hooks to record real-time (requires complex perm...
  - **Function `__init__()`**: Signature: (self, profile_name)
  - **Function `add_action()`**: Add an action to the current training session
  - **Function `save_workflow()`**: Save the trained workflow to disk
  - **Function `load_workflow()`**: Signature: (filename)

### File: `core_ai\src\ai_assistant\agents\video\video_agent.py`
- **Class `VideoAgent`**: Handles video editing, creation, and transcription.
  - **Function `__init__()`**: Signature: (self, agent_id, config)
  - **Function `verifier()`**: Signature: (self)
  - **Function `_load_moviepy()`**: Signature: (self)
  - **Function `_load_whisper()`**: Signature: (self)

### File: `core_ai\src\ai_assistant\agents\video\visual_verifier.py`
- **Class `VisualVerifier`**: Provides computer vision capabilities to the agent.
  - **Function `__init__()`**: Signature: (self)
  - **Function `_ensure_libs()`**: Signature: (self)
  - **Function `capture_screen()`**: Capture the screen or a region. Region is (left, top, width, height). Returns an OpenCV BGR image.
  - **Function `find_template()`**: Find a template image on the screen. Returns (x, y, w, h) of the match, or None.
  - **Function `verify_state()`**: High-level verification.  In a real scenario, this would look up template paths from the Knowledge Base. For now, it checks generic templates.

### File: `core_ai\src\ai_assistant\agents\web\web_agent.py`
- **Class `WebAgent`**: Handles general web automation (Forms, Interaction, Dynamic Scraping).
  - **Function `__init__()`**: Signature: (self, agent_id, config)

### File: `core_ai\src\ai_assistant\agents\writer\writer_agent.py`
- **Class `WriterAgent`**: Handles content generation, writing, and summarization using LLMs.
  - **Function `__init__()`**: Signature: (self, agent_id, config)
  - **Function `_generate_mock_content()`**: Generate plausible mock content for testing

### File: `core_ai\src\ai_assistant\ai\active_learning.py`
- **Class `ActiveLearner`**: Active learning for sample-efficient model training
  - **Function `example_usage()`**: Demonstrate active learning
  - **Function `__init__()`**: Signature: (self, db_path, uncertainty_threshold)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_queue()`**: Load pending labeling queue
  - **Function `add_unlabeled_sample()`**: Add unlabeled sample to pool
  - **Function `uncertainty_sampling()`**: Calculate prediction uncertainty (least confident) Lower = more uncertain
  - **Function `query_by_committee()`**: Calculate disagreement among committee members Higher = more disagreement = more informative
  - **Function `expected_model_change()`**: Estimate how much model would change if we label this sample Uses gradient magnitude as proxy
  - **Function `select_samples_to_label()`**: Select most informative samples for labeling
  - **Function `_add_to_queue()`**: Add sample to labeling queue
  - **Function `get_next_to_label()`**: Get next samples to label from queue
  - **Function `provide_label()`**: Provide label for a sample
  - **Function `train()`**: Train committee models on labeled data
  - **Function `get_labeling_efficiency()`**: Calculate labeling efficiency metrics Shows how much accuracy we get per label
  - **Function `get_stats()`**: Get active learning statistics

### File: `core_ai\src\ai_assistant\ai\adaptive_prompts.py`
- **Class `PromptTemplate`**: Prompt template with metadata
- **Class `PromptExperiment`**: A/B test experiment for prompts
- **Class `PromptOptimizer`**: Optimizes prompts through reinforcement learning and A/B testing
  - **Function `example_usage()`**: Demonstrate prompt optimization
  - **Function `render()`**: Render template with variables
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_templates()`**: Load existing templates
  - **Function `_init_default_templates()`**: Initialize default prompt templates
  - **Function `_generate_id()`**: Generate unique ID for template
  - **Function `save_template()`**: Save template to database
  - **Function `get_best_template()`**: Get best performing template for category
  - **Function `render_prompt()`**: Render prompt from template
  - **Function `_enrich_context()`**: Add contextual information to prompt variables
  - **Function `record_feedback()`**: Record feedback for prompt performance
  - **Function `create_ab_experiment()`**: Create A/B test experiment
  - **Function `record_experiment_result()`**: Record A/B test result
  - **Function `get_optimization_insights()`**: Get insights for prompt optimization
  - **Function `score()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\adaptive_voice.py`
- **Class `AdaptiveVoiceRecognition`**: Application-level adaptive voice recognition Learns user's voice patterns and improves accuracy
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_adaptations()`**: Load user-specific adaptations
  - **Function `log_recognition()`**: Log voice recognition result
  - **Function `apply_correction()`**: Apply user correction to improve model
  - **Function `_learn_from_correction()`**: Learn patterns from user corrections
  - **Function `get_vocabulary_boost()`**: Get user's frequently used words for recognition boost
  - **Function `suggest_corrections()`**: Suggest potential corrections based on user patterns
  - **Function `get_confidence_adjustment()`**: Adjust confidence based on user vocabulary
  - **Function `analyze_accent_patterns()`**: Analyze user's accent patterns
  - **Function `get_stats()`**: Get statistics

### File: `core_ai\src\ai_assistant\ai\advanced_chat_system.py`
- **Class `ResponseMode`**: Response generation modes.
- **Class `TokenCounter`**: Token counter for various models.
- **Class `ToolSchema`**: Schema for tool/function calling.
- **Class `AdvancedChatSystem`**: Advanced chat system with streaming, context management, and tool calling.
  - **Function `create_sample_tools()`**: Create sample tools for demonstration.
  - **Function `__init__()`**: Initialize advanced chat system.
  - **Function `count()`**: Count tokens in text.
  - **Function `count_messages()`**: Count tokens in a message list.
  - **Function `fits_in_context()`**: Check if message list + new message fits in context window.
  - **Function `trim_history()`**: Trim message history to fit within token limit.
  - **Function `to_dict()`**: Convert to dictionary format for API.
  - **Function `__init__()`**: Initialize advanced chat system.
  - **Function `_init_database()`**: Initialize SQLite database for chat persistence.
  - **Function `add_system_prompt()`**: Add or update system prompt.
  - **Function `add_message()`**: Add a message to conversation history.
  - **Function `get_conversation_history()`**: Get conversation history, optionally trimmed to fit token limit.
  - **Function `register_tool()`**: Register a tool/function for tool calling.
  - **Function `get_tool_schemas()`**: Get tool schemas in API format.
  - **Function `handle_tool_call()`**: Execute a tool call and return result.
  - **Function `stream_response()`**: Stream a response token-by-token.
  - **Function `get_response()`**: Get a response from the chat system.
  - **Function `regenerate_response()`**: Regenerate the last response (retry with same input).
  - **Function `get_alternatives()`**: Get alternative responses for the last user message.
  - **Function `edit_message()`**: Edit a message in the conversation.
  - **Function `search_history()`**: Search conversation history for relevant messages.
  - **Function `export_conversation()`**: Export conversation in specified format.
  - **Function `get_stats()`**: Get conversation statistics.
  - **Function `clear_history()`**: Clear conversation history (keeping system message if present).
  - **Function `_generate_cache_key()`**: Generate cache key for a message.
  - **Function `save_to_db()`**: Save conversation to database.
  - **Function `load_from_db()`**: Load conversation from database.

### File: `core_ai\src\ai_assistant\ai\advanced_feedback_learning.py`
- **Class `FeedbackType`**: Types of feedback
- **Class `ResponseQuality`**: Quality levels for responses
- **Class `FeedbackEntry`**: Single feedback entry
- **Class `PreferencePair`**: Pair of responses for preference learning
- **Class `ResponseMetrics`**: Metrics for evaluating response quality
- **Class `RewardModel`**: Reward model trained on human preferences Uses implicit reward from preference comparisons
- **Class `DirectPreferenceOptimizer`**: Direct Preference Optimization (DPO) implementation Bypasses explicit reward modeling for more stable training
- **Class `FeedbackCollector`**: Collects and manages user feedback
- **Class `AdaptiveLearningEngine`**: Main engine coordinating all learning components Implements continuous learning with concept drift detection
- **Class `ConceptDriftDetector`**: Detects concept drift in user preferences using ADWIN algorithm (Adaptive Windowing)
  - **Function `example_usage()`**: Demonstrate usage of the feedback learning system
  - **Function `to_dict()`**: Signature: (self)
  - **Function `overall_score()`**: Compute weighted overall score
  - **Function `__init__()`**: Signature: (self, delta)
  - **Function `_initialize_weights()`**: Initialize feature weights for reward calculation
  - **Function `extract_features()`**: Extract features from prompt-response pair
  - **Function `compute_reward()`**: Compute reward score for a response Uses learned weights from feedback
  - **Function `update_from_preference()`**: Update reward model based on preference comparison Uses gradient-based update similar to DPO
  - **Function `get_preference_accuracy()`**: Calculate how well the reward model predicts preferences
  - **Function `__init__()`**: Signature: (self, delta)
  - **Function `compute_dpo_loss()`**: Compute DPO loss as per Rafailov et al., 2023
  - **Function `add_preference()`**: Add preference pair to training data
  - **Function `get_training_signal()`**: Get signal for updating language model policy
  - **Function `_extract_patterns()`**: Extract common patterns from responses
  - **Function `__init__()`**: Signature: (self, delta)
  - **Function `_init_database()`**: Initialize feedback database
  - **Function `record_feedback()`**: Record user feedback
  - **Function `record_preference_pair()`**: Record preference comparison
  - **Function `get_recent_feedback()`**: Get recent unprocessed feedback
  - **Function `mark_processed()`**: Mark feedback as processed
  - **Function `__init__()`**: Signature: (self, delta)
  - **Function `record_interaction()`**: Record an interaction for potential feedback
  - **Function `process_thumbs_feedback()`**: Process thumbs up/down feedback
  - **Function `process_preference_comparison()`**: Process A/B preference comparison
  - **Function `collect_feedback()`**: Collect feedback (wrapper for compatibility)
  - **Function `collect_preference_pair()`**: Collect preference pair (wrapper for compatibility)
  - **Function `get_learning_stats()`**: Get learning system statistics
  - **Function `_get_performance_trend()`**: Analyze performance trend
  - **Function `_background_learning()`**: Background thread for continuous learning
  - **Function `_update_from_feedback()`**: Update models from feedback item
  - **Function `shutdown()`**: Cleanup resources
  - **Function `__init__()`**: Signature: (self, delta)
  - **Function `check_drift()`**: Check if concept drift occurred
  - **Function `is_drift_detected()`**: Check if drift was recently detected

### File: `core_ai\src\ai_assistant\ai\anomaly_detection.py`
- **Class `AnomalyDetector`**: Detects anomalous behavior patterns
  - **Function `example_usage()`**: Demonstrate anomaly detection
  - **Function `__init__()`**: Signature: (self, db_path, contamination)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_baseline()`**: Load baseline statistics
  - **Function `_extract_command_features()`**: Extract features from command event
  - **Function `_extract_voice_features()`**: Extract features from voice event
  - **Function `detect_anomaly()`**: Detect if event is anomalous
  - **Function `_detect_statistical()`**: Statistical anomaly detection
  - **Function `_get_feature_names()`**: Get feature names for event type
  - **Function `_analyze_anomaly()`**: Analyze why event is anomalous
  - **Function `_record_event()`**: Record event in database
  - **Function `_generate_alert()`**: Generate security alert
  - **Function `_update_baseline()`**: Update baseline statistics
  - **Function `_extract_system_features()`**: Extract system performance features
  - **Function `train()`**: Train anomaly detection model
  - **Function `get_alerts()`**: Get recent alerts
  - **Function `acknowledge_alert()`**: Mark alert as acknowledged
  - **Function `get_stats()`**: Get anomaly detection statistics

### File: `core_ai\src\ai_assistant\ai\auto_learning_router.py`
- **Class `LearningDataRouter`**: Automatically routes new conversation data to appropriate learning systems Integrate this into your chat interface
  - **Function `integrate_with_chat_system()`**: Example of how to integrate the router into BOTH chat and voice systems SAME LEARNING, SAME MEMORY for both interfaces
  - **Function `__init__()`**: Signature: (self)
  - **Function `_initialize_systems()`**: Initialize all learning systems
  - **Function `route_conversation()`**: Route a conversation to appropriate learning systems WORKS FOR BOTH CHAT AND VOICE - Same learning, same memory
  - **Function `_route_to_behavior_clustering()`**: Route to behavior clustering system
  - **Function `_route_to_conversation_clustering()`**: Route to conversation clustering
  - **Function `_route_to_command_sequences()`**: Route to command sequence learner
  - **Function `_route_to_command_predictor()`**: Route to command success predictor
  - **Function `_route_to_context_generator()`**: Route to context-aware response generator
  - **Function `_route_to_smart_commands()`**: Route to smart command predictor
  - **Function `_route_to_knowledge_graph()`**: Route to knowledge graph - extract facts
  - **Function `_route_to_query_cache()`**: Route to query cache
  - **Function `get_routing_stats()`**: Get statistics about data routing

### File: `core_ai\src\ai_assistant\ai\behavior_clustering.py`
- **Class `BehaviorClusterer`**: Clusters user behavior patterns
  - **Function `example_usage()`**: Demonstrate behavior clustering
  - **Function `__init__()`**: Signature: (self, db_path, n_clusters)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_clusters()`**: Load cluster profiles
  - **Function `extract_session_features()`**: Extract features from session
  - **Function `add_session()`**: Add session to database
  - **Function `cluster_sessions()`**: Cluster all sessions using K-Means
  - **Function `_analyze_clusters()`**: Analyze cluster characteristics
  - **Function `_determine_cluster_type()`**: Determine cluster type from characteristics
  - **Function `classify_user()`**: Classify user based on their session history
  - **Function `get_cluster_insights()`**: Get insights about all clusters
  - **Function `get_stats()`**: Get clustering statistics

### File: `core_ai\src\ai_assistant\ai\causal_inference.py`
- **Class `CausalInference`**: Causal inference for understanding cause-effect
  - **Function `example_usage()`**: Demonstrate causal inference
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_causal_graph()`**: Load causal graph from database
  - **Function `add_causal_edge()`**: Add causal edge to graph
  - **Function `learn_causal_structure()`**: Learn causal structure from observational data Uses correlation + temporal ordering as proxy for causation
  - **Function `get_parents()`**: Get direct causes of variable
  - **Function `get_children()`**: Get direct effects of variable
  - **Function `get_ancestors()`**: Get all ancestors (transitive causes)
  - **Function `get_descendants()`**: Get all descendants (transitive effects)
  - **Function `backdoor_adjustment()`**: Find variables to adjust for (backdoor criterion) To estimate causal effect of treatment on outcome
  - **Function `estimate_causal_effect()`**: Estimate causal effect of treatment on outcome Using backdoor adjustment
  - **Function `do_intervention()`**: Simulate intervention (do-calculus) Predict effects of setting variable to value
  - **Function `counterfactual()`**: Counterfactual reasoning: what would happen if...?
  - **Function `get_stats()`**: Get causal inference statistics

### File: `core_ai\src\ai_assistant\ai\command_predictor.py`
- **Class `CommandSuccessPredictor`**: Predicts command success probability using ML
  - **Function `example_usage()`**: Demonstrate command success prediction
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_stats()`**: Load historical statistics
  - **Function `_serialize_context()`**: Serialize context to string
  - **Function `_extract_features()`**: Extract features for ML model
  - **Function `predict_success()`**: Predict if command will succeed
  - **Function `_predict_rule_based()`**: Rule-based prediction fallback
  - **Function `_generate_warnings()`**: Generate warnings based on prediction
  - **Function `record_execution()`**: Record command execution result
  - **Function `train()`**: Train ML model on historical data
  - **Function `get_stats()`**: Get prediction statistics

### File: `core_ai\src\ai_assistant\ai\command_sequences.py`
- **Class `CommandMarkovChain`**: Predicts next command using Markov chain models
  - **Function `example_usage()`**: Demonstrate command sequence prediction
  - **Function `__init__()`**: Signature: (self, db_path, order, context_aware)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_transitions()`**: Load transition matrix from database
  - **Function `_serialize_context()`**: Serialize context dict to string key
  - **Function `_get_state()`**: Create state from command history
  - **Function `record_command()`**: Record a command in the sequence
  - **Function `predict_next()`**: Predict next likely commands
  - **Function `get_common_sequences()`**: Find common command sequences
  - **Function `validate_prediction()`**: Record prediction accuracy
  - **Function `get_accuracy_stats()`**: Get prediction accuracy statistics
  - **Function `get_stats()`**: Get command sequence statistics (alias for get_accuracy_stats)
  - **Function `clear_old_data()`**: Remove old command sequences

### File: `core_ai\src\ai_assistant\ai\context_aware_response.py`
- **Class `ContextAwareResponseGenerator`**: Application-level context-aware response generation Generates intelligent responses based on conversation context
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_templates()`**: Load response templates
  - **Function `update_context()`**: Update conversation context
  - **Function `generate_response()`**: Generate context-aware response
  - **Function `_extract_intent()`**: Extract user intent from message
  - **Function `_get_conversation_context()`**: Get current conversation context
  - **Function `_generate_contextual_response()`**: Generate response with context awareness
  - **Function `_log_conversation()`**: Log conversation to database
  - **Function `learn_from_feedback()`**: Learn from user feedback on responses
  - **Function `_analyze_feedback_patterns()`**: Analyze patterns in user feedback
  - **Function `get_personalization_suggestions()`**: Get personalization suggestions based on conversation history
  - **Function `get_stats()`**: Get statistics

### File: `core_ai\src\ai_assistant\ai\contrastive_learning.py`
- **Class `ContrastiveLearner`**: Contrastive learning for better embeddings
  - **Function `example_usage()`**: Demonstrate contrastive learning
  - **Function `__init__()`**: Signature: (self, db_path, embedding_dim, temperature)
  - **Function `_init_database()`**: Initialize database
  - **Function `generate_pairs()`**: Generate contrastive pairs (anchor, positive, negative)
  - **Function `nt_xent_loss()`**: NT-Xent (Normalized Temperature-scaled Cross Entropy) Loss Used in SimCLR
  - **Function `triplet_loss()`**: Triplet loss: ||anchor - positive||^2 - ||anchor - negative||^2 + margin
  - **Function `train_batch()`**: Train on batch of contrastive pairs
  - **Function `train_epoch()`**: Train one epoch on samples
  - **Function `encode()`**: Encode features to embeddings
  - **Function `save_embedding()`**: Save embedding to database
  - **Function `find_similar()`**: Find similar samples by embedding
  - **Function `evaluate_embedding_quality()`**: Evaluate embedding quality using retrieval metrics
  - **Function `get_stats()`**: Get learning statistics

### File: `core_ai\src\ai_assistant\ai\conversational_ai.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\ai\conversational_ai_commands.py`
  - **Function `_try_execute_command()`**: Try to execute actionable commands and return result.
  - **Function `_execute_open_command()`**: Execute open application commands.
  - **Function `_execute_close_command()`**: Execute close application commands.
  - **Function `_execute_search_command()`**: Execute Google search commands.
  - **Function `_execute_play_command()`**: Execute play music commands.
  - **Function `_execute_create_document()`**: Execute document creation commands.
  - **Function `_execute_volume_command()`**: Execute volume control commands.
  - **Function `_execute_settings_command()`**: Execute system settings commands.

### File: `core_ai\src\ai_assistant\ai\conversation_clustering.py`
- **Class `ConversationClusterer`**: Clusters conversations by topics
  - **Function `example_usage()`**: Demonstrate conversation clustering
  - **Function `__init__()`**: Signature: (self, db_path, n_clusters, n_topics)
  - **Function `_init_database()`**: Initialize database
  - **Function `preprocess_text()`**: Clean and normalize text
  - **Function `add_conversation()`**: Add conversation to database
  - **Function `cluster_conversations()`**: Cluster conversations using TF-IDF + K-Means
  - **Function `_analyze_clusters()`**: Analyze cluster topics
  - **Function `_extract_keywords()`**: Extract top keywords from texts
  - **Function `_generate_cluster_name()`**: Generate readable cluster name from keywords
  - **Function `discover_topics()`**: Discover latent topics using LDA
  - **Function `find_similar_conversations()`**: Find conversations similar to query
  - **Function `_find_similar_fallback()`**: Fallback similarity using keyword overlap
  - **Function `get_cluster_summary()`**: Get summary of a cluster
  - **Function `get_cluster_conversations()`**: Get conversations in a cluster
  - **Function `get_stats()`**: Get clustering statistics

### File: `core_ai\src\ai_assistant\ai\domain_embeddings.py`
- **Class `DomainExample`**: Training example for domain adaptation
- **Class `DomainAdapter`**: Adapter network for domain-specific fine-tuning
- **Class `DomainAdaptedEmbeddings`**: Domain-adapted embeddings system Fine-tunes pre-trained embeddings for specific domains
  - **Function `__init__()`**: Signature: (self, base_model, adapter_dim, db_path)
  - **Function `forward()`**: Adapter forward pass
  - **Function `__init__()`**: Signature: (self, base_model, adapter_dim, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `register_domain()`**: Register a new domain
  - **Function `add_domain_example()`**: Add training example for domain adaptation
  - **Function `get_base_embedding()`**: Get base embedding from pre-trained model
  - **Function `get_adapted_embedding()`**: Get domain-adapted embedding
  - **Function `train_adapter()`**: Train adapter on domain examples
  - **Function `compute_domain_similarity()`**: Compute similarity between text and domain
  - **Function `detect_domain()`**: Detect most likely domain for text
  - **Function `get_stats()`**: Get statistics

### File: `core_ai\src\ai_assistant\ai\enhanced_learning.py`
- **Class `Skill`**: Represents a learned skill
- **Class `BehaviorPattern`**: Represents a learned behavior pattern
- **Class `KnowledgeNode`**: Node in the personal knowledge graph
- **Class `EnhancedLearningSystem`**: Main learning system coordinating all learning components
- **Class `BehavioralLearner`**: Learns from user behavior patterns
- **Class `SkillAcquisitionManager`**: Manages skill learning and development
- **Class `PredictiveActionEngine`**: Predicts likely user actions based on context
- **Class `PersonalKnowledgeGraph`**: Manages personal knowledge graph and relationships
  - **Function `main()`**: Example usage of the Enhanced Learning System
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `init_database()`**: Initialize the learning database
  - **Function `learn_from_interaction()`**: Learn from user interactions
  - **Function `get_predictions()`**: Get predictions for current context
  - **Function `get_skill_recommendations()`**: Get recommendations for skills to develop
  - **Function `get_knowledge_insights()`**: Get insights from knowledge graph
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `record_behavior()`**: Record a behavior instance
  - **Function `_generate_pattern_id()`**: Generate a unique pattern ID from context and action
  - **Function `get_behavior_patterns()`**: Get learned behavior patterns above confidence threshold
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `update_skill_usage()`**: Update skill usage statistics
  - **Function `get_skills_by_category()`**: Get skills, optionally filtered by category
  - **Function `get_skill_recommendations()`**: Get recommendations for skills to develop
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `predict_actions()`**: Predict likely actions for current context
  - **Function `_calculate_context_similarity()`**: Calculate similarity between current context and historical patterns
  - **Function `update_predictions()`**: Update prediction accuracy
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `load_graph()`**: Load knowledge graph from database
  - **Function `add_knowledge_node()`**: Add a new knowledge node
  - **Function `add_relationship()`**: Add a relationship between nodes
  - **Function `update_from_interaction()`**: Update knowledge graph from interaction
  - **Function `find_related_concepts()`**: Find concepts related to given concept
  - **Function `generate_insights()`**: Generate insights from the knowledge graph
  - **Function `visualize_graph()`**: Create a visualization of the knowledge graph

### File: `core_ai\src\ai_assistant\ai\explainability.py`
- **Class `ExplainabilityEngine`**: Provides interpretable explanations for predictions
  - **Function `example_usage()`**: Demonstrate explainability
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `set_feature_names()`**: Set feature names for interpretability
  - **Function `compute_feature_importance()`**: Compute feature importance scores (SHAP-style)
  - **Function `_permutation_importance()`**: Compute permutation importance
  - **Function `generate_counterfactual()`**: Generate counterfactual: minimal changes to flip prediction
  - **Function `find_similar_examples()`**: Find similar past examples (case-based reasoning)
  - **Function `generate_natural_language_explanation()`**: Generate human-readable explanation
  - **Function `explain_prediction()`**: Generate comprehensive explanation for a prediction
  - **Function `get_feature_importance_summary()`**: Get aggregate feature importance across all predictions
  - **Function `get_stats()`**: Get explainability statistics

### File: `core_ai\src\ai_assistant\ai\federated_learning.py`
- **Class `ClientUpdate`**: Update from a federated learning client
- **Class `FederatedRound`**: Single round of federated learning
- **Class `FederatedClient`**: Client in federated learning system Trains on local data without sharing raw data
- **Class `FederatedServer`**: Central server coordinating federated learning Aggregates client updates without accessing raw data
- **Class `SecureAggregation`**: Secure aggregation for differential privacy Adds noise to protect individual client contributions
  - **Function `example_federated_learning()`**: Example of federated learning with multiple clients
- **Class `FederatedModel`**: Core component.
  - **Function `__init__()`**: Signature: (self, noise_scale, clipping_norm)
  - **Function `set_model_parameters()`**: Update local model with global parameters
  - **Function `train_local_model()`**: Train model on local data
  - **Function `_simple_train()`**: Simplified training for fallback
  - **Function `_empty_update()`**: Return empty update when no data
  - **Function `add_local_data()`**: Add more data to client's local dataset
  - **Function `__init__()`**: Signature: (self, noise_scale, clipping_norm)
  - **Function `_init_database()`**: Initialize database for federated learning
  - **Function `register_client()`**: Register a new client
  - **Function `get_global_parameters()`**: Get current global model parameters
  - **Function `federated_averaging()`**: FedAvg: Aggregate client updates weighted by number of samples
  - **Function `federated_round()`**: Execute one round of federated learning
  - **Function `_compute_convergence_delta()`**: Compute parameter change between rounds
  - **Function `_save_client_update()`**: Save client update to database
  - **Function `_save_round()`**: Save round summary to database
  - **Function `get_stats()`**: Get federated learning statistics
  - **Function `__init__()`**: Signature: (self, noise_scale, clipping_norm)
  - **Function `clip_update()`**: Clip update to bounded norm
  - **Function `add_noise()`**: Add Gaussian noise for differential privacy
  - **Function `secure_aggregate()`**: Securely aggregate updates with differential privacy
  - **Function `__init__()`**: Signature: (self, noise_scale, clipping_norm)
  - **Function `forward()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\full_rl_system.py`
- **Class `Experience`**: Single experience tuple for RL
- **Class `Episode`**: Complete episode trajectory
- **Class `PPOAgent`**: Proximal Policy Optimization agent State-of-the-art policy gradient method with clipped objective
- **Class `A3CWorker`**: Asynchronous Advantage Actor-Critic Worker For parallel training across multiple environments
- **Class `RLEnvironmentWrapper`**: Wrapper for converting assistant tasks into RL environments Maps commands/queries to states and actions
  - **Function `train_ppo_agent()`**: Train PPO agent on environment
- **Class `ActorCriticNetwork`**: Core component.
  - **Function `__init__()`**: Signature: (self, state_dim, action_dim)
  - **Function `_init_database()`**: Initialize SQLite database for experience storage
  - **Function `select_action()`**: Select action using current policy Returns: (action, log_prob, state_value)
  - **Function `store_transition()`**: Store experience in memory
  - **Function `compute_returns()`**: Compute discounted returns
  - **Function `update()`**: Update policy using PPO algorithm
  - **Function `save_episode()`**: Save episode to database
  - **Function `get_stats()`**: Get agent statistics
  - **Function `__init__()`**: Signature: (self, state_dim, action_dim)
  - **Function `sync_with_global()`**: Synchronize local network with global network
  - **Function `compute_gradient()`**: Compute gradients from trajectory
  - **Function `__init__()`**: Signature: (self, state_dim, action_dim)
  - **Function `reset()`**: Reset environment to initial state
  - **Function `step()`**: Take action in environment Returns: (next_state, reward, done, info)
  - **Function `encode_command()`**: Encode text command into state vector
  - **Function `decode_action()`**: Decode action to command
  - **Function `__init__()`**: Signature: (self, state_dim, action_dim)
  - **Function `forward()`**: Signature: ()
  - **Function `act()`**: Signature: ()
  - **Function `evaluate()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\graph_neural_networks.py`
- **Class `GraphNeuralNetwork`**: Graph Neural Network system for knowledge graph reasoning
- **Class `GraphConvLayer`**: Core component.
- **Class `GraphAttentionLayer`**: Core component.
- **Class `GNNModel`**: Core component.
  - **Function `__init__()`**: Signature: (self, node_feature_dim, hidden_dim, output_dim, use_attention, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `add_node()`**: Add node to graph
  - **Function `add_edge()`**: Add edge to graph
  - **Function `get_adjacency_matrix()`**: Get adjacency matrix and node list
  - **Function `get_feature_matrix()`**: Get node feature matrix
  - **Function `train()`**: Train GNN model
  - **Function `get_node_embedding()`**: Get learned embedding for a node
  - **Function `predict_link()`**: Predict likelihood of link between two nodes
  - **Function `find_similar_nodes()`**: Find most similar nodes based on embeddings
  - **Function `get_stats()`**: Get GNN statistics
  - **Function `__init__()`**: Signature: (self, node_feature_dim, hidden_dim, output_dim, use_attention, db_path)
  - **Function `forward()`**: Signature: ()
  - **Function `__init__()`**: Signature: (self, node_feature_dim, hidden_dim, output_dim, use_attention, db_path)
  - **Function `forward()`**: Signature: ()
  - **Function `_prepare_attentional_mechanism_input()`**: Signature: ()
  - **Function `__init__()`**: Signature: (self, node_feature_dim, hidden_dim, output_dim, use_attention, db_path)
  - **Function `forward()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\historical_rag.py`
- **Class `HistoricalRAG`**: Retrieval-Augmented Generation using historical interactions
  - **Function `example_usage()`**: Demonstrate historical RAG
  - **Function `__init__()`**: Signature: (self, db_path, model_name, embedding_dim)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_index()`**: Load existing interactions into FAISS index
  - **Function `add_interaction()`**: Add an interaction to the RAG database
  - **Function `retrieve_similar()`**: Retrieve similar past interactions
  - **Function `_retrieve_fallback()`**: Fallback retrieval using SQL LIKE
  - **Function `_record_retrieval()`**: Record retrieval statistics
  - **Function `augment_prompt()`**: Augment prompt with relevant past examples
  - **Function `update_feedback()`**: Update success score based on user feedback
  - **Function `get_stats()`**: Get RAG statistics

### File: `core_ai\src\ai_assistant\ai\intelligent_responder.py`
- **Class `IntelligentResponder`**: Generates context-aware, mood-sensitive responses
  - **Function `get_responder()`**: Get global responder instance
  - **Function `generate_intelligent_response()`**: Main function to generate intelligent response
  - **Function `__init__()`**: Signature: (self)
  - **Function `analyze_input()`**: Analyze user input for intent, mood, urgency, and context
  - **Function `_detect_intent()`**: Detect primary intent from user input
  - **Function `_detect_mood()`**: Detect user's emotional state
  - **Function `_extract_keywords()`**: Extract important keywords
  - **Function `_detect_urgency()`**: Detect urgency level 1-5
  - **Function `generate_response()`**: Generate appropriate response based on analysis
  - **Function `_greeting_response()`**: Generate greeting response
  - **Function `_appreciation_response()`**: Respond to thanks/appreciation
  - **Function `_complaint_response()`**: Respond to complaints/problems
  - **Function `_question_response()`**: Acknowledge questions
  - **Function `_command_acknowledgment()`**: Acknowledge commands
  - **Function `_default_response()`**: Default fallback response

### File: `core_ai\src\ai_assistant\ai\intent_classification.py`
- **Class `Intent`**: Intent classification result
- **Class `Entity`**: Named entity
- **Class `IntentClassifier`**: Intent classification using semantic similarity Learns from user corrections and adaptsto personal vocabulary
- **Class `NamedEntityRecognizer`**: Named Entity Recognition for extracting structured information Learns user-specific entities (custom app names, contact nicknames, etc.)
  - **Function `example_usage()`**: Demonstrate intent classification and NER
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_initialize_intents()`**: Initialize intent categories with examples
  - **Function `_init_database()`**: Initialize database for custom entities
  - **Function `_load_user_patterns()`**: Load learned user patterns
  - **Function `_precompute_embeddings()`**: Precompute embeddings for all intent examples
  - **Function `classify()`**: Classify user intent
  - **Function `classify_intent()`**: Wrapper for compatibility - returns tuple of (intent, confidence, entities)
  - **Function `_classify_with_transformers()`**: Classify using sentence transformers
  - **Function `_classify_with_keywords()`**: Fallback keyword-based classification
  - **Function `_extract_entities()`**: Extract named entities from text
  - **Function `correct_intent()`**: Learn from user correction
  - **Function `add_user_vocabulary()`**: Learn user's personal vocabulary
  - **Function `get_learning_stats()`**: Get learning statistics
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_patterns()`**: Initialize regex patterns for entity extraction
  - **Function `_init_database()`**: Initialize database for custom entities
  - **Function `_load_custom_entities()`**: Load user-defined entities
  - **Function `extract_entities()`**: Extract all entities from text
  - **Function `_remove_overlaps()`**: Remove overlapping entities, keeping highest confidence
  - **Function `add_custom_entity()`**: Add custom entity to knowledge base

### File: `core_ai\src\ai_assistant\ai\intent_recognizer.py`
- **Class `IntentRecognizer`**: Recognizes user intent from natural language commands. Handles English, Hindi, and Hinglish without requiring LLM training.
  - **Function `__init__()`**: Signature: (self)
  - **Function `normalize_text()`**: Normalize text by removing special characters and extra spaces.
  - **Function `extract_intent()`**: Extract intent from command. Returns: (intent_type, context_dict)
  - **Function `extract_app_name()`**: Extract app name from command, handling various formats.
  - **Function `normalize_app_name()`**: Normalize app name to canonical form using fuzzy matching. Handles misspellings, spaces, and variations.
  - **Function `find_app_in_text()`**: Find any known app name in the text.
  - **Function `analyze_sentiment()`**: Analyze the sentiment/tone of the command to adapt responses.
  - **Function `parse_command()`**: Parse a natural language command into structured format.
  - **Function `add_app_alias()`**: Add new app alias dynamically. Useful for learning user-specific app names.

### File: `core_ai\src\ai_assistant\ai\llm_bandit.py`
- **Class `LLMBandit`**: Multi-armed bandit for optimal LLM selection
  - **Function `example_usage()`**: Demonstrate LLM bandit
  - **Function `__init__()`**: Signature: (self, db_path, exploration_rate)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_performance()`**: Load historical performance data
  - **Function `extract_task_features()`**: Extract features from task
  - **Function `thompson_sampling()`**: Thompson Sampling: sample from posterior distribution Returns expected reward
  - **Function `select_llm()`**: Select best LLM for task using contextual bandit
  - **Function `record_outcome()`**: Record outcome and update performance
  - **Function `get_best_llm_for_task()`**: Get best performing LLM for task type
  - **Function `get_performance_summary()`**: Get performance summary for all LLMs
  - **Function `get_stats()`**: Get bandit statistics

### File: `core_ai\src\ai_assistant\ai\llm_provider.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\ai\local_ai_manager.py`
- **Class `LocalModelConfig`**: Configuration for local AI model
- **Class `LocalAIManager`**: Manages local AI inference with Ollama
  - **Function `quick_test()`**: Quick test of LocalAIManager with Ollama
  - **Function `__init__()`**: Signature: (self, models_dir)
  - **Function `is_ollama_running()`**: Check if Ollama service is running
  - **Function `list_ollama_models()`**: List available Ollama models
  - **Function `find_best_available_model()`**: Find the best available model from Ollama. Priority: 1. llama3.2 (Best quality for general tasks) 2. qwen2.5 (Fastest) 3. Any other available model
  - **Function `load_model()`**: Load model from Ollama
  - **Function `generate()`**: Generate text using Ollama model
  - **Function `_generate_stream()`**: Stream tokens as they're generated from Ollama
  - **Function `chat()`**: Chat with conversation history
  - **Function `clear_history()`**: Clear conversation history
  - **Function `get_stats()`**: Get performance statistics

### File: `core_ai\src\ai_assistant\ai\local_model_manager.py`
- **Class `LocalModelManager`**: Manage tiny local models optimized for low-resource systems Target: 8GB RAM, CPU-only inference and training
  - **Function `demo_local_model()`**: Demo the local model
  - **Function `__init__()`**: Initialize local model manager
  - **Function `download_model()`**: Download and cache model locally
  - **Function `load_model()`**: Load model into memory
  - **Function `unload_model()`**: Free up memory by unloading model
  - **Function `generate()`**: Generate text from prompt
  - **Function `get_system_info()`**: Get current system resource usage
  - **Function `list_available_models()`**: List all tiny models suitable for 8GB RAM
  - **Function `check_system_requirements()`**: Check if system meets minimum requirements

### File: `core_ai\src\ai_assistant\ai\memory.py`
- **Class `ConnectionPool`**: Simple connection pool for SQLite to reuse connections.
  - **Function `get_encrypted_db()`**: Get encrypted database instance
  - **Function `get_db_connection()`**: Context manager for database connections with automatic cleanup.
  - **Function `get_db_transaction()`**: Context manager for database transactions with automatic commit/rollback.
  - **Function `setup_memory()`**: Creates the memory databases and tables if they don't exist.
  - **Function `save_to_memory()`**: Saves a line of dialogue to both memory tables with transaction safety and encryption.
  - **Function `get_memory()`**: Retrieves the last N messages from the conversation history. :param last_n_messages: The number of recent messages to retrieve.
  - **Function `search_memory()`**: Searches through conversation history for messages containing the query. :param query: Search term to look for :param limit: Maximum number of resu...
  - **Function `get_conversation_summary()`**: Gets a summary of conversations for a specific date or today. :param date: Date in YYYY-MM-DD format (optional, defaults to today)
  - **Function `save_knowledge()`**: Saves important knowledge/facts to the knowledge base. :param topic: The topic or category of the knowledge :param content: The actual knowledge co...
  - **Function `get_knowledge()`**: Retrieves knowledge from the knowledge base by topic. :param topic: The topic to search for
  - **Function `determine_importance()`**: Determines importance level (1-5) based on content analysis.
  - **Function `categorize_content()`**: Categorizes content based on keywords and context.
  - **Function `generate_summary()`**: Generates a brief summary of the content.
  - **Function `semantic_search_memory()`**: Perform semantic search on conversation history. Uses simple keyword matching and TF-IDF style scoring. :param query: Search query :param limit: Ma...
  - **Function `__init__()`**: Signature: (self, database, max_connections)
  - **Function `get_connection()`**: Get a connection from the pool or create a new one.
  - **Function `return_connection()`**: Return a connection to the pool.
  - **Function `close_all()`**: Close all connections in the pool.

### File: `core_ai\src\ai_assistant\ai\meta_learning.py`
- **Class `Task`**: Single task for meta-learning
- **Class `MetaLearningResult`**: Result of meta-learning episode
- **Class `MAMLLearner`**: Model-Agnostic Meta-Learning implementation Learn to learn: meta-optimize for fast adaptation
- **Class `FewShotClassifier`**: Few-shot classification using MAML Learn to classify with few examples per class
  - **Function `example_meta_learning()`**: Example of using meta-learning for few-shot tasks
- **Class `MetaLearnerNetwork`**: Core component.
  - **Function `__init__()`**: Signature: (self, feature_dim, num_classes)
  - **Function `_init_database()`**: Initialize database for meta-learning tasks
  - **Function `register_task()`**: Register a new task
  - **Function `inner_loop_adapt()`**: Perform inner loop adaptation on a task Returns: (adapted_model, losses)
  - **Function `evaluate_on_query()`**: Evaluate model on query set
  - **Function `meta_train_step()`**: Single meta-training step on a batch of tasks
  - **Function `adapt_to_new_task()`**: Quickly adapt to a new task using meta-learned initialization
  - **Function `_save_episode()`**: Save meta-learning episode
  - **Function `get_stats()`**: Get meta-learning statistics
  - **Function `__init__()`**: Signature: (self, feature_dim, num_classes)
  - **Function `train_on_tasks()`**: Train on a distribution of tasks
  - **Function `classify_few_shot()`**: Classify a query example given few support examples
  - **Function `__init__()`**: Signature: (self, feature_dim, num_classes)
  - **Function `forward()`**: Signature: ()
  - **Function `clone()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\model_compression.py`
- **Class `ModelCompressor`**: Compress models for efficient deployment
  - **Function `example_usage()`**: Demonstrate model compression
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `quantize_dynamic()`**: Apply dynamic quantization (CPU inference) Reduces precision of weights/activations at inference time
  - **Function `prune_model()`**: Apply structured pruning to remove less important weights
  - **Function `distill_model()`**: Knowledge distillation: train smaller student model from teacher
  - **Function `apply_mixed_precision()`**: Convert model to mixed precision (FP16/FP32) for faster inference
  - **Function `compress_pipeline()`**: Apply multiple compression methods in sequence
  - **Function `_get_model_size()`**: Get model size in MB
  - **Function `_save_compression_record()`**: Save compression record to database
  - **Function `get_compression_history()`**: Get history of model compressions
  - **Function `get_stats()`**: Get compression statistics

### File: `core_ai\src\ai_assistant\ai\model_router.py`
- **Class `ModelTier`**: Model capability tiers
- **Class `ModelConfig`**: Configuration for a model
- **Class `QueryAnalysis`**: Analysis of a query
- **Class `IntelligentModelRouter`**: Routes queries to optimal model based on analysis
  - **Function `get_model_router()`**: Get global router instance
  - **Function `__init__()`**: Initialize router
  - **Function `_initialize_models()`**: Initialize available models
  - **Function `analyze_query()`**: Analyze query to determine complexity and requirements
  - **Function `_calculate_complexity()`**: Calculate query complexity score (0-1)
  - **Function `route()`**: Route query to best model
  - **Function `record_usage()`**: Record model usage for stats
  - **Function `get_stats()`**: Get routing statistics
  - **Function `_calculate_savings()`**: Calculate cost savings from routing vs always using GPT-4
  - **Function `recommend_model()`**: Recommend model based on constraints

### File: `core_ai\src\ai_assistant\ai\multimodal_learning.py`
- **Class `MultiModalProfile`**: Unified user profile across modalities
- **Class `ModalityInteraction`**: Record of multi-modal interaction
- **Class `CrossModalEmbedder`**: Creates unified embeddings from multiple modalities
- **Class `VoiceTextCorrelator`**: Learns correlations between voice patterns and text preferences
- **Class `MultiModalLearningEngine`**: Main engine for multi-modal learning
  - **Function `example_usage()`**: Demonstrate multi-modal learning
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `embed_voice()`**: Convert voice features to embedding
  - **Function `embed_text()`**: Convert text embedding to unified space
  - **Function `embed_behavior()`**: Convert behavioral features to embedding
  - **Function `fuse_modalities()`**: Fuse multiple modal embeddings
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `learn_correlation()`**: Learn voice-text correlation
  - **Function `_voice_fingerprint()`**: Create fingerprint from voice features
  - **Function `predict_preference()`**: Predict text preference from voice
  - **Function `detect_emotion_from_voice()`**: Detect likely emotion from voice pattern
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_profiles()`**: Load user profiles
  - **Function `get_or_create_profile()`**: Get or create user profile
  - **Function `save_profile()`**: Save profile to database
  - **Function `record_interaction()`**: Record multi-modal interaction
  - **Function `_update_voice_features()`**: Update voice feature averages
  - **Function `_update_text_preferences()`**: Update text preference scores
  - **Function `get_unified_embedding()`**: Get unified multi-modal embedding for user
  - **Function `predict_user_state()`**: Predict user state from available modalities
  - **Function `get_contextual_insights()`**: Get insights from multi-modal data

### File: `core_ai\src\ai_assistant\ai\multi_step_parser.py`
- **Class `TaskStep`**: Represents a single step in a task chain.
- **Class `MultiStepCommandParser`**: Parses complex, multi-step commands into sequential tasks.
  - **Function `parse_multi_step_command()`**: Parse a multi-step command into task steps.
  - **Function `__post_init__()`**: Signature: (self)
  - **Function `__init__()`**: Initialize parser with patterns.
  - **Function `is_multi_step()`**: Check if command contains multiple steps.
  - **Function `split_into_steps()`**: Split command into individual step strings.
  - **Function `parse_single_step()`**: Parse a single command step.
  - **Function `infer_dependencies()`**: Infer dependencies between steps.
  - **Function `parse_command()`**: Parse a command into task steps.
  - **Function `extract_message_content()`**: Extract message content from command.
  - **Function `extract_contact_name()`**: Extract contact/recipient name from command.
  - **Function `enhance_step_params()`**: Enhance step parameters with extracted information.

### File: `core_ai\src\ai_assistant\ai\network_aware_llm.py`
- **Class `OnlineLLMConfig`**: Configuration for online-only LLM providers.
  - **Function `get_optimal_llm_config()`**: Get the optimal LLM configuration.
  - **Function `force_online_mode()`**: Force refresh of online providers.
  - **Function `__init__()`**: Signature: (self)
  - **Function `_load_api_keys()`**: Load API keys from secure locations.
  - **Function `check_internet_connectivity()`**: Check if internet connection is available.
  - **Function `get_optimal_provider()`**: Get the optimal online provider based on availability.
  - **Function `_test_provider()`**: Quick test of online provider availability.
  - **Function `get_provider_config()`**: Get complete provider configuration.

### File: `core_ai\src\ai_assistant\ai\offline_llm_provider.py`
- **Class `OfflineLLMProvider`**: Abstract base class for offline LLM providers.
- **Class `OllamaProvider`**: Ollama local model provider - requires Ollama to be installed and running.
- **Class `TransformersProvider`**: Hugging Face Transformers provider for offline local models.
- **Class `SimpleOfflineProvider`**: Simple fallback provider for basic text matching and rule-based responses.
- **Class `OfflineLLMManager`**: Manager for offline LLM providers with fallback chain.
  - **Function `get_offline_llm()`**: Get the offline LLM manager instance.
  - **Function `generate_response()`**: Generate response with fallback chain.
  - **Function `stream_response()`**: Stream response with fallback chain.
  - **Function `count_tokens()`**: Count tokens using current provider.
  - **Function `is_available()`**: Simple provider is always available.
  - **Function `__init__()`**: Initialize with multiple offline providers.
  - **Function `_check_availability()`**: Check if Ollama server is running and model is available.
  - **Function `is_available()`**: Simple provider is always available.
  - **Function `generate_response()`**: Generate response with fallback chain.
  - **Function `stream_response()`**: Stream response with fallback chain.
  - **Function `count_tokens()`**: Count tokens using current provider.
  - **Function `_format_prompt()`**: Format messages into a prompt string.
  - **Function `__init__()`**: Initialize with multiple offline providers.
  - **Function `_init_pipeline()`**: Initialize the transformation pipeline.
  - **Function `is_available()`**: Simple provider is always available.
  - **Function `generate_response()`**: Generate response with fallback chain.
  - **Function `stream_response()`**: Stream response with fallback chain.
  - **Function `count_tokens()`**: Count tokens using current provider.
  - **Function `_format_prompt()`**: Format messages into a prompt string.
  - **Function `__init__()`**: Initialize with multiple offline providers.
  - **Function `_init_knowledge_base()`**: Initialize basic knowledge base for common queries.
  - **Function `_get_help_text()`**: Get help text.
  - **Function `is_available()`**: Simple provider is always available.
  - **Function `generate_response()`**: Generate response with fallback chain.
  - **Function `stream_response()`**: Stream response with fallback chain.
  - **Function `count_tokens()`**: Count tokens using current provider.
  - **Function `__init__()`**: Initialize with multiple offline providers.
  - **Function `_init_providers()`**: Initialize available providers.
  - **Function `generate_response()`**: Generate response with fallback chain.
  - **Function `stream_response()`**: Stream response with fallback chain.
  - **Function `count_tokens()`**: Count tokens using current provider.
  - **Function `get_provider_info()`**: Get information about available providers.

### File: `core_ai\src\ai_assistant\ai\offline_mode.py`
- **Class `OfflineModeManager`**: Manages offline/online mode detection and switching.
  - **Function `get_offline_manager()`**: Get or create the global offline mode manager instance.
  - **Function `__init__()`**: Initialize offline mode manager.
  - **Function `_check_connectivity()`**: Check if device has internet connectivity.
  - **Function `start_connectivity_check()`**: Start background connectivity check thread.
  - **Function `stop_connectivity_check()`**: Stop background connectivity check thread.
  - **Function `_connectivity_check_loop()`**: Background thread for periodic connectivity checks.
  - **Function `set_offline_mode()`**: Force offline mode regardless of connectivity.
  - **Function `is_connected()`**: Check if device should be in online mode.
  - **Function `should_use_offline()`**: Check if offline mode should be used.
  - **Function `add_mode_change_callback()`**: Add callback for mode changes.
  - **Function `_trigger_mode_change_callbacks()`**: Trigger all registered mode change callbacks.
  - **Function `get_status()`**: Get current offline/online status.
  - **Function `cache_response()`**: Cache a response for offline use.
  - **Function `get_cached_response()`**: Get cached response if available and not expired.
  - **Function `clear_cache()`**: Clear cache files.
  - **Function `get_cache_info()`**: Get information about cached data.

### File: `core_ai\src\ai_assistant\ai\qlora_trainer.py`
- **Class `TrainingConfig`**: Configuration for QLoRA training optimized for 8GB RAM
- **Class `QLoRATrainer`**: Train tiny models with QLoRA on 8GB RAM systems Can run on CPU-only (slow but works)
  - **Function `create_sample_training_data()`**: Create a sample training dataset
  - **Function `demo_training()`**: Demo the QLoRA training process
  - **Function `__post_init__()`**: Signature: (self)
  - **Function `__init__()`**: Initialize QLoRA trainer
  - **Function `prepare_dataset()`**: Prepare dataset for fine-tuning
  - **Function `load_training_data()`**: Load training data from JSON file
  - **Function `tokenize_dataset()`**: Tokenize the dataset
  - **Function `setup_model_and_tokenizer()`**: Load model with 4-bit quantization and prepare for LoRA training
  - **Function `train()`**: Fine-tune the model with QLoRA
  - **Function `tokenize_function()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\query_cache.py`
- **Class `QuerySimilarityCache`**: Smart query caching using TF-IDF similarity
  - **Function `example_usage()`**: Demonstrate query caching
  - **Function `__init__()`**: Signature: (self, db_path, similarity_threshold, cache_ttl_hours)
  - **Function `_init_database()`**: Initialize cache database
  - **Function `_load_cache()`**: Load existing cache entries
  - **Function `_compute_hash()`**: Compute hash for query
  - **Function `_compute_similarity_sklearn()`**: Compute similarity using sklearn
  - **Function `_compute_similarity_fallback()`**: Fallback similarity using word overlap
  - **Function `get()`**: Get cached response for query
  - **Function `set()`**: Cache a query-response pair
  - **Function `_record_hit()`**: Record cache hit
  - **Function `_record_miss()`**: Record cache miss
  - **Function `clear_expired()`**: Remove expired cache entries
  - **Function `get_stats()`**: Get cache statistics
  - **Function `invalidate_similar()`**: Invalidate cache entries similar to query (for concept drift)

### File: `core_ai\src\ai_assistant\ai\self_supervised_learning.py`
- **Class `SelfSupervisedLearner`**: Self-supervised learning for data-efficient training
  - **Function `example_usage()`**: Demonstrate self-supervised learning
  - **Function `__init__()`**: Signature: (self, db_path, hidden_dim, mask_probability)
  - **Function `_init_database()`**: Initialize database
  - **Function `mask_tokens()`**: Mask tokens for MLM (Masked Language Modeling)
  - **Function `mlm_loss()`**: Masked Language Modeling loss
  - **Function `autoencoding_loss()`**: Autoencoding: reconstruct input from latent representation
  - **Function `rotation_prediction_loss()`**: Rotation prediction: predict which rotation was applied (Simulated for generic features)
  - **Function `train_task()`**: Train on self-supervised task
  - **Function `extract_representation()`**: Extract learned representation
  - **Function `save_representation()`**: Save learned representation
  - **Function `get_stats()`**: Get learning statistics

### File: `core_ai\src\ai_assistant\ai\semantic_cache.py`
- **Class `SemanticResponseCache`**: Intelligent response caching with semantic similarity
  - **Function `get_response_cache()`**: Get global response cache instance
  - **Function `cache_response()`**: Cache a response
  - **Function `get_cached_response()`**: Get cached response
  - **Function `get_cache_stats()`**: Get cache statistics
  - **Function `__init__()`**: Initialize semantic cache
  - **Function `_ensure_embedder_loaded()`**: Lazy load embedder on first use
  - **Function `_load_stats()`**: Load cache statistics
  - **Function `_save_stats()`**: Save cache statistics
  - **Function `_load_embedder_if_needed()`**: Lazy load embedder on first use (background download if needed)
  - **Function `_get_embedding()`**: Get embedding for text
  - **Function `_compute_similarity()`**: Compute cosine similarity between embeddings
  - **Function `_get_cache_key()`**: Generate cache key from text
  - **Function `get()`**: Get cached response for query
  - **Function `_find_similar()`**: Find semantically similar cached entry
  - **Function `set()`**: Cache a response
  - **Function `_vary_response()`**: Add slight variations to cached responses to feel more natural
  - **Function `invalidate()`**: Invalidate cache entry or entire cache
  - **Function `get_stats()`**: Get cache statistics
  - **Function `optimize()`**: Optimize cache by removing old/unused entries
  - **Function `_download_model()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\smart_command_prediction.py`
- **Class `SmartCommandPredictor`**: Application-level intelligent command prediction Suggests commands based on context, history, and patterns
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_patterns()`**: Load patterns from database
  - **Function `log_command()`**: Log command usage
  - **Function `predict_next_commands()`**: Predict most likely next commands
  - **Function `autocomplete_command()`**: Autocomplete command based on partial input
  - **Function `get_popular_commands()`**: Get most popular commands in time range
  - **Function `get_stats()`**: Get statistics

### File: `core_ai\src\ai_assistant\ai\smart_memory_retrieval.py`
- **Class `SmartMemoryRetrieval`**: Intelligently retrieve information from learned conversations
  - **Function `enhance_response_with_memory()`**: Enhance AI response by checking memory first
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `answer_from_memory()`**: Try to answer a question from memory
  - **Function `_extract_date_query()`**: Extract date-related information (exams, appointments, etc.)
  - **Function `_search_for_dates()`**: Search memory for date-related information
  - **Function `_extract_dates_from_text()`**: Extract date mentions from text
  - **Function `_extract_app_query()`**: Extract app usage information
  - **Function `_search_app_usage()`**: Search for app usage patterns
  - **Function `_extract_event_query()`**: Extract event-related information
  - **Function `_search_events()`**: Search for upcoming events
  - **Function `_search_general_memory()`**: General memory search based on keywords

### File: `core_ai\src\ai_assistant\ai\streaming_handler.py`
- **Class `StreamProvider`**: Supported streaming providers
- **Class `StreamChunk`**: A chunk of streamed response
- **Class `StreamingResponseHandler`**: Handles streaming responses from multiple LLM providers
  - **Function `get_streaming_handler()`**: Get global streaming handler
  - **Function `__init__()`**: Initialize streaming handler
  - **Function `_initialize_providers()`**: Initialize provider clients
  - **Function `get_stats()`**: Get streaming statistics
  - **Function `print_chunk()`**: Signature: ()

### File: `core_ai\src\ai_assistant\ai\usage_pattern_analyzer.py`
- **Class `UsagePatternAnalyzer`**: Analyzes usage patterns for personalized fine-tuning
  - **Function `__init__()`**: Initialize analyzer
  - **Function `analyze_all()`**: Run complete analysis
  - **Function `_get_conversations()`**: Get conversations from database
  - **Function `_analyze_common_commands()`**: Identify most common command patterns
  - **Function `_analyze_topics()`**: Extract frequent topics using TF-IDF
  - **Function `_analyze_time_patterns()`**: Analyze usage by time of day and day of week
  - **Function `_analyze_app_usage()`**: Analyze which apps are used most
  - **Function `_analyze_sequences()`**: Identify common command sequences (workflows)
  - **Function `_analyze_preferences()`**: Analyze user preferences from feedback
  - **Function `_generate_training_data()`**: Generate training data in fine-tuning format
  - **Function `export_for_finetuning()`**: Export training data for fine-tuning
  - **Function `generate_report()`**: Generate human-readable analysis report

### File: `core_ai\src\ai_assistant\ai\workflow_recommender.py`
- **Class `WorkflowRecommender`**: Application-level workflow recommendation system Suggests optimal workflows and automation opportunities
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `_init_database()`**: Initialize database
  - **Function `register_workflow()`**: Register a workflow
  - **Function `log_workflow_execution()`**: Log workflow execution
  - **Function `recommend_workflow()`**: Recommend workflows based on context
  - **Function `identify_automation_opportunities()`**: Identify repetitive patterns that can be automated
  - **Function `suggest_workflow_optimization()`**: Suggest optimizations for a workflow
  - **Function `get_workflow_analytics()`**: Get detailed analytics for a workflow
  - **Function `get_stats()`**: Get statistics

### File: `core_ai\src\ai_assistant\ai\workflow_scheduler.py`
- **Class `WorkflowScheduler`**: RL-powered workflow scheduler
  - **Function `example_usage()`**: Demonstrate workflow scheduler
  - **Function `__init__()`**: Signature: (self, db_path, learning_rate, discount_factor)
  - **Function `_init_database()`**: Initialize database
  - **Function `_load_tasks()`**: Load registered tasks
  - **Function `_load_q_values()`**: Load Q-learning values
  - **Function `register_task()`**: Register a new task
  - **Function `get_state()`**: Get current state representation for RL State = (pending_tasks, time_of_day, resources)
  - **Function `get_valid_actions()`**: Get tasks that can be scheduled (dependencies met)
  - **Function `select_action()`**: Select action using epsilon-greedy policy
  - **Function `update_q_value()`**: Update Q-value using Q-learning
  - **Function `schedule_workflow()`**: Generate optimal schedule using RL
  - **Function `_save_schedule()`**: Save generated schedule
  - **Function `record_execution()`**: Record task execution outcome
  - **Function `get_stats()`**: Get scheduler statistics

### File: `core_ai\src\ai_assistant\api\voice_api.py`
  - **Function `get_voice_status()`**: Get voice system status Returns information about available engines and current state
  - **Function `get_voice_config()`**: Get current voice configuration
  - **Function `speak_text()`**: Convert text to speech Body: {     "text": "Text to speak",     "voice": "en-US-AriaNeural" (optional),     "speed": 1.0 (optional),     "volume": ...
  - **Function `get_available_voices()`**: Get list of available TTS voices
  - **Function `preview_voice()`**: Generate preview audio for a voice Body: {     "voice_id": "en-US-AriaNeural",     "text": "Sample text" (optional) }
  - **Function `listen_for_speech()`**: Listen for speech and return transcribed text Body: {     "timeout": 10 (optional),     "phrase_time_limit": 15 (optional) }
  - **Function `transcribe_audio()`**: Transcribe audio data Body: {     "audio_data": "base64 encoded audio",     "format": "wav" (optional) }
  - **Function `start_wake_word()`**: Start wake word detection
  - **Function `stop_wake_word()`**: Stop wake word detection
  - **Function `configure_wake_word()`**: Get or update wake word configuration
  - **Function `get_voice_history()`**: Get voice command history
  - **Function `clear_audio_cache()`**: Clear audio cache
  - **Function `get_cache_stats()`**: Get audio cache statistics
  - **Function `health_check()`**: Health check endpoint for voice service
  - **Function `on_wake_word_detected()`**: Signature: ()

### File: `core_ai\src\ai_assistant\auth\pin_auth.py`
- **Class `PINAuth`**: PIN-based authentication system
  - **Function `authenticate()`**: Main authentication function to be called at startup
  - **Function `require_pin_auth()`**: Decorator/helper function to add PIN authentication to any script
  - **Function `setup_pin_cli()`**: CLI utility for PIN setup
  - **Function `__init__()`**: Initialize PIN authentication
  - **Function `_hash_pin()`**: Hash a PIN using PBKDF2
  - **Function `is_pin_configured()`**: Check if a PIN is already configured
  - **Function `verify_pin()`**: Verify a PIN against the stored hash
  - **Function `prompt_for_pin()`**: Prompt user for PIN and verify
  - **Function `setup_pin()`**: Set up a new PIN for the assistant
  - **Function `_save_pin_to_env()`**: Save PIN hash and salt to environment file
  - **Function `_setup_new_pin()`**: Set up a new PIN interactively
  - **Function `change_pin()`**: Change the current PIN

### File: `core_ai\src\ai_assistant\automation\analytics.py`
- **Class `MetricType`**: Types of metrics
- **Class `AlertLevel`**: Alert severity levels
- **Class `AnalyticsInterval`**: Analytics collection intervals
- **Class `MetricPoint`**: Individual metric data point
- **Class `PerformanceMetrics`**: Performance metrics snapshot
- **Class `OptimizationSuggestion`**: Performance optimization suggestion
- **Class `AnalyticsAlert`**: Analytics alert
- **Class `PerformanceReport`**: Comprehensive performance report
- **Class `MetricStore`**: Thread-safe storage for metrics data
- **Class `PerformanceMonitor`**: Real-time performance monitoring system
- **Class `OptimizationAnalyzer`**: Analyzes performance data and suggests optimizations
- **Class `ReportGenerator`**: Generates comprehensive performance reports
- **Class `AutomationAnalytics`**: Main automation analytics system
  - **Function `create_execution_time_collector()`**: Create collector for automation execution times
  - **Function `create_queue_metrics_collector()`**: Create collector for queue metrics
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `add_metric()`**: Add metric point
  - **Function `get_metrics()`**: Get metric points for a specific metric
  - **Function `get_latest_value()`**: Get latest value for metric
  - **Function `get_aggregated_stats()`**: Get aggregated statistics for metric
  - **Function `get_all_metric_names()`**: Get all metric names
  - **Function `clear_old_data()`**: Clear old metric data
  - **Function `_update_aggregated_metrics()`**: Update aggregated metrics for a metric
  - **Function `_recalculate_aggregated_metrics()`**: Recalculate aggregated metrics after data cleanup
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start_monitoring()`**: Start performance monitoring
  - **Function `stop_monitoring()`**: Stop performance monitoring
  - **Function `add_custom_collector()`**: Add custom metric collector
  - **Function `set_alert_threshold()`**: Set alert threshold for metric
  - **Function `add_alert_callback()`**: Add alert callback function
  - **Function `record_metric()`**: Record custom metric
  - **Function `record_execution_time()`**: Record operation execution time
  - **Function `get_performance_snapshot()`**: Get current performance snapshot
  - **Function `_monitor_loop()`**: Main monitoring loop
  - **Function `_collect_system_metrics()`**: Collect system resource metrics
  - **Function `_check_metric_alerts()`**: Check if metric triggers any alerts
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `analyze_performance()`**: Analyze performance and generate optimization suggestions
  - **Function `add_optimization_rule()`**: Add custom optimization rule
  - **Function `_setup_default_rules()`**: Set up default optimization rules
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `generate_report()`**: Generate performance report
  - **Function `_generate_daily_report()`**: Generate daily performance report
  - **Function `_generate_weekly_report()`**: Generate weekly performance report
  - **Function `_generate_monthly_report()`**: Generate monthly performance report
  - **Function `_generate_custom_report()`**: Generate custom performance report
  - **Function `_calculate_period_metrics()`**: Calculate aggregated metrics for time period
  - **Function `_calculate_execution_trends()`**: Calculate execution trends over time
  - **Function `_calculate_resource_trends()`**: Calculate resource usage trends over time
  - **Function `_analyze_errors()`**: Analyze error patterns
  - **Function `_generate_insights()`**: Generate key insights from report data
  - **Function `_calculate_performance_score()`**: Calculate overall performance score (0-100)
  - **Function `_generate_charts()`**: Generate visualization charts
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start()`**: Start analytics system
  - **Function `stop()`**: Stop analytics system
  - **Function `record_automation_event()`**: Record automation event for analytics
  - **Function `get_current_performance()`**: Get current performance snapshot
  - **Function `generate_optimization_suggestions()`**: Get optimization suggestions
  - **Function `generate_report()`**: Generate performance report
  - **Function `add_custom_metric_collector()`**: Add custom metric collector
  - **Function `set_performance_alert()`**: Set performance alert threshold
  - **Function `get_analytics_dashboard_data()`**: Get data for analytics dashboard
  - **Function `_calculate_system_health_score()`**: Calculate overall system health score
  - **Function `_init_database()`**: Initialize analytics database
  - **Function `collector()`**: Signature: ()
  - **Function `collector()`**: Signature: ()
  - **Function `high_cpu_usage_rule()`**: Signature: ()
  - **Function `high_memory_usage_rule()`**: Signature: ()
  - **Function `high_error_rate_rule()`**: Signature: ()
  - **Function `slow_execution_rule()`**: Signature: ()
  - **Function `queue_buildup_rule()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\app_automation.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\automation\app_discovery.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\automation\automation_engine.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\automation\automation_tools_new.py`
  - **Function `__getattr__()`**: Lazy load modules/functions when accessed. This prevents importing all 15+ submodules at startup.

### File: `core_ai\src\ai_assistant\automation\browser_automation.py`
- **Class `BrowserConfig`**: Browser configuration
- **Class `BrowserAutomation`**: Enhanced browser automation with AI-powered element detection
- **Class `YouTubeAutomation`**: Specialized automation for YouTube with common actions
  - **Function `__init__()`**: Initialize browser automation
  - **Function `start_browser()`**: Start the browser
  - **Function `navigate()`**: Navigate to URL
  - **Function `find_element_by_description()`**: Find element by natural language description
  - **Function `_find_by_common_patterns()`**: Find element using common patterns
  - **Function `_find_by_text()`**: Find element containing the description text
  - **Function `_find_by_attributes()`**: Find element by attributes (aria-label, title, etc.)
  - **Function `_try_selectors()`**: Try multiple selectors
  - **Function `click_element()`**: Click element by description
  - **Function `type_text()`**: Type text into an input field
  - **Function `select_option()`**: Select dropdown option
  - **Function `scroll()`**: Scroll page
  - **Function `wait_for_element()`**: Wait for element to appear
  - **Function `take_screenshot()`**: Take screenshot
  - **Function `_save_screenshot()`**: Save error screenshot
  - **Function `get_page_text()`**: Get all visible text from page
  - **Function `close()`**: Close browser
  - **Function `go_to_history()`**: Navigate to YouTube history page
  - **Function `clear_watch_history()`**: Clear watch history
  - **Function `search()`**: Search YouTube

### File: `core_ai\src\ai_assistant\automation\complex_workflows.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\automation\context_aware.py`
- **Class `ContextType`**: Types of context information
- **Class `AdaptationStrategy`**: Strategies for adaptation
- **Class `LearningMode`**: Machine learning modes
- **Class `ContextData`**: Context information snapshot
- **Class `ContextPattern`**: Detected context pattern
- **Class `AdaptationRule`**: Rule for context-based adaptation
- **Class `ContextCollector`**: Collects context information from various sources
- **Class `PatternDetector`**: Detects patterns in context data
- **Class `AdaptationEngine`**: Engine for context-based automation adaptation
- **Class `ContextAwareAutomation`**: Main context-aware automation system
  - **Function `create_context_collector()`**: Create custom context collector
  - **Function `create_adaptation_callback()`**: Create adaptation callback for automation system integration
  - **Function `get_signature()`**: Get context signature for similarity comparison
  - **Function `matches_context()`**: Check if current context matches trigger conditions
  - **Function `_evaluate_condition()`**: Evaluate a single condition
  - **Function `_get_nested_value()`**: Get nested value from data using dot notation
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start_collection()`**: Start context collection
  - **Function `stop_collection()`**: Stop context collection
  - **Function `register_collector()`**: Register context collector
  - **Function `get_current_context()`**: Get current context information
  - **Function `collect_context_now()`**: Force immediate context collection
  - **Function `_collection_loop()`**: Context collection loop for specific type
  - **Function `_setup_default_collectors()`**: Setup default context collectors
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `add_context_sample()`**: Add context sample for pattern detection
  - **Function `get_detected_patterns()`**: Get detected context patterns
  - **Function `get_patterns_by_type()`**: Get patterns by type
  - **Function `predict_next_context()`**: Predict likely next context based on patterns
  - **Function `_detect_patterns()`**: Run pattern detection on current contexts
  - **Function `_update_pattern()`**: Update detected pattern
  - **Function `_find_similar_contexts()`**: Find historically similar contexts
  - **Function `_create_context_signature()`**: Create numerical signature for contexts
  - **Function `_calculate_similarity()`**: Calculate similarity between context signatures
  - **Function `_setup_default_detection_rules()`**: Setup default pattern detection rules
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start_engine()`**: Start adaptation engine
  - **Function `stop_engine()`**: Stop adaptation engine
  - **Function `add_adaptation_rule()`**: Add custom adaptation rule
  - **Function `remove_adaptation_rule()`**: Remove adaptation rule
  - **Function `register_adaptation_callback()`**: Register callback for adaptation actions
  - **Function `force_adaptation_check()`**: Force immediate adaptation check
  - **Function `get_adaptation_stats()`**: Get adaptation engine statistics
  - **Function `_adaptation_loop()`**: Main adaptation engine loop
  - **Function `_evaluate_adaptations()`**: Evaluate adaptation rules against current context
  - **Function `_trigger_adaptation()`**: Trigger adaptation rule
  - **Function `_execute_adaptation_actions()`**: Execute adaptation actions
  - **Function `_resolve_action_parameters()`**: Resolve action parameters from context
  - **Function `_get_nested_value()`**: Get nested value from data using dot notation
  - **Function `_setup_default_adaptation_rules()`**: Setup default adaptation rules
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start()`**: Start context-aware automation system
  - **Function `stop()`**: Stop context-aware automation system
  - **Function `get_current_context()`**: Get current context information
  - **Function `get_detected_patterns()`**: Get detected context patterns
  - **Function `get_adaptation_rules()`**: Get adaptation rules
  - **Function `predict_context()`**: Predict context for future time
  - **Function `register_context_collector()`**: Register custom context collector
  - **Function `add_adaptation_rule()`**: Add custom adaptation rule
  - **Function `register_adaptation_callback()`**: Register callback for adaptation actions
  - **Function `get_system_stats()`**: Get system statistics
  - **Function `_init_database()`**: Initialize context database
  - **Function `_load_saved_data()`**: Load saved patterns and rules from database
  - **Function `_save_current_state()`**: Save current state to database
  - **Function `collector()`**: Signature: ()
  - **Function `callback()`**: Signature: ()
  - **Function `collect_system_context()`**: Signature: ()
  - **Function `collect_temporal_context()`**: Signature: ()
  - **Function `collect_performance_context()`**: Signature: ()
  - **Function `high_cpu_pattern()`**: Signature: ()
  - **Function `temporal_pattern()`**: Signature: ()
  - **Function `performance_degradation_pattern()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\file_automation.py`
- **Class `FileAutomation`**: Handles file system interactions and automation
  - **Function `__init__()`**: Initialize file automation
  - **Function `get_standard_folder()`**: Get path to standard user folders
  - **Function `open_explorer()`**: Open File Explorer at specific path
  - **Function `find_file()`**: Find a file by name
  - **Function `move_file()`**: Move a file to a destination folder
  - **Function `copy_file()`**: Copy a file to a destination folder

### File: `core_ai\src\ai_assistant\automation\live_taskbar_analysis.py`
  - **Function `analyze_current_taskbar()`**: Analyze what's currently visible on the taskbar
  - **Function `check_specific_app()`**: Check if a specific application is running
  - **Function `enum_window_callback()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\main_interface.py`
- **Class `AutomationStatus`**: Overall automation system status
- **Class `AutomationConfig`**: Automation system configuration
- **Class `AutomationAPI`**: RESTful API interface for automation system
- **Class `AutomationCLI`**: Command-line interface for automation system
- **Class `AutomationDashboard`**: Web dashboard for automation system
- **Class `AutomationManager`**: Main automation system manager
  - **Function `create_automation_manager()`**: Factory function to create automation manager
  - **Function `main()`**: Main CLI entry point
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `_setup_routes()`**: Setup API routes
  - **Function `run()`**: Run CLI
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `_setup_commands()`**: Setup CLI commands
  - **Function `run()`**: Run CLI
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `get_dashboard_data()`**: Get dashboard data
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `_initialize_components()`**: Initialize all automation components
  - **Function `start()`**: Start the automation system
  - **Function `stop()`**: Stop the automation system
  - **Function `get_status()`**: Get current system status
  - **Function `create_task()`**: Create a new automation task
  - **Function `execute_task()`**: Execute a task
  - **Function `get_task()`**: Get task details
  - **Function `list_tasks()`**: List tasks with optional filtering
  - **Function `delete_task()`**: Delete a task
  - **Function `create_schedule()`**: Create a new schedule
  - **Function `list_schedules()`**: List schedules
  - **Function `list_templates()`**: List available templates
  - **Function `instantiate_template()`**: Instantiate a template
  - **Function `get_analytics_metrics()`**: Get analytics metrics
  - **Function `get_report()`**: Generate analytics report
  - **Function `get_context_info()`**: Get context information
  - **Function `get_security_dashboard()`**: Get security dashboard data
  - **Function `authenticate_user()`**: Authenticate user
  - **Function `get_config()`**: Get system configuration
  - **Function `update_config()`**: Update system configuration
  - **Function `start_web_interface()`**: Start web interface
  - **Function `add_status_subscriber()`**: Add status update subscriber
  - **Function `remove_status_subscriber()`**: Remove status update subscriber
  - **Function `_start_status_monitoring()`**: Start status monitoring thread
  - **Function `_stop_status_monitoring()`**: Stop status monitoring thread
  - **Function `_status_monitor_loop()`**: Status monitoring loop
  - **Function `get_status()`**: Get current system status
  - **Function `list_tasks()`**: List tasks with optional filtering
  - **Function `create_task()`**: Create a new automation task
  - **Function `get_task()`**: Get task details
  - **Function `execute_task()`**: Execute a task
  - **Function `delete_task()`**: Delete a task
  - **Function `list_schedules()`**: List schedules
  - **Function `create_schedule()`**: Create a new schedule
  - **Function `list_templates()`**: List available templates
  - **Function `instantiate_template()`**: Instantiate a template
  - **Function `get_metrics()`**: Signature: ()
  - **Function `get_report()`**: Generate analytics report
  - **Function `get_context()`**: Signature: ()
  - **Function `security_dashboard()`**: Signature: ()
  - **Function `login()`**: Signature: ()
  - **Function `get_config()`**: Get system configuration
  - **Function `update_config()`**: Update system configuration
  - **Function `handle_connect()`**: Signature: ()
  - **Function `handle_disconnect()`**: Signature: ()
  - **Function `handle_subscribe_status()`**: Signature: ()
  - **Function `handle_unsubscribe_status()`**: Signature: ()
  - **Function `automation()`**: Signature: ()
  - **Function `status()`**: Signature: ()
  - **Function `start()`**: Start the automation system
  - **Function `stop()`**: Stop the automation system
  - **Function `task()`**: Signature: ()
  - **Function `list()`**: Signature: ()
  - **Function `show()`**: Signature: ()
  - **Function `execute()`**: Signature: ()
  - **Function `template()`**: Signature: ()
  - **Function `list()`**: Signature: ()
  - **Function `analytics()`**: Signature: ()
  - **Function `metrics()`**: Signature: ()
  - **Function `serve()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\orchestrator.py`
- **Class `TaskPriority`**: Task execution priority levels
- **Class `TaskStatus`**: Task execution status
- **Class `ResourceType`**: System resource types
- **Class `ExecutionMode`**: Task execution modes
- **Class `ResourceRequirements`**: Resource requirements for task execution
- **Class `TaskDependency`**: Task dependency definition
- **Class `TaskMetrics`**: Task execution metrics
- **Class `AutomationTask`**: Comprehensive automation task definition
- **Class `SystemResources`**: Current system resource state
- **Class `ExecutionContext`**: Task execution context
- **Class `ResourceManager`**: Manages system resources and allocation for tasks
- **Class `TaskQueue`**: Intelligent task queue with priority handling and resource awareness
- **Class `TaskExecutor`**: Executes automation tasks with intelligent resource management
- **Class `AutomationOrchestrator`**: Main automation orchestration layer that coordinates all automation subsystems
  - **Function `create_automation_orchestrator()`**: Create and configure automation orchestrator
  - **Function `create_automation_task()`**: Create automation task with default settings
  - **Function `quick_submit_task()`**: Quick task submission
  - **Function `get_orchestrator_status()`**: Get orchestrator status summary
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `start_monitoring()`**: Start system resource monitoring
  - **Function `stop_monitoring()`**: Stop resource monitoring
  - **Function `_monitor_resources()`**: Monitor system resources continuously
  - **Function `get_current_resources()`**: Get current system resources
  - **Function `get_resource_history()`**: Get resource history for specified duration
  - **Function `can_allocate_resources()`**: Check if resources can be allocated for task
  - **Function `reserve_resources()`**: Reserve resources for task execution
  - **Function `release_resources()`**: Release reserved resources
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `add_task()`**: Add task to queue
  - **Function `get_next_task()`**: Get next task for execution
  - **Function `complete_task()`**: Mark task as completed and update dependents
  - **Function `_validate_task()`**: Validate task before adding to queue
  - **Function `_update_dependencies()`**: Update task dependency tracking
  - **Function `_can_queue_task()`**: Check if task can be queued (dependencies satisfied)
  - **Function `_can_execute_task()`**: Check if task can be executed (resources available)
  - **Function `_calculate_priority_score()`**: Calculate dynamic priority score for task
  - **Function `_check_dependent_tasks()`**: Check and queue dependent tasks that are now ready
  - **Function `get_queue_status()`**: Get current queue status
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `start()`**: Start automation orchestration
  - **Function `stop()`**: Stop automation orchestration
  - **Function `_execution_coordinator()`**: Coordinate task execution
  - **Function `_execute_task_async()`**: Execute task asynchronously
  - **Function `_execute_task()`**: Execute single task
  - **Function `_execute_sequential()`**: Execute task in sequential mode
  - **Function `_execute_parallel()`**: Execute task in parallel mode
  - **Function `_execute_batch()`**: Execute task in batch mode
  - **Function `_execute_streaming()`**: Execute task in streaming mode
  - **Function `_task_completion_callback()`**: Handle task completion
  - **Function `_cleanup_completed_executions()`**: Clean up completed task executions
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `start()`**: Start automation orchestration
  - **Function `stop()`**: Stop automation orchestration
  - **Function `submit_task()`**: Submit automation task for execution
  - **Function `get_task_status()`**: Get task status and details
  - **Function `cancel_task()`**: Cancel pending or running task
  - **Function `get_system_status()`**: Get overall system status
  - **Function `get_performance_metrics()`**: Get performance metrics and analytics
  - **Function `_init_database()`**: Initialize SQLite database for persistence
  - **Function `_save_task()`**: Save task to database

### File: `core_ai\src\ai_assistant\automation\rule_engine.py`
- **Class `RuleType`**: Types of automation rules
- **Class `ConditionOperator`**: Operators for rule conditions
- **Class `ActionType`**: Types of rule actions
- **Class `RuleStatus`**: Rule execution status
- **Class `EventType`**: System event types
- **Class `RuleCondition`**: Individual rule condition
- **Class `RuleAction`**: Rule action definition
- **Class `RuleEvent`**: Rule event definition
- **Class `RuleContext`**: Context for rule evaluation
- **Class `AutomationRule`**: Complete automation rule definition
- **Class `EventManager`**: Manages events and event-driven rule triggers
- **Class `FactDatabase`**: Database for storing and querying facts
- **Class `RuleExecutor`**: Executes rule actions
- **Class `AutomationRuleEngine`**: Main automation rule engine
  - **Function `create_condition_rule()`**: Create condition-based rule
  - **Function `create_event_rule()`**: Create event-triggered rule
  - **Function `create_simple_condition()`**: Create simple rule condition
  - **Function `create_function_action()`**: Create function call action
  - **Function `evaluate()`**: Evaluate condition against context
  - **Function `_get_field_value()`**: Get field value from context using dot notation
  - **Function `evaluate_conditions()`**: Evaluate rule conditions
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start_processing()`**: Start event processing
  - **Function `stop_processing()`**: Stop event processing
  - **Function `emit_event()`**: Emit system event
  - **Function `register_handler()`**: Register event handler
  - **Function `unregister_handler()`**: Unregister event handler
  - **Function `get_recent_events()`**: Get recent events
  - **Function `_process_events()`**: Process events from queue
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `set_fact()`**: Set fact in fact database
  - **Function `get_fact()`**: Get fact from fact database
  - **Function `delete_fact()`**: Delete fact
  - **Function `get_facts_matching()`**: Get facts matching pattern
  - **Function `get_fact_history()`**: Get fact history
  - **Function `get_all_facts()`**: Get all facts
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `register_function()`**: Register function for rule actions
  - **Function `execute_actions()`**: Execute list of rule actions
  - **Function `_execute_single_action()`**: Execute single rule action
  - **Function `_execute_function_call()`**: Execute function call action
  - **Function `_execute_set_property()`**: Execute set property action
  - **Function `_execute_send_event()`**: Execute send event action
  - **Function `_execute_log_message()`**: Execute log message action
  - **Function `_execute_conditional()`**: Execute conditional action
  - **Function `_execute_loop()`**: Execute loop action
  - **Function `_execute_custom()`**: Execute custom action
  - **Function `_register_builtin_functions()`**: Register built-in functions
  - **Function `_resolve_parameters()`**: Resolve parameter values from context
  - **Function `_get_context_value()`**: Get value from context using dot notation
  - **Function `_set_context_value()`**: Set value in context using dot notation
  - **Function `_resolve_template()`**: Resolve template string with context values
  - **Function `_evaluate_action_condition()`**: Evaluate action condition
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start()`**: Start rule engine
  - **Function `stop()`**: Stop rule engine
  - **Function `add_rule()`**: Add automation rule
  - **Function `remove_rule()`**: Remove automation rule
  - **Function `enable_rule()`**: Enable rule
  - **Function `disable_rule()`**: Disable rule
  - **Function `trigger_rule()`**: Manually trigger rule execution
  - **Function `set_fact()`**: Set fact in fact database
  - **Function `get_fact()`**: Get fact from fact database
  - **Function `emit_event()`**: Emit system event
  - **Function `register_function()`**: Register function for rule actions
  - **Function `get_rule_status()`**: Get rule status and information
  - **Function `list_rules()`**: List all rules
  - **Function `get_engine_stats()`**: Get rule engine statistics
  - **Function `_engine_loop()`**: Main engine evaluation loop
  - **Function `_build_context()`**: Build current rule context
  - **Function `_evaluate_condition_rules()`**: Evaluate condition-based rules
  - **Function `_should_evaluate_rule()`**: Check if rule should be evaluated
  - **Function `_execute_rule()`**: Execute automation rule
  - **Function `_setup_event_handlers()`**: Set up event handlers for rule triggers
  - **Function `_setup_rule_triggers()`**: Set up triggers for rule
  - **Function `_validate_rule()`**: Validate rule before adding
  - **Function `_cleanup_expired_rules()`**: Clean up expired rules
  - **Function `_init_database()`**: Initialize database for rule storage
  - **Function `_save_rule()`**: Save rule to database
  - **Function `_load_rules()`**: Load rules from database
  - **Function `_delete_rule()`**: Delete rule from database
  - **Function `handle_event()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\security.py`
- **Class `SecurityLevel`**: Security levels for automation operations
- **Class `PermissionType`**: Types of permissions
- **Class `ResourceType`**: Types of protected resources
- **Class `AuditEventType`**: Types of audit events
- **Class `Permission`**: Individual permission definition
- **Class `Role`**: Security role definition
- **Class `User`**: User account definition
- **Class `SecurityCredential`**: Secure credential storage
- **Class `AuditEvent`**: Security audit event
- **Class `SecurityPolicy`**: Security policy definition
- **Class `SecuritySession`**: User security session
- **Class `CredentialManager`**: Secure credential storage and management
- **Class `AccessController`**: Role-based access control system
- **Class `AuditLogger`**: Security audit logging system
- **Class `SecurityPolicyEngine`**: Security policy enforcement engine
- **Class `AutomationSecurity`**: Main automation security system
  - **Function `require_permission()`**: Decorator for permission checking
  - **Function `secure_operation()`**: Decorator for marking operations with security levels
  - **Function `matches_request()`**: Check if permission matches request
  - **Function `has_permission()`**: Check if role has specific permission
  - **Function `is_locked()`**: Check if user account is locked
  - **Function `verify_password()`**: Verify password against hash
  - **Function `is_expired()`**: Check if session is expired
  - **Function `is_idle()`**: Check if session is idle
  - **Function `__init__()`**: Signature: (self, db_path, master_key)
  - **Function `store_credential()`**: Store secure credential
  - **Function `retrieve_credential()`**: Retrieve secure credential
  - **Function `list_credentials()`**: List available credentials for user
  - **Function `delete_credential()`**: Delete credential
  - **Function `_check_credential_access()`**: Check if user can access credential
  - **Function `_derive_key()`**: Derive encryption key from master key
  - **Function `__init__()`**: Signature: (self, db_path, master_key)
  - **Function `create_user()`**: Create new user account
  - **Function `authenticate_user()`**: Authenticate user and create session
  - **Function `validate_session()`**: Validate and refresh session
  - **Function `check_permission()`**: Check if session has required permission
  - **Function `logout_user()`**: Logout user and invalidate session
  - **Function `create_role()`**: Create new role
  - **Function `assign_role_to_user()`**: Assign role to user
  - **Function `revoke_role_from_user()`**: Revoke role from user
  - **Function `_hash_password()`**: Hash password securely
  - **Function `_calculate_effective_permissions()`**: Calculate effective permissions from roles
  - **Function `_update_user_sessions()`**: Update all active sessions for user
  - **Function `_invalidate_session()`**: Invalidate session
  - **Function `_create_default_roles()`**: Create default system roles
  - **Function `__init__()`**: Signature: (self, db_path, master_key)
  - **Function `log_event()`**: Log security audit event
  - **Function `get_recent_events()`**: Get recent audit events with filtering
  - **Function `get_security_violations()`**: Get security violations within time window
  - **Function `get_user_activity()`**: Get user activity within time window
  - **Function `_init_database()`**: Initialize security database
  - **Function `_store_audit_event()`**: Store audit event in database
  - **Function `__init__()`**: Signature: (self, db_path, master_key)
  - **Function `add_policy()`**: Add security policy
  - **Function `evaluate_policies()`**: Evaluate all policies against context
  - **Function `_evaluate_policy()`**: Evaluate single policy
  - **Function `_evaluate_rule()`**: Evaluate single policy rule
  - **Function `_evaluate_ip_whitelist_rule()`**: Evaluate IP whitelist rule
  - **Function `_evaluate_time_restriction_rule()`**: Evaluate time restriction rule
  - **Function `_evaluate_resource_limit_rule()`**: Evaluate resource limit rule
  - **Function `_evaluate_session_limit_rule()`**: Evaluate session limit rule
  - **Function `_create_default_policies()`**: Create default security policies
  - **Function `__init__()`**: Signature: (self, db_path, master_key)
  - **Function `start_security()`**: Start security system
  - **Function `stop_security()`**: Stop security system
  - **Function `authenticate()`**: Authenticate user
  - **Function `check_access()`**: Check access permissions
  - **Function `store_credential()`**: Store secure credential
  - **Function `retrieve_credential()`**: Retrieve secure credential
  - **Function `get_security_dashboard()`**: Get security dashboard data
  - **Function `_init_database()`**: Initialize security database
  - **Function `_create_default_admin()`**: Create default admin user if none exists
  - **Function `decorator()`**: Signature: ()
  - **Function `decorator()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\smart_automation.py`
- **Class `WorkflowStatus`**: Workflow execution status.
- **Class `TaskType`**: Types of tasks in workflows.
- **Class `TriggerType`**: Types of workflow triggers.
- **Class `WorkflowTask`**: Individual task within a workflow.
- **Class `WorkflowTrigger`**: Workflow trigger configuration.
- **Class `WorkflowDefinition`**: Complete workflow definition.
- **Class `WorkflowExecution`**: Workflow execution instance.
- **Class `SmartAutomationEngine`**: Advanced automation and workflow management system.
- **Class `PatternDetector`**: Detects automation patterns from user behavior.
  - **Function `create_simple_workflow()`**: Create a simple workflow from action names.
  - **Function `execute_workflow_by_name()`**: Execute a workflow by name.
  - **Function `suggest_automation_from_pattern()`**: Get automation suggestions based on pattern description.
  - **Function `get_workflow_status_simple()`**: Get simple workflow status description.
  - **Function `to_dict()`**: Signature: (self)
  - **Function `from_dict()`**: Signature: (cls, data)
  - **Function `to_dict()`**: Signature: (self)
  - **Function `from_dict()`**: Signature: (cls, data)
  - **Function `to_dict()`**: Signature: (self)
  - **Function `from_dict()`**: Signature: (cls, data)
  - **Function `add_log()`**: Add log entry with timestamp.
  - **Function `__init__()`**: Signature: (self)
  - **Function `_init_database()`**: Initialize SQLite database for workflow storage.
  - **Function `_register_built_in_functions()`**: Register built-in functions for workflows.
  - **Function `register_function()`**: Register a function for use in workflows.
  - **Function `create_workflow()`**: Create a new workflow.
  - **Function `execute_workflow()`**: Execute a workflow.
  - **Function `_execute_workflow_thread()`**: Execute workflow in separate thread.
  - **Function `_execute_task()`**: Execute a single task.
  - **Function `_execute_action_task()`**: Execute an action task.
  - **Function `_execute_condition_task()`**: Execute a condition task.
  - **Function `_execute_delay_task()`**: Execute a delay task.
  - **Function `_execute_loop_task()`**: Execute a loop task.
  - **Function `_resolve_parameters()`**: Resolve parameter placeholders.
  - **Function `_build_task_graph()`**: Build task dependency graph.
  - **Function `suggest_workflow_from_pattern()`**: Suggest a workflow based on detected patterns.
  - **Function `create_workflow_from_pattern()`**: Create a workflow from a detected pattern.
  - **Function `pause_workflow()`**: Pause a running workflow.
  - **Function `cancel_workflow()`**: Cancel a running workflow.
  - **Function `get_workflow_status()`**: Get status of workflow execution.
  - **Function `list_workflows()`**: List all workflows.
  - **Function `delete_workflow()`**: Delete a workflow.
  - **Function `_schedule_workflow_triggers()`**: Schedule workflow triggers.
  - **Function `_add_scheduled_workflow()`**: Add scheduled workflow to scheduler.
  - **Function `_run_scheduler()`**: Run the scheduler in background thread.
  - **Function `_save_workflow()`**: Save workflow to database.
  - **Function `_save_execution()`**: Save execution results to database.
  - **Function `_load_workflows()`**: Load workflows from database.
  - **Function `cleanup()`**: Cleanup resources.
  - **Function `__init__()`**: Signature: (self)
  - **Function `record_action()`**: Record user action for pattern detection.
  - **Function `detect_patterns()`**: Detect automation patterns from action history.
  - **Function `_detect_time_patterns()`**: Detect time-based patterns.
  - **Function `_detect_sequence_patterns()`**: Detect action sequence patterns.

### File: `core_ai\src\ai_assistant\automation\system_automation.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\automation\taskbar_detection.py`
- **Class `TaskbarDetector`**: Detects and analyzes Windows taskbar and running applications.
  - **Function `detect_taskbar_apps()`**: Main function to detect and describe taskbar applications.
  - **Function `can_see_taskbar()`**: Check if the assistant can see and analyze the taskbar.
  - **Function `__init__()`**: Signature: (self)
  - **Function `get_running_applications()`**: Get detailed information about all running applications.
  - **Function `_get_window_information()`**: Get information about all visible windows using win32gui.
  - **Function `get_taskbar_apps_visual()`**: Use computer vision to analyze the taskbar and identify apps.
  - **Function `get_taskbar_region_analysis()`**: Capture and analyze just the taskbar region for more focused results.
  - **Function `get_complete_desktop_analysis()`**: Provide a complete analysis combining process detection and visual analysis.
  - **Function `find_specific_app_in_taskbar()`**: Look for a specific application in the taskbar.
  - **Function `enum_window_callback()`**: Signature: ()

### File: `core_ai\src\ai_assistant\automation\task_planner.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\automation\task_scheduler.py`
- **Class `ScheduleType`**: Types of schedule patterns
- **Class `ScheduleStatus`**: Schedule status
- **Class `BusinessHours`**: Business hour patterns
- **Class `ScheduleCondition`**: Condition for conditional scheduling
- **Class `ScheduleConstraint`**: Constraints for schedule execution
- **Class `ScheduledTask`**: Scheduled task definition
- **Class `ExecutionRecord`**: Record of task execution
- **Class `CronParser`**: Advanced cron pattern parser with extended features
- **Class `ScheduleEvaluator`**: Evaluates schedule conditions and constraints
- **Class `LoadBalancer`**: Intelligent load balancer for scheduled tasks
- **Class `AdvancedTaskScheduler`**: Advanced task scheduler with intelligent scheduling and load management
  - **Function `create_cron_task()`**: Create a cron-scheduled task
  - **Function `create_interval_task()`**: Create an interval-scheduled task
  - **Function `create_daily_task()`**: Create a daily scheduled task
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `parse_pattern()`**: Parse cron pattern and return croniter object
  - **Function `_validate_pattern()`**: Validate cron pattern format
  - **Function `_validate_field()`**: Validate individual cron field
  - **Function `get_next_execution()`**: Get next execution time for pattern
  - **Function `describe_pattern()`**: Get human-readable description of cron pattern
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `should_execute()`**: Determine if task should execute now
  - **Function `_is_business_hours()`**: Check if current time is within business hours
  - **Function `_is_holiday()`**: Check if current date is a holiday
  - **Function `_get_daily_execution_count()`**: Get number of executions today (simplified - would need execution history)
  - **Function `_evaluate_condition()`**: Evaluate custom condition
  - **Function `_compare_values()`**: Compare values based on operator
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `calculate_optimal_delay()`**: Calculate optimal delay before execution based on system load
  - **Function `_calculate_historical_delay()`**: Calculate delay based on historical performance
  - **Function `should_defer_execution()`**: Determine if execution should be deferred due to high load
  - **Function `__init__()`**: Signature: (self, db_path)
  - **Function `start()`**: Start the scheduler
  - **Function `stop()`**: Stop the scheduler
  - **Function `schedule_task()`**: Schedule a new task
  - **Function `unschedule_task()`**: Remove scheduled task
  - **Function `pause_task()`**: Pause scheduled task
  - **Function `resume_task()`**: Resume paused task
  - **Function `get_task_info()`**: Get information about scheduled task
  - **Function `list_tasks()`**: List all scheduled tasks
  - **Function `get_execution_history()`**: Get execution history for task
  - **Function `get_scheduler_stats()`**: Get scheduler statistics
  - **Function `_scheduler_loop()`**: Main scheduler loop
  - **Function `_executor_loop()`**: Main executor loop
  - **Function `_execute_task()`**: Execute scheduled task
  - **Function `_calculate_next_execution()`**: Calculate next execution time for task
  - **Function `_parse_interval()`**: Parse interval string to seconds
  - **Function `_validate_task()`**: Validate task before scheduling
  - **Function `_add_to_queue()`**: Add task to execution queue
  - **Function `_reschedule_recurring_tasks()`**: Reschedule recurring tasks that need updating
  - **Function `_cleanup_expired_tasks()`**: Remove expired tasks
  - **Function `_init_database()`**: Initialize database for task storage
  - **Function `_save_task()`**: Save task to database
  - **Function `_load_tasks()`**: Load tasks from database
  - **Function `_delete_task()`**: Delete task from database

### File: `core_ai\src\ai_assistant\automation\templates.py`
- **Class `TemplateCategory`**: Template categories
- **Class `TemplateType`**: Template types
- **Class `ParameterType`**: Parameter types for templates
- **Class `TemplateParameter`**: Template parameter definition
- **Class `TemplateStep`**: Individual step in template workflow
- **Class `AutomationTemplate`**: Automation template definition
- **Class `RenderedTemplate`**: Rendered template ready for execution
- **Class `TemplateLibrary`**: Library of automation templates
- **Class `TemplateManager`**: Main template management system
  - **Function `create_simple_task_template()`**: Create simple single-task template
  - **Function `create_workflow_template()`**: Create workflow template from step definitions
  - **Function `validate()`**: Validate parameter value
  - **Function `_validate_type()`**: Validate parameter type
  - **Function `_validate_rules()`**: Validate custom rules
  - **Function `validate_parameters()`**: Validate template parameters
  - **Function `render_with_parameters()`**: Render template with parameter values
  - **Function `_render_step()`**: Render template step with parameters
  - **Function `_render_data()`**: Render data structure with parameters
  - **Function `_render_string()`**: Render string template with parameters
  - **Function `to_automation_definition()`**: Convert to automation system definition
  - **Function `__init__()`**: Signature: (self, library)
  - **Function `add_template()`**: Add template to library
  - **Function `get_template()`**: Get template by ID
  - **Function `search_templates()`**: Search templates with enhanced filtering
  - **Function `list_categories()`**: List template categories with counts
  - **Function `get_popular_templates()`**: Get popular templates
  - **Function `create_template_from_workflow()`**: Create template from existing workflow
  - **Function `export_template()`**: Export template to file
  - **Function `import_template()`**: Import template from file
  - **Function `_validate_template()`**: Validate template structure
  - **Function `_load_builtin_templates()`**: Load built-in automation templates
  - **Function `_discover_user_templates()`**: Discover user-created templates
  - **Function `_save_template_file()`**: Save template to file
  - **Function `_extract_parameters_from_workflow()`**: Extract parameterizable values from workflow
  - **Function `_convert_workflow_steps()`**: Convert workflow steps to template steps
  - **Function `_create_file_copy_template()`**: Create file copy template
  - **Function `_create_backup_template()`**: Create backup template
  - **Function `_create_log_analysis_template()`**: Create log analysis template
  - **Function `_create_api_monitoring_template()`**: Create API monitoring template
  - **Function `_create_database_backup_template()`**: Create database backup template
  - **Function `_create_email_notification_template()`**: Create email notification template
  - **Function `_create_system_health_check_template()`**: Create system health check template
  - **Function `_create_file_cleanup_template()`**: Create file cleanup template
  - **Function `__init__()`**: Signature: (self, library)
  - **Function `create_automation_from_template()`**: Create automation instance from template
  - **Function `validate_template_parameters()`**: Validate template parameters
  - **Function `get_template_info()`**: Get template information
  - **Function `search_templates()`**: Search templates with enhanced filtering
  - **Function `get_template_categories()`**: Get template categories with metadata
  - **Function `get_popular_templates()`**: Get popular templates
  - **Function `create_custom_template()`**: Create custom template
  - **Function `clone_template()`**: Clone existing template
  - **Function `_update_usage_stats()`**: Update template usage statistics
  - **Function `_setup_validators()`**: Setup template validators
  - **Function `_get_category_description()`**: Get description for template category

### File: `core_ai\src\ai_assistant\automation\visual_automation.py`
- **Class `VisualAutomationEngine`**: VLM-powered visual automation engine.
  - **Function `click_element()`**: Quick function to click an element by description.
  - **Function `type_into_field()`**: Quick function to type into a field.
  - **Function `automate_task()`**: Quick function to plan and execute a task.
  - **Function `__init__()`**: Initialize visual automation engine.
  - **Function `find_and_click()`**: Find UI element by description and click it.
  - **Function `find_and_type()`**: Find input field and type text.
  - **Function `execute_visual_workflow()`**: Execute multi-step visual workflow.
  - **Function `plan_and_execute()`**: Use VLM to plan a task and optionally execute it.
  - **Function `_verify_action_result()`**: Verify that an action had the expected effect.
  - **Function `get_action_history()`**: Get recent action history.
  - **Function `clear_history()`**: Clear action history.

### File: `core_ai\src\ai_assistant\automation\visual_verification.py`
- **Class `VerificationResult`**: Result of visual verification
- **Class `VisualAutomationVerifier`**: Verifies automation success using computer vision
  - **Function `get_visual_verifier()`**: Get global verifier instance
  - **Function `__init__()`**: Initialize verifier
  - **Function `capture_screenshot()`**: Capture current screen
  - **Function `verify_action()`**: Verify that an automation action succeeded
  - **Function `verify_app_launched()`**: Verify that an application was launched successfully
  - **Function `_detect_error_dialogs()`**: Detect if error dialogs are present
  - **Function `_check_window_title()`**: Check if expected window title is visible
  - **Function `_calculate_confidence()`**: Calculate confidence score for verification
  - **Function `_save_diff_image()`**: Save difference image with highlighting
  - **Function `_get_unknown_result()`**: Get result for failed verification
  - **Function `get_success_rate()`**: Get verification success statistics

### File: `core_ai\src\ai_assistant\cli\app_manager.py`
  - **Function `register_app_interactive()`**: Interactive app registration process.
  - **Function `list_apps()`**: List all registered apps.
  - **Function `launch_app()`**: Launch an app.
  - **Function `stop_app()`**: Stop an app.
  - **Function `remove_app()`**: Remove an app.
  - **Function `app_status()`**: Show detailed app status.
  - **Function `main()`**: Main CLI entry point.

### File: `core_ai\src\ai_assistant\cli\launch_assistant.py`
- **Class `SystemChecker`**: Comprehensive system compatibility checker
  - **Function `install_missing_dependencies()`**: Install missing critical dependencies
  - **Function `download_voice_models()`**: Download required voice models
  - **Function `start_assistant()`**: Start the Pulsar Assistant
  - **Function `main()`**: Main launcher function
  - **Function `__init__()`**: Signature: (self)
  - **Function `check_python_version()`**: Check Python version compatibility
  - **Function `check_dependencies()`**: Check critical dependencies
  - **Function `check_models()`**: Check if AI models are available
  - **Function `check_audio_system()`**: Check audio system compatibility
  - **Function `check_config_files()`**: Check configuration files
  - **Function `run_full_check()`**: Run complete system check

### File: `core_ai\src\ai_assistant\cli\mcp_cli.py`
- **Class `MCPCli`**: CLI interface for MCP management
  - **Function `__init__()`**: Signature: (self)

### File: `core_ai\src\ai_assistant\core\access_control.py`
- **Class `Permission`**: System permissions
- **Class `Role`**: User roles with predefined permission sets
- **Class `User`**: User with role and permissions
- **Class `AccessControlManager`**: Central access control manager for the AI Assistant
  - **Function `get_role_permissions()`**: Get default permissions for a role
  - **Function `get_access_control()`**: Get global access control manager
  - **Function `require_permission()`**: Decorator to require permission for function execution
  - **Function `require_admin()`**: Require admin role
  - **Function `require_system_access()`**: Require system command execution permission
  - **Function `require_file_write()`**: Require file write permission
  - **Function `require_data_access()`**: Require data read permission
  - **Function `has_permission()`**: Check if user has specific permission
  - **Function `to_dict()`**: Convert to dictionary for serialization
  - **Function `__init__()`**: Initialize access control manager
  - **Function `_load_config()`**: Load access control configuration
  - **Function `_save_config()`**: Save access control configuration
  - **Function `_ensure_admin_user()`**: Ensure at least one admin user exists
  - **Function `create_user()`**: Create a new user
  - **Function `get_user()`**: Get user by ID
  - **Function `get_user_by_session()`**: Get user by session ID
  - **Function `create_session()`**: Create user session
  - **Function `end_session()`**: End user session
  - **Function `check_permission()`**: Check if user has specific permission
  - **Function `grant_permission()`**: Grant custom permission to user
  - **Function `revoke_permission()`**: Revoke custom permission from user
  - **Function `change_user_role()`**: Change user role
  - **Function `decorator()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()
  - **Function `test_system_command()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\action_chain_models.py`
- **Class `ChainStatus`**: Status of action chain execution
- **Class `ActionType`**: Types of actions in a chain
- **Class `Action`**: Single action in a chain
- **Class `ActionChain`**: Complete chain of actions
- **Class `ExecutionReport`**: Report of chain execution
- **Class `ProgressReport`**: Real-time progress report
  - **Function `generate_chain_id()`**: Generate unique chain ID
  - **Function `generate_action_id()`**: Generate unique action ID
  - **Function `to_dict()`**: Convert to dictionary
  - **Function `total_actions()`**: Total number of actions
  - **Function `progress_percentage()`**: Overall progress percentage
  - **Function `duration_seconds()`**: Total execution duration
  - **Function `to_dict()`**: Convert to dictionary
  - **Function `to_dict()`**: Convert to dictionary
  - **Function `to_dict()`**: Convert to dictionary

### File: `core_ai\src\ai_assistant\core\app_discovery.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\core\app_integrator.py`
- **Class `AppIntegration`**: Represents an app integration configuration.
- **Class `SecureAppIntegrator`**: Manages secure integration with third-party applications.
  - **Function `__post_init__()`**: Signature: (self)
  - **Function `__init__()`**: Signature: (self, assistant_config)
  - **Function `register_app()`**: Register a new app integration.
  - **Function `_determine_security_level()`**: Determine security level based on permissions and integration type.
  - **Function `launch_app()`**: Securely launch an integrated application.
  - **Function `_delayed_launch()`**: Launch app after delay.
  - **Function `_launch_process()`**: Actually launch the process.
  - **Function `stop_app()`**: Stop a running integrated application.
  - **Function `list_running_apps()`**: List currently running integrated applications.
  - **Function `cleanup_terminated_processes()`**: Clean up terminated processes from running integrations.
  - **Function `get_app_status()`**: Get detailed status of an integrated application.
  - **Function `auto_start_apps()`**: Auto-start applications that are configured for auto-start.

### File: `core_ai\src\ai_assistant\core\app_security.py`
- **Class `SecureAppManager`**: Manages secure app integrations with encryption and access controls.
  - **Function `__init__()`**: Signature: (self, config_dir)
  - **Function `_initialize_encryption()`**: Initialize encryption for sensitive data.
  - **Function `encrypt_data()`**: Encrypt sensitive data.
  - **Function `decrypt_data()`**: Decrypt sensitive data.
  - **Function `store_app_credentials()`**: Securely store app credentials.
  - **Function `load_app_credentials()`**: Load and decrypt app credentials.
  - **Function `register_secure_app()`**: Register an app with secure configuration.
  - **Function `get_app_access_token()`**: Get access token for an app (if available).
  - **Function `validate_app_permissions()`**: Validate if an app has required permissions.
  - **Function `list_registered_apps()`**: List all registered apps (without sensitive data).
  - **Function `remove_app()`**: Remove an app and its credentials.

### File: `core_ai\src\ai_assistant\core\assistant.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\core\audit_logger.py`
- **Class `EventType`**: Types of audit events
- **Class `SeverityLevel`**: Event severity levels
- **Class `AuditEvent`**: Audit event structure
- **Class `AuditLogger`**: Comprehensive audit logging system
  - **Function `get_audit_logger()`**: Get global audit logger instance
  - **Function `audit_auth_success()`**: Log successful authentication
  - **Function `audit_auth_failure()`**: Log failed authentication
  - **Function `audit_system_command()`**: Log system command execution
  - **Function `audit_api_request()`**: Log API request
  - **Function `audit_data_access()`**: Log data access
  - **Function `audit_security_event()`**: Log security event
  - **Function `to_dict()`**: Convert to dictionary for serialization
  - **Function `from_dict()`**: Create from dictionary
  - **Function `__init__()`**: Initialize audit logger
  - **Function `_init_database()`**: Initialize audit database
  - **Function `_generate_event_id()`**: Generate unique event ID
  - **Function `_calculate_checksum()`**: Calculate integrity checksum for event data
  - **Function `log_event()`**: Log an audit event
  - **Function `start_processing()`**: Start background event processing
  - **Function `_process_events()`**: Background thread for processing audit events
  - **Function `_store_event()`**: Store event in database
  - **Function `_write_file_log()`**: Write event to daily log file
  - **Function `_check_security_patterns()`**: Check for security patterns and generate alerts
  - **Function `_generate_security_alert()`**: Generate security alert
  - **Function `query_events()`**: Query audit events with filters
  - **Function `get_security_alerts()`**: Get security alerts
  - **Function `generate_compliance_report()`**: Generate compliance report for given date range
  - **Function `cleanup_old_logs()`**: Clean up old audit logs
  - **Function `stop()`**: Stop audit logging

### File: `core_ai\src\ai_assistant\core\auto_updater.py`
- **Class `Version`**: Semantic version comparison
- **Class `AutoUpdater`**: Automatic update checker and installer
  - **Function `get_updater()`**: Get singleton updater instance
  - **Function `__init__()`**: Initialize auto-updater
  - **Function `__str__()`**: Signature: (self)
  - **Function `__gt__()`**: Signature: (self, other)
  - **Function `__eq__()`**: Signature: (self, other)
  - **Function `__init__()`**: Initialize auto-updater
  - **Function `_load_config()`**: Load update configuration
  - **Function `_save_config()`**: Save update configuration
  - **Function `should_check_for_updates()`**: Check if it's time to check for updates
  - **Function `check_for_updates()`**: Check for updates from GitHub Releases
  - **Function `download_update()`**: Download update ZIP file
  - **Function `install_update()`**: Install downloaded update
  - **Function `ignore_version()`**: Ignore a specific version
  - **Function `get_update_info()`**: Get current update information
  - **Function `check_for_updates_async()`**: Check for updates in background thread
  - **Function `_check()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\backup_manager.py`
- **Class `BackupManager`**: Core component.
  - **Function `__init__()`**: Signature: (self)
  - **Function `backup_settings()`**: Create a zip backup of the config directory
  - **Function `list_backups()`**: List all available backups

### File: `core_ai\src\ai_assistant\core\biometric_encryption.py`
- **Class `BiometricEncryptionError`**: Base exception for biometric encryption errors
- **Class `BiometricEncryption`**: Manages encryption/decryption of biometric data with secure key management.
  - **Function `get_biometric_encryptor()`**: Get global BiometricEncryption instance (singleton pattern).
  - **Function `__init__()`**: Initialize biometric encryption manager.
  - **Function `_initialize_cipher()`**: Initialize Fernet cipher with derived key.
  - **Function `_derive_key()`**: Derive encryption key from password using PBKDF2.
  - **Function `encrypt_biometric()`**: Encrypt biometric data (model, fingerprint, embedding, etc.).
  - **Function `decrypt_biometric()`**: Decrypt biometric data.
  - **Function `save_encrypted_model()`**: Save encrypted biometric model to disk.
  - **Function `load_encrypted_model()`**: Load and decrypt biometric model from disk.
  - **Function `migrate_legacy_model()`**: Migrate unencrypted legacy model to encrypted format.
  - **Function `rotate_keys()`**: Rotate encryption keys by re-encrypting all models with new key.
  - **Function `get_encryption_info()`**: Get information about encryption configuration.

### File: `core_ai\src\ai_assistant\core\chain_of_actions_manager.py`
- **Class `ChainOfActionsManager`**: Central manager for chain-of-actions execution
  - **Function `get_chain_manager()`**: Get singleton chain manager
  - **Function `__init__()`**: Initialize manager
  - **Function `_map_action_type()`**: Map TaskPlanner action type to ActionType enum
  - **Function `_infer_intent()`**: Infer intent from action type
  - **Function `_estimate_remaining_time()`**: Estimate remaining execution time
  - **Function `subscribe_progress()`**: Subscribe to progress updates
  - **Function `get_chain()`**: Get chain by ID
  - **Function `get_stats()`**: Get manager statistics
  - **Function `_run_browser_task()`**: Signature: ()
  - **Function `_run_app_task()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\config_loader.py`
- **Class `ConfigurationError`**: Configuration related errors
- **Class `Config`**: Configuration manager for AI Assistant
  - **Function `get_config()`**: Get global configuration instance (singleton)
  - **Function `load_config()`**: Load configuration from .env file
  - **Function `__init__()`**: Initialize configuration loader
  - **Function `_load_config()`**: Load configuration from .env file
  - **Function `_validate_config()`**: Validate configuration has required values
  - **Function `get()`**: Get configuration value
  - **Function `__getitem__()`**: Get configuration value using dict syntax
  - **Function `__contains__()`**: Check if configuration key exists
  - **Function `to_dict()`**: Get all configuration as dictionary
  - **Function `reload()`**: Reload configuration from .env file

### File: `core_ai\src\ai_assistant\core\config_validator.py`
- **Class `ConfigValidator`**: Validates application configuration and API keys
  - **Function `validate_config()`**: Validate configuration and optionally exit on failure
  - **Function `quick_check()`**: Quick validation check without detailed output
  - **Function `__init__()`**: Initialize configuration validator
  - **Function `load_environment()`**: Load environment variables from .env file
  - **Function `validate_required_keys()`**: Validate all required configuration keys
  - **Function `validate_optional_keys()`**: Check which optional features are configured
  - **Function `validate_feature_dependencies()`**: Validate that enabled features have required configuration
  - **Function `validate_file_paths()`**: Validate required directories exist and create them if needed
  - **Function `validate_google_credentials()`**: Check if Google credentials.json exists for Calendar/Gmail
  - **Function `validate()`**: Run complete validation
  - **Function `_print_results()`**: Print validation results
  - **Function `get_config()`**: Get configuration value

### File: `core_ai\src\ai_assistant\core\context_optimizer.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\core\conversation_context.py`
- **Class `ExecutionState`**: States of task execution.
- **Class `ConversationContext`**: Container for conversation context.
- **Class `ContextManager`**: Manages conversation context with persistence.
  - **Function `get_context_manager()`**: Get singleton context manager.
  - **Function `__post_init__()`**: Signature: (self)
  - **Function `to_dict()`**: Convert to dictionary.
  - **Function `from_dict()`**: Create from dictionary.
  - **Function `__init__()`**: Initialize context manager.
  - **Function `set_var()`**: Set a context variable.
  - **Function `get_var()`**: Get a context variable.
  - **Function `has_var()`**: Check if context variable exists.
  - **Function `delete_var()`**: Delete a context variable.
  - **Function `clear_vars()`**: Clear all context variables.
  - **Function `set_state()`**: Set execution state.
  - **Function `get_state()`**: Get current execution state.
  - **Function `set_task_chain()`**: Set current task chain.
  - **Function `get_task_chain()`**: Get current task chain.
  - **Function `advance_step()`**: Move to next step in task chain.
  - **Function `get_current_step()`**: Get current step number.
  - **Function `clear_task_chain()`**: Clear task chain.
  - **Function `add_command()`**: Add command to history.
  - **Function `get_last_command()`**: Get last command from history.
  - **Function `get_command_history()`**: Get recent command history.
  - **Function `is_override()`**: Detect if new command is an override of current task.
  - **Function `handle_override()`**: Handle command override.
  - **Function `infer_missing_params()`**: Infer missing parameters from context.
  - **Function `save_context()`**: Save context to disk.
  - **Function `load_context()`**: Load context from disk.
  - **Function `reset()`**: Reset context to initial state.
  - **Function `get_summary()`**: Get context summary.

### File: `core_ai\src\ai_assistant\core\core.py`
  - **Function `extract_number()`**: Extract a number from text (supports both digits and words).
  - **Function `write_a_note()`**: Opens Notepad, types a message, and closes it without saving.
  - **Function `open_application()`**: Opens any application on the computer using intelligent discovery.
  - **Function `open_settings_page()`**: Opens a specific Windows settings page using ms-settings URI.
  - **Function `search_google()`**: Searches for a query on Google in the default web browser.
  - **Function `search_youtube()`**: Searches for a query on YouTube in the default web browser.
  - **Function `close_application()`**: Closes an open application by its window name.
  - **Function `speak()`**: Speaks a given text string out loud.
  - **Function `set_system_volume()`**: Sets the system's master volume to a specific level (0-100).
  - **Function `get_system_volume()`**: Gets the current system volume level (0-100).
  - **Function `volume_up()`**: Increases system volume by specified increment.
  - **Function `volume_down()`**: Decreases system volume by specified decrement.
  - **Function `mute_volume()`**: Mutes system volume.
  - **Function `unmute_volume()`**: Unmutes system volume.
  - **Function `make_phone_call()`**: Initiates a phone call (stub function for future implementation). This is a placeholder for phone calling functionality.
  - **Function `process_hinglish_command()`**: Processes Hinglish commands and maps them to appropriate functions.
  - **Function `scan_and_save_apps()`**: Scans the Windows Start Menu for.lnk shortcuts and saves them to apps.json.
  - **Function `get_app_path_from_name()`**: Loads the apps.json file and finds the path for a given app name.
  - **Function `write_to_file()`**: Creates a new text file (like.txt or.md) or a simple PDF and writes the given content to it. :param filename: The name of the file to create (e.g.,...

### File: `core_ai\src\ai_assistant\core\custom_commands.py`
- **Class `CustomCommandManager`**: Core component.
  - **Function `__init__()`**: Signature: (self, data_dir)
  - **Function `_load_commands()`**: Signature: (self)
  - **Function `_save_commands()`**: Signature: (self)
  - **Function `add_alias()`**: Signature: (self, alias, commands)
  - **Function `remove_alias()`**: Signature: (self, alias)
  - **Function `resolve_command()`**: Returns a list of commands. If it's an alias, returns the mapped commands.

### File: `core_ai\src\ai_assistant\core\database_config.py`
  - **Function `get_db_path()`**: Get the path to a database file.
  - **Function `get_db_path_str()`**: Get the path to a database file as a string.
  - **Function `list_databases()`**: List all configured databases and their paths.
  - **Function `database_exists()`**: Check if a database file exists.
  - **Function `get_database_size()`**: Get the size of a database file in bytes.
  - **Function `migrate_legacy_databases()`**: Migrate databases from root directory to data/ directory. This should be called once during application startup.

### File: `core_ai\src\ai_assistant\core\encrypted_database.py`
- **Class `EncryptedDatabase`**: Database wrapper that provides transparent encryption for sensitive fields.
  - **Function `create_encrypted_memory_db()`**: Create encrypted database for conversation memory
  - **Function `create_encrypted_conversation_db()`**: Create encrypted database for conversation AI
  - **Function `create_encrypted_credentials_db()`**: Create encrypted database for API credentials
  - **Function `__init__()`**: Initialize encrypted database wrapper.
  - **Function `add_encrypted_field()`**: Mark a field as encrypted for automatic handling
  - **Function `_is_encrypted_field()`**: Check if a field should be encrypted
  - **Function `_encrypt_value()`**: Encrypt a field value
  - **Function `_decrypt_value()`**: Decrypt a field value
  - **Function `_process_row_for_encryption()`**: Process a row for encryption/decryption
  - **Function `get_connection()`**: Get database connection with proper cleanup
  - **Function `execute()`**: Execute a SQL command with automatic encryption
  - **Function `insert()`**: Insert data with automatic encryption
  - **Function `select()`**: Select data with automatic decryption
  - **Function `update()`**: Update data with automatic encryption
  - **Function `delete()`**: Delete records (no encryption needed)
  - **Function `migrate_to_encrypted()`**: Migrate existing table data to encrypted format

### File: `core_ai\src\ai_assistant\core\encryption.py`
- **Class `EncryptionError`**: Custom exception for encryption-related errors
- **Class `SecureEncryption`**: Secure encryption/decryption utility for AI Assistant data.
- **Class `DatabaseEncryption`**: Encryption helper for database fields
- **Class `ConfigEncryption`**: Encryption helper for configuration files
  - **Function `get_encryption()`**: Get global encryption instance
  - **Function `get_db_encryption()`**: Get database encryption helper
  - **Function `get_config_encryption()`**: Get configuration encryption helper
  - **Function `encrypt_sensitive_data()`**: Convenience function to encrypt sensitive data
  - **Function `decrypt_sensitive_data()`**: Convenience function to decrypt sensitive data
  - **Function `__init__()`**: Signature: (self, encryption)
  - **Function `_get_master_key()`**: Get master key from environment or generate new one
  - **Function `_generate_master_key()`**: Generate a new cryptographically secure master key
  - **Function `_save_master_key()`**: Save master key to secure location
  - **Function `_derive_key()`**: Derive encryption key from master key using PBKDF2
  - **Function `encrypt()`**: Encrypt data with AES-256-GCM
  - **Function `decrypt()`**: Decrypt AES-256-GCM encrypted data
  - **Function `encrypt_file()`**: Encrypt entire file contents
  - **Function `decrypt_file()`**: Decrypt and save file contents
  - **Function `__init__()`**: Signature: (self, encryption)
  - **Function `encrypt_field()`**: Encrypt a database field value
  - **Function `decrypt_field()`**: Decrypt a database field value
  - **Function `__init__()`**: Signature: (self, encryption)
  - **Function `encrypt_config()`**: Encrypt entire configuration dictionary
  - **Function `decrypt_config()`**: Decrypt configuration dictionary
  - **Function `encrypt_api_keys()`**: Encrypt API keys while preserving structure
  - **Function `decrypt_api_keys()`**: Decrypt API keys

### File: `core_ai\src\ai_assistant\core\enhanced_integration.py`
- **Class `EnhancedAI`**: Enhanced AI with all optimizations integrated
  - **Function `get_enhanced_ai()`**: Get global enhanced AI instance
  - **Function `__init__()`**: Initialize enhanced AI
  - **Function `_log_available_features()`**: Log which features are available
  - **Function `get_stats()`**: Get comprehensive statistics
  - **Function `optimize()`**: Run optimization on all components
  - **Function `print_chunk()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\input_sanitizer.py`
- **Class `InputSanitizer`**: Comprehensive input validation and sanitization
  - **Function `get_input_sanitizer()`**: Get global input sanitizer instance (singleton)
  - **Function `__init__()`**: Signature: (self)
  - **Function `sanitize_sql()`**: Sanitize input for SQL queries
  - **Function `validate_sql_input()`**: Validate if input is safe for SQL
  - **Function `sanitize_html()`**: Sanitize HTML input to prevent XSS
  - **Function `sanitize_command()`**: Sanitize system command to prevent command injection
  - **Function `validate_file_path()`**: Validate file path to prevent path traversal attacks
  - **Function `sanitize_file_path()`**: Sanitize file path
  - **Function `sanitize_filename()`**: Sanitize filename to remove dangerous characters
  - **Function `sanitize_url()`**: Sanitize and validate URL
  - **Function `sanitize_prompt()`**: Sanitize AI prompt to prevent prompt injection
  - **Function `sanitize_json()`**: Sanitize JSON data recursively
  - **Function `validate_email()`**: Validate email address format
  - **Function `validate_integer()`**: Validate integer input with optional range
  - **Function `sanitize_dict()`**: Sanitize dictionary by filtering keys and sanitizing values
  - **Function `_sanitize_recursive()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\input_validation.py`
- **Class `ValidationError`**: Custom exception for validation failures
- **Class `InputType`**: Types of input validation
- **Class `ValidationRule`**: Validation rule configuration
- **Class `InputValidator`**: Comprehensive input validation system
- **Class `WebSocketValidator`**: Specialized validator for WebSocket messages
- **Class `CLIValidator`**: Specialized validator for CLI command inputs
  - **Function `get_input_validator()`**: Get global input validator instance
  - **Function `get_websocket_validator()`**: Get WebSocket validator instance
  - **Function `get_cli_validator()`**: Get CLI validator instance
  - **Function `validate_api_input()`**: Validate API input data
  - **Function `validate_websocket_message()`**: Validate WebSocket message
  - **Function `validate_cli_command()`**: Validate CLI command arguments
  - **Function `validate_pin()`**: Validate PIN format
  - **Function `validate_email()`**: Validate email address
  - **Function `validate_file_upload()`**: Validate file upload parameters
  - **Function `__init__()`**: Signature: (self, input_validator)
  - **Function `__init__()`**: Signature: (self, input_validator)
  - **Function `validate_field()`**: Validate a single field against its rule
  - **Function `_validate_type()`**: Validate and convert value to expected type
  - **Function `_check_security_threats()`**: Check for common security threats in string inputs
  - **Function `_sanitize_string()`**: Sanitize string input based on type
  - **Function `validate_dict()`**: Validate a dictionary against a set of rules
  - **Function `validate_api_request()`**: Validate API request data based on endpoint
  - **Function `_get_api_rules()`**: Get validation rules for specific API endpoints
  - **Function `__init__()`**: Signature: (self, input_validator)
  - **Function `validate_message()`**: Validate WebSocket message
  - **Function `__init__()`**: Signature: (self, input_validator)
  - **Function `validate_command_args()`**: Validate CLI command arguments
  - **Function `validate_file_path()`**: Validate file path for CLI operations

### File: `core_ai\src\ai_assistant\core\interaction.py`
- **Class `InteractionManager`**: Manages direct interaction with the human user. Supports asking questions and requesting approval.
  - **Function `__init__()`**: Signature: (self)

### File: `core_ai\src\ai_assistant\core\memory_manager.py`
- **Class `MemoryManager`**: Manages shared context and memory for the agent system. Persists data to a JSON file.
  - **Function `__init__()`**: Signature: (self, storage_path)
  - **Function `_load()`**: Load memory from disk
  - **Function `_save()`**: Save memory to disk
  - **Function `set()`**: Set a value in memory
  - **Function `get()`**: Get a value from memory
  - **Function `delete()`**: Remove a key from memory
  - **Function `list_keys()`**: List all keys
  - **Function `clear()`**: Clear all memory

### File: `core_ai\src\ai_assistant\core\multi_agent_coordinator.py`
- **Class `MultiAgentCoordinator`**: Central coordinator for the Multi-Agent System. Handles task routing, agent assignment, and progress tracking.
  - **Function `__init__()`**: Signature: (self, registry)

### File: `core_ai\src\ai_assistant\core\onboarding.py`
- **Class `OnboardingManager`**: Core component.
  - **Function `__init__()`**: Signature: (self, settings_path)
  - **Function `_load_settings()`**: Signature: (self)
  - **Function `_save_settings()`**: Signature: (self)
  - **Function `is_onboarded()`**: Signature: (self)
  - **Function `set_onboarded()`**: Signature: (self, status)
  - **Function `get_onboarding_system_prompt()`**: Signature: (self)
  - **Function `process_onboarding_response()`**: Check if the onboarding is complete based on the LLM response. Returns (cleaned_response, is_complete)

### File: `core_ai\src\ai_assistant\core\performance_optimization.py`
- **Class `PerformanceLevel`**: Performance optimization levels
- **Class `ResourceType`**: System resource types
- **Class `CacheType`**: Cache implementation types
- **Class `PerformanceMetrics`**: Performance metrics data structure
- **Class `OptimizationSettings`**: Performance optimization settings
- **Class `SmartCache`**: Advanced caching system with multiple strategies
- **Class `MemoryManager`**: Advanced memory management and optimization
- **Class `AsyncTaskManager`**: Asynchronous task management and optimization
- **Class `DatabaseOptimizer`**: Database performance optimization
- **Class `PerformanceProfiler`**: Performance profiling and analysis
- **Class `ResourceMonitor`**: System resource monitoring and alerting
- **Class `PerformanceOptimizer`**: Main performance optimization manager
  - **Function `create_performance_decorator()`**: Create a performance optimization decorator
  - **Function `main()`**: Example usage of Performance Optimization
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `get()`**: Get value from cache
  - **Function `set()`**: Set value in cache
  - **Function `delete()`**: Delete key from cache
  - **Function `_evict()`**: Evict items based on cache type strategy
  - **Function `clear()`**: Clear entire cache
  - **Function `get_stats()`**: Get task manager statistics
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `monitor_memory()`**: Monitor current memory usage
  - **Function `optimize_memory()`**: Perform memory optimization
  - **Function `auto_memory_management()`**: Automatic memory management in background
  - **Function `get_memory_recommendations()`**: Get memory optimization recommendations
  - **Function `get_stats()`**: Get task manager statistics
  - **Function `cleanup()`**: Cleanup memory and return freed amount
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `initialize_loop()`**: Initialize async event loop
  - **Function `cleanup_completed_tasks()`**: Clean up completed task references
  - **Function `submit_task()`**: Submit a task for execution
  - **Function `get_task_status()`**: Get status of a specific task
  - **Function `get_stats()`**: Get task manager statistics
  - **Function `stop()`**: Stop the task manager
  - **Function `get_task_stats()`**: Get task execution statistics
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `get_connection()`**: Get database connection from pool
  - **Function `execute_query_cached()`**: Execute query with caching
  - **Function `optimize_database()`**: Optimize database performance
  - **Function `get_database_stats()`**: Get database performance statistics
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `profile_function()`**: Decorator to profile function performance
  - **Function `start_cpu_profile()`**: Start CPU profiling
  - **Function `stop_cpu_profile()`**: Stop CPU profiling and return results
  - **Function `get_function_stats()`**: Get statistics for a specific function
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `collect_metrics()`**: Collect current performance metrics
  - **Function `check_thresholds()`**: Check if metrics exceed thresholds and generate alerts
  - **Function `start_monitoring()`**: Start all monitoring systems
  - **Function `stop_monitoring()`**: Stop all monitoring systems
  - **Function `_monitor_loop()`**: Background monitoring loop
  - **Function `get_current_status()`**: Get current system status
  - **Function `__init__()`**: Signature: (self, settings)
  - **Function `register_database()`**: Register a database for optimization
  - **Function `optimize_all_systems()`**: Perform comprehensive system optimization
  - **Function `auto_optimize_check()`**: Check if auto-optimization should run
  - **Function `get_performance_summary()`**: Get comprehensive performance summary
  - **Function `start_monitoring()`**: Start all monitoring systems
  - **Function `stop_monitoring()`**: Stop all monitoring systems
  - **Function `performance_optimized()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\permission_system.py`
- **Class `PermissionLevel`**: Permission levels for operations
- **Class `RiskLevel`**: Risk levels for operations
- **Class `OperationRequest`**: Represents a request to perform an operation
- **Class `PermissionResult`**: Result of a permission check
- **Class `PermissionPolicy`**: Defines permission policies for different operation types
- **Class `PermissionSystem`**: Centralized permission and authorization system
  - **Function `get_permission_system()`**: Get global permission system instance (singleton)
  - **Function `require_permission()`**: Decorator to require permission for a function
  - **Function `__init__()`**: Signature: (self, config_path)
  - **Function `_load_default_policies()`**: Load default permission policies
  - **Function `get_policy()`**: Get policy for an operation type
  - **Function `__init__()`**: Signature: (self, config_path)
  - **Function `_load_permissions()`**: Load user permissions from config file
  - **Function `_save_permissions()`**: Save user permissions to config file
  - **Function `check_permission()`**: Check if an operation is permitted
  - **Function `_is_blacklisted()`**: Check if operation/resource is blacklisted
  - **Function `_is_whitelisted()`**: Check if operation/resource is whitelisted
  - **Function `_generate_confirmation_message()`**: Generate user-friendly confirmation message
  - **Function `grant_user_permission()`**: Grant a permission level to a user
  - **Function `revoke_user_permission()`**: Revoke a permission level from a user
  - **Function `add_to_whitelist()`**: Add an operation/resource to whitelist
  - **Function `add_to_blacklist()`**: Add an operation/resource to blacklist
  - **Function `request_user_confirmation()`**: Request user confirmation for an operation
  - **Function `decorator()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\privacy_consent.py`
- **Class `ConsentType`**: Types of consent that can be requested
- **Class `ConsentStatus`**: Status of consent
- **Class `ConsentRecord`**: Record of a single consent decision
- **Class `UserConsent`**: Complete consent profile for a user
- **Class `PrivacyConsentManager`**: Manages privacy consent for all users and data processing activities.
  - **Function `get_consent_manager()`**: Get global PrivacyConsentManager instance (singleton pattern)
  - **Function `is_valid()`**: Check if consent is currently valid
  - **Function `to_dict()`**: Convert to dictionary for JSON storage
  - **Function `from_dict()`**: Create from dictionary
  - **Function `__init__()`**: Initialize consent manager.
  - **Function `has_consent()`**: Check if user has granted valid consent for a specific type.
  - **Function `grant_consent()`**: Grant consent for a user.
  - **Function `deny_consent()`**: Explicitly deny consent (user said no).
  - **Function `withdraw_consent()`**: Withdraw previously granted consent (user changed mind).
  - **Function `get_user_consents()`**: Get all consent records for a user.
  - **Function `get_consent_summary()`**: Get summary of user's consent status.
  - **Function `export_user_data()`**: Export all consent data for a user (GDPR right to access).
  - **Function `delete_user_data()`**: Delete all consent data for a user (GDPR right to erasure).
  - **Function `_save_user_consent()`**: Save user consent to disk
  - **Function `_load_all_consents()`**: Load all existing consent records from disk
  - **Function `require_consent()`**: Decorator to require consent before executing a function.
  - **Function `decorator()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\privacy_protection.py`
- **Class `DataSensitivity`**: Data sensitivity classification
- **Class `ThreatLevel`**: Threat detection levels
- **Class `PrivacyRule`**: Privacy protection rule
- **Class `SensitiveLocation`**: Sensitive file/folder location
- **Class `PrivacyProtectionSystem`**: Advanced privacy protection system
  - **Function `get_privacy_protection()`**: Get global privacy protection instance (singleton)
  - **Function `is_request_safe()`**: Check if user request is safe
  - **Function `check_file_access_allowed()`**: Check if file access is allowed
  - **Function `sanitize_ai_response()`**: Sanitize AI response for privacy
  - **Function `__init__()`**: Initialize privacy protection system
  - **Function `_load_config()`**: Load privacy rules from config
  - **Function `_setup_default_sensitive_locations()`**: Setup default sensitive file/folder locations
  - **Function `analyze_request()`**: Analyze user request for privacy/security threats
  - **Function `check_file_access()`**: Check if file access should be allowed
  - **Function `redact_pii()`**: Redact personal identifiable information from text
  - **Function `sanitize_response()`**: Sanitize AI response to prevent data leakage
  - **Function `require_confirmation()`**: Check if action requires user confirmation
  - **Function `generate_confirmation_prompt()`**: Generate user-friendly confirmation prompt

### File: `core_ai\src\ai_assistant\core\proactive_anticipator.py`
- **Class `ProactiveAnticipator`**: Core component.
  - **Function `__init__()`**: Signature: (self, chat_interface)
  - **Function `start()`**: Signature: (self)
  - **Function `stop()`**: Signature: (self)
  - **Function `_schedule_loop()`**: Signature: (self)
  - **Function `_check_for_proactive_actions()`**: Signature: (self, now)

### File: `core_ai\src\ai_assistant\core\progress_tracker.py`
- **Class `PersistentProgressTracker`**: Persistent progress tracker using SQLite. Stores chain execution history and real-time status.
  - **Function `get_progress_tracker()`**: Get singleton progress tracker
  - **Function `__init__()`**: Initialize tracker with database path
  - **Function `_init_db()`**: Initialize database schema
  - **Function `start_chain()`**: Record start of a new chain
  - **Function `update_chain_status()`**: Update chain status and progress
  - **Function `record_action_start()`**: Record start of an action
  - **Function `update_action_status()`**: Update action status
  - **Function `save_chain_result()`**: Save final chain results
  - **Function `_calculate_duration()`**: Calculate duration for a chain
  - **Function `get_recent_chains()`**: Get list of recent execution chains
  - **Function `get_chain_details()`**: Get full details for a chain including actions

### File: `core_ai\src\ai_assistant\core\secrets_manager.py`
- **Class `SecretsValidationError`**: Raised when required secrets are missing or invalid.
- **Class `SecretsManager`**: Centralized secrets management with validation and secure defaults.
  - **Function `get_secrets_manager()`**: Get the global secrets manager instance.
  - **Function `get_secret()`**: Convenience function to get a secret.
  - **Function `generate_secret()`**: Generate a secure random secret.
  - **Function `__init__()`**: Initialize secrets manager.
  - **Function `_load_environment()`**: Load environment variables from .env file.
  - **Function `get_required()`**: Get a required secret. Raises error if not set or insecure.
  - **Function `get_optional()`**: Get an optional secret with fallback to default.
  - **Function `get_or_generate()`**: Get a secret or generate a secure one if not set.
  - **Function `_is_insecure_value()`**: Check if a value appears to be an insecure default.
  - **Function `validate_all_required()`**: Validate all required secrets are properly set.
  - **Function `generate_secure_value()`**: Generate a cryptographically secure random value.
  - **Function `hash_value()`**: Hash a value securely using PBKDF2.
  - **Function `print_setup_instructions()`**: Print instructions for setting up secrets.

### File: `core_ai\src\ai_assistant\core\system.py`
  - **Function `get_system_status()`**: Gets comprehensive system status including CPU, RAM, disk, and network info.
  - **Function `get_running_processes()`**: Gets information about currently running processes. :param limit: Number of top processes to show (by CPU usage)
  - **Function `cleanup_temp_files()`**: Cleans up temporary files and system cache.
  - **Function `get_network_info()`**: Gets detailed network information including active connections.
  - **Function `monitor_system_alerts()`**: Monitors system for potential issues and alerts.
  - **Function `get_system_info()`**: Gets detailed system information including OS, hardware, and Python environment.
  - **Function `get_battery_status()`**: Gets detailed battery status if available.

### File: `core_ai\src\ai_assistant\core\task_chain_orchestrator.py`
- **Class `ExecutionResult`**: Result of task chain execution.
- **Class `TaskChainOrchestrator`**: Orchestrates execution of multi-step task chains.
  - **Function `get_orchestrator()`**: Get singleton orchestrator.
  - **Function `__init__()`**: Initialize orchestrator.
  - **Function `execute_command()`**: Execute a command (single or multi-step).
  - **Function `execute_chain()`**: Execute a chain of task steps.
  - **Function `execute_step()`**: Execute a single task step.
  - **Function `_verify_step()`**: Verify that a step was ACTUALLY successful using 3-layer check: 1. Code Return (already checked) 2. System State (os.exists, process list) 3. Visua...
  - **Function `_check_dependencies()`**: Check if step dependencies are met.
  - **Function `_rollback_steps()`**: Attempt to rollback executed steps.
  - **Function `handle_override()`**: Handle a command override during execution.
  - **Function `get_current_status()`**: Get current execution status.
  - **Function `pause()`**: Pause current execution.
  - **Function `resume()`**: Resume paused execution.
  - **Function `cancel()`**: Cancel current execution.

### File: `core_ai\src\ai_assistant\core\tool_executor.py`
- **Class `ToolType`**: Tool execution type.
- **Class `ToolResult`**: Result from tool execution.
- **Class `ToolExecutor`**: Executes tools/functions called by LLM.
  - **Function `web_search()`**: Search the web for information.
  - **Function `execute_code()`**: Execute code (sandboxed).
  - **Function `get_current_time()`**: Get current date and time.
  - **Function `calculator()`**: Evaluate a mathematical expression.
  - **Function `get_default_executor()`**: Create executor with default tools.
  - **Function `to_dict()`**: Convert to dictionary.
  - **Function `__init__()`**: Initialize tool executor.
  - **Function `register_tool()`**: Register a tool that can be called by LLM.
  - **Function `get_tool_definitions()`**: Get all registered tool definitions in OpenAI format.
  - **Function `execute_tool()`**: Execute a registered tool.
  - **Function `execute_tool_call()`**: Execute a tool call from LLM response.
  - **Function `format_tool_result_for_llm()`**: Format tool result for sending back to LLM.
  - **Function `get_execution_history()`**: Get recent tool execution history.
  - **Function `clear_history()`**: Clear execution history.
  - **Function `evaluate()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\universal_app_controller.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\core\voice_access_control.py`
- **Class `Role`**: User roles with hierarchical permissions
- **Class `Permission`**: Granular permissions for voice operations
- **Class `User`**: User account with role and permissions
- **Class `Session`**: User session for authentication
- **Class `VoiceAccessControl`**: Manages access control for voice biometric operations.
  - **Function `get_voice_access_control()`**: Get global VoiceAccessControl instance
  - **Function `require_permission()`**: Decorator to require permission for a function.
  - **Function `has_permission()`**: Check if user has a specific permission
  - **Function `owns_speaker()`**: Check if user owns a speaker
  - **Function `is_valid()`**: Check if session is still valid
  - **Function `is_expired()`**: Check if session has expired
  - **Function `__init__()`**: Initialize access control system.
  - **Function `create_user()`**: Create a new user.
  - **Function `get_user()`**: Get user by ID
  - **Function `check_permission()`**: Check if user has permission.
  - **Function `can_modify_speaker()`**: Check if user can modify a speaker.
  - **Function `register_speaker_ownership()`**: Register speaker ownership.
  - **Function `remove_speaker_ownership()`**: Remove speaker ownership.
  - **Function `create_session()`**: Create a new session for user.
  - **Function `verify_mfa()`**: Mark session as MFA verified.
  - **Function `invalidate_session()`**: Invalidate a session (logout).
  - **Function `cleanup_expired_sessions()`**: Remove expired sessions.
  - **Function `_save_user()`**: Save user to disk
  - **Function `_load_users()`**: Load users from disk
  - **Function `decorator()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\voice_audit_logger.py`
- **Class `AuditEventType`**: Types of events that can be audited
- **Class `AuditSeverity`**: Severity levels for audit events
- **Class `AuditEvent`**: Single audit log entry
- **Class `VoiceAuditLogger`**: Audit logger for voice biometric operations.
  - **Function `get_voice_audit_logger()`**: Get global VoiceAuditLogger instance
  - **Function `to_dict()`**: Convert to dictionary for JSON storage
  - **Function `to_log_line()`**: Convert to single-line log format
  - **Function `__init__()`**: Initialize audit logger.
  - **Function `_generate_event_id()`**: Generate unique event ID
  - **Function `_write_event()`**: Write event to log file (append-only)
  - **Function `_rotate_logs()`**: Rotate log files when max size reached
  - **Function `log_event()`**: Log a general audit event.
  - **Function `log_speaker_enrollment()`**: Log speaker enrollment
  - **Function `log_verification_attempt()`**: Log speaker verification attempt
  - **Function `log_speaker_deletion()`**: Log speaker deletion
  - **Function `log_permission_check()`**: Log permission check
  - **Function `log_consent_change()`**: Log consent grant/withdrawal
  - **Function `log_api_usage()`**: Log external API usage
  - **Function `_check_suspicious_activity()`**: Check for suspicious activity patterns
  - **Function `get_user_audit_trail()`**: Get audit trail for a user (GDPR right to access).
  - **Function `get_resource_audit_trail()`**: Get audit trail for a specific resource (e.g., speaker).
  - **Function `get_recent_events()`**: Get recent audit events.

### File: `core_ai\src\ai_assistant\core\services\ai_service_manager.py`
- **Class `AIServiceManager`**: Manages AI services with lazy initialization
  - **Function `__init__()`**: Initialize AI service manager
  - **Function `multimodal_ai()`**: Get multimodal AI service (lazy loaded)
  - **Function `conversational_ai()`**: Get conversational AI service (lazy loaded)
  - **Function `llm_chat()`**: Get LLM chat service (lazy loaded)
  - **Function `get_status()`**: Get initialization status of all AI services

### File: `core_ai\src\ai_assistant\core\services\command_processor.py`
- **Class `CommandProcessor`**: Process user commands with multilingual support
  - **Function `__init__()`**: Initialize command processor
  - **Function `process_command()`**: Main command processing entry point
  - **Function `_fallback_response()`**: Fallback response when AI is not available
  - **Function `clear_history()`**: Clear conversation history
  - **Function `get_history()`**: Get recent conversation history

### File: `core_ai\src\ai_assistant\core\services\initialization_service.py`
- **Class `InitializationService`**: Manages initialization of assistant services
  - **Function `__init__()`**: Initialize service manager
  - **Function `initialize_memory()`**: Initialize memory system
  - **Function `background_initialize()`**: Background initialization of services
  - **Function `eager_initialize()`**: Eager initialization - load everything immediately
  - **Function `get_status()`**: Get initialization status
  - **Function `init()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\services\monitoring_service.py`
- **Class `MonitoringService`**: System monitoring and statistics service
  - **Function `__init__()`**: Initialize monitoring service
  - **Function `get_real_time_system_stats()`**: Get real-time system statistics
  - **Function `start_monitoring()`**: Start background system monitoring
  - **Function `get_process_info()`**: Get current process information
  - **Function `monitor()`**: Signature: ()

### File: `core_ai\src\ai_assistant\core\services\voice_service_manager.py`
- **Class `VoiceServiceManager`**: Manages voice services with lazy initialization
  - **Function `__init__()`**: Initialize voice service manager
  - **Function `voice_recognizer()`**: Get voice recognizer (lazy loaded)
  - **Function `tts_engine()`**: Get TTS engine (lazy loaded)
  - **Function `wake_word_detector()`**: Get wake word detector (lazy loaded)
  - **Function `start_listening()`**: Start voice listening
  - **Function `stop_listening()`**: Stop voice listening
  - **Function `speak()`**: Speak text using TTS
  - **Function `get_status()`**: Get initialization status of all voice services

### File: `core_ai\src\ai_assistant\integrations\email_handler.py`
- **Class `GmailManager`**: Manages Gmail API authentication and operations
  - **Function `setup_email_auth()`**: Sets up Gmail API authentication. Returns status message. User needs to run this once to authenticate.
  - **Function `get_gmail_service()`**: Helper function to get authenticated Gmail service.
  - **Function `get_inbox_summary()`**: Gets a summary of recent emails in the inbox. :param max_emails: Maximum number of emails to retrieve (default 10)
  - **Function `send_email()`**: Sends an email using Gmail API. :param to: Recipient email address :param subject: Email subject :param body: Email body content :param cc: CC reci...
  - **Function `search_emails()`**: Searches emails using Gmail search syntax. :param query: Search query (e.g., "from:someone@example.com", "subject:meeting") :param max_results: Max...
  - **Function `read_email_content()`**: Reads the full content of a specific email. :param email_id: Specific Gmail message ID :param sender: Filter by sender email/name :param subject_co...
  - **Function `get_unread_count()`**: Gets the count of unread emails in inbox.
  - **Function `mark_email_read()`**: Marks an email as read. :param email_id: Specific Gmail message ID :param sender: Filter by sender email/name   :param subject_contains: Filter by ...
  - **Function `delete_email()`**: Deletes an email (moves to trash). :param email_id: Specific Gmail message ID :param sender: Filter by sender email/name :param subject_contains: F...
  - **Function `compose_quick_reply()`**: Sends a quick reply with predefined templates. :param to: Recipient email address :param reply_type: Type of reply (acknowledge, thanks, meeting_ac...
  - **Function `extract_email_address()`**: Extracts email address from 'Name <email@domain.com>' format.
  - **Function `extract_display_name()`**: Extracts display name from 'Name <email@domain.com>' format.
  - **Function `extract_email_body()`**: Recursively extracts email body from Gmail API payload.
  - **Function `__new__()`**: Signature: (cls)
  - **Function `__init__()`**: Signature: (self)
  - **Function `setup_auth()`**: Sets up Gmail API authentication Returns status message
  - **Function `_get_setup_instructions()`**: Returns setup instructions for Gmail API
  - **Function `get_service()`**: Get authenticated Gmail service, initialize if needed
  - **Function `is_authenticated()`**: Check if Gmail is authenticated

### File: `core_ai\src\ai_assistant\integrations\google_calendar.py`
- **Class `CalendarManager`**: Manages Google Calendar API authentication and operations
  - **Function `setup_calendar_auth()`**: Sets up Google Calendar authentication. Returns status message. User needs to run this once to authenticate.
  - **Function `get_calendar_service()`**: Helper function to get authenticated calendar service.
  - **Function `get_upcoming_events()`**: Gets upcoming calendar events for the next N days. :param days_ahead: Number of days to look ahead (default 7)
  - **Function `create_calendar_event()`**: Creates a new calendar event. :param title: Event title :param date: Date in format 'YYYY-MM-DD' or 'MM/DD/YYYY' :param time: Time in format 'HH:MM...
  - **Function `get_todays_schedule()`**: Gets today's calendar schedule with a nice formatted view.
  - **Function `search_calendar_events()`**: Searches for calendar events containing the query. :param query: Search term to look for in event titles and descriptions :param days_back: How man...
  - **Function `delete_calendar_event()`**: Deletes a calendar event by title and optional date. :param event_title: Title of the event to delete :param date: Optional date to narrow down sea...
  - **Function `update_calendar_event()`**: Updates an existing calendar event. :param event_title: Title of the event to update :param date: Optional date to narrow down search (YYYY-MM-DD o...
  - **Function `__new__()`**: Signature: (cls)
  - **Function `__init__()`**: Signature: (self)
  - **Function `setup_auth()`**: Sets up Google Calendar authentication Returns status message
  - **Function `_get_setup_instructions()`**: Returns setup instructions for Google Calendar API
  - **Function `get_service()`**: Get authenticated calendar service, initialize if needed
  - **Function `is_authenticated()`**: Check if calendar is authenticated

### File: `core_ai\src\ai_assistant\integrations\learning_automation.py`
  - **Function `with_learning()`**: Decorator to add learning capabilities to automation functions Logs execution for learning and provides intelligent suggestions
  - **Function `get_smart_suggestion()`**: Get smart suggestion based on current task
  - **Function `predict_next_action()`**: Predict next action based on command history
  - **Function `enhance_voice_recognition()`**: Enhance voice recognition using adaptive learning
  - **Function `log_automation_workflow()`**: Log complete automation workflow for learning
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\integrations\learning_integration.py`
- **Class `LearningAssistant`**: Intelligent assistant that learns from interactions Integrates all 27 learning systems into a unified interface
  - **Function `get_learning_assistant()`**: Get or create learning assistant instance
  - **Function `initialize_learning_integration()`**: Initialize learning systems integration
  - **Function `predict_command()`**: Quick command prediction
  - **Function `log_interaction()`**: Quick interaction logging
  - **Function `get_smart_response()`**: Quick intelligent response generation
  - **Function `recommend_workflows()`**: Quick workflow recommendations
  - **Function `__init__()`**: Signature: (self, user_id)
  - **Function `predict_next_command()`**: Predict the next command user might want to execute
  - **Function `get_command_suggestions()`**: Get autocomplete suggestions for partial command
  - **Function `generate_intelligent_response()`**: Generate context-aware response using learning
  - **Function `log_command_execution()`**: Log command execution for learning
  - **Function `log_voice_recognition()`**: Log voice recognition for adaptive learning
  - **Function `get_workflow_suggestions()`**: Get workflow recommendations based on current task
  - **Function `log_conversation()`**: Log conversation for learning
  - **Function `select_best_llm()`**: Select the best LLM for the task using multi-armed bandit
  - **Function `get_explanation()`**: Get explanation for a prediction
  - **Function `update_context()`**: Update current context
  - **Function `get_session_stats()`**: Get statistics for current session

### File: `core_ai\src\ai_assistant\integrations\mcp_client.py`
- **Class `MCPServerConfig`**: Configuration for an MCP server connection
- **Class `MCPClient`**: Client for interacting with Model Context Protocol servers
  - **Function `get_mcp_client()`**: Get or create the global MCP client instance
  - **Function `__init__()`**: Initialize MCP client
  - **Function `get_connected_servers()`**: Get list of connected server names
  - **Function `get_server_info()`**: Get information about a specific server
  - **Function `get_all_servers()`**: Get information about all configured servers

### File: `core_ai\src\ai_assistant\integrations\mcp_conversational.py`
- **Class `MCPConversationalEnhancer`**: Enhances conversational AI with MCP tool calling capabilities
  - **Function `__init__()`**: Initialize MCP enhancer
  - **Function `get_available_mcp_tools_description()`**: Get a description of available MCP tools for the AI to use
  - **Function `enhanced_process_message()`**: Signature: ()

### File: `core_ai\src\ai_assistant\integrations\mcp_manager.py`
- **Class `MCPManager`**: High-level manager for MCP server connections and tool execution
  - **Function `__init__()`**: Initialize MCP Manager
  - **Function `_load_config()`**: Load MCP server configuration from JSON file
  - **Function `_create_default_config()`**: Create a default configuration file
  - **Function `_replace_env_vars()`**: Replace ${VAR} placeholders with environment variables
  - **Function `get_server_info()`**: Get configuration info for a specific server
  - **Function `get_enabled_servers()`**: Get list of enabled server names
  - **Function `get_failed_servers()`**: Get list of servers that failed to connect
  - **Function `get_status()`**: Get overall status of the MCP manager
  - **Function `clear_cache()`**: Clear the tools and resources cache

### File: `core_ai\src\ai_assistant\integrations\music.py`
- **Class `SpotifyController`**: Spotify Web API integration with proper OAuth2 authentication
- **Class `YouTubeMusicController`**: YouTube Music integration using ytmusicapi
  - **Function `search_youtube_music()`**: Search for songs on YouTube Music
  - **Function `play_youtube_music()`**: Play a song on YouTube Music (opens in browser)
  - **Function `get_ytmusic_playlists()`**: Get user's YouTube Music playlists
  - **Function `get_spotify_status()`**: Get current Spotify playback status Alias for _get_current_spotify_track() for backward compatibility
  - **Function `spotify_play_pause()`**: Toggle Spotify play/pause
  - **Function `spotify_next_track()`**: Skip to next track on Spotify
  - **Function `spotify_previous_track()`**: Go to previous track on Spotify
  - **Function `search_and_play_spotify()`**: Search for music on Spotify and play it Args:     query: Search term (song, artist, album)
  - **Function `get_media_players()`**: Get list of running media players
  - **Function `control_media_player()`**: Control local media players using Windows media keys Args:     action: play_pause, next, previous, volume_up, volume_down     player: specific play...
  - **Function `get_system_volume()`**: Get current system volume level
  - **Function `set_system_volume()`**: Set system volume level Args:     level: Volume level (0-100)
  - **Function `create_spotify_playlist()`**: Create a new Spotify playlist Args:     name: Playlist name     description: Playlist description (optional)
  - **Function `add_to_spotify_playlist()`**: Add a track to a Spotify playlist Args:     playlist_name: Name of the playlist     track_query: Search query for the track to add
  - **Function `get_music_recommendations()`**: Get music recommendations from Spotify Args:     seed_type: 'genre', 'artist', or 'track'     seed_value: The seed value (genre name, artist name, ...
  - **Function `get_spotify_playlists()`**: Get user's Spotify playlists
  - **Function `__new__()`**: Signature: (cls)
  - **Function `__init__()`**: Signature: (self)
  - **Function `setup_spotify_auth()`**: Set up Spotify API authentication using OAuth2 Returns status message
  - **Function `_ensure_authenticated()`**: Ensure we have valid authentication
  - **Function `__new__()`**: Signature: (cls)
  - **Function `__init__()`**: Signature: (self)
  - **Function `setup_ytmusic_auth()`**: Set up YouTube Music authentication
  - **Function `_ensure_authenticated()`**: Ensure we have valid authentication

### File: `core_ai\src\ai_assistant\integrations\orchestrator_integration.py`
  - **Function `should_use_orchestrator()`**: Determine if command should use multi-step orchestration.
  - **Function `process_with_orchestrator()`**: Process command using task chain orchestrator.
  - **Function `get_orchestrator_status()`**: Get current orchestrator status.

### File: `core_ai\src\ai_assistant\integrations\research.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\integrations\web_scraping.py`
- **Class `WebScrapingManager`**: Advanced web scraping and data aggregation manager
  - **Function `get_weather_info()`**: Get current weather information for a location Args:     location: City name or coordinates     api_key: OpenWeatherMap API key (optional, uses fre...
  - **Function `get_weather_forecast()`**: Get weather forecast for upcoming days Args:     location: City name     days: Number of days to forecast (1-7)
  - **Function `get_latest_news()`**: Get latest news headlines from various sources Args:     category: News category (general, business, technology, sports, etc.)     country: Country...
  - **Function `search_web()`**: Perform web search and return summarized results Args:     query: Search query     num_results: Number of results to return     safe_search: Enable...
  - **Function `get_stock_price()`**: Get current stock price and basic information Args:     symbol: Stock symbol (e.g., AAPL, GOOGL)
  - **Function `get_crypto_price()`**: Get cryptocurrency price information Args:     symbol: Crypto symbol or name (bitcoin, ethereum, etc.)
  - **Function `scrape_website_content()`**: Extract and summarize content from a website Args:     url: Website URL to scrape     extract_text: Whether to extract readable text     max_length...
  - **Function `get_trending_topics()`**: Get trending topics from various platforms Args:     platform: Platform to check (general, reddit, github)
  - **Function `monitor_rss_feeds()`**: Monitor multiple RSS feeds and return latest updates Args:     feed_urls: List of RSS feed URLs to monitor     max_items: Maximum items per feed
  - **Function `get_product_price()`**: Get product pricing information (simplified version for demonstration) Args:     product_name: Product name to search for     marketplace: Marketpl...
  - **Function `__init__()`**: Signature: (self)
  - **Function `ensure_cache_dir()`**: Ensure cache directory exists

### File: `core_ai\src\ai_assistant\integrations\web_search_integration.py`
- **Class `SearchTriggerType`**: Triggers for web search.
- **Class `SearchResult`**: A single search result.
- **Class `SearchResponse`**: Response from web search.
- **Class `WebSearchTrigger`**: Detects when web search should be used.
- **Class `WebSearchCache`**: Cache for web search results to reduce API calls.
- **Class `WebSearchIntegration`**: Integrates web search into chat.
  - **Function `integrate_search_into_chat()`**: Integrate web search into a chat system.
  - **Function `to_dict()`**: Convert to dictionary.
  - **Function `to_dict()`**: Convert to dictionary.
  - **Function `should_search()`**: Determine if message should trigger web search.
  - **Function `__init__()`**: Initialize web search integration.
  - **Function `get()`**: Get cached search results.
  - **Function `set()`**: Cache search results.
  - **Function `clear()`**: Clear cache.
  - **Function `cleanup()`**: Remove expired entries.
  - **Function `__init__()`**: Initialize web search integration.
  - **Function `should_search_for_message()`**: Check if message should trigger search.
  - **Function `search_web()`**: Perform web search.
  - **Function `_search_duckduckgo()`**: Fallback search using DuckDuckGo.
  - **Function `format_results_for_llm()`**: Format search results for inclusion in LLM prompt.
  - **Function `enhance_prompt_with_search()`**: Enhance user prompt with search results context.
  - **Function `get_search_stats()`**: Get search statistics.

### File: `core_ai\src\ai_assistant\integrations\whatsapp.py`
  - **Function `load_contacts()`**: Signature: ()
  - **Function `get_contact_number()`**: Signature: (name)
  - **Function `send_whatsapp_message()`**: Sends a WhatsApp message to a contact. 1. Looks up contact number. 2. Opens WhatsApp (Web or App) with pre-filled message. 3. Simulates 'Enter' to ...

### File: `core_ai\src\ai_assistant\integrations\youtube_ops.py`
- **Class `YouTubeDownloader`**: Core component.
  - **Function `__init__()`**: Signature: (self, download_path)
  - **Function `search_and_download_audio()`**: Searches for a video on YouTube and downloads the audio. Returns a dictionary with the result status and details.

### File: `core_ai\src\ai_assistant\nlp\generate_dataset.py`
  - **Function `main()`**: Signature: ()

### File: `core_ai\src\ai_assistant\nlp\intent_extractor.py`
- **Class `IntentResult`**: Core component.
- **Class `IntentExtractor`**: A simple rule-based intent and entity extractor for natural language commands. Uses regex patterns to identify intents and extract entities.
  - **Function `__init__()`**: Signature: (self)
  - **Function `extract()`**: Extract intent and entities from the given text. Returns an IntentResult with the best match.

### File: `core_ai\src\ai_assistant\nlp\predict_command.py`
- **Class `OfflineCommandPredictor`**: Core component.
  - **Function `__init__()`**: Signature: (self)
  - **Function `predict()`**: Takes a natural language command (English, Hindi, or Bhojpuri)  and returns the corresponding INTENT tag.

### File: `core_ai\src\ai_assistant\nlp\train_model.py`
  - **Function `main()`**: Signature: ()
  - **Function `tokenize_function()`**: Signature: ()

### File: `core_ai\src\ai_assistant\tests\test_personalization.py`
  - **Function `test_context_optimizer()`**: Signature: ()
  - **Function `test_intent_recognizer()`**: Signature: ()

### File: `core_ai\src\ai_assistant\utils\advanced_logging.py`
  - **Function `log_performance()`**: Decorator to log function performance
- **Class `ContextualErrorLogger`**: Enhanced error logger with context information
- **Class `APIRequestLogger`**: Logger for API requests and responses
- **Class `SecurityLogger`**: Logger for security-related events
- **Class `UserActivityLogger`**: Logger for user activity and interactions
- **Class `LogAggregator`**: Aggregates and analyzes log data
  - **Function `log_error_with_context()`**: Convenience function for logging errors with context
  - **Function `log_api_call()`**: Convenience function for logging API calls
  - **Function `log_user_action()`**: Convenience function for logging user actions
  - **Function `decorator()`**: Signature: ()
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_exception()`**: Log exception with full context
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_request()`**: Log incoming API request
  - **Function `log_response()`**: Log API response
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_auth_attempt()`**: Log authentication attempt
  - **Function `log_suspicious_activity()`**: Log suspicious activity
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_user_action()`**: Convenience function for logging user actions
  - **Function `log_voice_command()`**: Log voice command interaction
  - **Function `__init__()`**: Signature: (self)
  - **Function `generate_daily_summary()`**: Generate daily log summary
  - **Function `slow_function()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `core_ai\src\ai_assistant\utils\backend_utils.py`
  - **Function `validate_input()`**: Validate input data against pattern
  - **Function `sanitize_command()`**: Sanitize command input to prevent injection

### File: `core_ai\src\ai_assistant\utils\convert_prints.py`
- **Class `PrintToLoggerConverter`**: Converts print statements to logger calls throughout the project
  - **Function `main()`**: Run the conversion
  - **Function `__init__()`**: Signature: (self, project_root)
  - **Function `convert_project()`**: Convert all Python files in the project
  - **Function `_should_skip_file()`**: Check if file should be skipped
  - **Function `_convert_file()`**: Convert a single file

### File: `core_ai\src\ai_assistant\utils\dataset_generator.py`
  - **Function `generate_dataset()`**: Signature: (num_samples)

### File: `core_ai\src\ai_assistant\utils\embeddings.py`
- **Class `EmbeddingStore`**: Core component.
  - **Function `get_openai_embedding()`**: Get OpenAI embedding for text.
  - **Function `__init__()`**: Signature: (self, dim)
  - **Function `add()`**: Signature: (self, text, embedding)
  - **Function `search()`**: Signature: (self, query_embedding, top_k)

### File: `core_ai\src\ai_assistant\utils\file_ops.py`
- **Class `FileOperationsManager`**: Advanced file operations manager with intelligent features
  - **Function `organize_files_by_type()`**: Organize files in a directory by their type/extension Args:     directory: Target directory to organize     create_subfolders: Whether to create su...
  - **Function `find_duplicate_files()`**: Find duplicate files in a directory based on file content hash Args:     directory: Directory to scan for duplicates     include_subdirs: Whether t...
  - **Function `remove_duplicate_files()`**: Remove duplicate files, keeping either oldest or newest Args:     directory: Directory to clean     keep_oldest: If True, keep oldest files; if Fal...
  - **Function `create_backup_archive()`**: Create a compressed backup archive of a directory Args:     source_dir: Directory to backup     backup_name: Custom backup name (optional)     comp...
  - **Function `smart_file_search()`**: Advanced file search with content search and filtering Args:     directory: Directory to search in     pattern: Search pattern (filename or content...
  - **Function `batch_rename_files()`**: Batch rename files using pattern matching Args:     directory: Directory containing files to rename     pattern: Pattern to match (supports wildcar...
  - **Function `analyze_directory_structure()`**: Analyze directory structure and provide insights Args:     directory: Directory to analyze     max_depth: Maximum depth to analyze
  - **Function `sync_directories()`**: Synchronize two directories (one-way sync from source to destination) Args:     source_dir: Source directory     dest_dir: Destination directory   ...
  - **Function `__init__()`**: Signature: (self)
  - **Function `ensure_backup_dir()`**: Ensure backup directory exists

### File: `core_ai\src\ai_assistant\utils\logging_analyzer.py`
- **Class `LoggingAnalyzer`**: Analyzes the entire project for logging issues and improvements.
  - **Function `main()`**: Run comprehensive logging analysis.
  - **Function `__init__()`**: Signature: (self, project_root)
  - **Function `analyze_project()`**: Perform comprehensive logging analysis.
  - **Function `_analyze_python_files()`**: Analyze all Python files for logging issues.
  - **Function `_analyze_python_file()`**: Analyze a single Python file.
  - **Function `_analyze_frontend_files()`**: Analyze frontend files for console.log statements.
  - **Function `_analyze_js_file()`**: Analyze a JavaScript/TypeScript file.
  - **Function `_analyze_config_files()`**: Analyze configuration files.
  - **Function `_should_skip_file()`**: Check if file should be skipped.
  - **Function `_generate_recommendations()`**: Generate recommendations for logging improvements.

### File: `core_ai\src\ai_assistant\utils\logging_completion.py`
- **Class `LoggingSystemValidator`**: Validates the complete logging system
  - **Function `create_logging_utilities()`**: Create helpful logging utilities
  - **Function `main()`**: Main function to complete logging system
  - **Function `__init__()`**: Signature: (self)
  - **Function `validate_all()`**: Run comprehensive validation
  - **Function `_validate_directories()`**: Validate log directory structure
  - **Function `_validate_configuration()`**: Validate logging configuration
  - **Function `_test_loggers()`**: Test all logger types
  - **Function `_validate_rotation()`**: Validate log rotation settings
  - **Function `_test_performance_logging()`**: Test performance logging decorator
  - **Function `_test_error_handling()`**: Test error logging
  - **Function `_test_api_logging()`**: Test API logging
  - **Function `_validate_frontend_logging()`**: Validate frontend logging integration
  - **Function `_validate_documentation()`**: Validate logging documentation
  - **Function `generate_report()`**: Generate comprehensive validation report
  - **Function `test_performance_function()`**: Signature: ()

### File: `core_ai\src\ai_assistant\utils\logging_config.py`

### File: `core_ai\src\ai_assistant\utils\multilingual.py`
- **Class `Language`**: Supported languages.
- **Class `TranslationEngine`**: Available translation engines.
- **Class `LanguageContext`**: Context information for language processing.
- **Class `MultilingualSupport`**: Advanced multilingual support system.
  - **Function `voice_listen_loop()`**: Main voice listening loop with wake word detection and multilingual support.
  - **Function `_voice_listen_loop_vosk()`**: Voice loop using Vosk for offline recognition.
  - **Function `_voice_listen_loop_google()`**: Voice loop using Google Speech Recognition (online, fallback).
  - **Function `test_voice_recognition()`**: Test voice recognition for a specified duration.
  - **Function `detect_text_language()`**: Quick function to detect language of text.
  - **Function `translate_quick()`**: Quick translation function.
  - **Function `speak_in_language()`**: Quick TTS function with language support.
  - **Function `process_hinglish_input()`**: Quick function to process Hinglish input.
  - **Function `__init__()`**: Initialize multilingual support.
  - **Function `_default_config()`**: Default configuration for multilingual support.
  - **Function `_setup_translation()`**: Setup translation services.
  - **Function `_setup_speech_recognition()`**: Setup speech recognition for multiple languages.
  - **Function `_load_vosk_models()`**: Load Vosk models for offline speech recognition.
  - **Function `_setup_tts()`**: Setup text-to-speech for multiple languages.
  - **Function `_setup_database()`**: Setup language database for caching and learning.
  - **Function `_load_language_patterns()`**: Load language patterns for detection.
  - **Function `detect_language()`**: Detect language of input text with confidence score.
  - **Function `translate_text()`**: Translate text between languages.
  - **Function `_translate_hinglish()`**: Handle Hinglish to other language translation.
  - **Function `_create_hinglish_output()`**: Create natural Hinglish by mixing Hindi and English.
  - **Function `_get_cached_translation()`**: Get cached translation if available.
  - **Function `_cache_translation()`**: Cache translation for future use.
  - **Function `recognize_speech_multilingual()`**: Recognize speech in multiple languages.
  - **Function `speak_multilingual()`**: Speak text in the appropriate language using Edge-TTS, gTTS, or pyttsx3 fallback.
  - **Function `process_hinglish_command()`**: Process Hinglish commands with cultural context.
  - **Function `_extract_hinglish_parameters()`**: Extract parameters from Hinglish text.
  - **Function `set_language_preference()`**: Set user language preference.
  - **Function `get_language_preference()`**: Get user language preference.
  - **Function `get_language_stats()`**: Get language usage statistics.
  - **Function `callback()`**: Signature: ()

### File: `core_ai\src\ai_assistant\utils\secure_storage.py`
  - **Function `save_secure_key()`**: Save a secure key (like an API key) to the OS keychain.
  - **Function `get_secure_key()`**: Retrieve a secure key from the OS keychain. Returns empty string if not found.
  - **Function `delete_secure_key()`**: Delete a secure key from the OS keychain.

### File: `core_ai\src\ai_assistant\utils\session_activity_logger.py`

### File: `core_ai\src\ai_assistant\utils\session_init.py`

### File: `core_ai\src\ai_assistant\utils\sitecustomize.py`

### File: `core_ai\src\ai_assistant\utils\tool_schemas.py`

### File: `core_ai\src\ai_assistant\utils\update_logging.py`
  - **Function `update_logging_calls()`**: Update logging calls in a file
  - **Function `main()`**: Update all module files

### File: `core_ai\src\ai_assistant\utils\user_data_logger.py`
  - **Function `get_timestamp()`**: Signature: ()
  - **Function `save_data()`**: Saves data to the appropriate folder with a timestamp.
  - **Function `log_action()`**: Logs a user action.
  - **Function `log_query()`**: Logs a user query.
  - **Function `log_reply()`**: Logs an assistant reply.
  - **Function `log_module_usage()`**: Logs the usage of a module and function.

### File: `core_ai\src\ai_assistant\vision\document_ocr.py`
- **Class `DocumentAnalyzer`**: Advanced document analysis and OCR manager
  - **Function `check_ocr_dependencies()`**: Check which OCR dependencies are available
  - **Function `extract_text_from_image()`**: Extract text from an image using OCR Args:     image_path: Path to the image file     language: OCR language (eng, fra, deu, spa, etc.)     enhance...
  - **Function `extract_text_from_pdf()`**: Extract text from a PDF document Args:     pdf_path: Path to the PDF file     page_range: Optional tuple (start_page, end_page) to limit extraction
  - **Function `analyze_document_structure()`**: Analyze document structure and extract metadata Args:     file_path: Path to the document file
  - **Function `preprocess_image_for_ocr()`**: Preprocess image to improve OCR accuracy Args:     image_path: Path to the input image     output_path: Path for the processed image (optional)
  - **Function `extract_key_information()`**: Extract key information from extracted text based on type Args:     text: Extracted text to analyze     info_type: Type of information to extract (...
  - **Function `batch_ocr_directory()`**: Perform OCR on multiple files in a directory Args:     directory: Directory containing files     file_pattern: File pattern to match (e.g., *.jpg, ...
  - **Function `summarize_document_content()`**: Create a simple summary of extracted document text Args:     text: Text to summarize     max_sentences: Maximum sentences in summary
  - **Function `__init__()`**: Signature: (self)
  - **Function `ensure_cache_dir()`**: Ensure OCR cache directory exists

### File: `core_ai\src\ai_assistant\vision\gemini_vision_provider.py`
- **Class `GeminiVisionProvider`**: Google Gemini Vision API implementation.
  - **Function `__init__()`**: Initialize Gemini Vision provider.
  - **Function `_load_image()`**: Load image from path or return PIL Image as-is.
  - **Function `_optimize_image()`**: Optimize image for API while maintaining quality.
  - **Function `analyze_image()`**: Analyze an image with Gemini Vision.
  - **Function `extract_text()`**: Extract text from image using Gemini Vision OCR.
  - **Function `detect_objects()`**: Detect and describe objects in the image.
  - **Function `analyze_document()`**: Analyze a document image with structure understanding.
  - **Function `analyze_table()`**: Extract table data from image.
  - **Function `provider_name()`**: Return provider name.
  - **Function `supported_features()`**: Return list of supported features.

### File: `core_ai\src\ai_assistant\vision\image_utils.py`
- **Class `ImageProcessor`**: Utilities for image processing and optimization.
  - **Function `optimize_for_vlm()`**: Optimize image for VLM processing.
  - **Function `enhance_for_ocr()`**: Enhance image for better OCR results.
  - **Function `draw_bounding_box()`**: Draw a bounding box on the image.
  - **Function `annotate_screenshot()`**: Annotate screenshot with multiple elements.
  - **Function `convert_to_base64()`**: Convert PIL Image to base64 string.
  - **Function `from_base64()`**: Create PIL Image from base64 string.
  - **Function `convert_pdf_page_to_image()`**: Convert a PDF page to image.
  - **Function `convert_pdf_to_images()`**: Convert all PDF pages to images.
  - **Function `crop_region()`**: Crop a region from the image.
  - **Function `resize_maintaining_aspect()`**: Resize image maintaining aspect ratio.
  - **Function `get_image_info()`**: Get information about an image.

### File: `core_ai\src\ai_assistant\vision\multimodal.py`
- **Class `MultiModalAI`**: Advanced multi-modal AI system for visual understanding and generation.
  - **Function `analyze_current_screen()`**: Quick function to analyze current screen.
  - **Function `answer_visual_question_quick()`**: Quick function to answer visual questions about current screen.
  - **Function `extract_screen_text()`**: Quick function to extract text from current screen.
  - **Function `describe_current_screen()`**: Quick function to describe current screen.
  - **Function `analyze_video_file()`**: Quick function to analyze a video file.
  - **Function `__init__()`**: Initialize the multi-modal AI system with API key validation.
  - **Function `capture_screen()`**: Capture screenshot of the entire screen or specific region with caching.
  - **Function `image_to_base64()`**: Convert PIL Image to base64 string.
  - **Function `_image_hash()`**: Generate hash for image to check cache.
  - **Function `_cleanup_old_cache()`**: Remove expired items from screenshot cache.
  - **Function `analyze_image()`**: Analyze an image using Gemini Vision with caching support.
  - **Function `analyze_screen()`**: Analyze current screen content.
  - **Function `answer_visual_question()`**: Answer questions about visual content.
  - **Function `extract_text_from_screen()`**: Extract text from screen using AI vision.
  - **Function `describe_ui_elements()`**: Describe UI elements on the current screen.
  - **Function `find_ui_element()`**: Find and locate specific UI elements on screen.
  - **Function `monitor_screen_changes()`**: Monitor screen for changes and trigger callback.
  - **Function `stop_monitoring()`**: Stop screen monitoring.
  - **Function `generate_image_description()`**: Generate a comprehensive description of current screen.
  - **Function `save_screenshot_with_analysis()`**: Save current screenshot with optional AI analysis.
  - **Function `get_analysis_history()`**: Get recent analysis history.
  - **Function `clear_analysis_history()`**: Clear analysis history.
  - **Function `_optimize_image()`**: Optimize image size for API processing while maintaining quality.
  - **Function `clear_cache()`**: Clear screenshot and analysis cache.
  - **Function `analyze_video()`**: Analyze a video by extracting and analyzing key frames.
- **Class `Image`**: Core component.
  - **Function `monitor_loop()`**: Signature: ()
- **Class `Image`**: Core component.

### File: `core_ai\src\ai_assistant\vision\vlm_provider.py`
- **Class `VLMResponse`**: Standardized response from VLM providers.
- **Class `VLMProvider`**: Abstract base class for Vision Language Model providers.
  - **Function `to_dict()`**: Convert response to dictionary.
  - **Function `extract_json()`**: Attempt to extract JSON from text response.
  - **Function `__init__()`**: Initialize the VLM provider.
  - **Function `analyze_image()`**: Analyze an image with a text prompt.
  - **Function `extract_text()`**: Extract text from an image (OCR).
  - **Function `detect_objects()`**: Detect objects in an image.
  - **Function `extract_ui_elements()`**: Extract UI elements from a screenshot.
  - **Function `find_element_coordinates()`**: Find pixel coordinates of a specific UI element.
  - **Function `compare_images()`**: Compare two images and describe differences.
  - **Function `_get_cache_key()`**: Generate cache key for image + prompt combination.
  - **Function `_check_cache()`**: Check if response is in cache and still valid.
  - **Function `_add_to_cache()`**: Add response to cache.
  - **Function `clear_cache()`**: Clear the response cache.
  - **Function `provider_name()`**: Return the name of this provider.
  - **Function `supported_features()`**: Return list of supported features.

### File: `core_ai\src\ai_assistant\voice\advanced_speech_recognizer.py`
- **Class `RecognitionModel`**: Available recognition models
- **Class `AdvancedSpeechRecognizer`**: Advanced speech recognition engine matching Google Assistant accuracy Multi-model approach with automatic fallback
  - **Function `get_advanced_speech_recognizer()`**: Get or create the advanced speech recognizer instance
  - **Function `__init__()`**: Signature: (self, whisper_api_key, google_cloud_key, prefer_online, noise_reduction, cache_dir, user_id, require_consent)
  - **Function `_initialize_recognizers()`**: Initialize all available recognition engines
  - **Function `_legacy_vosk_init()`**: Signature: ()
  - **Function `reduce_noise()`**: Apply noise reduction to audio data
  - **Function `recognize_google_cloud_speech()`**: Signature: ()
  - **Function `recognize_speech_recognition()`**: Signature: ()
  - **Function `recognize_vosk()`**: Signature: ()
  - **Function `recognize()`**: Recognize speech with automatic model selection and fallback
  - **Function `get_recognition_stats()`**: Get recognition performance statistics
- **Class `sr`**: Core component.
  - **Function `_resolve_model_path()`**: Signature: ()
- **Class `AudioSource`**: Core component.

### File: `core_ai\src\ai_assistant\voice\advanced_voice.py`
- **Class `VoiceProfileManager`**: Manages voice profiles and speaker identification
- **Class `AdvancedWakeWordDetector`**: Enhanced wake word detection with fuzzy matching and learning
- **Class `ContinuousListeningManager`**: Manages continuous listening with smart activation/deactivation
- **Class `VoiceCommandRegistry`**: Registry for voice commands and their handlers
  - **Function `get_voice_features()`**: Get comprehensive voice feature set
  - **Function `__init__()`**: Signature: (self)
  - **Function `extract_voice_features()`**: Extract voice features from audio data
  - **Function `add_voice_sample()`**: Add voice sample for speaker training
  - **Function `identify_speaker()`**: Identify speaker from audio sample
  - **Function `save_profiles()`**: Save voice profiles to disk
  - **Function `load_profiles()`**: Load voice profiles from disk
  - **Function `__init__()`**: Signature: (self)
  - **Function `_build_phonetic_patterns()`**: Build phonetic patterns for wake words
  - **Function `calculate_similarity()`**: Calculate similarity between two text strings
  - **Function `detect_wake_word()`**: Detect wake word in text with confidence score
  - **Function `report_false_positive()`**: Report a false positive to improve detection
  - **Function `__init__()`**: Signature: (self)
  - **Function `_initialize_audio()`**: Initialize audio system
  - **Function `start_listening()`**: Start continuous listening
  - **Function `stop_listening()`**: Stop continuous listening
  - **Function `pause_listening()`**: Pause listening temporarily
  - **Function `resume_listening()`**: Resume listening
  - **Function `_listen_loop()`**: Main listening loop
  - **Function `_process_audio()`**: Process captured audio
  - **Function `_recognize_speech()`**: Recognize speech from audio
  - **Function `_extract_command()`**: Extract command text after wake word
  - **Function `get_statistics()`**: Get listening statistics
  - **Function `__init__()`**: Signature: (self)
  - **Function `register_command()`**: Register a voice command
  - **Function `register_alias()`**: Register an alias for an existing command
  - **Function `register_context_handler()`**: Register a context-aware handler
  - **Function `find_command()`**: Find matching command for text
  - **Function `_register_default_commands()`**: Register default voice commands
  - **Function `_handle_time_command()`**: Handle time request
  - **Function `_handle_date_command()`**: Handle date request
  - **Function `_handle_stop_listening()`**: Handle stop listening request
  - **Function `_handle_help_command()`**: Handle help request
- **Class `sr`**: Core component.
  - **Function `levenshtein_distance()`**: Signature: ()
- **Class `AudioSource`**: Core component.
- **Class `Microphone`**: Core component.
- **Class `AudioData`**: Core component.
- **Class `UnknownValueError`**: Core component.
- **Class `RequestError`**: Core component.

### File: `core_ai\src\ai_assistant\voice\async_recognizer.py`
  - **Function `init_async_recognizer()`**: Initialize the async recognizer singleton
  - **Function `recognize_background()`**: Start recognition in background and return Future
- **Class `RecognitionMetrics`**: Track async recognition performance metrics
  - **Function `get_recognition_stats()`**: Get recognition performance statistics
  - **Function `shutdown_async_recognizer()`**: Shutdown thread pool gracefully
  - **Function `__init__()`**: Signature: (self)
  - **Function `record_success()`**: Signature: (self, latency)
  - **Function `record_failure()`**: Signature: (self)
  - **Function `get_stats()`**: Signature: (self)

### File: `core_ai\src\ai_assistant\voice\emotion_detection.py`
- **Class `Emotion`**: Detected emotions
- **Class `EmotionResult`**: Emotion detection result
- **Class `SpeechEmotionDetector`**: Detects emotions from speech audio
  - **Function `get_emotion_detector()`**: Get global emotion detector
  - **Function `__init__()`**: Initialize emotion detector
  - **Function `analyze_audio()`**: Analyze emotion from audio file
  - **Function `analyze_realtime()`**: Analyze emotion from real-time audio buffer
  - **Function `_extract_features()`**: Extract audio features for emotion detection
  - **Function `_classify_emotion()`**: Classify emotion based on features
  - **Function `_get_neutral_result()`**: Get default neutral result
  - **Function `get_mood_trend()`**: Analyze mood trend over recent history
  - **Function `adapt_response_style()`**: Get response adaptation recommendations based on emotion

### File: `core_ai\src\ai_assistant\voice\enhanced_wake_word.py`
  - **Function `enhanced_wake_word_detection()`**: Enhanced wake word detection with fuzzy matching for better accuracy

### File: `core_ai\src\ai_assistant\voice\ml_features.py`
- **Class `SileroVAD`**: Deep learning-based VAD using Silero models
- **Class `VoiceCloner`**: Voice cloning using Coqui TTS
- **Class `SpeakerDiarizer`**: Speaker diarization using pyannote.audio
  - **Function `example_ml_pipeline()`**: Example of how to use all ML features together
  - **Function `__init__()`**: Initialize speaker diarization
  - **Function `detect()`**: Detect voice activity with high accuracy
  - **Function `__init__()`**: Initialize speaker diarization
  - **Function `train_voice_profile()`**: Train a voice profile from audio samples
  - **Function `clone_voice()`**: Synthesize speech with cloned voice
  - **Function `__init__()`**: Initialize speaker diarization
  - **Function `diarize()`**: Perform speaker diarization on audio
  - **Function `identify_speakers()`**: Match diarized speakers to known voice profiles

### File: `core_ai\src\ai_assistant\voice\multilingual_wake_words.py`
- **Class `SupportedLanguage`**: Supported languages for wake word detection
- **Class `WakeWordConfidence`**: Wake word detection confidence levels
- **Class `PhonemeSequence`**: Phonemic representation of a wake word
- **Class `WakeWordTemplate`**: Template for wake word detection
- **Class `DetectionResult`**: Result of wake word detection
- **Class `MultilingualConfig`**: Configuration for multilingual wake word detection
- **Class `PhonemeExtractor`**: Extract phonemes from text in different languages
- **Class `AcousticFeatureExtractor`**: Extract acoustic features for wake word matching
- **Class `PhoneticMatcher`**: Match phoneme sequences with similarity scoring
- **Class `MultilingualWakeWordDetector`**: Advanced multilingual wake word detection system
  - **Function `create_multilingual_detector()`**: Create multilingual wake word detector with specified languages
  - **Function `quick_wake_word_detection()`**: Quick wake word detection function
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `_initialize_processors()`**: Initialize language-specific phoneme processors
  - **Function `_init_fallback_processors()`**: Initialize simple fallback phoneme processors
  - **Function `extract_phonemes()`**: Extract phoneme sequence from text
  - **Function `_fallback_phoneme_extraction()`**: Simple fallback phoneme extraction
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `extract_features()`**: Extract acoustic features from audio
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `calculate_similarity()`**: Calculate phonetic similarity between two sequences
  - **Function `_create_distance_matrix()`**: Create distance matrix for phoneme comparison
  - **Function `_phoneme_similarity()`**: Calculate similarity between individual phonemes
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `register_wake_word()`**: Register a new wake word with audio samples
  - **Function `detect_wake_word()`**: Detect wake words in audio data
  - **Function `_calculate_acoustic_similarity()`**: Calculate acoustic similarity between feature vectors
  - **Function `start_continuous_detection()`**: Start continuous wake word detection
  - **Function `stop_continuous_detection()`**: Stop continuous detection
  - **Function `_continuous_detection_loop()`**: Continuous detection loop
  - **Function `add_audio_data()`**: Add audio data for continuous detection
  - **Function `get_latest_detection()`**: Get latest detection result
  - **Function `_save_wake_word_template()`**: Save wake word template to disk
  - **Function `_load_wake_word_templates()`**: Load wake word templates from disk
  - **Function `delete_wake_word()`**: Delete a wake word template
  - **Function `get_registered_wake_words()`**: Get list of registered wake words
  - **Function `update_confidence_threshold()`**: Update confidence threshold for a specific wake word

### File: `core_ai\src\ai_assistant\voice\neural_voice_engine.py`
- **Class `VoiceGender`**: Voice gender options
- **Class `SpeakingStyle`**: Speaking style options for natural conversation
- **Class `NeuralVoiceEngine`**: High-quality neural voice synthesis engine
  - **Function `get_neural_voice_engine()`**: Get or create the neural voice engine singleton
  - **Function `__init__()`**: Signature: (self, cache_dir, gpu)
  - **Function `_initialize_engines()`**: Initialize all available TTS engines
  - **Function `synthesize_kitten_tts()`**: Synthesize speech using KittenTTS (offline, ultra-lightweight)
  - **Function `synthesize_edge_tts_sync()`**: Signature: ()
  - **Function `speak()`**: Generate audio using KittenTTS, falling back to Edge-TTS. Returns the path to the audio file.

### File: `core_ai\src\ai_assistant\voice\noise_reduction.py`
- **Class `NoiseReductionMethod`**: Available noise reduction methods
- **Class `NoiseLevel`**: Noise reduction intensity levels
- **Class `NoiseReductionConfig`**: Configuration for noise reduction system
- **Class `NoiseProfile`**: Noise characteristics profile
- **Class `AudioQualityMetrics`**: Audio quality assessment metrics
- **Class `SpectralSubtractionProcessor`**: Spectral subtraction noise reduction processor
- **Class `WienerFilterProcessor`**: Wiener filter noise reduction processor
- **Class `AdaptiveNoiseReducer`**: Adaptive noise reduction that adjusts parameters based on  current noise conditions and signal characteristics
- **Class `NoiseReductionSystem`**: Complete noise reduction system with multiple algorithms and real-time processing capabilities
  - **Function `create_noise_reducer()`**: Create noise reduction system with specified method and level
  - **Function `reduce_audio_noise()`**: Quick noise reduction function
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `estimate_noise()`**: Estimate noise profile from audio data
  - **Function `process()`**: Process audio with adaptive noise reduction
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `initialize()`**: Initialize Wiener filter with noise and optional speech samples
  - **Function `process()`**: Process audio with adaptive noise reduction
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `process()`**: Process audio with adaptive noise reduction
  - **Function `_estimate_snr()`**: Estimate signal-to-noise ratio
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `_initialize_processors()`**: Initialize noise reduction processors
  - **Function `reduce_noise()`**: Apply noise reduction to audio data
  - **Function `_apply_spectral_subtraction()`**: Apply spectral subtraction
  - **Function `_apply_wiener_filter()`**: Apply Wiener filter
  - **Function `_apply_adaptive_filter()`**: Apply adaptive filter
  - **Function `_apply_hybrid_method()`**: Apply hybrid noise reduction method
  - **Function `_calculate_quality_metrics()`**: Calculate audio quality metrics
  - **Function `start_realtime_processing()`**: Start real-time noise reduction processing
  - **Function `stop_realtime_processing()`**: Stop real-time processing
  - **Function `_realtime_processing_loop()`**: Real-time processing loop
  - **Function `add_audio_for_processing()`**: Add audio data for real-time processing
  - **Function `get_processed_audio()`**: Get processed audio from real-time processing
  - **Function `estimate_noise_profile()`**: Estimate noise profile from audio sample
  - **Function `get_quality_metrics()`**: Get latest quality metrics
  - **Function `update_config()`**: Update noise reduction configuration

### File: `core_ai\src\ai_assistant\voice\speaker_verification.py`
- **Class `VerificationResult`**: Speaker verification results
- **Class `SecurityLevel`**: Security levels for speaker verification
- **Class `VerificationConfig`**: Configuration for speaker verification system
- **Class `SpeakerProfile`**: Speaker biometric profile
- **Class `VerificationAttempt`**: Result of speaker verification attempt
- **Class `SpeakerVerificationSystem`**: Advanced speaker verification system using voice biometrics
  - **Function `create_speaker_verifier()`**: Create speaker verification system with specified security level
  - **Function `quick_verify_speaker()`**: Quick speaker verification function
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `enroll_speaker()`**: Enroll a new speaker with multiple audio samples
  - **Function `verify_speaker()`**: Verify if audio matches enrolled speaker
  - **Function `identify_speaker()`**: Identify which enrolled speaker matches the audio
  - **Function `_extract_features()`**: Extract MFCC features from audio
  - **Function `_calculate_audio_quality()`**: Calculate audio quality score
  - **Function `_create_anti_spoofing_profile()`**: Create anti-spoofing profile for speaker
  - **Function `_check_anti_spoofing()`**: Check for potential spoofing attempts
  - **Function `_convert_likelihood_to_confidence()`**: Convert log-likelihood to confidence score 0-1
  - **Function `_save_speaker_profile()`**: Save speaker profile to disk with encryption
  - **Function `_load_speaker_profiles()`**: Load existing speaker profiles from disk (encrypted or legacy)
  - **Function `delete_speaker()`**: Delete speaker profile and associated files (encrypted and legacy)
  - **Function `get_enrolled_speakers()`**: Get list of enrolled speaker IDs
  - **Function `get_speaker_info()`**: Get information about enrolled speaker
  - **Function `update_security_level()`**: Update security level for verification

### File: `core_ai\src\ai_assistant\voice\test_voice_recognition.py`
  - **Function `test_voice_callback()`**: Callback function for voice recognition
  - **Function `test_vosk_models()`**: Test if Vosk models are available
  - **Function `main()`**: Signature: ()

### File: `core_ai\src\ai_assistant\voice\voice_activity_detection.py`
- **Class `VADSensitivity`**: Voice Activity Detection sensitivity levels
- **Class `VADAlgorithm`**: Available VAD algorithms
- **Class `VADConfig`**: Voice Activity Detection configuration
- **Class `VADResult`**: Voice Activity Detection result
- **Class `VoiceActivityDetector`**: Advanced Voice Activity Detection system with multiple algorithms
- **Class `VADProcessor`**: High-level VAD processor for easy integration
  - **Function `create_vad_detector()`**: Create a VAD detector with specified settings
  - **Function `detect_voice_activity()`**: Quick voice activity detection for audio data
  - **Function `__init__()`**: Signature: (self, sensitivity)
  - **Function `_init_webrtc_vad()`**: Initialize WebRTC VAD
  - **Function `_init_energy_detector()`**: Initialize energy-based detection
  - **Function `_init_spectral_detector()`**: Initialize spectral analysis detector
  - **Function `detect_voice_activity()`**: Quick voice activity detection for audio data
  - **Function `_calculate_energy()`**: Calculate RMS energy of audio frame
  - **Function `_update_noise_estimation()`**: Update background noise level estimation
  - **Function `_webrtc_detect()`**: WebRTC VAD detection
  - **Function `_energy_detect()`**: Energy-based VAD detection
  - **Function `_spectral_detect()`**: Spectral analysis-based VAD detection
  - **Function `_extract_spectral_features()`**: Extract spectral features for voice detection
  - **Function `_combine_results()`**: Combine results from multiple VAD algorithms
  - **Function `_temporal_filter()`**: Apply temporal filtering to reduce false positives/negatives
  - **Function `start_continuous_detection()`**: Start continuous VAD processing in background thread
  - **Function `stop_continuous_detection()`**: Stop continuous VAD processing
  - **Function `_continuous_processing_loop()`**: Continuous processing loop for real-time VAD
  - **Function `add_audio_data()`**: Add audio data for continuous processing
  - **Function `get_latest_result()`**: Get latest VAD result from processing
  - **Function `calibrate()`**: Manually calibrate with noise sample
  - **Function `reset_calibration()`**: Reset calibration to start fresh
  - **Function `get_status()`**: Get current VAD status and statistics
  - **Function `__init__()`**: Signature: (self, sensitivity)
  - **Function `is_speech_detected()`**: Simple speech detection interface
  - **Function `process_audio_stream()`**: Process continuous audio stream with callback
  - **Function `calibrate_with_silence()`**: Auto-calibrate by recording silence

### File: `core_ai\src\ai_assistant\voice\voice_fingerprinting.py`
- **Class `RecognitionConfidence`**: Voice recognition confidence levels
- **Class `VoiceQuality`**: Voice sample quality assessment
- **Class `VoiceEmbedding`**: Voice embedding representation
- **Class `UserVoiceProfile`**: User voice profile with multiple embeddings
- **Class `RecognitionResult`**: Voice recognition result
- **Class `VoiceFingerprintConfig`**: Configuration for voice fingerprinting
- **Class `VoiceEmbeddingExtractor`**: Extract voice embeddings using various models
- **Class `VoiceQualityAssessor`**: Assess voice sample quality for fingerprinting
- **Class `AntiSpoofingDetector`**: Detect voice spoofing and liveness
- **Class `VoiceFingerprintingSystem`**: Complete voice fingerprinting and user recognition system
  - **Function `create_voice_fingerprinting_system()`**: Create voice fingerprinting system with configuration
  - **Function `quick_user_recognition()`**: Quick user recognition function
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `_initialize_models()`**: Initialize embedding models
  - **Function `_create_mfcc_extractor()`**: Create MFCC-based fallback extractor
  - **Function `extract_embedding()`**: Extract voice embedding from audio
  - **Function `_validate_audio()`**: Validate audio data
  - **Function `_extract_speechbrain_embedding()`**: Extract embedding using SpeechBrain model
  - **Function `_extract_mfcc_embedding()`**: Extract MFCC-based embedding
  - **Function `assess_quality()`**: Assess overall quality score (0-1)
  - **Function `_assess_snr()`**: Assess signal-to-noise ratio
  - **Function `_assess_spectral_clarity()`**: Assess spectral clarity and definition
  - **Function `_assess_speech_activity()`**: Assess speech activity level
  - **Function `_assess_clipping()`**: Assess audio clipping
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `detect_spoofing()`**: Detect voice spoofing
  - **Function `_analyze_spectral_artifacts()`**: Analyze spectral artifacts common in synthetic speech
  - **Function `_analyze_temporal_artifacts()`**: Analyze temporal artifacts for replay detection
  - **Function `_analyze_harmonic_structure()`**: Analyze harmonic structure naturalness
  - **Function `__init__()`**: Signature: (self, config)
  - **Function `enroll_user()`**: Enroll a new user with voice samples
  - **Function `recognize_user()`**: Recognize user from voice sample
  - **Function `_preprocess_audio()`**: Preprocess audio for fingerprinting
  - **Function `_calculate_embedding_similarity()`**: Calculate similarity between embeddings
  - **Function `_adapt_user_profile()`**: Adaptively update user profile with new embedding
  - **Function `_optimize_profile_embeddings()`**: Optimize profile embeddings using clustering
  - **Function `start_continuous_recognition()`**: Start continuous user recognition
  - **Function `stop_continuous_recognition()`**: Stop continuous recognition
  - **Function `_continuous_recognition_loop()`**: Continuous recognition loop
  - **Function `add_recognition_audio()`**: Add audio for continuous recognition
  - **Function `get_latest_recognition()`**: Get latest recognition result
  - **Function `delete_user_profile()`**: Delete a user profile
  - **Function `get_user_profiles()`**: Get list of enrolled user profiles
  - **Function `_save_user_profile()`**: Save user profile to disk
  - **Function `_load_user_profiles()`**: Load user profiles from disk

### File: `core_ai\src\ai_assistant\voice\voice_settings_manager.py`
  - *(Documentation parsing failed for this file)*

### File: `core_ai\src\ai_assistant\voice\wake_word_detector.py`
- **Class `WakeWordDetectionMode`**: Wake word detection modes
- **Class `SmartWakeWordDetector`**: Always-on wake word detection like Google Assistant Low latency, works completely offline using PocketSphinx
- **Class `WakeWordManager`**: Manages wake word detection and integration with main assistant Handles custom wake words, profiles, and learning
  - **Function `get_wake_word_manager()`**: Get or create wake word manager instance
  - **Function `__init__()`**: Initialize wake word manager
  - **Function `_initialize_decoder()`**: Initialize Vosk decoder for wake word detection
  - **Function `start_listening()`**: Start continuous listening for wake words
  - **Function `stop_listening()`**: Stop listening for wake words
  - **Function `_listen_loop()`**: Main listening loop
  - **Function `_process_audio_chunk()`**: Process audio chunk for wake word detection
  - **Function `_on_detection()`**: Handle wake word detection
  - **Function `add_custom_wake_word()`**: Add custom wake word at runtime
  - **Function `remove_wake_word()`**: Remove wake word
  - **Function `get_detection_stats()`**: Get detection statistics
  - **Function `simulate_wake_word()`**: Simulate wake word for testing
  - **Function `__init__()`**: Initialize wake word manager
  - **Function `_on_wake_word()`**: Handle wake word detection
  - **Function `start()`**: Start wake word detection
  - **Function `stop()`**: Stop wake word detection
  - **Function `get_stats()`**: Get manager statistics
  - **Function `set_custom_wake_words()`**: Set custom wake words
  - **Function `on_wake_word()`**: Signature: ()

### File: `core_ai\src\ai_assistant\workflow\intent_registry.py`
- **Class `IntentMapping`**: Represents a mapping from intent to workflow template.
- **Class `IntentRegistry`**: Registry for mapping natural language intents to workflow templates.
  - **Function `__init__()`**: Initialize the intent registry.
  - **Function `_load_templates()`**: Load all workflow templates from the templates directory.
  - **Function `_load_template_file()`**: Load a single workflow template file and extract intent information.
  - **Function `get_intent_mapping()`**: Get the intent mapping for a given intent string.
  - **Function `get_all_intents()`**: Get a list of all registered intents.
  - **Function `reload_templates()`**: Reload all template files.

### File: `core_ai\src\ai_assistant\workflow\intent_router.py`
- **Class `IntentRouter`**: Semantic Router for advanced intent classification. Uses local embeddings to map user queries to actionable routes.
  - **Function `__init__()`**: Signature: (self, threshold)
  - **Function `_define_routes()`**: Define the semantic routes for the system.
  - **Function `determine_intent()`**: Determine the intent of a query. Returns: (route_name, confidence_score)

### File: `core_ai\src\ai_assistant\workflow\orchestrator.py`
- **Class `WorkflowOrchestrator`**: Manages high-level workflows that require coordination between multiple agents.
  - **Function `__init__()`**: Signature: (self, registry)

### File: `backend\app_integration_api.py`
  - **Function `require_auth()`**: Decorator to require authentication for API endpoints.
  - **Function `login()`**: Authenticate user for web interface.
  - **Function `logout()`**: Logout user.
  - **Function `list_apps()`**: List all registered applications.
  - **Function `register_app()`**: Register a new application.
  - **Function `get_app_details()`**: Get detailed information about a specific app.
  - **Function `launch_app()`**: Launch an application.
  - **Function `stop_app()`**: Stop an application.
  - **Function `remove_app()`**: Remove an application registration.
  - **Function `toggle_app_enabled()`**: Enable or disable an application.
  - **Function `trigger_autostart()`**: Trigger auto-start for all configured apps.
  - **Function `cleanup_processes()`**: Clean up terminated processes.
  - **Function `system_status()`**: Get overall system status.
  - **Function `get_categories()`**: Get available app categories and their default permissions.
  - **Function `get_integration_types()`**: Get available integration types.
  - **Function `not_found()`**: Signature: (error)
  - **Function `internal_error()`**: Signature: (error)
  - **Function `decorated_function()`**: Signature: ()

### File: `backend\google_speech_websocket_handler.py`
  - **Function `register_google_speech_handlers()`**: Signature: ()
  - **Function `handle_start_google()`**: Signature: ()
  - **Function `handle_google_audio()`**: Signature: ()
  - **Function `handle_stop_google()`**: Signature: ()

### File: `backend\insights_engine.py`
- **Class `InsightsEngine`**: Aggregates contextual data for the Proactive Insights Dashboard. Manages Calendar, Tasks, Weather, and News data.
  - **Function `get_insights_engine()`**: Signature: ()
  - **Function `__init__()`**: Signature: (self)
  - **Function `get_daily_briefing()`**: Aggregates all insights into a daily briefing object.
  - **Function `get_upcoming_events()`**: Fetches upcoming calendar events. Currently returns mock data for demonstration.
  - **Function `get_pending_tasks()`**: Fetches pending tasks. Currently returns mock data.
  - **Function `get_weather_summary()`**: Fetches weather summary. Tries to use automation_tools_new if available, else mock.
  - **Function `get_top_news()`**: Fetches top news headlines.
  - **Function `calculate_daily_focus()`**: Determines the 'Focus of the Day' based on schedule and tasks.

### File: `backend\learning_api.py`
- **Class `SampleData`**: Core component.
- **Class `LabelRequest`**: Core component.
- **Class `ExplainRequest`**: Core component.
- **Class `SessionData`**: Core component.
- **Class `ConversationData`**: Core component.
- **Class `TaskRequest`**: Core component.
- **Class `WorkflowRequest`**: Core component.
- **Class `CausalEdge`**: Core component.
- **Class `InterventionRequest`**: Core component.
- **Class `RLStateAction`**: Core component.
- **Class `MetaTaskRequest`**: Core component.
- **Class `FederatedClientRequest`**: Core component.
- **Class `GNNNodeRequest`**: Core component.
- **Class `GNNEdgeRequest`**: Core component.
- **Class `DomainRequest`**: Core component.
- **Class `CommandContext`**: Core component.
- **Class `VoiceRecognition`**: Core component.
- **Class `WorkflowContext`**: Core component.
- **Class `ContextRequest`**: Core component.
  - **Function `get_active_learner()`**: Signature: ()
  - **Function `get_explainability()`**: Signature: ()
  - **Function `get_behavior_clusterer()`**: Signature: ()
  - **Function `get_conversation_clusterer()`**: Signature: ()
  - **Function `get_llm_bandit()`**: Signature: ()
  - **Function `get_model_compressor()`**: Signature: ()
  - **Function `get_workflow_scheduler()`**: Signature: ()
  - **Function `get_contrastive_learner()`**: Signature: ()
  - **Function `get_self_supervised()`**: Signature: ()
  - **Function `get_causal_inference()`**: Signature: ()
  - **Function `get_query_cache()`**: Signature: ()
  - **Function `get_command_sequences()`**: Signature: ()
  - **Function `get_historical_rag()`**: Signature: ()
  - **Function `get_command_predictor()`**: Signature: ()
  - **Function `get_anomaly_detector()`**: Signature: ()
  - **Function `get_knowledge_graph()`**: Signature: ()
  - **Function `get_ppo_agent()`**: Signature: ()
  - **Function `get_maml_learner()`**: Signature: ()
  - **Function `get_federated_server()`**: Signature: ()
  - **Function `get_gnn()`**: Signature: ()
  - **Function `get_domain_embeddings()`**: Signature: ()
  - **Function `get_smart_commands()`**: Signature: ()
  - **Function `get_adaptive_voice()`**: Signature: ()
  - **Function `get_workflow_recommender()`**: Signature: ()
  - **Function `get_context_generator()`**: Signature: ()

### File: `backend\learning_dashboard_api.py`
- **Class `LearningDashboardAPI`**: Provides data for the learning dashboard
  - **Function `__init__()`**: Signature: (self, data_dir)
  - **Function `_get_all_databases()`**: Get list of all learning databases
  - **Function `get_dashboard_data()`**: Get complete dashboard data
  - **Function `get_summary_stats()`**: Get summary statistics
  - **Function `get_database_stats()`**: Get detailed stats for each database
  - **Function `get_recent_activity()`**: Get recent learning activity
  - **Function `get_growth_trend()`**: Get growth trend over time
  - **Function `get_system_breakdown()`**: Get breakdown by learning system
  - **Function `search_memory()`**: Search memory database
  - **Function `get_database_content()`**: Get content from a specific database table
  - **Function `_count_records()`**: Count records in a table
  - **Function `_count_active_systems()`**: Count how many learning systems have data
  - **Function `_aggregate_weekly()`**: Aggregate daily stats to weekly
  - **Function `_aggregate_monthly()`**: Aggregate daily stats to monthly

### File: `backend\learning_integration.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\modern_web_backend.py`
  - **Function `_get_learning_router_lazy()`**: Signature: ()
  - **Function `_get_memory_retriever_lazy()`**: Signature: ()
  - **Function `_get_enhanced_ai_lazy()`**: Lazy load enhanced AI on first use
  - **Function `_get_usage_analyzer_lazy()`**: Lazy load usage analyzer on first use
  - **Function `_load_voice_modules()`**: Signature: ()
  - **Function `initialize_heavy_ai_models()`**: Run in a background thread to pre-warm the AI models without blocking the UI
  - **Function `start_ai_background_thread()`**: Starts the AI loading thread. Called by desktop app or main.
  - **Function `get_or_create_env_secret()`**: Signature: (name)
  - **Function `exempt_localhost()`**: Exempt the local desktop app from all rate limits so health checks don't ban it.
  - **Function `initialize_local_ai()`**: Initialize local AI model in background
  - **Function `get_current_context()`**: Signature: ()
  - **Function `get_user_preferences()`**: Signature: ()
  - **Function `get_user_profile_status()`**: Signature: ()
  - **Function `setup_user_profile()`**: Signature: ()
  - **Function `save_user_preferences()`**: Signature: ()
  - **Function `get_initialization_status()`**: Signature: ()
  - **Function `validate_input()`**: Validate input data against pattern
  - **Function `sanitize_command()`**: Sanitize command input to prevent injection
  - **Function `index()`**: Signature: ()
  - **Function `serve_static_or_react()`**: Signature: ()
  - **Function `enhanced_chat()`**: Signature: ()
  - **Function `download_page()`**: Signature: ()
  - **Function `download_windows_app()`**: Signature: ()
  - **Function `test_page()`**: Signature: ()
  - **Function `api_register()`**: Signature: ()
  - **Function `api_login()`**: Signature: ()
  - **Function `api_verify_token()`**: Signature: ()
  - **Function `api_status()`**: Signature: ()
  - **Function `api_learning_stats()`**: Signature: ()
  - **Function `learning_dashboard()`**: Signature: ()
  - **Function `api_learning_dashboard()`**: Signature: ()
  - **Function `api_learning_databases()`**: Signature: ()
  - **Function `api_database_content()`**: Signature: ()
  - **Function `api_memory_search()`**: Signature: ()
  - **Function `api_learning_documentation()`**: Signature: ()
  - **Function `api_logs_recent()`**: Signature: ()
  - **Function `api_all_learning_stats()`**: Signature: ()
  - **Function `api_smart_command_predict()`**: Signature: ()
  - **Function `api_context_generate()`**: Signature: ()
  - **Function `api_workflow_recommend()`**: Signature: ()
  - **Function `api_anomaly_detect()`**: Signature: ()
  - **Function `api_causal_query()`**: Signature: ()
  - **Function `api_knowledge_graph_query()`**: Signature: ()
  - **Function `api_adaptive_voice_log()`**: Signature: ()
  - **Function `api_rl_select_action()`**: Signature: ()
  - **Function `api_single_system_stats()`**: Signature: ()
  - **Function `api_local_ai_status()`**: Signature: ()
  - **Function `api_chat()`**: Signature: ()
  - **Function `api_command()`**: Signature: ()
  - **Function `api_startup_sequence()`**: Signature: ()
  - **Function `api_startup_diagnostics()`**: Signature: ()
  - **Function `api_startup_briefing()`**: Signature: ()
  - **Function `api_enhanced_stats()`**: Signature: ()
  - **Function `api_clear_cache()`**: Signature: ()
  - **Function `api_usage_analysis()`**: Signature: ()
  - **Function `api_export_training_data()`**: Signature: ()
  - **Function `api_chat_stream()`**: Signature: ()
  - **Function `api_get_session()`**: Signature: ()
  - **Function `api_delete_session()`**: Signature: ()
  - **Function `api_system_stats()`**: Signature: ()
  - **Function `api_weather()`**: Signature: ()
  - **Function `api_features()`**: Signature: ()
  - **Function `api_create_context()`**: Signature: ()
  - **Function `api_get_suggestions()`**: Signature: ()
  - **Function `api_multimodal_analyze()`**: Signature: ()
  - **Function `api_analyze_screen()`**: Signature: ()
  - **Function `api_get_workflows()`**: Signature: ()
  - **Function `api_execute_workflow()`**: Signature: ()
  - **Function `api_save_memory()`**: Signature: ()
  - **Function `api_search_memory()`**: Signature: ()
  - **Function `api_detect_language()`**: Signature: ()
  - **Function `api_translate_text()`**: Signature: ()
  - **Function `api_apps()`**: Signature: ()
  - **Function `api_refresh_apps()`**: Signature: ()
  - **Function `api_launch_app()`**: Signature: ()
  - **Function `api_spotify_status()`**: Signature: ()
  - **Function `api_spotify_control()`**: Signature: ()
  - **Function `api_visual_question()`**: Signature: ()
  - **Function `api_activity()`**: Signature: ()
  - **Function `api_voice_history()`**: Signature: ()
  - **Function `api_voice_status()`**: Signature: ()
  - **Function `api_start_voice()`**: Signature: ()
  - **Function `api_stop_voice()`**: Signature: ()
  - **Function `api_speak()`**: Signature: ()
  - **Function `api_list_voices()`**: Signature: ()
  - **Function `api_preview_voice()`**: Signature: ()
  - **Function `api_process_voice()`**: Signature: ()
  - **Function `handle_enhanced_chat()`**: Signature: ()
  - **Function `handle_chat_stream()`**: Signature: ()
  - **Function `handle_analyze_image()`**: Signature: ()
  - **Function `handle_analyze_screen()`**: Signature: ()
  - **Function `handle_get_suggestions()`**: Signature: ()
  - **Function `handle_execute_workflow()`**: Signature: ()
  - **Function `handle_mood_detection()`**: Signature: ()
  - **Function `handle_system_stats_request()`**: Signature: ()
  - **Function `handle_start_voice()`**: Signature: ()
  - **Function `handle_stop_voice()`**: Signature: ()
  - **Function `handle_voice_audio()`**: Signature: ()
  - **Function `handle_voice_command()`**: Signature: ()
  - **Function `handle_tts_request()`**: Signature: ()
  - **Function `process_hinglish()`**: Signature: ()
  - **Function `set_language_preference()`**: Signature: ()
  - **Function `get_language_preference()`**: Signature: ()
  - **Function `handle_multilingual_command()`**: Signature: ()
  - **Function `api_log_error()`**: Signature: ()
  - **Function `api_save_settings()`**: Signature: ()
  - **Function `api_load_settings()`**: Signature: ()
  - **Function `api_get_all_settings()`**: Signature: ()
  - **Function `api_update_settings()`**: Signature: ()
  - **Function `api_reset_settings()`**: Signature: ()
  - **Function `api_export_settings()`**: Signature: ()
  - **Function `api_import_settings()`**: Signature: ()
  - **Function `api_get_available_models()`**: Signature: ()
  - **Function `api_get_model_preference()`**: Signature: ()
  - **Function `api_set_model_preference()`**: Signature: ()
  - **Function `api_get_model_stats()`**: Signature: ()
  - **Function `api_compare_models()`**: Signature: ()
  - **Function `api_get_providers()`**: Signature: ()
  - **Function `local_ai_status()`**: Signature: ()
  - **Function `local_ai_chat()`**: Signature: ()
  - **Function `local_ai_reset()`**: Signature: ()
  - **Function `local_ai_stats()`**: Signature: ()
  - **Function `local_ai_load_model()`**: Signature: ()
  - **Function `local_ai_unload()`**: Signature: ()
  - **Function `api_organize_files()`**: Signature: ()
  - **Function `api_find_duplicates()`**: Signature: ()
  - **Function `api_search_files()`**: Signature: ()
  - **Function `api_batch_rename()`**: Signature: ()
  - **Function `api_analyze_directory()`**: Signature: ()
  - **Function `api_ocr_check_dependencies()`**: Signature: ()
  - **Function `api_extract_text_image()`**: Signature: ()
  - **Function `api_extract_text_pdf()`**: Signature: ()
  - **Function `api_analyze_document()`**: Signature: ()
  - **Function `api_extract_key_information()`**: Signature: ()
  - **Function `api_get_weather()`**: Signature: ()
  - **Function `api_get_news()`**: Signature: ()
  - **Function `api_get_stock()`**: Signature: ()
  - **Function `api_get_crypto()`**: Signature: ()
  - **Function `api_scrape_website()`**: Signature: ()
  - **Function `api_get_trending()`**: Signature: ()
  - **Function `api_detect_taskbar()`**: Signature: ()
  - **Function `api_taskbar_capabilities()`**: Signature: ()
  - **Function `api_find_app_in_taskbar()`**: Signature: ()
  - **Function `api_get_running_apps()`**: Signature: ()
  - **Function `not_found_error()`**: Signature: (error)
  - **Function `internal_error()`**: Signature: (error)
  - **Function `bad_request_error()`**: Signature: (error)
  - **Function `service_unavailable_error()`**: Signature: (error)
  - **Function `create_chain()`**: Signature: ()
  - **Function `resume_chain()`**: Signature: ()
  - **Function `get_chain_status()`**: Signature: ()
  - **Function `get_chain_history()`**: Signature: ()
  - **Function `_broadcast_chain_progress()`**: Broadcast chain progress via WebSocket
  - **Function `handle_chain_subscribe()`**: Signature: ()
  - **Function `serve_unified_dashboard()`**: Signature: ()
  - **Function `write_a_note()`**: Signature: ()
  - **Function `open_application()`**: Signature: ()
  - **Function `search_google()`**: Signature: ()
  - **Function `search_youtube()`**: Signature: ()
  - **Function `close_application()`**: Signature: ()
  - **Function `speak()`**: Signature: ()
  - **Function `set_system_volume()`**: Signature: ()
  - **Function `get_app_path_from_name()`**: Signature: ()
  - **Function `setup_memory()`**: Signature: ()
  - **Function `save_to_memory()`**: Signature: ()
  - **Function `get_memory()`**: Signature: ()
  - **Function `search_memory()`**: Signature: ()
  - **Function `get_conversation_summary()`**: Signature: ()
  - **Function `save_knowledge()`**: Signature: ()
  - **Function `get_knowledge()`**: Signature: ()
  - **Function `discover_applications()`**: Signature: ()
  - **Function `smart_open_application()`**: Signature: ()
  - **Function `list_installed_apps()`**: Signature: ()
  - **Function `get_apps_for_web()`**: Signature: ()
  - **Function `get_system_status()`**: Signature: ()
  - **Function `get_running_processes()`**: Signature: ()
  - **Function `cleanup_temp_files()`**: Signature: ()
  - **Function `get_network_info()`**: Signature: ()
  - **Function `get_upcoming_events()`**: Signature: ()
  - **Function `get_inbox_summary()`**: Signature: ()
  - **Function `get_spotify_status()`**: Signature: ()
  - **Function `spotify_play_pause()`**: Signature: ()
  - **Function `spotify_next_track()`**: Signature: ()
  - **Function `spotify_previous_track()`**: Signature: ()
  - **Function `search_and_play_spotify()`**: Signature: ()
  - **Function `get_weather_info()`**: Signature: ()
  - **Function `get_latest_news()`**: Signature: ()
  - **Function `get_stock_price()`**: Signature: ()
  - **Function `detect_taskbar_apps()`**: Signature: ()
  - **Function `can_see_taskbar()`**: Signature: ()
  - **Function `get_cached_stats()`**: Signature: ()
  - **Function `broadcast_system_stats()`**: Signature: ()
- **Class `MinimalAssistant`**: Core component.
  - **Function `generate_stream()`**: Signature: ()
  - **Function `run_chain_background()`**: Signature: ()
  - **Function `__init__()`**: Signature: ()
  - **Function `process_command()`**: Signature: ()
  - **Function `get_real_time_system_stats()`**: Signature: ()
  - **Function `get_init_status()`**: Signature: ()
  - **Function `analyze_screen()`**: Signature: ()
  - **Function `answer_visual_question()`**: Signature: ()
  - **Function `start_voice_listening()`**: Signature: ()
  - **Function `stop_voice_listening()`**: Signature: ()
  - **Function `speak_text()`**: Signature: ()
  - **Function `process_voice_audio()`**: Signature: ()

### File: `backend\startup_sequence.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\user_preferences.py`
- **Class `UserPreferencesManager`**: Manages user preferences with file-based storage
  - **Function `get_preferences_manager()`**: Get or create preferences manager instance
  - **Function `__init__()`**: Signature: (self, storage_dir)
  - **Function `_get_user_file()`**: Get the preferences file path for a user
  - **Function `get_preferences()`**: Get user preferences, returns defaults if not found
  - **Function `save_preferences()`**: Save user preferences to file
  - **Function `_merge_with_defaults()`**: Merge user preferences with defaults to ensure all keys exist
  - **Function `_deep_merge()`**: Deep merge two dictionaries
  - **Function `reset_preferences()`**: Reset user preferences to defaults

### File: `backend\voice_service.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\backend\app.py`
  - **Function `create_app()`**: Create and configure the Flask application
  - **Function `initialize_components()`**: Initialize AI components and automation tools

### File: `backend\backend\error_handler.py`
- **Class `AIAssistantError`**: Base exception for AI Assistant
- **Class `VoiceError`**: Voice-related errors
- **Class `AutomationError`**: Automation-related errors
- **Class `ValidationError`**: Input validation errors
  - **Function `handle_error()`**: Centralized error handling with logging
  - **Function `error_handler()`**: Decorator for consistent error handling in routes
  - **Function `log_request()`**: Log incoming request details
  - **Function `decorator()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `backend\backend\main.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\backend\middleware.py`
  - **Function `request_logger()`**: Log all incoming requests
  - **Function `add_security_headers()`**: Add security headers to all responses
  - **Function `validate_json()`**: Ensure request contains valid JSON
  - **Function `sanitize_input()`**: Basic input sanitization
  - **Function `wrapper()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `backend\backend\routes.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\backend\system_monitor.py`
  - **Function `get_network_speed()`**: Signature: ()
  - **Function `start_system_monitor()`**: Starts a background task that emits system stats via SocketIO.
  - **Function `monitor_loop()`**: Signature: ()

### File: `backend\backend\update_routes.py`
  - **Function `init_update_routes()`**: Initialize update routes with updater instance
  - **Function `check_for_updates()`**: Check if updates are available
  - **Function `get_update_info()`**: Get current update status and configuration
  - **Function `download_update()`**: Download available update
  - **Function `install_update()`**: Install downloaded update
  - **Function `update_config()`**: Get or update configuration
  - **Function `ignore_version()`**: Ignore a specific version

### File: `backend\backend\utils.py`
  - **Function `generate_session_id()`**: Generate secure session ID
  - **Function `generate_api_token()`**: Generate API token
  - **Function `hash_string()`**: Hash a string with salt
  - **Function `format_timestamp()`**: Format timestamp for API responses
  - **Function `safe_dict_get()`**: Safely get value from dict
  - **Function `truncate_string()`**: Truncate string to max length
  - **Function `validate_required_fields()`**: Validate that required fields are present

### File: `backend\backend\websocket.py`
  - **Function `register_handlers()`**: Register all WebSocket event handlers
  - **Function `handle_connect()`**: Signature: ()
  - **Function `handle_disconnect()`**: Signature: ()
  - **Function `handle_ping()`**: Signature: ()
  - **Function `handle_chat_message()`**: Signature: ()
  - **Function `handle_voice_start()`**: Signature: ()
  - **Function `handle_voice_audio()`**: Signature: ()
  - **Function `handle_voice_stop()`**: Signature: ()
  - **Function `handle_system_command()`**: Signature: ()
  - **Function `handle_get_status()`**: Signature: ()

### File: `backend\backend\blueprints\apps.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\backend\blueprints\auth.py`
  - **Function `create_blueprint()`**: Create and configure the auth blueprint
  - **Function `register()`**: Signature: ()
  - **Function `login()`**: Signature: ()
  - **Function `verify_token()`**: Signature: ()

### File: `backend\backend\blueprints\chat.py`
  - **Function `create_blueprint()`**: Create and configure the chat blueprint
  - **Function `chat()`**: Signature: ()
  - **Function `command()`**: Signature: ()
  - **Function `chat_stream()`**: Signature: ()
  - **Function `get_session()`**: Signature: ()
  - **Function `delete_session()`**: Signature: ()
  - **Function `set_context()`**: Signature: ()
  - **Function `get_suggestions()`**: Signature: ()
  - **Function `generate()`**: Signature: ()

### File: `backend\backend\blueprints\learning.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\backend\blueprints\memory.py`
  - **Function `create_blueprint()`**: Create and configure the memory & language blueprint
  - **Function `save_memory()`**: Signature: ()
  - **Function `search_memory()`**: Signature: ()
  - **Function `recall_memory()`**: Signature: ()
  - **Function `detect_language()`**: Signature: ()
  - **Function `translate_text()`**: Signature: ()

### File: `backend\backend\blueprints\multimodal.py`
  - **Function `create_blueprint()`**: Create and configure the multimodal blueprint
  - **Function `analyze_multimodal()`**: Signature: ()
  - **Function `analyze_screen()`**: Signature: ()
  - **Function `visual_question()`**: Signature: ()
  - **Function `extract_text_ocr()`**: Signature: ()
  - **Function `analyze_document()`**: Signature: ()
  - **Function `generate_image()`**: Signature: ()

### File: `backend\backend\blueprints\preferences.py`
  - **Function `get_settings_path()`**: Get absolute path to app_settings.json
  - **Function `load_settings()`**: Load settings from file
  - **Function `save_settings_to_file()`**: Save settings to file
  - **Function `create_blueprint()`**: Create and configure the settings blueprint
  - **Function `get_all_settings()`**: Signature: ()
  - **Function `complete_onboarding()`**: Signature: ()
  - **Function `update_settings()`**: Signature: ()
  - **Function `reset_settings()`**: Signature: ()
  - **Function `export_settings()`**: Signature: ()
  - **Function `import_settings()`**: Signature: ()

### File: `backend\backend\blueprints\system.py`
  - *(Documentation parsing failed for this file)*

### File: `backend\backend\blueprints\utilities.py`
  - **Function `create_blueprint()`**: Create and configure the utilities blueprint
  - **Function `get_weather()`**: Signature: ()
  - **Function `get_features()`**: Signature: ()
  - **Function `get_activity()`**: Signature: ()
  - **Function `get_workflows()`**: Signature: ()
  - **Function `execute_automation()`**: Signature: ()
  - **Function `spotify_status()`**: Signature: ()
  - **Function `spotify_control()`**: Signature: ()

### File: `backend\backend\blueprints\voice.py`
  - **Function `create_blueprint()`**: Create and configure the voice blueprint
  - **Function `voice_status()`**: Signature: ()
  - **Function `voice_history()`**: Signature: ()
  - **Function `start_voice()`**: Signature: ()
  - **Function `stop_voice()`**: Signature: ()
  - **Function `get_voice_settings()`**: Signature: ()
  - **Function `update_voice_settings()`**: Signature: ()
  - **Function `speak_text()`**: Signature: ()
  - **Function `recognize_audio()`**: Signature: ()

### File: `backend\backend\blueprints\web.py`
  - **Function `create_blueprint()`**: Signature: (assistant)
  - **Function `status()`**: Signature: ()

### File: `backend\utils\advanced_logging.py`
  - **Function `log_performance()`**: Decorator to log function performance
- **Class `ContextualErrorLogger`**: Enhanced error logger with context information
- **Class `APIRequestLogger`**: Logger for API requests and responses
- **Class `SecurityLogger`**: Logger for security-related events
- **Class `UserActivityLogger`**: Logger for user activity and interactions
- **Class `LogAggregator`**: Aggregates and analyzes log data
  - **Function `log_error_with_context()`**: Convenience function for logging errors with context
  - **Function `log_api_call()`**: Convenience function for logging API calls
  - **Function `log_user_action()`**: Convenience function for logging user actions
  - **Function `decorator()`**: Signature: ()
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_exception()`**: Log exception with full context
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_request()`**: Log incoming API request
  - **Function `log_response()`**: Log API response
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_auth_attempt()`**: Log authentication attempt
  - **Function `log_suspicious_activity()`**: Log suspicious activity
  - **Function `__init__()`**: Signature: (self)
  - **Function `log_user_action()`**: Convenience function for logging user actions
  - **Function `log_voice_command()`**: Log voice command interaction
  - **Function `__init__()`**: Signature: (self)
  - **Function `generate_daily_summary()`**: Generate daily log summary
  - **Function `slow_function()`**: Signature: ()
  - **Function `wrapper()`**: Signature: ()

### File: `backend\utils\convert_prints.py`
- **Class `PrintToLoggerConverter`**: Converts print statements to logger calls throughout the project
  - **Function `main()`**: Run the conversion
  - **Function `__init__()`**: Signature: (self, project_root)
  - **Function `convert_project()`**: Convert all Python files in the project
  - **Function `_should_skip_file()`**: Check if file should be skipped
  - **Function `_convert_file()`**: Convert a single file

### File: `backend\utils\embeddings.py`
- **Class `EmbeddingStore`**: Core component.
  - **Function `get_openai_embedding()`**: Get OpenAI embedding for text.
  - **Function `__init__()`**: Signature: (self, dim)
  - **Function `add()`**: Signature: (self, text, embedding)
  - **Function `search()`**: Signature: (self, query_embedding, top_k)

### File: `backend\utils\logging_analyzer.py`
- **Class `LoggingAnalyzer`**: Analyzes the entire project for logging issues and improvements.
  - **Function `main()`**: Run comprehensive logging analysis.
  - **Function `__init__()`**: Signature: (self, project_root)
  - **Function `analyze_project()`**: Perform comprehensive logging analysis.
  - **Function `_analyze_python_files()`**: Analyze all Python files for logging issues.
  - **Function `_analyze_python_file()`**: Analyze a single Python file.
  - **Function `_analyze_frontend_files()`**: Analyze frontend files for console.log statements.
  - **Function `_analyze_js_file()`**: Analyze a JavaScript/TypeScript file.
  - **Function `_analyze_config_files()`**: Analyze configuration files.
  - **Function `_should_skip_file()`**: Check if file should be skipped.
  - **Function `_generate_recommendations()`**: Generate recommendations for logging improvements.

### File: `backend\utils\logging_completion.py`
- **Class `LoggingSystemValidator`**: Validates the complete logging system
  - **Function `create_logging_utilities()`**: Create helpful logging utilities
  - **Function `main()`**: Main function to complete logging system
  - **Function `__init__()`**: Signature: (self)
  - **Function `validate_all()`**: Run comprehensive validation
  - **Function `_validate_directories()`**: Validate log directory structure
  - **Function `_validate_configuration()`**: Validate logging configuration
  - **Function `_test_loggers()`**: Test all logger types
  - **Function `_validate_rotation()`**: Validate log rotation settings
  - **Function `_test_performance_logging()`**: Test performance logging decorator
  - **Function `_test_error_handling()`**: Test error logging
  - **Function `_test_api_logging()`**: Test API logging
  - **Function `_validate_frontend_logging()`**: Validate frontend logging integration
  - **Function `_validate_documentation()`**: Validate logging documentation
  - **Function `generate_report()`**: Generate comprehensive validation report
  - **Function `test_performance_function()`**: Signature: ()

### File: `backend\utils\logging_config.py`
- **Class `SessionManager`**: Manages logging sessions with unique identifiers
- **Class `LoggingConfig`**: Centralized logging configuration manager
  - **Function `get_logger()`**: Get or create a configured logger with session support
  - **Function `get_api_logger()`**: Get a logger configured specifically for API logging
  - **Function `get_performance_logger()`**: Get a logger configured for performance metrics
  - **Function `log_api_request()`**: Helper function to log API requests with consistent formatting
  - **Function `get_current_date()`**: Get current date in YYYY-MM-DD format for folder organization
  - **Function `start_new_session()`**: Start a new logging session with timestamp
  - **Function `get_current_session()`**: Get current session ID (returns None if no session started)
  - **Function `get_session_start_time()`**: Get session start time
  - **Function `get_dated_log_dirs()`**: Get log directories organized by current date
  - **Function `LOG_DIRS()`**: Signature: (cls)
  - **Function `initialize()`**: Initialize logging directory structure
  - **Function `_generate_readme()`**: Generate README for logs directory
  - **Function `get_session_file_handler()`**: Create a session-specific file handler
  - **Function `get_session_error_handler()`**: Create session-specific error-only file handler
  - **Function `get_console_handler()`**: Create console handler
  - **Function `get_formatter()`**: Get a log formatter

### File: `backend\utils\session_activity_logger.py`
- **Class `SessionActivityLogger`**: Logs all user activities in session-specific files
  - **Function `get_session_activity_logger()`**: Get or create singleton session activity logger
- **Class `_LazyLogger`**: Core component.
  - **Function `log_voice_command()`**: Log a voice command activity
  - **Function `log_file_operation()`**: Log a file operation activity
  - **Function `log_system_command()`**: Log a system command activity
  - **Function `log_api_request()`**: Log an API request activity
  - **Function `log_user_interaction()`**: Log a user interaction activity
  - **Function `log_music_control()`**: Log a music control activity
  - **Function `log_email_operation()`**: Log an email operation activity
  - **Function `log_calendar_operation()`**: Log a calendar operation activity
  - **Function `log_web_scraping()`**: Log a web scraping activity
  - **Function `log_multimodal_ai()`**: Log a multimodal AI activity
  - **Function `log_automation()`**: Log an automation activity
  - **Function `end_current_session()`**: End the current logging session
  - **Function `__init__()`**: Signature: (self)
  - **Function `__getattr__()`**: Signature: (self, name)
  - **Function `_initialize_logger()`**: Initialize logger components (called after session is ready)
  - **Function `_save_session_start()`**: Save session start information
  - **Function `log_voice_command()`**: Log a voice command activity
  - **Function `log_file_operation()`**: Log a file operation activity
  - **Function `log_system_command()`**: Log a system command activity
  - **Function `log_api_request()`**: Log an API request activity
  - **Function `log_user_interaction()`**: Log a user interaction activity
  - **Function `log_music_control()`**: Log a music control activity
  - **Function `log_email_operation()`**: Log an email operation activity
  - **Function `log_calendar_operation()`**: Log a calendar operation activity
  - **Function `log_web_scraping()`**: Log a web scraping activity
  - **Function `log_multimodal_ai()`**: Log a multimodal AI activity
  - **Function `log_automation()`**: Log an automation activity
  - **Function `_update_session_summary()`**: Update session summary with new activity
  - **Function `end_session()`**: Mark session as ended
  - **Function `__getattr__()`**: Signature: (self, name)

### File: `backend\utils\session_init.py`
  - **Function `_initialize_session()`**: Initialize session only once
  - **Function `get_session_info()`**: Get current session information
  - **Function `log_module_initialization()`**: Log when a module is initialized

### File: `backend\utils\tool_schemas.py`

### File: `backend\utils\update_logging.py`
  - **Function `update_logging_calls()`**: Update logging calls in a file
  - **Function `main()`**: Update all module files

### File: `backend\utils\user_data_logger.py`
  - **Function `get_timestamp()`**: Signature: ()
  - **Function `save_data()`**: Saves data to the appropriate folder with a timestamp.
  - **Function `log_action()`**: Logs a user action.
  - **Function `log_query()`**: Logs a user query.
  - **Function `log_reply()`**: Logs an assistant reply.
  - **Function `log_module_usage()`**: Logs the usage of a module and function.

---

## 🖥️ 6. Desktop Integration & Automation
- **App Discovery**: Continously maps common names to deep `.exe` paths.
- **PyWinAuto UI Trees**: Inspects native Windows application UI elements.
- **Media Control**: Simulates OS-level Virtual-Key Codes.

---

## 🛠️ 7. Comprehensive Setup & Installation
1. Install Python 3.10+, Node.js 18+, Ollama, Tesseract-OCR, and C++ Build Tools.
2. Setup `.env` with `OPENAI_API_KEY`, `GOOGLE_GEMINI_API_KEY`, `ELEVEN_LABS_API_KEY`.
3. Start Backend: `python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt && python backend/modern_web_backend.py`
4. Start Frontend: `cd frontend/web-app && npm install && npm run dev`

---

## 📦 8. Executable Packaging Guide
To distribute the AI Assistant to non-technical users:
1. Build React bundle: `cd frontend/web-app && npm run build`
2. Run PyInstaller: `desktop\build_exe.bat`
3. Execute `dist_package/Pulsar_Assistant/Pulsar_Assistant.exe`

---

## ⚠️ 9. Troubleshooting & Known Issues
- `WebView2 initialization failed (0x800700AA)`: Zombie `msedgewebview2.exe` process holding cache lock.
- `Hidden import 'pywinauto' not found`: Ensure `--hidden-import=pywinauto` is present in `.spec`.

---
Appendix: Technical Deep Dive
This appendix provides detailed technical information about specific subsystems and implementations mentioned throughout the documentation.

���������������������� Vision Language Model (VLM) System
PULSAR implements a Vision Language Model system using Google's Gemini Vision API for advanced visual understanding capabilities.

Key Components:

GeminiVisionProvider (gemini_vision_provider.py): Concrete implementation of the VLMProvider abstract interface
Supported Model: gemini-1.5-flash for efficient vision-language tasks
Capabilities:
Image analysis and description generation
Text extraction from images (OCR-like functionality)
Object detection and localization
Visual question answering
Implementation Details:
class GeminiVisionProvider(VLMProvider):
    def __init__(self, api_key=None, model_name="gemini-1.5-flash"):
        # Configures Gemini API with provided key
        # Initializes model for vision tasks
    
    def analyze_image(self, image, prompt="Describe this image in detail"):
        # Processes image with Gemini Vision API
        # Returns detailed textual analysis
    
    def extract_text(self, image):
        # Specialized OCR function using VLM capabilities
        # Often more accurate than traditional OCR for complex layouts
    
    def detect_objects(self, image):
        # Identifies and localizes objects within images
        # Returns bounding boxes and class labels

Dependencies: google-generativeai, Pillow (PIL)
Environment Variable: GEMINI_API_KEY

������������������� OCR (Optical Character Recognition) System
PULSAR features a robust OCR system based on Tesseract with extensive image preprocessing capabilities for accurate text extraction from various document formats.

Key Components:

DocumentAnalyzer (document_ocr.py): Main OCR processing class
Dependency Management: Runtime checks for all required OCR dependencies
Multi-format Support: Images (PNG, JPG, TIFF, etc.) and PDF documents
OCR Pipeline:

Image Preprocessing (using PIL/Pillow and OpenCV):
Contrast enhancement
Sharpness improvement
Noise reduction via median filtering
RGB conversion for consistency
Text Extraction (using pytesseract):
Configurable OCR Engine Mode (OEM) and Page Segmentation Mode (PSM)
Multi-language support (English, French, German, Spanish, etc.)
PDF Processing:
PyPDF2 for basic PDF text extraction
pdfplumber for advanced table and layout preservation
Key Functions:

extract_text_from_image(): Extract text from image files with enhancement options
extract_text_from_pdf(): Process PDF documents page-by-page
check_ocr_dependencies(): Diagnostic function reporting availability of all OCR components
Dependencies:

PIL/Pillow (image processing)
pytesseract (Tesseract OCR wrapper)
OpenCV (image preprocessing)
PyPDF2 + pdfplumber (PDF processing)
Tesseract OCR engine (system-level installation required)
������������������� PDF Generation System
PULSAR includes PDF generation capabilities for creating documents, reports, and notes using the ReportLab library.

Key Components:

write_a_note function (core.py): Primary PDF generation interface
Runtime Dependency Checking: Graceful degradation when ReportLab is unavailable
Formatted Output: Proper text formatting, spacing, and document structure
Implementation Details:
if REPORTLAB_INSTALLED:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    
    # Create PDF with proper formatting
    c = canvas.Canvas(filename, pagesize=letter)
    # Text rendering with line wrapping and spacing
    c.save()

Features:

Automatic text wrapping and line spacing
Configurable page sizes (Letter, A4, etc.)
Font handling and text styling
Binary PDF output suitable for sharing and archiving
Dependencies: reportlab (optional - checked at runtime)

������������������� Productivity & MS Word Integration
PULSAR provides deep integration with Microsoft Office productivity suites through specialized agents that can create, edit, and manipulate Word documents, Excel spreadsheets, and PowerPoint presentations.

Productivity Agent (productivity_agent.py):

Specialized Capabilities:
create_word_document: Generate .docx files with formatted content
create_excel_spreadsheet: Build .xlsx files with data and formulas
create_powerpoint: Generate .pptx presentations with slides
edit_document: Modify existing office files
convert_formats: Convert between different document formats
Word Document Generation:

from docx import Document
from docx.shared import Inches

doc = Document()
doc.add_heading(title, 0)
doc.add_paragraph(content)
doc.save(output_path)

Excel Spreadsheet Creation:

from openpyxl import Workbook

wb = Workbook()
ws = wb.active
# Add data, formulas, formatting
wb.save(output_path)

PowerPoint Presentation:
from pptx import Presentation

prs = Presentation()
# Add slides with titles, content, images
prs.save(output_path)

Dependencies (lazy-loaded when needed):

python-docx (.docx manipulation)
openpyxl (.xlsx/spreadsheet handling)
python-pptx (.pptx/presentation creation)
File Management Integration: Works with FileManagerAgent for organizing generated documents in appropriate folders.

###����� Multi-Agent System (10-12 Specialized Agents)

PULSAR implements a sophisticated multi-agent architecture with 10-12 specialized agents, each handling specific domains of expertise. Agents communicate through a central dispatcher and can be dynamically loaded based on task requirements.

Agent Categories and Specializations:

Audio Agent (agents/audio/audio_agent.py)

Purpose: Audio generation and processing tasks
Capabilities: Music generation, sound effects creation, audio cleaning/noise reduction
Technologies: Mock implementations calling external APIs (MusicGen, Suno) for audio synthesis
Communication Agent (agents/communication/communication_agent.py)

Purpose: Handling messaging and communication tasks
Capabilities: Email sending, instant messaging, social media posting
Technologies: SMTP simulation, WhatsApp API simulation, social media API integration
Creative Agent (agents/creative/creative_agent.py)

Purpose: Generating creative assets (images, audio)
Capabilities: Image generation (thumbnails, art), audio generation (voiceovers, narration)
Technologies: DALL-E/Midjourney simulation for images, TTS systems for audio
File Manager Agent (agents/file/file_manager_agent.py)

Purpose: File system organization and manipulation
Capabilities: File organization by type, renaming, listing, cleanup operations
Technologies: Standard Python file I/O, shutil for file operations
Productivity Agent (agents/productivity/productivity_agent.py)

Purpose: Office productivity suite automation
Capabilities: Word document creation, Excel spreadsheet generation, PowerPoint presentation creation
Technologies: python-docx, openpyxl, python-pptx libraries
Research Agent (agents/research/research_agent.py & deep_research_agent.py)

Purpose: Information gathering and synthesis
Capabilities: Web scraping, search query generation, result summarization
Technologies: Requests, BeautifulSoup, simulated search APIs
Student Agent (agents/student/student_agent.py)

Purpose: Educational assistance and learning support
Capabilities: Homework help, concept explanation, study guide creation
Technologies: Knowledge retrieval, explanation generation, example creation
Video Agent (agents/video/video_agent.py)

Purpose: Video processing and editing tasks
Capabilities: Video editing, effect application, format conversion
Technologies: MoviePy simulation, Whisper for audio transcription
Web Agent (agents/web/web_agent.py)

Purpose: Web interaction and automation
Capabilities: Form filling, navigation, data extraction from websites
Technologies: Selenium/Playwright simulation, HTTP request handling
Writer Agent (agents/writer/writer_agent.py)

Purpose: Content creation and writing assistance
Capabilities: Article writing, story generation, content rewriting
Technologies: Template-based generation, language model prompting
Autonomous Learning Agent (agents/core/autonomous_agent.py)

Purpose: Self-improvement through observation and learning
Capabilities: Conversation persistence, behavior learning, skill generation
Technologies: LearningDataRouter integration, pattern recognition, knowledge extraction
Dispatcher Agent (agents/dispatcher.py)

Purpose: Central coordination and task routing
Capabilities: Agent registration, task distribution, load balancing
Technologies: Message queuing, capability matching, async task handling
Agent Communication Pattern:

Agents register with the Dispatcher upon initialization
Tasks are evaluated against each agent's can_handle() method
Matching agents execute tasks via their execute() method
Results are returned through standardized TaskResult objects
Failed attempts cascade to next capable agent
���������������������� Voice Systems
PULSAR implements a comprehensive voice processing pipeline with four core components working together to enable natural voice interaction.

1. Voice Activity Detection (VAD) (voice/voice_activity_detection.py)

Purpose: Detects presence of human speech in audio streams
Algorithms Implemented:
WebRTC VAD (Google's real-time voice detection)
Energy-based VAD (amplitude threshold analysis)
Spectral VAD (frequency domain analysis)
Configuration: Adjustable sensitivity and frame duration
Dependencies: webrtcvad, numpy, scipy
2. Noise Reduction (voice/noise_reduction.py)

Purpose: Cleans audio signals by removing background noise
Techniques:
Spectral subtraction (noise profile estimation and removal)
Wiener filtering (adaptive noise reduction)
Band-pass filtering (frequency isolation)
Dependencies: numpy, scipy for signal processing
3. Speech-to-Text (STT) (voice/advanced_speech_recognizer.py)

Purpose: Converts spoken audio to text transcriptions
Engines:
Whisper (OpenAI's robust speech recognition model)
Google Speech API (cloud-based alternative)
Sphinx (offline CMU Sphinx engine)
Features: Language detection, confidence scoring, timestamp generation
Dependencies: openai-whisper, SpeechRecognition, pydub
4. Text-to-Speech (TTS) (voice/neural_voice_engine.py)

Purpose: Converts text responses to natural-sounding speech
Engines:
Neural TTS (Tacotron, FastPitch, VITS variants)
gTTS (Google Text-to-Speech)
Edge TTS (Microsoft's neural voices)
Features: Voice selection, speed control, pitch adjustment, emotion modulation
Dependencies: TTS, gTTS, edge-tts, pydub
Voice Pipeline Flow:

Audio input → VAD (voice detection)
Detected speech → Noise Reduction (cleaning)
Clean audio → STT (transcription to text)
Text processed → LLM (response generation)
LLM response → TTS (speech synthesis)
Speech output → Audio playback
������������������� Camera & Screen Integration
PULSAR features advanced camera and screen capture capabilities for visual understanding and automation.

Multimodal AI System (vision/multimodal.py):

Core Class: MultiModalAI handles all visual input processing
Key Functions:
capture_screen(): Captures current desktop/screen contents
analyze_screen(image, prompt): Analyzes captured screen with VLM
process_webcam_frame(): Processes live webcam input
detect_ui_elements(): Identifies buttons, text fields, and interactive elements
Screen Capture Implementation:

def capture_screen():
    # Uses platform-specific methods (Windows GDI, etc.)
    # Returns PIL Image object for further processing
    # Optional region specification for partial captures

Visual Analysis Capabilities:

Screen Reading: Extract text and UI elements from screen captures
Context Understanding: Interpret visual context for informed decisions
Automation Guidance: Provide click coordinates and action recommendations
Accessibility Support: Describe visual content for visually impaired users
Dependencies:

Platform-specific screen capture libraries (mss, PIL.ImageGrab, etc.)
Gemini Vision Provider for image understanding
OpenCV for image processing operations
������������������� The 27 Advanced Learning Systems (Expanded)
Beyond the basic listing in the main documentation, here are detailed explanations of each learning paradigm implemented in PULSAR:

1. Active Learning: Queries humans to label the most informative unlabeled data points, reducing labeling effort while maximizing model improvement.

2. Meta Learning: "Learning to learn" - optimizes learning algorithms themselves based on experience with multiple learning tasks.

3. Federated Learning: Trains models across decentralized devices while keeping data localized, enhancing privacy and reducing centralization risks.

4. Contrastive Learning: Learns representations by contrasting similar and dissimilar pairs, improving feature discrimination without explicit labels.

5. Self-Supervised Learning: Creates supervisory signals from the data itself (e.g., predicting masked portions) when external labels are unavailable.

6. Transfer Learning: Applies knowledge learned from one task to improve performance on a related but different task.

7. Multi-Task Learning: Trains a single model on multiple related tasks simultaneously, leveraging shared representations for improved efficiency.

8. Continual Learning: Enables learning from a continuous stream of data without catastrophic forgetting of previously learned knowledge.

9. Few-Shot Learning: Learns new concepts from very few examples (often 1-5), mimicking human rapid learning capability.

10. Zero-Shot Learning: Performs tasks on classes never seen during training by leveraging semantic relationships and descriptions.

11. Reinforcement Learning: Learns optimal behaviors through trial-and-error interactions with an environment to maximize cumulative reward.

12. Deep Q-Learning (DQN): Combines Q-learning with deep neural networks to handle high-dimensional state spaces.

13. Policy Gradient Methods: Directly optimizes the policy function through gradient ascent on expected rewards.

14. Actor-Critic Methods: Combines value-based (critic) and policy-based (actor) approaches for more stable learning.

15. Proximal Policy Optimization (PPO): State-of-the-art RL algorithm that improves training stability through clipped objective functions.

16. Curriculum Learning: Trains on progressively more difficult examples, mimicking human educational scaffolding.

17. Multi-Modal Learning: Learns from multiple types of data (text, image, audio) simultaneously to build richer representations.

18. Transformer Learning: Utilizes self-attention mechanisms to capture long-range dependencies in sequential data.

19. Graph Neural Networks (GNN): Processes graph-structured data by propagating information between connected nodes.

20. Causal Learning: Discovers cause-effect relationships rather than mere correlations for more robust generalization.

21. Bayesian Learning: Applies probabilistic reasoning to quantify uncertainty in predictions and model parameters.

22. Uncertainty-Aware Learning: Explicitly models and propagates uncertainty through the learning pipeline.

23. Meta-Reasoning: Learns to reason about its own reasoning processes to improve decision-making strategies.

24. Analogical Reasoning: Transfers knowledge between domains by identifying structural similarities.

25. Concept Learning: Identifies and generalizes underlying concepts from specific examples.

26. Procedural Learning: Learns sequences of actions and procedures for skill automation.

27. Declarative Learning: Acquires factual knowledge and relationships for explicit recall and reasoning.

Each system is implemented in dedicated modules under ai with standardized interfaces for integration with the auto-learning router.

���������������������� Knowledge Base & Knowledge Graphs
PULSAR implements sophisticated knowledge representation and reasoning capabilities through semantic knowledge graphs that store information as interconnected entities and relationships.

Knowledge Storage Systems:

Primary Storage: Neo4j graph database (when available) for production-grade knowledge graphs
Fallback Storage: SQLite with graph extensions for lightweight, portable operation
Serialization: JSON-LD and RDF formats for knowledge exchange and persistence
Knowledge Graph Construction:

Entity Extraction: Identifies people, places, organizations, concepts from text
Relation Extraction: Discovers relationships between extracted entities (works-for, located-in, etc.)
Triple Formation: Structures knowledge as subject-predicate-object triples
Graph Assembly: Connects triples into a cohesive, queryable knowledge graph
Key Components:

Triple Extractor (knowledge/triple_extractor.py): Parses text to generate RDF triples
Semantic Search (knowledge/semantic_search.py): Finds related concepts using vector similarity
Reasoning Engine (knowledge/reasoning.py): Performs logical inference over stored knowledge
Ontology Manager (knowledge/ontology.py): Defines and manages knowledge schemas
Knowledge Graph Features:

Semantic Relationships: Hierarchical (is-a), meronymic (part-of), temporal, causal links
Property Inheritance: Attributes propagate through taxonomic hierarchies
Path Finding: Discovers connection chains between distantly related concepts
Clustering: Groups similar entities based on relationship patterns
Link Prediction: Suggests probable missing relationships
Query Capabilities:

SPARQL-like Interface: Graph pattern matching for complex queries
Natural Language Queries: Converts questions to graph traversals
Temporal Queries: Handles time-based knowledge and event sequencing
Geospatial Queries: Supports location-based reasoning when available
Applications in PULSAR:

Contextual Understanding: Maintains persistent context across conversations
Personal Knowledge: Learns and recalls user-specific facts and preferences
Domain Expertise: Builds specialized knowledge in user's areas of interest
Fact Verification: Checks consistency of new information against existing knowledge
Recommendation Engine: Suggests relevant content based on knowledge connections
Dependencies:

neo4j (primary graph database)
sqlite3 with spatial extensions (fallback)
numpy, scikit-learn (for embedding-based similarity)
rdflib (for RDF serialization/parsing)
������������������� AI Learning Methods
Beyond the core learning paradigms, PULSAR implements several advanced AI learning methods that enhance its adaptive capabilities:

1. Usage Pattern Analyzers:

Temporal Pattern Detection: Identifies recurring behaviors at specific times (daily, weekly routines)
Sequential Mining: Discovers common action sequences (workflows, multi-step processes)
Contextual Bandits: Optimizes decisions based on contextual features and delayed rewards
Implementation: Located in ai/usage_analyzer.py and ai/pattern_miner.py
2. Semantic Caching System:

Intent-Based Caching: Stores and retrieves responses based on semantic similarity of queries
Hierarchical Cache Organization: General → Specific knowledge organization
Cache Invalidation: Intelligent expiration based on relevance and usage patterns
Implementation: Found in ai/semantic_cache.py with vector similarity search
3. Context-Aware Response Generation:

Dynamic Context Assembly: Combines short-term conversation with long-term user knowledge
Relevance Scoring: Weights different context sources by predictive utility
Attention Mechanisms: Focuses generation on most pertinent contextual elements
Implementation: Integrated in ai/advanced_chat_system.py with context enrichment
4. Online Learning Trainers:

Incremental Model Updates: Continuously refines models with new data without full retraining
Elastic Weight Consolidation: Protects important knowledge while allowing adaptation
Experience Replay: Buffers experiences to prevent catastrophic forgetting
Implementation: Distributed across learning modules with train() methods supporting online updates
5. Meta-Learning Optimizers:

Learning Rate Adaptation: Adjusts optimization hyperparameters based on performance trends
Architecture Search: Experiments with model configurations to find optimal setups
Regularization Tuning: Dynamically adjusts prevention of overfitting/underfitting
Implementation: Found in ai/optimizer.py and ai/hyperparameter_tuner.py
6. Feedback-Driven Adaptation:

Explicit Feedback Processing: Learns from user corrections and ratings
Implicit Signal Detection: Infers satisfaction from interaction patterns and completion rates
Reward Modeling: Predicts user satisfaction to guide future behavior
Implementation: Centralized in ai/advanced_feedback_learning.py
7. Uncertainty Calibration:

Confidence Estimation: Quantifies prediction reliability for risk-aware decision making
Ensemble Methods: Combines multiple models to estimate prediction variance
Temperature Scaling: Post-hoc calibration of probability outputs
Implementation: Part of ai/uncertainty_quantifier.py and ensemble learners
8. Knowledge Distillation:

Model Compression: Transfers knowledge from large to smaller, faster models
Response-Based Distillation: Trains student to match teacher's output distributions
Feature-Based Distillation: Aligns intermediate representations between models
Implementation: Found in ai/distillation.py for model optimization
These learning methods work in concert with the 27 core learning paradigms to create a continuously improving system that adapts to individual user patterns while maintaining robust generalization capabilities.

This appendix provides technical details for developers and advanced users interested in the specific implementations of PULSAR's capabilities. For general usage information, refer to the main sections above.

You can manually append this content to the end of your README.md file. The analysis of all requested features (VLM, OCR, PDF Generation, Productivity/MS Word integration, Agents, Voice systems, Camera integration, 27 Learning Systems, Knowledge Base/Knowledge Graphs, and AI Learning Methods) has been completed through thorough examination of the codebase structure and implementation details.
