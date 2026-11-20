# 🎨 PULSAR Frontend Web & Desktop App

## 📌 Overview
The **Pulsar Frontend** is a modern, responsive web application and native desktop shell (via Tauri & PySide6) built using React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, and Three.js. It interfaces directly with the Python backend via REST APIs, Server-Sent Events (SSE) for streaming chat generation, and Socket.IO for real-time multi-agent telemetry.

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
│   │   ├── CenterColumn/       # Central interactive chat view & VoiceButton
│   │   ├── DetailViews/        # Deep-dive views (Chat, Voice, Settings, Agents)
│   │   ├── LeftColumn/         # Sidebar navigation & active session list
│   │   ├── RightColumn/        # Conversation tracker, telemetry & system monitors
│   │   └── Modals/             # PIN login, OnboardingModal, & Confirmation prompts
│   ├── contexts/               # React Context Providers
│   │   └── DashboardContext.tsx# Central global state (voice, orb, settings, agents)
│   ├── hooks/                  # Custom React hooks (useSpatialGestures, useAudio)
│   ├── services/               # API clients (axios / fetch with JWT interceptors)
│   └── App.tsx                 # Master layout & responsive column split
└── public/                     # Static assets, manifests, icons
```

---

## 🌟 Key Visual & UI Features

### 1. Three.js 4D Particle Orb State Sync
* Embedded WebGL canvas that renders a fluid 4D particle mesh.
* Dynamically shifts color and particle vibration between `idle`, `listening`, `thinking`, `speaking`, and `error` in response to backend Socket.IO events.

### 2. Multi-Session Conversation Manager
* Create, rename, delete, and switch between multiple conversational threads.
* Auto-persisted via `backend/utils/chat_session_store.py` with full markdown rendering and copy-to-clipboard code blocks.

### 3. Real-Time Telemetry & Agent Matrix
* Live CPU, RAM, GPU temperature, and disk usage gauges.
* Dynamic agent status cards showing which of the 14 multi-agent cores is currently active, pending, or idle.

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

## 📚 Related Documentation
* [Subsystem Capabilities & Architecture](file:///d:/Projects/Ai_Assistant/docs/capabilities/)
* [Pulsar Standalone 3-Tier Architecture](file:///d:/Projects/Ai_Assistant/docs/architecture/PULSAR_STANDALONE_ARCHITECTURE.md)
* [Backend Services Guide](file:///d:/Projects/Ai_Assistant/backend/README.md)
