# Files to Commit

This commit is the result of the backend refactoring, combined with some uncommitted changes that were already sitting in the working directory.

## What Work Was Done:

### 1. The Main Refactoring (The bulk of the commit)
- **Shrinking the Monolith:** `backend/modern_web_backend.py` was reduced from over 5,300 lines to about 1,000 lines. Over 4,300 lines of routes and socket handlers were removed and cleanly modularized.
- **New Route Blueprints:** 11 new modules were created in `backend/routes/` (such as `chat_routes.py`, `settings_routes.py`, `learning_routes.py`, etc.) and all endpoint logic was cleanly moved into them.
- **WebSockets:** All 15 `socketio.on` handlers were decoupled and moved into a new `backend/websockets.py` file.

### 2. Pre-existing Working Directory Changes
The commit also swept up several other files that already had minor tweaks sitting uncommitted in the local branch prior to the refactoring:
- **Frontend Tweaks:** Minor changes in `frontend/web-app/src/App.tsx`, `OnboardingModal.tsx`, and `vite.config.ts`.
- **Configuration & CI:** Minor updates in `.github/workflows/ci.yml`, `pytest.ini`, `.env.example`, `requirements.txt`, and `mcp_servers.json`.
- **Test Files & Scripts:** Minor modifications to some validation scripts (`test_online_only.py`, `test_all_27_systems.py`) and launcher scripts (`start_learning_api.py`).

---

## Changed Files:

- .github/workflows/ci.yml
- backend/backend/blueprints/system.py
- backend/backend/blueprints/voice.py
- backend/google_speech_websocket_handler.py
- backend/learning_api.py
- backend/learning_dashboard_api.py
- backend/modern_web_backend.py
- backend/routes/auth_routes.py
- backend/routes/chain_routes.py
- backend/routes/chat_routes.py
- backend/routes/file_routes.py
- backend/routes/learning_routes.py
- backend/routes/local_ai_routes.py
- backend/routes/settings_routes.py
- backend/routes/system_routes.py
- backend/routes/taskbar_routes.py
- backend/routes/voice_routes.py
- backend/routes/web_routes.py
- backend/websockets.py
- config/.env.example
- config/backend.env.example
- config/mcp_servers.json
- config/requirements/requirements-ci.txt
- config/requirements/requirements.txt
- deploy/Procfile
- frontend/web-app/src/App.tsx
- frontend/web-app/src/components/OnboardingModal.tsx
- frontend/web-app/vite.config.ts
- pytest.ini
- scripts/launchers/start_learning_api.py
- scripts/utilities/quickstart_api.py
- scripts/validation/test_online_only.py
- scripts/validation/test_online_only_simple.py
- shared/config/mcp_servers.json
- start.bat
- tests/conftest.py
- tests/system/test_all_27_systems.py
- committed_files.md
