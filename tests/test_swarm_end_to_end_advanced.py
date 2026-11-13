"""
Advanced End-to-End Test Suite for Multi-Agent Swarm Orchestration:
1. Human-in-the-Loop Checkpoint Gate Approval & Execution
2. Checkpoint Gate Rejection & Safe Cancellation
3. Creator-Critic Adversarial Peer Review & Revision Loop
4. Workflow Memory Generalized Parameterization & Instant Recall
5. REST API Verification (/api/agents/workflows, /api/agents/checkpoints, etc.)
"""

import asyncio
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_SRC = REPO_ROOT / "core_ai" / "src"
BACKEND_DIR = REPO_ROOT / "backend"
for p in (str(REPO_ROOT), str(CORE_SRC), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ai_assistant.agents.base_agent import BaseAgent
from ai_assistant.agents.models import AgentStatus, Task, TaskResult
from ai_assistant.agents.registry import AgentRegistry
from ai_assistant.core.multi_agent_coordinator import MultiAgentCoordinator
from ai_assistant.core.swarm_planner import (
    AGENT_CAPABILITY_CONTRACTS,
    SwarmPlanner,
    WorkflowPlan,
    WorkflowStep,
    WorkflowWave,
)
from ai_assistant.core.workflow_memory import WorkflowMemory
from flask import Flask
from backend.routes import register_all_routes


class MockWorkerAgent(BaseAgent):
    """Configurable mock agent for testing swarm capabilities."""

    def __init__(self, agent_id: str, name: str, capabilities=None, sensitive: bool = False):
        super().__init__(agent_id=agent_id)
        self.name = name
        self.capabilities = capabilities or ["execute"]
        self.sensitive = sensitive
        self.execution_count = 0
        self.last_task: Task = None

    async def can_handle(self, task: Task) -> bool:
        return True

    async def execute(self, task: Task) -> TaskResult:
        self.execution_count += 1
        self.last_task = task
        # Provide rich output for critic and memory tests
        output_text = f"Successfully executed {task.description} by {self.agent_id}."
        if "[REVISION CRITIQUE]" in (task.description or ""):
            output_text += " This is the revised, improved, high-quality edition with comprehensive benchmarks."

        return TaskResult(
            success=True,
            agent_id=self.agent_id,
            agent_name=self.name,
            data={
                "output": output_text,
                "text": output_text,
                "summary": f"Summary of {self.name}",
            },
        )


class TestSwarmEndToEndAdvanced(unittest.TestCase):
    def setUp(self):
        self.test_db_path = str(REPO_ROOT / "data" / "core" / "test_e2e_advanced_memory.db")
        self.memory = WorkflowMemory(db_path=self.test_db_path)
        self.memory.clear_memory()

        self.registry = AgentRegistry()
        self.worker1 = MockWorkerAgent(agent_id="research-001", name="Research Agent", capabilities=["research_topic"])
        self.worker2 = MockWorkerAgent(agent_id="comm-001", name="Comm Agent", capabilities=["send_email"], sensitive=True)
        self.worker3 = MockWorkerAgent(agent_id="writer-001", name="Writer Agent", capabilities=["write_article"])

        self.registry.register_agent(self.worker1)
        self.registry.register_agent(self.worker2)
        self.registry.register_agent(self.worker3)

        self.coordinator = MultiAgentCoordinator(registry=self.registry, memory=self.memory)

        # Flask Test Client
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-swarm-e2e"
        self.app.config["JWT_SECRET_KEY"] = "test-jwt-secret-swarm-e2e"
        self.app.config["JWT_TOKEN_LOCATION"] = ["headers"]
        try:
            from flask_jwt_extended import JWTManager
            JWTManager(self.app)
        except Exception:
            pass
        register_all_routes(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            self.memory.clear_memory()
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except Exception:
            pass

    def test_01_checkpoint_gate_approval(self):
        """Verify Human-in-the-Loop Checkpoint Gate pauses, awaits user approval, and resumes."""
        async def _run():
            steps = [
                {
                    "step_id": "step_1",
                    "agent_id": "research-001",
                    "task": "Find market metrics",
                    "depends_on": [],
                },
                {
                    "step_id": "step_2",
                    "agent_id": "comm-001",
                    "task": "Email metrics to CEO",
                    "depends_on": ["step_1"],
                    "requires_confirmation": True,
                },
            ]

            # Start execution in background task
            dag_task = asyncio.create_task(self.coordinator.execute_dag(steps))

            # Poll for the checkpoint to be registered
            checkpoint = None
            for _ in range(50):
                await asyncio.sleep(0.05)
                pending = self.coordinator.get_pending_checkpoints()
                if pending:
                    checkpoint = pending[0]
                    break

            self.assertIsNotNone(checkpoint, "Checkpoint gate should be generated for sensitive step")
            self.assertEqual(checkpoint["agent_id"], "comm-001")
            self.assertEqual(checkpoint["step_id"], "step_2")
            self.assertEqual(checkpoint["status"], "pending")

            # User approves checkpoint gate
            approved = self.coordinator.respond_checkpoint(checkpoint["checkpoint_id"], confirmed=True)
            self.assertTrue(approved, "Checkpoint response should succeed")

            # DAG should now complete
            result = await dag_task
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["steps"]), 2)
            self.assertTrue(result["results"]["step_2"]["success"])
            self.assertEqual(self.worker2.execution_count, 1)

        asyncio.run(_run())

    def test_02_checkpoint_gate_rejection(self):
        """Verify Human-in-the-Loop Checkpoint Gate aborts sensitive action when rejected by user."""
        async def _run():
            steps = [
                {
                    "step_id": "step_sensitive",
                    "agent_id": "comm-001",
                    "task": "Send unsolicited bulk communication",
                    "depends_on": [],
                    "requires_confirmation": True,
                }
            ]

            dag_task = asyncio.create_task(self.coordinator.execute_dag(steps))

            # Poll for the checkpoint to be registered
            checkpoint = None
            for _ in range(50):
                await asyncio.sleep(0.05)
                pending = self.coordinator.get_pending_checkpoints()
                if pending:
                    checkpoint = pending[0]
                    break

            self.assertIsNotNone(checkpoint)

            # User rejects checkpoint gate
            approved = self.coordinator.respond_checkpoint(checkpoint["checkpoint_id"], confirmed=False)
            self.assertTrue(approved)

            result = await dag_task
            # The rejected step must be marked failed/cancelled without throwing unhandled exceptions
            step_res = result["results"]["step_sensitive"]
            self.assertFalse(step_res["success"])
            self.assertIn("cancelled by user at confirmation checkpoint gate", step_res["error"].lower())
            self.assertEqual(self.worker2.execution_count, 0, "Worker must NOT execute when checkpoint is rejected")

        asyncio.run(_run())

    def test_03_creator_critic_peer_review_and_revision(self):
        """Verify Creator-Critic Peer Review loop triggers revision when score is low."""
        async def _run():
            # Step 1: Request with verify_quality=True
            steps = [
                {
                    "step_id": "step_write",
                    "agent_id": "writer-001",
                    "task": "Draft in-depth essay",
                    "depends_on": [],
                    "verify_quality": True,
                }
            ]

            planner = SwarmPlanner(registry=self.registry)
            call_count = {"critique": 0}

            async def mock_critique(creator_agent_id, task, output_text):
                call_count["critique"] += 1
                # First round rejects with low score; revised round passes
                if call_count["critique"] == 1:
                    return {
                        "critic_agent_id": "critic-001",
                        "score": 6.0,
                        "approved": False,
                        "critique": "Lacks sufficient depth and quantitative benchmarks.",
                        "revision_prompt": "Please add concrete metrics and benchmarks.",
                    }
                else:
                    return {
                        "critic_agent_id": "critic-001",
                        "score": 9.2,
                        "approved": True,
                        "critique": "Excellent depth and comprehensive benchmarks included.",
                        "revision_prompt": None,
                    }

            with patch.object(SwarmPlanner, "critique_output", side_effect=mock_critique):
                result = await self.coordinator.execute_dag(steps)
                self.assertEqual(result["status"], "completed")

                step_res = result["results"]["step_write"]
                self.assertTrue(step_res["success"])
                # Verify that revision occurred: execution count should be 2 (initial + revision)
                self.assertEqual(self.worker3.execution_count, 2)
                self.assertIn("REVISION CRITIQUE", self.worker3.last_task.description)
                self.assertIn("critic_review", step_res["data"])
                self.assertTrue(step_res["data"].get("revised"))

        asyncio.run(_run())

    def test_04_creator_critic_immediate_approval(self):
        """Verify Creator-Critic directly approves when score is >= 7.5."""
        async def _run():
            steps = [
                {
                    "step_id": "step_write",
                    "agent_id": "writer-001",
                    "task": "Draft short headline",
                    "depends_on": [],
                    "verify_quality": True,
                }
            ]

            async def mock_high_critique(creator_agent_id, task, output_text):
                return {
                    "critic_agent_id": "critic-001",
                    "score": 8.8,
                    "approved": True,
                    "critique": "Sharp and concise.",
                    "revision_prompt": None,
                }

            with patch.object(SwarmPlanner, "critique_output", side_effect=mock_high_critique):
                result = await self.coordinator.execute_dag(steps)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(self.worker3.execution_count, 1)

        asyncio.run(_run())

    def test_05_workflow_memory_zero_token_recall(self):
        """Verify entity parameterization and fuzzy/exact recall bypassing LLM."""
        pattern = "Download dataset from http://example.com/data.csv and summarize findings"
        steps = [
            WorkflowStep(step_id="step_1", agent_id="research-001", capability="research_topic", task="Download http://example.com/data.csv"),
            WorkflowStep(step_id="step_2", agent_id="writer-001", capability="write_article", task="Summarize findings", depends_on=["step_1"]),
        ]
        plan = WorkflowPlan(
            workflow_id="wf-test-url-recall",
            workflow_name="Download_And_Summarize",
            user_goal=pattern,
            reasoning="Test breakdown",
            waves=[WorkflowWave(wave_number=1, steps=[steps[0]]), WorkflowWave(wave_number=2, steps=[steps[1]])],
            all_steps=steps,
        )

        # 1. Record pattern
        self.memory.record_success(pattern, plan)

        # 2. Similar query with different URL
        query2 = "Download dataset from https://acme.org/quarterly.csv and summarize findings"
        cached_plan = self.memory.find_matching_workflow(query2)
        self.assertIsNotNone(cached_plan, "WorkflowMemory should match parameterized <URL> recipe")
        self.assertEqual(len(cached_plan.all_steps), 2)
        # Entity substitution should replace <URL> with the new URL
        self.assertIn("https://acme.org/quarterly.csv", cached_plan.all_steps[0].task)

        # Verify recipe listing
        recipes = self.memory.list_all_recipes()
        self.assertTrue(len(recipes) >= 1)
        self.assertEqual(recipes[0]["success_count"], 1)

    def test_06_rest_api_workflow_and_checkpoint_routes(self):
        """Verify Flask REST endpoints for workflow memory and checkpoint gates."""
        # Prepopulate one recipe in memory
        plan = WorkflowPlan(
            workflow_id="wf-test-sec",
            workflow_name="Security_Scan",
            user_goal="Analyze security vulnerabilities and report",
            reasoning="Security scan",
            waves=[WorkflowWave(wave_number=1, steps=[WorkflowStep(step_id="step_1", agent_id="research-001", capability="research_topic", task="Scan logs")])],
            all_steps=[WorkflowStep(step_id="step_1", agent_id="research-001", capability="research_topic", task="Scan logs")],
        )
        self.memory.record_success("Analyze security vulnerabilities and report", plan)

        # 1. GET /api/agents/workflows
        with patch("ai_assistant.core.workflow_memory.get_workflow_memory", return_value=self.memory):
            resp = self.client.get("/api/agents/workflows")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["success"])
            self.assertGreaterEqual(data["count"], 1)

            # 2. POST /api/agents/workflows/synthesize
            with patch.object(SwarmPlanner, "_call_llm", return_value=None):
                resp_synth = self.client.post(
                    "/api/agents/workflows/synthesize",
                    data=json.dumps({"goal": "Research climate change and prepare presentation"}),
                    content_type="application/json",
                )
                self.assertEqual(resp_synth.status_code, 200)
                synth_data = resp_synth.get_json()
                self.assertTrue(synth_data["success"])
                self.assertIn("workflow", synth_data)
                self.assertIn("waves", synth_data["workflow"])

            # 3. POST /api/agents/workflows/clear
            resp_clear = self.client.post("/api/agents/workflows/clear")
            self.assertEqual(resp_clear.status_code, 200)
            self.assertTrue(resp_clear.get_json()["success"])

            # Verify cleared
            self.assertEqual(len(self.memory.list_all_recipes()), 0)

        # 4. Checkpoint Gate APIs
        chk_id, chk_evt = self.coordinator.create_checkpoint(
            step_id="step_api_1",
            agent_id="comm-001",
            description="API test checkpoint",
            params={"mode": "test"},
        )

        with patch("backend.routes.agent_routes.get_agent_registry_and_coordinator", return_value=(self.registry, self.coordinator)):
            # GET /api/agents/checkpoints/pending
            resp_chk = self.client.get("/api/agents/checkpoints/pending")
            self.assertEqual(resp_chk.status_code, 200)
            chk_data = resp_chk.get_json()
            self.assertTrue(chk_data["success"])
            self.assertEqual(chk_data["count"], 1)
            self.assertEqual(chk_data["checkpoints"][0]["checkpoint_id"], chk_id)

            # POST /api/agents/checkpoint/respond (missing field error)
            resp_err = self.client.post(
                "/api/agents/checkpoint/respond",
                data=json.dumps({}),
                content_type="application/json",
            )
            self.assertEqual(resp_err.status_code, 400)

            # POST /api/agents/checkpoint/respond (valid confirm)
            resp_resp = self.client.post(
                "/api/agents/checkpoint/respond",
                data=json.dumps({"checkpoint_id": chk_id, "confirmed": True}),
                content_type="application/json",
            )
            self.assertEqual(resp_resp.status_code, 200)
            resp_data = resp_resp.get_json()
            self.assertTrue(resp_data["success"])
            self.assertEqual(resp_data["status"], "confirmed")
            self.assertTrue(chk_evt.is_set())


if __name__ == "__main__":
    unittest.main()
