# 📚 PULSAR Documentation Hub & Master Index

Welcome to the centralized, categorized documentation repository for **PULSAR (`Ai_Assistant`)**. This directory contains comprehensive technical specifications for all 14 multi-agent cores, underlying AI capabilities, system architecture, API endpoints, and security audits.

---

## 🗺️ Quick Navigation Map

```text
docs/
├── agents/             ⭐ Exhaustive specifications for all 14 registered AI agents
├── capabilities/       ⭐ In-depth guides for Voice, Vision, Automation, NLP, and MCP
├── architecture/       🏛️ Multi-agent coordinator, state machines, and database schemas
├── api/                🔌 Complete REST & WebSocket API references
├── setup/              🛠️ Environment setup, dependencies, hardware specs, and packaging
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

* 🎙️ **Voice & Speech Engine:** [VOICE_AND_SPEECH_ENGINE.md](capabilities/VOICE_AND_SPEECH_ENGINE.md)  
  *Vosk offline ASR, Whisper, EchoGuard loop suppression, Voice Activity Detection, Neural TTS.*
* 👁️ **Vision & OCR System:** [VISION_AND_OCR_SYSTEM.md](capabilities/VISION_AND_OCR_SYSTEM.md)  
  *Tesseract OCR, Gemini Vision, local VLM, facial recognition & MediaPipe hand gestures.*
* 🖥️ **Desktop & GUI Automation:** [DESKTOP_AND_GUI_AUTOMATION.md](capabilities/DESKTOP_AND_GUI_AUTOMATION.md)  
  *Pywinauto UI control, window manager, live taskbar analysis, closed-loop visual verification.*
* ⚡ **Smart Workflows & Chains:** [SMART_WORKFLOWS_AND_CHAINS.md](capabilities/SMART_WORKFLOWS_AND_CHAINS.md)  
  *Multi-agent DAG scheduling, step dependency pipelining, and self-healing automation.*
* 💬 **Offline NLP & Intent Matching:** [OFFLINE_NLP_AND_INTENTS.md](capabilities/OFFLINE_NLP_AND_INTENTS.md)  
  *Fine-tuned offline transformer model, sub-millisecond intent tables, zero-latency local routing.*
* 🕸️ **Personal Knowledge Graph:** [PERSONAL_KNOWLEDGE_GRAPH.md](capabilities/PERSONAL_KNOWLEDGE_GRAPH.md)  
  *Entity-relationship memory in SQLite, edge weight reinforcement, adaptive preference recall.*
* 🤖 **Local AI & Model Switching:** [LOCAL_AI_AND_MODEL_SWITCHING.md](capabilities/LOCAL_AI_AND_MODEL_SWITCHING.md)  
  *Ollama / GGUF local inference gateway vs. Gemini / OpenAI cloud routing with automatic failover.*
* 🌐 **Browser Automation & Scraping:** [BROWSER_AUTOMATION_AND_SCRAPING.md](capabilities/BROWSER_AUTOMATION_AND_SCRAPING.md)  
  *Persistent cookie/session profiles, dynamic waiting, and anti-bot stealth.*
* 🔌 **Model Context Protocol (MCP):** [MCP_AND_EXTERNAL_INTEGRATIONS.md](capabilities/MCP_AND_EXTERNAL_INTEGRATIONS.md)  
  *Connecting standardized local and remote tool servers via STDIO/SSE.*

---

## 🏛️ 3. Core Architecture (`docs/architecture/`)

* [DATABASE_SCHEMAS.md](architecture/DATABASE_SCHEMAS.md): Relational schemas for `personal_knowledge`, `memory`, and `users`.
* [ADVANCED_LEARNING_SYSTEMS.md](architecture/ADVANCED_LEARNING_SYSTEMS.md): Machine learning paradigms and continuous learning loops.
* [ONLINE_LEARNING_ARCHITECTURE.md](architecture/ONLINE_LEARNING_ARCHITECTURE.md): Data routing, observation buffers, and memory persistence.
* [FINE_TUNING_STRATEGY.md](architecture/FINE_TUNING_STRATEGY.md): LoRA fine-tuning pipelines and training datasets.
* [COMPLETE_MULTI_AGENT_IMPLEMENTATION_PLAN.md](architecture/COMPLETE_MULTI_AGENT_IMPLEMENTATION_PLAN.md): Multi-Agent coordinator design.

---

## 🔌 4. API Reference (`docs/api/`)

* [API_REFERENCE_COMPLETE.md](api/API_REFERENCE_COMPLETE.md): Complete REST endpoint catalog.
* [CHAIN_OF_ACTIONS_API.md](api/CHAIN_OF_ACTIONS_API.md): Specification for `/api/chain/*` DAG endpoints.
* [MODEL_SELECTION_API.md](api/MODEL_SELECTION_API.md): Dynamic model switching and LLM status endpoints.
* [WEB_BACKEND_INTEGRATION.md](api/WEB_BACKEND_INTEGRATION.md): Telemetry, health checks, and WebSocket streams.

---

## 🛠️ 5. Setup & Developer Environment (`docs/setup/`)

* [DEVELOPER_SETUP.md](setup/DEVELOPER_SETUP.md): Windows environment configuration and toolchain.
* [INSTALLATION_GUIDE.md](setup/INSTALLATION_GUIDE.md): Step-by-step setup from scratch.
* [DEPLOYMENT_GUIDE.md](setup/DEPLOYMENT_GUIDE.md): Packaging desktop binaries and running background services.
* [DEPENDENCY_UPDATE_MANAGEMENT.md](setup/DEPENDENCY_UPDATE_MANAGEMENT.md): Managing Python and npm package upgrades.

---

## 🛡️ 6. Security & Vulnerability Audits (`docs/security/`)

* [SECURITY.md](security/SECURITY.md): Global security policies and disclosure guidelines.
* [PIN_AUTHENTICATION.md](security/PIN_AUTHENTICATION.md): Secure PIN verification and constant-time comparison.
* [APP_INTEGRATION_SECURITY.md](security/APP_INTEGRATION_SECURITY.md): Gated confirmation workflows and sandbox boundaries.
* [AUDIT_AND_VULNERABILITY_REPORT.md](security/AUDIT_AND_VULNERABILITY_REPORT.md): Comprehensive codebase audit tracking bugs, breakpoints, and loose connections.

---

## 🔗 Primary Repository Entrypoints
* 🏠 **[Root Project README](../../README.md)**: Global project architecture and quickstart.
* 🎨 **[Frontend README](../../frontend/web-app/README.md)**: React 18, Vite, Tailwind, and Tauri client.
* ⚙️ **[Backend README](../../backend/README.md)**: Flask/FastAPI runtime, routes, and background threads.
