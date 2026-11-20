# 📚 PULSAR Documentation Hub & Master Index

Welcome to the centralized, categorized documentation repository for **PULSAR (`Ai_Assistant`)**. This directory contains comprehensive technical specifications for all 14 multi-agent cores, underlying AI capabilities, system architecture, API endpoints, and security audits.

---

## 🗺️ Quick Navigation Map

```text
docs/
├── agents/             ⭐ Specifications for all 14 registered AI agents
├── capabilities/       ⭐ In-depth guides for Web Intelligence, Voice, Vision, Automation, NLP, and MCP
├── architecture/       🏛️ Pulsar Standalone, Zero-Hardcoded Storage, Multi-Agent Swarm, and SQLite Schemas
├── api/                🔌 Complete REST, WebSocket, and IPC API references
├── setup/              🛠️ Environment setup, dependencies, Packaging & Distribution, and Developer Guide
├── security/           🛡️ Security architecture, PIN authentication, and vulnerability audit
└── archive_reports/    🗄️ Historical point-in-time reports, snapshots, and legacy notes
```

---

## 🤖 1. The 14 Multi-Agent Cores (`docs/agents/`)

Every agent has a dedicated document covering identity, class hierarchy, declared capabilities, parameter schemas, return types, error handling, and invocation examples:

| # | Agent Name | Agent ID | Canonical Specification | Key Focus |
|---|---|---|---|---|
| **01** | Productivity Agent | `productivity-001` | [01_PRODUCTIVITY_AGENT.md](agents/01_PRODUCTIVITY_AGENT.md) | Word, Excel, PowerPoint, PDF generation & format conversion |
| **02** | Research Agent | `research-001` | [02_RESEARCH_AGENT.md](agents/02_RESEARCH_AGENT.md) | Asynchronous DuckDuckGo search, Wikipedia & URL scraping |
| **03** | Writer Agent | `writer-001` | [03_WRITER_AGENT.md](agents/03_WRITER_AGENT.md) | Articles, essays, emails, proofreading & text summarization |
| **04** | Video Agent | `video-001` | [04_VIDEO_AGENT.md](agents/04_VIDEO_AGENT.md) | Video clipping, transcription, audio extraction & desktop app control |
| **05** | Creative Agent | `creative-001` | [05_CREATIVE_AGENT.md](agents/05_CREATIVE_AGENT.md) | PNG graphics, banners, layouts, Pillow filters & voiceovers |
| **06** | Data Analyst Agent | `data-001` | [06_DATA_ANALYST_AGENT.md](agents/06_DATA_ANALYST_AGENT.md) | Statistical analysis, CSV/JSON processing & chart generation |
| **07** | Database Agent | `database-001` | [07_DATABASE_AGENT.md](agents/07_DATABASE_AGENT.md) | SQLite/SQL schemas, query execution & destructive command gating |
| **08** | Communication Agent | `comm-001` | [08_COMMUNICATION_AGENT.md](agents/08_COMMUNICATION_AGENT.md) | Gmail drafting/dispatch, WhatsApp & Calendar scheduling |
| **09** | Web Agent | `web-001` | [09_WEB_AGENT.md](agents/09_WEB_AGENT.md) | Web navigation, form inspection & Selenium dynamic automation |
| **10** | Student Agent | `student-001` | [10_STUDENT_AGENT.md](agents/10_STUDENT_AGENT.md) | Symbolic math (SymPy), flashcards & local note RAG tutor |
| **11** | File Manager Agent | `file-001` | [11_FILE_MANAGER_AGENT.md](agents/11_FILE_MANAGER_AGENT.md) | File categorization, searching, batch renaming & zip backups |
| **12** | Audio Agent | `audio-001` | [12_AUDIO_AGENT.md](agents/12_AUDIO_AGENT.md) | Procedural music/SFX synthesis, audio noise removal & TTS |
| **13** | Deep Research Agent | `deep-research-001` | [13_DEEP_RESEARCH_AGENT.md](agents/13_DEEP_RESEARCH_AGENT.md) | Multi-query expansion, parallel scraping & whitepaper synthesis |
| **14** | Autonomous Learning Agent | `autonomous-001` | [14_AUTONOMOUS_LEARNING_AGENT.md](agents/14_AUTONOMOUS_LEARNING_AGENT.md) | Long-term memory, preference tracking & autonomous skill synthesis |

---

## 🌟 2. Subsystem Capabilities & Engines (`docs/capabilities/`)

Deep architectural dives into core features operating across the platform:

* 🌐 **Web Intelligence & Real-Time Search:** [WEB_INTELLIGENCE_AND_SEARCH.md](capabilities/WEB_INTELLIGENCE_AND_SEARCH.md)  
  *Autonomous 4-mode classifier (`BACKGROUND_GROUNDING`, `BROWSER_ACTION`, `DEEP_RESEARCH`, `DIRECT_CHAT`), multi-engine fallback (DuckDuckGo, Instant Facts, SerpApi, Tavily, Wikipedia), tiered TTL caching, and LLM prompt grounding.*
* 🎙️ **Voice & Speech Engine:** [VOICE_AND_SPEECH_ENGINE.md](capabilities/VOICE_AND_SPEECH_ENGINE.md)  
  *Reference-counted Windows CoreAudio ducking (-65%), faster-whisper STT, Vosk offline ASR, EchoGuard acoustic loop suppression, speech text crisper, Hinglish vocabulary registry, and EdgeTTS/KittenTTS synthesis.*
* 👁️ **Vision & OCR System:** [VISION_AND_OCR_SYSTEM.md](capabilities/VISION_AND_OCR_SYSTEM.md)  
  *Tesseract OCR, Gemini Vision, local VLM, facial recognition & MediaPipe hand gestures.*
* 🖥️ **Desktop & GUI Automation:** [DESKTOP_AND_GUI_AUTOMATION.md](capabilities/DESKTOP_AND_GUI_AUTOMATION.md)  
  *Windows COM automation, screen-share stealth mode exclusion (`SetWindowDisplayAffinity`), floating 4D particle orb overlay, window manager, live taskbar analysis, and debounced emergency stop.*
* ⚡ **Smart Workflows, Swarm Planner & DAG Memory:** [SMART_WORKFLOWS_AND_CHAINS.md](capabilities/SMART_WORKFLOWS_AND_CHAINS.md)  
  *Dynamic Swarm Meta-Planner, Workflow Memory DAG Cache (`projects.db`), multi-agent DAG scheduling, compound syntax parsing (`&&`, `->`, Hinglish), and self-healing automation.*
* 💬 **Offline NLP & Intent Matching:** [OFFLINE_NLP_AND_INTENTS.md](capabilities/OFFLINE_NLP_AND_INTENTS.md)  
  *27 system intent categories, local command normalizer, Hinglish intent classifier, zero-latency local routing.*
* 🕸️ **Personal Knowledge Graph:** [PERSONAL_KNOWLEDGE_GRAPH.md](capabilities/PERSONAL_KNOWLEDGE_GRAPH.md)  
  *Entity-relationship memory in SQLite, edge weight reinforcement, adaptive preference recall.*
* 🤖 **Local AI & Model Switching:** [LOCAL_AI_AND_MODEL_SWITCHING.md](capabilities/LOCAL_AI_AND_MODEL_SWITCHING.md)  
  *Native GGUF CPU/GPU execution via `llama-cpp-python` (Llama 3.1 8B Instruct Q4_K_M), strict intent routing, and network-aware cloud failover to Gemini/OpenRouter/Groq.*
* 🔌 **Model Context Protocol (MCP):** [MCP_AND_EXTERNAL_INTEGRATIONS.md](capabilities/MCP_AND_EXTERNAL_INTEGRATIONS.md)  
  *Connecting standardized local and remote tool servers via STDIO/SSE.*

---

## 🏛️ 3. Core Architecture (`docs/architecture/`)

* 🌌 [PULSAR_STANDALONE_ARCHITECTURE.md](architecture/PULSAR_STANDALONE_ARCHITECTURE.md): Strict Paradigm B dual-mode binary design, Win32 Kernel Job Object supervision (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), Single-Instance Mutex, Token Security, Parent Watchdog, and 4D Orb Window.
* 🗄️ [STORAGE_AND_PATHS_ARCHITECTURE.md](architecture/STORAGE_AND_PATHS_ARCHITECTURE.md): Enterprise Zero-Hardcoded Storage Architecture, dynamic `%APPDATA%\PulsarAI\` path resolution, SQLite WAL mode concurrency, and crash recovery.
* 🤖 [COMPLETE_MULTI_AGENT_IMPLEMENTATION_PLAN.md](architecture/COMPLETE_MULTI_AGENT_IMPLEMENTATION_PLAN.md): Multi-Agent coordinator design and agent dispatch state machine.
* 🗃️ [DATABASE_SCHEMAS.md](architecture/DATABASE_SCHEMAS.md): Relational schemas for `personal_knowledge`, `historical_rag`, `commitments`, and `projects`.
* 🧠 [ADVANCED_LEARNING_SYSTEMS.md](architecture/ADVANCED_LEARNING_SYSTEMS.md): The 27 machine learning paradigms and continuous learning loops.
* 🔄 [ONLINE_LEARNING_ARCHITECTURE.md](architecture/ONLINE_LEARNING_ARCHITECTURE.md): Data routing, observation buffers, and memory persistence.
* 🎯 [FINE_TUNING_STRATEGY.md](architecture/FINE_TUNING_STRATEGY.md): LoRA fine-tuning pipelines and 2.5M command dataset generation.

---

## 🔌 4. API Reference (`docs/api/`)

* [API_REFERENCE_COMPLETE.md](api/API_REFERENCE_COMPLETE.md): Complete REST endpoint catalog across all 27 systems.
* [CHAIN_OF_ACTIONS_API.md](api/CHAIN_OF_ACTIONS_API.md): Specification for `/api/chain/*` DAG endpoints.
* [MODEL_SELECTION_API.md](api/MODEL_SELECTION_API.md): Dynamic model switching and LLM status endpoints.
* [WEB_BACKEND_INTEGRATION.md](api/WEB_BACKEND_INTEGRATION.md): Telemetry, health checks, and WebSocket streams.

---

## 🛠️ 5. Setup, Packaging & Distribution (`docs/setup/`)

* 📦 [PACKAGING_AND_DISTRIBUTION.md](setup/PACKAGING_AND_DISTRIBUTION.md): Automated distribution pipeline (`scripts/build_distributable_release.py`), native C# Windows 11 Setup Wizard (`PulsarSetup.exe`), PyInstaller specs, and privacy sanitization tools.
* 💻 [DEVELOPER_SETUP.md](setup/DEVELOPER_SETUP.md): Windows environment configuration and C++ build toolchain.
* 🚀 [INSTALLATION_GUIDE.md](setup/INSTALLATION_GUIDE.md): Step-by-step developer setup from scratch.
* 🔄 [DEPENDENCY_UPDATE_MANAGEMENT.md](setup/DEPENDENCY_UPDATE_MANAGEMENT.md): Managing Python and npm package upgrades.

---

## 🛡️ 6. Security & Vulnerability Audits (`docs/security/`)

* [SECURITY.md](security/SECURITY.md): Global security policies, sandbox boundaries, and disclosure guidelines.
* [PIN_AUTHENTICATION.md](security/PIN_AUTHENTICATION.md): Secure constant-time PIN verification and JWT token issuance.
* [APP_INTEGRATION_SECURITY.md](security/APP_INTEGRATION_SECURITY.md): Gated confirmation workflows for destructive system commands.
* [AUDIT_AND_VULNERABILITY_REPORT.md](security/AUDIT_AND_VULNERABILITY_REPORT.md): Comprehensive codebase audit tracking bugs, breakpoints, and loose connections.

---

## 🔗 Primary Repository Entrypoints
* 🏠 **[Root Project README](../README.md)**: Global project architecture and quickstart.
* 🌌 **[Pulsar Subsystem README](../pulsar/README.md)**: Standalone desktop companion, 4D Orb, tray app, and host supervisor.
* 🎨 **[Frontend README](../frontend/web-app/README.md)**: React 18, Vite, Tailwind, Three.js 4D Orb, and Tauri client.
* ⚙️ **[Backend README](../backend/README.md)**: Modern web backend, route blueprints, service forwarders, and websockets.
