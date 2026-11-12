import unittest
import asyncio
import sys
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for p in (
    PROJECT_ROOT,
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "core_ai" / "src",
    PROJECT_ROOT / "shared",
):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from ai_assistant.core.swarm_planner import (
    SwarmPlanner,
    WorkflowStep,
    WorkflowWave,
    WorkflowPlan,
    AGENT_CAPABILITY_CONTRACTS,
)
from ai_assistant.core.workflow_memory import WorkflowMemory
from ai_assistant.agents.registry import AgentRegistry
from ai_assistant.agents.loader import AgentLoader
from ai_assistant.agents.base_agent import BaseAgent
from ai_assistant.agents.models import Task, TaskResult
from ai_assistant.core.multi_agent_coordinator import MultiAgentCoordinator


class TestSwarmPlannerAndMemory(unittest.TestCase):
    """
    Comprehensive verification suite for:
    1. SwarmPlanner Capability Manifest & Model Validation
    2. Kahn's Topological Sort & Cycle Detection
    3. Self-Healing Dynamic Re-Planning Engine
    4. WorkflowMemory Cache & 'Never Think Twice' Macro Recall
    5. MultiAgentCoordinator End-to-End Self-Healing DAG Execution
    """

    def setUp(self):
        self.registry = AgentRegistry()
        AgentLoader.register_agent_definitions(self.registry)
        self.test_db_path = str(PROJECT_ROOT / "data" / "core" / "test_workflow_memory.db")
        self.memory = WorkflowMemory(db_path=self.test_db_path)
        self.memory.clear_memory()

    def tearDown(self):
        try:
            self.memory.clear_memory()
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except Exception:
            pass

    def test_agent_manifest_completeness(self):
        """Verify all 14 canonical agents have complete capability contracts."""
        self.assertEqual(len(AGENT_CAPABILITY_CONTRACTS), 14)
        for aid, contract in AGENT_CAPABILITY_CONTRACTS.items():
            self.assertTrue(len(contract["capabilities"]) > 0)
            self.assertTrue(len(contract["inputs"]) > 0)
            self.assertTrue(len(contract["outputs"]) > 0)
            self.assertIn("sensitive", contract)

        planner = SwarmPlanner(registry=self.registry)
        manifest_text = planner.build_agent_manifest_text()
        self.assertIn("productivity-001", manifest_text)
        self.assertIn("deep-research-001", manifest_text)
        self.assertIn("data-001", manifest_text)
        self.assertIn("autonomous-001", manifest_text)

    def test_topological_sort_and_cycle_detection(self):
        """Kahn's algorithm must order dependent steps into parallel waves and detect cycles."""
        planner = SwarmPlanner(registry=self.registry)

        # 1. Valid DAG: step_1 & step_2 (parallel Wave 1) -> step_3 (Wave 2)
        steps = [
            WorkflowStep(step_id="step_1", agent_id="research-001", capability="research_topic", task="Search topic"),
            WorkflowStep(step_id="step_2", agent_id="data-001", capability="analyze_data", task="Load data"),
            WorkflowStep(step_id="step_3", agent_id="productivity-001", capability="create_powerpoint", task="Create PPT", depends_on=["step_1", "step_2"]),
        ]
        waves = planner._build_waves_from_steps(steps)
        self.assertIsNotNone(waves)
        self.assertEqual(len(waves), 2)
        self.assertEqual(len(waves[0].steps), 2)  # Wave 1 has step_1 & step_2
        self.assertEqual(waves[1].steps[0].step_id, "step_3")  # Wave 2 has step_3

        # 2. Cyclic DAG: step_A -> step_B -> step_A (must be detected and return None)
        cyclic_steps = [
            WorkflowStep(step_id="step_a", agent_id="research-001", capability="research_topic", task="A", depends_on=["step_b"]),
            WorkflowStep(step_id="step_b", agent_id="writer-001", capability="write_article", task="B", depends_on=["step_a"]),
        ]
        cyclic_waves = planner._build_waves_from_steps(cyclic_steps)
        self.assertIsNone(cyclic_waves)

    def test_deterministic_fallback_planner(self):
        """Fallback planner must construct a valid WorkflowPlan when offline."""
        planner = SwarmPlanner(registry=self.registry)
        query = "analyze sales csv and then create presentation on results"
        plan = asyncio.run(planner._fallback_plan(query))

        self.assertIsInstance(plan, WorkflowPlan)
        self.assertTrue(len(plan.all_steps) >= 2)
        self.assertIn("data-001", [s.agent_id for s in plan.all_steps])
        self.assertIn("productivity-001", [s.agent_id for s in plan.all_steps])
        self.assertEqual(len(plan.waves), 2)  # Sequential waves

    def test_self_healing_replan_fallback(self):
        """When an agent fails, SwarmPlanner provides a replacement agent."""
        planner = SwarmPlanner(registry=self.registry)

        # 1. Designated fallback
        failed_step = WorkflowStep(
            step_id="step_1",
            agent_id="web-001",
            capability="scrape_dynamic",
            task="Scrape target site",
            fallback_agent_id="research-001"
        )
        replacement = asyncio.run(
            planner.replan_failed_step(
                failed_step=failed_step,
                error_message="Cloudflare 403 Forbidden",
                user_goal="Scrape website for news",
                completed_results={},
                remaining_steps=[]
            )
        )
        self.assertIsNotNone(replacement)
        self.assertEqual(replacement.agent_id, "research-001")

        # 2. Dynamic LLM Re-plan parsing path
        mock_llm_json = '{"replacement_step": {"step_id": "step_2", "agent_id": "deep-research-001", "capability": "deep_research", "task": "Alternative deep research"}}'
        with patch.object(planner, "_call_llm", return_value=mock_llm_json):
            failed_step_2 = WorkflowStep(
                step_id="step_2",
                agent_id="web-001",
                capability="scrape_dynamic",
                task="Scrape target site",
            )
            replacement_2 = asyncio.run(
                planner.replan_failed_step(
                    failed_step=failed_step_2,
                    error_message="Timeout loading page",
                    user_goal="Get website content",
                    completed_results={},
                    remaining_steps=[]
                )
            )
            self.assertIsNotNone(replacement_2)
            self.assertEqual(replacement_2.agent_id, "deep-research-001")

        # 3. Deterministic alternative fallback when LLM is unavailable
        with patch.object(planner, "_call_llm", return_value=None):
            failed_step_3 = WorkflowStep(
                step_id="step_3",
                agent_id="web-001",
                capability="scrape_dynamic",
                task="Scrape target site",
            )
            replacement_3 = asyncio.run(
                planner.replan_failed_step(
                    failed_step=failed_step_3,
                    error_message="Timeout loading page",
                    user_goal="Get website content",
                    completed_results={},
                    remaining_steps=[]
                )
            )
            self.assertIsNotNone(replacement_3)
            self.assertEqual(replacement_3.agent_id, "research-001")

    def test_workflow_memory_caching_and_recall(self):
        """WorkflowMemory must cache successful DAGs and recall them in ~0ms."""
        query = "analyze D:\\Data\\sales.csv and create a presentation"
        steps = [
            WorkflowStep(step_id="step_1", agent_id="data-001", capability="analyze_data", task="Analyze CSV"),
            WorkflowStep(step_id="step_2", agent_id="productivity-001", capability="create_powerpoint", task="Create PPT", depends_on=["step_1"]),
        ]
        plan = WorkflowPlan(
            workflow_id="wf-test-123",
            workflow_name="Sales_Data_To_PPT",
            user_goal=query,
            reasoning="Test breakdown",
            waves=[WorkflowWave(wave_number=1, steps=[steps[0]]), WorkflowWave(wave_number=2, steps=[steps[1]])],
            all_steps=steps,
        )

        # 1. Record success
        self.memory.record_success(query, plan)

        # 2. Exact match check
        cached = self.memory.find_matching_workflow(query)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.workflow_name, "Sales_Data_To_PPT")
        self.assertEqual(len(cached.all_steps), 2)

        # 3. Fuzzy match check with different filename
        similar_query = "analyze D:\\Reports\\q3_sales.csv and create a presentation"
        fuzzy_cached = self.memory.find_matching_workflow(similar_query)
        self.assertIsNotNone(fuzzy_cached)
        self.assertEqual(fuzzy_cached.workflow_name, "Sales_Data_To_PPT")

    def test_multi_agent_coordinator_self_healing_execution(self):
        """MultiAgentCoordinator must auto-heal when a primary agent fails and complete the DAG."""
        coordinator = MultiAgentCoordinator(self.registry)

        # Mock agent behaviors: agent_fail fails, agent_backup succeeds
        class FailingAgent(BaseAgent):
            def __init__(self):
                super().__init__("failing-agent-001", {})
                self.name = "Failing Agent"
            async def can_handle(self, task: Task) -> bool:
                return True
            async def execute(self, task: Task) -> TaskResult:
                return TaskResult(success=False, error="Simulated agent failure", agent_id="failing-agent-001")

        class BackupAgent(BaseAgent):
            def __init__(self):
                super().__init__("backup-agent-001", {})
                self.name = "Backup Agent"
            async def can_handle(self, task: Task) -> bool:
                return True
            async def execute(self, task: Task) -> TaskResult:
                return TaskResult(success=True, data={"output": "Recovered by backup"}, agent_id="backup-agent-001")

        self.registry.register_agent(FailingAgent())
        self.registry.register_agent(BackupAgent())

        # DAG: step_1 has failing agent with fallback_agent_id="backup-agent-001"
        steps = [
            {
                "step_id": "step_1",
                "agent_id": "failing-agent-001",
                "task": "Test task with auto-recovery",
                "depends_on": [],
                "fallback_agent_id": "backup-agent-001",
                "params": {},
            }
        ]

        outcome = asyncio.run(coordinator.execute_dag(steps))
        self.assertEqual(outcome["status"], "completed")
        self.assertTrue(outcome["steps"][0]["success"])
        self.assertEqual(outcome["steps"][0]["agent_id"], "backup-agent-001")


if __name__ == "__main__":
    unittest.main()
