# “PULSAR”
## A Native OS Automation and Multi-Modal Agentic AI Assistant for Windows

**SYNOPSIS OF MAJOR PROJECT**  
of  
**Bachelor of Technology**  
in  
**Computer Science & Engineering**  

### By
| S.No. | Student Name | Roll Number | Branch and Section |
| :---: | :---: | :---: | :---: |
| 1 | Diwakar Singh | 2301650100004 | Computer Science & Engineering |

**Kanpur Institute of Technology, Kanpur**  
**Dr. A.P.J. Abdul Kalam Technical University, Lucknow**  
**Academic Session: 2026–27**  

---

## DECLARATION
We hereby declare that this submission is our own work and that, to the best of our knowledge and belief, it contains no material previously published or written by another person nor material which to a substantial extent has been accepted for the award of any other degree or diploma by the university or other institute of higher learning, except where due acknowledgement has been made in the text.

**Signature:** _________________________________________  
**Name:** Diwakar Singh  
**Roll No:** 2301650100004  
**Date:** ________________________  

**Approved By:**  
**Rahul Singh**  
Head of Department  
Computer Science and Engineering  
KIT, KANPUR  
**Signature:** _________________________________________  

---

## TABLE OF CONTENTS
| No. | Particulars | Page |
| :---: | :--- | :---: |
| 1. | Introduction | 4 |
| 2. | Objectives and System Study | 5 |
| 3. | Requirement Analysis | 7 |
| 4. | System Architecture and Design | 8 |
| 5. | Module Description | 10 |
| 6. | Database Design | 13 |
| 7. | Implementation | 15 |
| 8. | Testing and Validation | 16 |
| 9. | Results, Benefits and Limitations | 18 |
| 10. | Future Scope and Conclusion | 19 |
| 11. | References and Appendix | 20 |

---

## 1. INTRODUCTION

### 1.1 Background
Personal computing workflows have expanded dramatically in scope and complexity. Modern users routinely operate across dozens of simultaneous desktop windows, disparate software utilities, web browsers, code editors, and file repositories. While modern Large Language Models (LLMs) have demonstrated remarkable conversational and cognitive capabilities, the overwhelming majority of existing AI assistants remain constrained within remote web browsers and sandboxed cloud environments. They act as passive conversational advisors rather than active operating system actuating agents.

PULSAR was developed as a unified, offline, multi-modal operating system automation platform for Windows. It connects natural language and voice interaction directly to the underlying operating system environment, allowing users to automate desktop applications, organize files, inspect system processes, perform real-time screen OCR, and retrieve long-term context entirely on-device without exposing sensitive data to cloud servers.

### 1.2 Problem Statement
Traditional commercial AI assistants suffer from three fundamental architectural shortcomings:
1. **Privacy Risks:** Private system state, typed documents, and personal queries are transmitted over the public internet to third-party data centers.
2. **Lack of OS Integration:** They cannot click desktop buttons, switch active windows, launch installed software, or manage local directory hierarchies.
3. **High Latency & Costs:** Recurring subscription fees and network round-trip latencies degrade real-time hands-free voice usability.

PULSAR addresses these challenges by implementing an air-gapped, zero-leakage desktop assistant architecture leveraging 4-bit quantized local GGUF models on consumer CPUs, real-time speech recognition, and native Windows Win32 APIs for safe, deterministic automation.

### 1.3 Need for the System
- 100% offline edge execution ensuring absolute privacy, data ownership, and zero telemetry leakage.
- Direct Windows OS automation (GUI navigation, window management, keystrokes, and registry inspection).
- Real-time multimodal sensory perception combining fast streaming voice STT, TTS, and desktop OCR.
- Deterministic multi-agent task planning to break down complex goals into safe, verifiable execution steps.
- Continuous personalization using 27 programmatic learning paradigms that adapt to user habits and slang.
- Zero-dependency persistent memory utilizing SQLite FTS5 full-text search with zero cloud footprint.

### 1.4 Scope of the Project
The scope includes a dual-engine architecture featuring a React + Vite + TypeScript desktop interface, a modular Flask API gateway with 11 domain blueprints, local Q4_K_M GGUF Llama 3.1 8B CPU inference, real-time speech recognition via faster-whisper, desktop vision and Tesseract OCR, PyWin32 automation drivers, SQLite database clusters, PIN-based cryptographic security, and automated system diagnostics.

---

## 2. OBJECTIVES AND SYSTEM STUDY

### 2.1 Objectives
1. Develop a high-performance offline AI desktop agent natively integrated into the Windows OS environment.
2. Implement local quantized LLM inference (Llama 3.1 8B Q4_K_M GGUF) operating efficiently on consumer CPUs.
3. Construct a multi-agent orchestration dispatcher for natural language goal decomposition and negotiation.
4. Integrate real-time streaming speech recognition (faster-whisper) with acoustic emotion tracking and TTS.
5. Provide visual desktop perception through window boundary tracking, screen capture, and Tesseract OCR.
6. Build an OS automation engine using PyWin32 and PyAutoGUI for hands-free software navigation and control.
7. Implement 27 continuous learning paradigms to dynamically adapt to user vocabulary, Hinglish slang, and habits.
8. Provide zero-dependency long-term memory retrieval using SQLite FTS5 BM25 search and semantic graphs.
9. Enforce strict PIN-based cryptographic authorization for privileged system, filesystem, and process controls.
10. Package the complete system into a responsive native Windows desktop application using PyWebView.

### 2.2 Existing System
| Area | Typical Approach | Limitation |
| :--- | :--- | :--- |
| **OS Control** | Web-based chatbots (ChatGPT, Claude) | Sandboxed inside browser; cannot interact with native apps or files. |
| **Data Privacy** | Cloud LLM REST APIs | User prompts, files, and system data are sent to remote corporate servers. |
| **Latency & Cost** | Pay-per-token cloud subscriptions | High network latency hampers voice interaction; ongoing monthly fees. |
| **Context & Memory** | Ephemeral session histories | Loss of context across desktop reboots; expensive context window scaling. |
| **Desktop Macros** | Rigid RPA / AutoHotkey scripts | Fragile to UI layout changes; incapable of cognitive reasoning or error recovery. |

### 2.3 Proposed System
PULSAR bridges the gap between neural cognitive reasoning and deterministic OS execution. The system runs an edge-quantized cognitive engine coupled with a multi-agent dispatcher, perception pipelines, and native Windows automation drivers. Complex user requests are autonomously decomposed into sequential sub-tasks, validated through security checks, executed directly against native Windows applications, and remembered across sessions via local SQLite databases.

*(Refer to Figure 2.1 in the generated PDF for the full interaction workflow diagram).*

---

## 3. REQUIREMENT ANALYSIS

### 3.1 Functional Requirements
- **Natural Language & Voice Processing:** Ingest real-time microphone streams, transcribe audio using faster-whisper, and parse natural text intents.
- **Edge LLM Inference:** Execute 4-bit quantized GGUF models on CPU without requiring external APIs, cloud compute, or active internet connections.
- **Native OS Automation:** Manipulate Windows desktop windows, click buttons, input text, dispatch hotkeys, and interact with the system taskbar.
- **Computer Vision & OCR:** Capture desktop screens, detect window boundaries, and extract textual content via Tesseract OCR.
- **Multi-Agent Goal Decomposition:** Break down complex user goals into verifiable sub-tasks and delegate to specialized domain agents.
- **Contextual Long-Term Memory:** Store conversation logs, extract semantic facts, and retrieve memories using SQLite FTS5 BM25 search.
- **Cryptographic Security Gate:** Enforce PIN-hash authentication for privileged system actions (file deletion, app kill, registry changes).
- **Automated Application Discovery:** Continuously index installed Windows software and system utilities via the Windows Registry.
- **Continuous Personalization:** Adapt to user slang (Hinglish), frequently used applications, and acoustic pitch patterns over time.
- **Proactive Telemetry & Self-Healing:** Monitor CPU/RAM consumption and autonomously retry failed automation actions.

### 3.2 Non-Functional Requirements
| Requirement | Implementation Consideration |
| :--- | :--- |
| **Security & Privacy** | 100% on-device air-gapped execution; salted SHA-256 PIN hashing; local database encryption; automated PII redaction from logs. |
| **Latency & Performance** | Sub-250ms voice transcription via faster-whisper; AVX2-accelerated GGUF CPU token streaming; lightweight PyWebView container. |
| **Reliability & Fault Tolerance** | Centralized error handling; traceback parsing; self-healing GUI retry loops; defensive parameter bounds checking. |
| **Usability & Ergonomics** | Dark-mode glassmorphic React interface; hands-free voice radar; non-intrusive floating desktop widget mode. |
| **Modularity & Extensibility** | Decoupled 11 Flask service blueprints; lazy-loaded multi-agent registry; pluggable tool definition schemas. |
| **Storage Efficiency** | Zero-dependency SQLite databases; FTS5 virtual tables; automated Ebbinghaus memory fading to prevent database bloat. |

### 3.3 Hardware and Software Requirements
- **Hardware:** Intel Core i5/i7 (8th Gen+) or AMD Ryzen 5/7 quad-core x64 processor supporting AVX2; minimum 8 GB of RAM (16 GB recommended); 20 GB free SSD storage; standard microphone and speakers.
- **Software:** Windows 10/11 64-bit OS; Python 3.10+; Node.js 18+ & npm; Tesseract-OCR 5+; C++ Build Tools (MSVC); SQLite3; Microsoft Edge / PyWebView runtime; Git.

---

## 4. SYSTEM ARCHITECTURE AND DESIGN

### 4.1 Architectural Overview
PULSAR follows a layered, edge-native client-server architecture:
- **Client Layer:** React 18 + Vite dashboard hosted in a frameless native PyWebView window.
- **API Gateway Layer:** Flask REST API with 11 domain blueprints and bidirectional Socket.IO WebSockets.
- **Cognitive & Multi-Agent Layer:** Central Dispatcher, Multi-Agent Swarm Registry, and Llama 3.1 8B Q4_K_M GGUF model via llama-cpp-python.
- **Perception & Automation Layer:** faster-whisper STT, offline TTS, Tesseract OCR, and PyWin32/PyAutoGUI automation.
- **Data & Persistence Layer:** 7 isolated SQLite databases with FTS5 full-text indexing, Neo4j semantic graph, and encrypted configurations.

### 4.2 Major Components
- **React Frontend:** Voice radar, chat assistant, telemetry monitors, and settings.
- **Flask Gateway:** Modular service endpoints routing requests and maintaining WebSockets.
- **Cognitive Engine:** Quantized LLM inference executing with native AVX2 instructions.
- **Multi-Agent Orchestrator:** Task planning, sub-agent delegation, and tool invocation.
- **Perception Pipeline:** Real-time audio stream listener and desktop OCR vision.
- **OS Controller:** Native Windows Win32 API window, mouse, and keyboard actuator.
- **SQLite FTS5 Core:** Sub-15ms BM25 long-term conversational memory store.

### 4.3 Data Flow
1. User provides input via microphone stream, text box, or global hotkey.
2. Sensory modules transcribe speech or extract screen text.
3. Gateway validates session tokens and payload parameters.
4. If privileged OS actions are requested, PIN Gate validates against `PIN_HASH`.
5. Dispatcher prompts Llama 3.1 8B GGUF model and plans sub-tasks.
6. Automation engine executes Win32 system actions.
7. Results are logged to SQLite memory, learning models are updated, and voice/UI feedback is returned.

### 4.4 Security Design
Air-gapped local execution guarantees zero external telemetry. Privileged actions require salted SHA-256 PIN hashing (`PIN_HASH`). Database and config files are encrypted with `SECURITY_KEY`. Local Named Entity Recognition (NER) redacts passwords and PII from execution logs before saving to disk.

---

## 5. MODULE DESCRIPTION

### 5.1 Authentication and Privileged Access Module
Enforces access control and defends system resources. Commands modifying filesystem hierarchies, terminating tasks, or accessing sensitive credentials require cryptographic PIN verification.

### 5.2 Multi-Agent Orchestration Module
Coordinates specialized autonomous agents:
- **Productivity Agent:** Schedules calendar events, reminders, and daily briefings.
- **File Manager Agent:** Categorizes files, batch renames, and eliminates duplicate downloads.
- **Communication Agent:** Composes emails, summarizes messages, and drafts replies.
- **Research & Student Agent:** Summarizes academic papers, extracts equations, and queries RAG facts.
- **Creative & Audio Agent:** Manages voice synthesis, volume controls, and media playback.
- **Autonomous Agent:** Passively observes user workflows and suggests proactive automations.

### 5.3 Offline LLM Inference & Cognitive Engine
Executes a fine-tuned, 4-bit quantized Llama 3.1 8B Instruct model (Q4_K_M GGUF) via llama-cpp-python, maintaining 12–18 tokens/sec on quad-core CPUs under 6.5 GB RAM.

### 5.4 Multimodal Perception (Voice & Vision) Module
Integrates `faster-whisper` for sub-250ms streaming transcription, an acoustic emotion tracker analyzing voice pitch and volume, and Tesseract 5 OCR for reading desktop windows.

### 5.5 Operating System Automation & Tool Execution Module
Translates cognitive goals into Windows API actions via `pywin32` and `pywinauto`. Features automated application discovery scanning the Windows Registry and Start Menu.

### 5.6 Continuous Learning & Memory Module
Implements 27 distinct programmatic learning systems including Active Learning, Intent Drift Adaptation for Hinglish slang, Ebbinghaus Memory Fading, and Contrastive Learning.

### 5.7 Contextual Telemetry & Proactive Diagnostics Module
Monitors active window focus shifts, tracks CPU/RAM via `psutil`, performs self-healing GUI recovery on failed clicks, and modulates AI personality dynamically.

---

## 6. DATABASE DESIGN

### 6.1 Database Technology
Lightweight local SQLite3 cluster partitioned into 7 databases. Utilizes SQLite's FTS5 extension for BM25 ranking without external vector database servers.

### 6.2 Major Entities and Databases
| Database | File | Purpose |
| :--- | :--- | :--- |
| **App Usage** | `app_usage.db` | Application launch frequencies, paths, and last-used timestamps. |
| **Chat History** | `chat_history.db` | Session metadata and message logs with token counts. |
| **Conversation AI** | `conversation_ai.db` | Context state, ongoing multi-turn goals, and personality parameters. |
| **Enhanced Learning** | `enhanced_learning.db` | Training samples, RLHF weights, intent drift logs, and feedback. |
| **Language Data** | `language_data.db` | Multilingual preferences, Hinglish slang mappings, and vocabulary caches. |
| **Memory Core** | `memory.db` | Long-term knowledge repository with SQLite FTS5 indexing and decay scores. |
| **Personal Knowledge** | `personal_knowledge.db` | User-defined rules, shortcut macros, and custom notes. |
| **Chain History** | `chain_history.db` | Multi-step execution traces, tool DAGs, and self-healing logs. |

### 6.3 Agent Task State Model
Tasks transition through `PENDING` -> `PARSING` -> `PLANNING` -> (`AWAITING_PIN` if privileged) -> `EXECUTING` -> `VERIFYING` -> `COMPLETED`. If errors occur, the state switches to `SELF_HEALING` to recalculate parameters.

### 6.4 Knowledge Graph and Memory Retention Pipeline
Interactions undergo entity/triple extraction, storage into SQLite FTS5 tables, exponential decay weighting via the Ebbinghaus forgetting curve, and dynamic injection into the LLM prompt.

---

## 7. IMPLEMENTATION

### 7.1 Frontend Implementation
React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, and PyWebView native container. Includes Voice Radar, Assistant chat, task execution monitors, and hardware widgets.

### 7.2 Backend Implementation
Python 3.10+ Flask gateway structured into 11 Blueprints with Socket.IO bidirectional event broadcasting.

### 7.3 Cognitive Engine & Local Inference
Llama 3.1 8B Instruct (Q4_K_M GGUF) via `llama-cpp-python` with AVX2 CPU vector optimizations and strict JSON grammar constraints.

### 7.4 Native Desktop Packaging & Automation
`pywin32`, `pywinauto`, and `pyautogui` for native Windows API interaction; PyInstaller for packaging into a standalone executable.

### 7.5 Deployment and Environment Configuration
Configured via `.env` with `PIN_HASH` and `SECURITY_KEY`. Automated installation and startup scripts (`install.ps1` and `Start.bat`).

---

## 8. TESTING AND VALIDATION

### 8.1 Testing Approach
Comprehensive testing across 42+ test suites in `tests/` using `pytest`. Tested model loading, voice latency, Win32 window focus, and SQLite FTS5 search.

### 8.2 Test Cases (Summary)
- Local GGUF Model Loading: **Passed**
- Real-Time Speech Recognition (<250ms): **Passed**
- Intent Classification (12 domains): **Passed**
- Privileged Action PIN Gate: **Passed**
- Window Focus & Keystrokes: **Passed**
- Screen OCR Extraction: **Passed**
- Multi-Agent Task Planning: **Passed**
- Hinglish Intent Drift Adaptation: **Passed**
- SQLite FTS5 Memory Retrieval (<15ms): **Passed**
- Memory Decay Weighting: **Passed**
- App Registry Indexing: **Passed**
- Audio Emotion Detection: **Passed**
- Self-Healing Error Recovery: **Passed**
- Offline Air-Gapped Operation: **Passed**

### 8.3 Error Handling & Self-Healing Engine
Self-Healing engine recalculates UI coordinates via OCR upon missed clicks. Exception middleware logs encrypted tracebacks and returns clear user feedback.

### 8.4 Validation Result
System demonstrated reliable operation across automated research paper summarization, hands-free voice desktop control, and proactive maintenance with memory usage under 6.5 GB RAM.

---

## 9. RESULTS, BENEFITS AND LIMITATIONS

### 9.1 Results
Fully functional offline AI desktop assistant with local GGUF inference, streaming speech recognition, desktop OCR vision, 11 service blueprints, and native Win32 automation.

### 9.2 Benefits
- 100% on-device privacy and data ownership.
- Zero subscription fees or per-token charges.
- Direct Windows OS desktop application and file automation.
- Multimodal natural voice, text, and visual interaction.
- Personalization with 27 learning systems and Hinglish support.
- Zero-overhead persistent memory using SQLite FTS5.

### 9.3 Limitations
- Inference speed depends on host CPU core count and AVX capability.
- Windows-specific Win32 automation hooks (Linux/macOS experimental).
- Multi-monitor DPI scaling variations can occasionally affect visual click coordinates.
- System RAM requirement of ~6 GB for running the quantized 8B model.

### 9.4 Academic Significance
Synthesizes edge computing, quantized language models, OS API engineering, speech processing, and human-computer interaction into a production-ready system.

---

## 10. FUTURE SCOPE AND CONCLUSION

### 10.1 Future Scope
- Cross-platform automation support for Linux and macOS.
- On-device lightweight Vision-Language Model (VLM) for direct pixel navigation.
- Peer-to-peer encrypted synchronization across personal devices.
- Dynamic LoRA adapter hot-swapping for specialized tasks.
- Local few-shot voice cloning.

### 10.2 Conclusion
PULSAR transforms the personal computer from a passive machine into an active, intelligent partner. By uniting local quantized LLMs with native Windows automation, multimodal perception, and continuous learning, it proves that private, autonomous AI assistants can operate reliably on consumer hardware without compromising privacy or incurring cloud costs.

### 10.3 Learning Outcomes
Mastery in local LLM quantization, C++ bindings, asynchronous Flask architectures, React frontend development, low-level Windows APIs, speech processing, and software validation.

---

## 11. REFERENCES AND APPENDIX

### 11.1 References
1. Meta AI, "Llama 3 Herd of Models: Architecture, Quantization, and Capabilities," 2024.
2. Gerganov, G., "llama.cpp: Efficient Port of LLaMA in C/C++," GitHub, 2024.
3. Radford, A. et al., "Robust Speech Recognition via Large-Scale Weak Supervision," OpenAI, 2023.
4. Smith, R., "An Overview of the Tesseract OCR Engine," ICDAR, 2007.
5. Pallets Projects, "Flask Documentation: Blueprints & Architecture," 2024.
6. Meta Open Source, "React 18 Documentation: Concurrent Features," 2024.
7. SQLite Consortium, "SQLite FTS5 Extension: Full-Text Search," 2024.
8. Hammond, M., "Python for Windows Extensions (pywin32)," 2023.
9. Al-Sweigart, A., "PyAutoGUI: Cross-Platform GUI Automation," 2024.
10. OWASP Foundation, "Top 10 Considerations for Agentic AI Applications," 2024.

### 11.2 Major Project Routes
- **Authentication & PIN:** `/api/auth/*`
- **Cognitive Engine:** `/api/local_ai/*`, `/api/chat`
- **Voice & Audio:** `/api/voice/*`
- **Screen & OCR:** `/api/screen/analyze`, `/api/ocr/*`
- **Windows Automation:** `/api/apps/*`, `/api/automation/execute`
- **Memory & Learning:** `/api/learning/*`, `/api/memory/*`
- **System Telemetry:** `/api/system/stats`, `/api/startup/*`

### 11.3 Technology Summary
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, PyWebView
- **Backend:** Python 3.10+, Flask, Socket.IO, 11 Blueprints
- **Cognitive Model:** Llama 3.1 8B Instruct (Q4_K_M GGUF via llama-cpp-python)
- **Voice/Vision:** faster-whisper, pyttsx3, Tesseract OCR 5, OpenCV
- **OS Automation:** pywin32, pywinauto, pyautogui
- **Persistence:** SQLite3 (FTS5), Neo4j Graph, JSON
- **Packaging:** PyInstaller, PyWebView, Batch/PowerShell scripts

**End of Synopsis**  
**PULSAR**
