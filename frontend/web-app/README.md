# 🎨 PULSAR Frontend Web & Desktop App

## 📌 Overview
The **Pulsar Frontend** is a modern, responsive web application and native desktop shell (via Tauri) built using React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, and Three.js. It interfaces directly with the Python backend via REST APIs, Server-Sent Events (SSE) for streaming chat generation, and Socket.IO for real-time multi-agent telemetry.

* **Working Directory:** [`frontend/web-app/`](file:///d:/Projects/Ai_Assistant/frontend/web-app/)
* **Dev Server URL:** `http://localhost:5173`
* **Backend Proxy Target:** `http://localhost:5000`

---

## 🏗️ Directory Layout

```text
frontend/web-app/
├── index.html                  # HTML entrypoint
├── package.json                # Dependencies and npm scripts
├── vite.config.ts              # Vite configuration & backend proxy
├── tailwind.config.js          # Tailwind styling configuration
├── tsconfig.json               # TypeScript compiler options
├── src/                        # React source code
│   ├── components/             # Reusable UI components
│   │   ├── agents/             # Multi-Agent status matrix & task logs
│   │   ├── chat/               # Streaming chat interface with SSE
│   │   ├── audio/              # Real-time visualizer & microphone input
│   │   ├── vision/             # Screen capture & OCR visualizer
│   │   └── automation/         # Workflow and live taskbar status monitors
│   ├── hooks/                  # Custom React hooks (useWebSocket, useAuth, useAudio)
│   ├── context/                # Global state (Auth, Theme, AgentContext)
│   ├── services/               # API clients (axios / fetch with JWT interceptors)
│   └── App.tsx                 # Main application view & router
└── public/                     # Static assets, manifests, icons
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
* Node.js 18.x or 20.x
* npm (bundled with Node.js)

### 2. Install Dependencies
```bash
cd frontend/web-app
npm install
```

### 3. Start Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:5173`. Any changes in `src/` automatically hot-reload via Vite HMR.

---

## 🛠️ Available Scripts

| Command | Description |
| :--- | :--- |
| `npm run dev` | Launches local Vite development server on port 5173. |
| `npm run build` | Compiles optimized production bundle into `dist/`. |
| `npm run preview` | Serves the production build locally for verification. |
| `npm run typecheck`| Runs TypeScript compiler (`tsc --noEmit`) to verify types. |
| `npm run test` | Runs unit tests using Vitest in single-run mode. |
| `npm run test:watch` | Runs unit tests in interactive watch mode. |
| `npm run tauri:dev`| Launches the native Windows desktop wrapper with live UI. |
| `npm run tauri:build`| Packages production Windows executable (`.exe` / `.msi`). |

---

## 🔌 Real-Time Telemetry & WebSocket Events

The frontend subscribes to real-time agent lifecycle and system metrics:
* `agent.started`: Agent assigned to task (triggers status pulse in UI).
* `agent.progress`: Step percentage and intermediate outputs.
* `agent.completed`: Task finished; delivers artifact links (PDF, charts, audio).
* `system.telemetry`: Live CPU, RAM, and GPU temperature metrics.

---

## 📚 Related Documentation
* [14 Multi-Agent Cores Specification](file:///d:/Projects/Ai_Assistant/docs/agents/)
* [Subsystem Capabilities & Architecture](file:///d:/Projects/Ai_Assistant/docs/capabilities/)
* [API Reference](file:///d:/Projects/Ai_Assistant/docs/api/)
