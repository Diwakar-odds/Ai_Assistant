"""
Integration tests for Backend Multi-Agent, Chain Orchestration, and System Details REST APIs.
Tests Flask endpoints with test client:
- /api/agents
- /api/agents/<agent_id>
- /api/agents/capabilities
- /api/agents/<agent_id>/load
- /api/agents/<agent_id>/execute
- /api/agents/dispatch
- /api/chains/active
- /api/chains/history
- /api/chains/create
- /api/system/details
- /api/status
"""

import json
import os
from pathlib import Path
import sys
import unittest

# Ensure imports resolve cleanly
REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "core_ai" / "src"
BACKEND_DIR = REPO_ROOT / "backend"
for p in (str(REPO_ROOT), str(CORE_SRC), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask
from backend.routes import register_all_routes


class TestBackendAgentsChainsApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config["TESTING"] = True
        cls.app.config["SECRET_KEY"] = "test-secret-key-123"
        cls.app.config["JWT_SECRET_KEY"] = "test-jwt-secret-456"
        cls.app.config["JWT_TOKEN_LOCATION"] = ["headers"]
        try:
            from flask_jwt_extended import JWTManager
            JWTManager(cls.app)
        except Exception:
            pass

        # Register all blueprints
        register_all_routes(cls.app)
        cls.client = cls.app.test_client()

    def test_01_api_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("services", data)

    def test_02_system_details(self):
        resp = self.client.get("/api/system/details")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        details = data.get("details", {})
        self.assertIn("os", details)
        self.assertIn("cpu_count", details)
        self.assertIn("memory_total_gb", details)

    def test_03_list_agents(self):
        resp = self.client.get("/api/agents")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        agents = data.get("agents", [])
        self.assertEqual(len(agents), 14)
        agent_ids = [a["id"] for a in agents]
        self.assertIn("productivity-001", agent_ids)
        self.assertIn("research-001", agent_ids)
        self.assertIn("writer-001", agent_ids)
        self.assertIn("data-001", agent_ids)
        self.assertIn("database-001", agent_ids)

    def test_04_get_single_agent_and_alias(self):
        # Direct canonical ID
        resp = self.client.get("/api/agents/data-001")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["agent"]["id"], "data-001")

        # Via alias "data"
        resp_alias = self.client.get("/api/agents/data")
        self.assertEqual(resp_alias.status_code, 200)
        data_alias = resp_alias.get_json()
        self.assertEqual(data_alias["agent"]["id"], "data-001")

    def test_05_agent_capabilities(self):
        resp = self.client.get("/api/agents/capabilities")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        caps = data.get("capabilities", {})
        self.assertIn("create_pdf", caps)
        self.assertIn("query_database", caps)
        self.assertIn("analyze_data", caps)

    def test_06_load_agent(self):
        resp = self.client.post("/api/agents/data-001/load")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["agent"]["status"], "idle")

    def test_07_execute_agent_task(self):
        payload = {
            "task": "Quick stats inspection",
            "params": {"data": [10, 20, 30, 40, 50]},
        }
        resp = self.client.post(
            "/api/agents/data-001/execute",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("result", data)
        self.assertTrue(data["result"].get("success"))

    def test_08_chains_active_and_history(self):
        resp_active = self.client.get("/api/chains/active")
        self.assertEqual(resp_active.status_code, 200)
        data_active = resp_active.get_json()
        self.assertTrue(data_active.get("success"))
        self.assertIsInstance(data_active.get("chains"), list)

        resp_hist = self.client.get("/api/chains/history")
        self.assertEqual(resp_hist.status_code, 200)
        data_hist = resp_hist.get_json()
        self.assertTrue(data_hist.get("success"))
        self.assertIsInstance(data_hist.get("history"), list)

    def test_09_create_chain(self):
        payload = {
            "command": "open notepad && type hello world",
            "auto_execute": False,  # Plan only without executing OS actions during unit tests
        }
        resp = self.client.post(
            "/api/chains/create",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        chain = data.get("chain", {})
        self.assertTrue(chain.get("chain_id"))
        self.assertEqual(chain.get("command"), "open notepad && type hello world")
        self.assertIsInstance(chain.get("actions"), list)


if __name__ == "__main__":
    unittest.main()
