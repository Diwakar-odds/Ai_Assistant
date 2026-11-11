import asyncio
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
import wave

# Ensure repo imports resolve cleanly when run via `python -m unittest` or pytest
REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "core_ai" / "src"
BACKEND_DIR = REPO_ROOT / "backend"
for p in (str(REPO_ROOT), str(CORE_SRC), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ai_assistant.agents.base_agent import BaseAgent
from ai_assistant.agents.loader import AgentLoader, get_global_registry
from ai_assistant.agents.models import AgentStatus, Task, TaskResult
from ai_assistant.agents.registry import AgentRegistry
from ai_assistant.core.multi_agent_coordinator import (
    MultiAgentCoordinator,
    get_multi_agent_coordinator,
    reset_multi_agent_coordinator,
)


class _MockLLM:
    """Deterministic test double supporting UnifiedChatInterface-style .chat()."""

    def __init__(self, canned: str = "Mock LLM generated response."):
        self.canned = canned
        self.calls = []
        self.system_message = None

    def set_system_message(self, msg: str) -> None:
        self.system_message = msg

    def chat(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        return self.canned


class _SlowAgent(BaseAgent):
    """Test helper agent to verify parallelism, per-agent locking, cancellation & errors."""

    def __init__(self, agent_id: str, delay: float = 0.15, fail: bool = False):
        super().__init__(agent_id, {})
        self.name = f"Slow-{agent_id}"
        self.category = "test"
        self.capabilities = [f"cap_{agent_id}"]
        self.delay = delay
        self.fail = fail
        self.runs: list[tuple[float, float]] = []

    async def can_handle(self, task: Task) -> bool:
        return self.agent_id in task.description.lower()

    async def execute(self, task: Task) -> TaskResult:
        t0 = time.monotonic()
        await asyncio.sleep(self.delay)
        t1 = time.monotonic()
        self.runs.append((t0, t1))
        if self.fail:
            raise RuntimeError("Simulated crash")
        upstream = self._extract_upstream_text(task)
        return TaskResult(
            success=True,
            data={
                "output": f"done:{self.agent_id}|upstream={upstream}",
                "summary": f"done:{self.agent_id}",
            },
        )


class TestRegistryAndLoader(unittest.TestCase):
    def test_lazy_load_all_14_agents_and_dtos(self):
        registry = AgentLoader.load_all_agents(eager=False)
        metadata = registry.get_all_metadata()
        self.assertEqual(len(metadata), 14)
        # No agent instantiated yet in standby mode
        self.assertEqual(len(registry.get_all_agents()), 0)

        # Capabilities map populated from metadata
        caps_map = registry.get_capabilities_map()
        self.assertIn("create_pdf", caps_map)
        self.assertIn("productivity-001", caps_map["create_pdf"])
        self.assertIn("query_database", caps_map)
        self.assertIn("database-001", caps_map["query_database"])

        # Alias resolution
        self.assertEqual(registry.resolve_agent_id("creative"), "creative-001")
        self.assertEqual(registry.resolve_agent_id("creative_01"), "creative-001")
        self.assertEqual(registry.resolve_agent_id("data"), "data-001")
        self.assertEqual(registry.resolve_agent_id("deep_research"), "deep-research-001")

        # Eager instantiation of all 14 agents succeeds without import/init errors
        for meta in metadata:
            agent = registry.get_agent(meta.agent_id)
            self.assertIsNotNone(agent, f"Failed to instantiate agent {meta.agent_id}")
            self.assertEqual(agent.agent_id, meta.agent_id)
            self.assertTrue(bool(agent.name))
            self.assertTrue(bool(agent.description))

        dtos = registry.list_agents_dto()
        self.assertEqual(len(dtos), 14)
        for dto in dtos:
            self.assertSetEqual(
                set(dto.keys()),
                {
                    "id", "name", "category", "description", "capabilities",
                    "status", "active_tasks", "completed_tasks", "failed_tasks",
                },
            )
            self.assertIn(dto["status"], ("idle", "busy", "offline", "error"))

    def test_thread_safe_concurrent_get_agent(self):
        registry = AgentLoader.load_all_agents(eager=False)
        results = []
        errors = []

        def _worker():
            try:
                agent = registry.get_agent("writer-001")
                results.append(id(agent))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 12)
        self.assertEqual(len(set(results)), 1)

    def test_routing_avoids_false_creative_match_on_create_pdf(self):
        async def _check():
            reg = AgentLoader.load_all_agents(eager=False)
            pdf_agent = await reg.find_best_agent(Task(description="Create a PDF summary report"))
            chart_agent = await reg.find_best_agent(Task(description="Analyze data and create a bar chart"))
            music_agent = await reg.find_best_agent(Task(description="Generate lofi background music"))
            math_agent = await reg.find_best_agent(Task(description="Solve equation 2*x + 5 = 15"))
            return pdf_agent.agent_id, chart_agent.agent_id, music_agent.agent_id, math_agent.agent_id

        pdf_id, chart_id, music_id, math_id = asyncio.run(_check())
        self.assertEqual(pdf_id, "productivity-001")
        self.assertEqual(chart_id, "data-001")
        self.assertEqual(music_id, "audio-001")
        self.assertEqual(math_id, "student-001")


class TestIndividualAgents(unittest.TestCase):
    def test_data_analyst_agent_creates_real_chart_and_stats(self):
        from ai_assistant.agents.data.data_analyst_agent import DataAnalystAgent
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            agent = DataAnalystAgent(config={"output_dir": tmp})
            csv_path = os.path.join(tmp, "sales.csv")
            with open(csv_path, "w", encoding="utf-8") as fh:
                fh.write("month,revenue\nJan,100\nFeb,150\nMar,220\n")

            task = Task(
                description="Analyze CSV sales and create bar chart",
                params={"data_path": csv_path, "chart_type": "bar", "output_dir": tmp},
            )
            res = asyncio.run(agent.execute(task))
            self.assertTrue(res.success, res.error)
            self.assertTrue(res.output_path and os.path.exists(res.output_path))
            with Image.open(res.output_path) as img:
                self.assertGreater(img.width, 100)
            ver = asyncio.run(agent.verify(res))
            self.assertTrue(ver.is_valid)

    def test_database_agent_read_and_confirmation_gate(self):
        from ai_assistant.agents.data.database_agent import DatabaseAgent

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "test.db")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)")
            conn.execute("INSERT INTO items (name, qty) VALUES ('Widget', 10), ('Gadget', 5)")
            conn.commit()
            conn.close()

            agent = DatabaseAgent(config={"db_path": db_path})

            # Read SQL succeeds
            res_read = asyncio.run(
                agent.execute(Task(description="Query items table", params={"sql": "SELECT name, qty FROM items ORDER BY id", "db_path": db_path}))
            )
            self.assertTrue(res_read.success, res_read.error)
            self.assertEqual(res_read.data["row_count"], 2)

            # Schema inspection succeeds
            res_schema = asyncio.run(
                agent.execute(Task(description="Inspect database schema", params={"db_path": db_path}))
            )
            self.assertTrue(res_schema.success, res_schema.error)
            self.assertIn("items", res_schema.data["schema"])

            # Destructive/write SQL blocked without confirmed=True
            res_blocked = asyncio.run(
                agent.execute(Task(description="Delete row", params={"sql": "DELETE FROM items WHERE id = 1", "db_path": db_path}))
            )
            self.assertFalse(res_blocked.success)
            self.assertTrue(res_blocked.metadata.get("requires_confirmation"))

            # Write succeeds when confirmed=True
            res_ok = asyncio.run(
                agent.execute(Task(description="Delete row", params={"sql": "DELETE FROM items WHERE id = 1", "db_path": db_path, "confirmed": True}))
            )
            self.assertTrue(res_ok.success, res_ok.error)

    def test_creative_agent_real_png_and_offline_wav(self):
        from ai_assistant.agents.creative.creative_agent import CreativeAgent

        with tempfile.TemporaryDirectory() as tmp:
            agent = CreativeAgent(config={"output_dir": tmp})

            img_res = asyncio.run(
                agent.execute(Task(description="Generate a futuristic city thumbnail", params={"size": "320x180", "output_dir": tmp}))
            )
            self.assertTrue(img_res.success, img_res.error)
            self.assertTrue(os.path.exists(img_res.output_path))
            self.assertTrue(asyncio.run(agent.verify(img_res)).is_valid)

            wav_res = asyncio.run(
                agent.execute(
                    Task(
                        description="Generate voiceover for intro script",
                        params={"text": "Welcome to CogniBloom", "offline": True, "synthetic_fallback_only": True, "output_dir": tmp},
                    )
                )
            )
            self.assertTrue(wav_res.success, wav_res.error)
            self.assertTrue(wav_res.output_path.endswith(".wav"))
            self.assertTrue(asyncio.run(agent.verify(wav_res)).is_valid)

    def test_audio_agent_music_sfx_and_denoise(self):
        from ai_assistant.agents.audio.audio_agent import AudioAgent

        with tempfile.TemporaryDirectory() as tmp:
            agent = AudioAgent(config={"output_dir": tmp})
            music_res = asyncio.run(
                agent.execute(Task(description="Generate lofi music track", params={"duration": 1.0, "output_dir": tmp}))
            )
            self.assertTrue(music_res.success, music_res.error)
            with wave.open(music_res.output_path, "rb") as wf:
                self.assertGreater(wf.getnframes(), 0)

            clean_res = asyncio.run(
                agent.execute(Task(description="Clean noise from audio file", params={"path": music_res.output_path, "output_dir": tmp}))
            )
            self.assertTrue(clean_res.success, clean_res.error)
            self.assertTrue(os.path.exists(clean_res.output_path))

    def test_productivity_agent_real_pdf_and_conversion(self):
        from ai_assistant.agents.productivity.productivity_agent import ProductivityAgent
        import PyPDF2

        with tempfile.TemporaryDirectory() as tmp:
            agent = ProductivityAgent(config={"output_dir": tmp})
            pdf_res = asyncio.run(
                agent.execute(
                    Task(
                        description="Create a PDF summary report",
                        params={"title": "Q4 Review", "content": "Revenue grew 35% YoY.", "output_dir": tmp},
                    )
                )
            )
            self.assertTrue(pdf_res.success, pdf_res.error)
            self.assertTrue(os.path.exists(pdf_res.output_path))
            ver = asyncio.run(agent.verify(pdf_res))
            self.assertTrue(ver.is_valid)
            with open(pdf_res.output_path, "rb") as fh:
                reader = PyPDF2.PdfReader(fh)
                self.assertGreaterEqual(len(reader.pages), 1)

            csv_in = os.path.join(tmp, "sample.csv")
            with open(csv_in, "w", encoding="utf-8") as fh:
                fh.write("a,b\n1,2\n")
            conv_res = asyncio.run(
                agent.execute(Task(description="Convert CSV to JSON", params={"source_path": csv_in, "target_format": "json", "output_dir": tmp}))
            )
            self.assertTrue(conv_res.success, conv_res.error)
            self.assertTrue(os.path.exists(conv_res.output_path))

    def test_writer_and_research_agents_mocked(self):
        from ai_assistant.agents.research.deep_research_agent import DeepResearchAgent
        from ai_assistant.agents.research.research_agent import ResearchAgent
        from ai_assistant.agents.writer.writer_agent import WriterAgent

        with tempfile.TemporaryDirectory() as tmp:
            writer = WriterAgent(config={"llm": _MockLLM("# Final Article\nClean mocked output."), "output_dir": tmp})
            w_res = asyncio.run(
                writer.execute(
                    Task(
                        description="Write an executive summary",
                        params={"filename": "exec.md", "output_dir": tmp},
                        context={"previous_output": "Upstream research notes."},
                    )
                )
            )
            self.assertTrue(w_res.success, w_res.error)
            self.assertTrue(w_res.data["used_llm"])
            self.assertTrue(os.path.exists(w_res.output_path))

            # Research agent Wikipedia lookup (mocked requests.get)
            r_agent = ResearchAgent(config={"output_dir": tmp})
            fake_resp = MagicMock()
            fake_resp.status_code = 200
            fake_resp.json.return_value = {
                "title": "Artificial intelligence",
                "extract": "Artificial intelligence is intelligence of machines.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Artificial_intelligence"}},
            }
            fake_resp.raise_for_status.return_value = None

            with patch("ai_assistant.agents.research.research_agent.requests.get", return_value=fake_resp):
                r_res = asyncio.run(r_agent.execute(Task(description="Wikipedia summary for Artificial intelligence")))
            self.assertTrue(r_res.success, r_res.error)
            self.assertIn("Artificial intelligence", r_res.data["summary"])

            # Deep research agent with mocked search/scrape + LLM synthesis
            dr_agent = DeepResearchAgent(config={"llm": _MockLLM("# Deep Report\nSynthesized findings."), "output_dir": tmp})
            with patch.object(
                dr_agent,
                "_parallel_search_and_scrape",
                return_value=[{"url": "https://example.com", "content": "Solar growth is 25% YoY."}],
            ):
                dr_res = asyncio.run(dr_agent.execute(Task(description="Deep research solar energy", params={"output_dir": tmp})))
            self.assertTrue(dr_res.success, dr_res.error)
            self.assertTrue(os.path.exists(dr_res.output_path))

    def test_communication_file_web_student_video_autonomous(self):
        from ai_assistant.agents.communication.communication_agent import CommunicationAgent
        from ai_assistant.agents.core.autonomous_agent import AutonomousAgent
        from ai_assistant.agents.file.file_manager_agent import FileManagerAgent
        from ai_assistant.agents.student.student_agent import StudentAgent
        from ai_assistant.agents.video.training_mode import TrainingMode
        from ai_assistant.agents.video.video_agent import VideoAgent
        from ai_assistant.agents.video.visual_verifier import VisualVerifier
        from ai_assistant.agents.web.web_agent import WebAgent

        with tempfile.TemporaryDirectory() as tmp:
            # 1. CommunicationAgent: confirmation gate + mocked send + LLM draft
            comm = CommunicationAgent(config={"llm": _MockLLM("Draft body text.")})
            draft_res = asyncio.run(comm.execute(Task(description="Draft email to Alice", params={"to": "alice@example.com", "subject": "Hi"})))
            self.assertTrue(draft_res.success)

            blocked = asyncio.run(comm.execute(Task(description="Send email to Alice", params={"to": "alice@example.com", "body": "Hello"})))
            self.assertFalse(blocked.success)
            self.assertTrue(blocked.metadata.get("requires_confirmation"))

            with patch("ai_assistant.integrations.email_handler.send_email", return_value="✅ Email sent"):
                sent = asyncio.run(
                    comm.execute(Task(description="Send email to Alice", params={"to": "alice@example.com", "body": "Hello", "confirmed": True}))
                )
            self.assertTrue(sent.success, sent.error)

            # 2. FileManagerAgent: organize + rename + search
            work_dir = Path(tmp) / "files"
            work_dir.mkdir()
            (work_dir / "photo.png").write_bytes(b"png")
            (work_dir / "notes.txt").write_text("hello", encoding="utf-8")

            fm = FileManagerAgent(config={"output_dir": tmp})
            org_res = asyncio.run(fm.execute(Task(description="Organize files", params={"path": str(work_dir)})))
            self.assertTrue(org_res.success, org_res.error)
            self.assertTrue((work_dir / "images" / "photo.png").exists())
            self.assertTrue((work_dir / "documents" / "notes.txt").exists())

            # 3. WebAgent: rejects file:// scheme and fetches mocked HTTP cleanly
            web = WebAgent()
            bad_url = asyncio.run(web.execute(Task(description="Browse file:///etc/passwd", params={"url": "file:///etc/passwd"})))
            self.assertFalse(bad_url.success)

            mock_http = MagicMock()
            mock_http.url = "https://example.com"
            mock_http.status_code = 200
            mock_http.text = "<html><head><title>Example</title></head><body><p>Hello Web</p><form action='/post'><input name='q'/></form></body></html>"
            mock_http.raise_for_status.return_value = None
            with patch("requests.get", return_value=mock_http):
                web_res = asyncio.run(web.execute(Task(description="Browse https://example.com")))
            self.assertTrue(web_res.success, web_res.error)
            self.assertEqual(web_res.data["title"], "Example")

            # 4. StudentAgent: SymPy math + folder RAG
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            (notes_dir / "physics.txt").write_text("Newton's second law states F equals m times a.", encoding="utf-8")
            student = StudentAgent(config={"persist_directory": str(Path(tmp) / "rag")})

            math_res = asyncio.run(student.execute(Task(description="Solve 2*x + 5 = 15")))
            self.assertTrue(math_res.success, math_res.error)
            self.assertIn("5", math_res.data["solutions"])

            ing_res = asyncio.run(student.execute(Task(description="Prepare study folder", params={"path": str(notes_dir)})))
            self.assertTrue(ing_res.success, ing_res.error)
            ans_res = asyncio.run(student.execute(Task(description="Exam question: What is Newton's second law?")))
            self.assertTrue(ans_res.success, ans_res.error)
            self.assertIn("Newton", ans_res.data["answer"])

            # 5. VideoAgent thumbnail + TrainingMode + VisualVerifier
            vid = VideoAgent(config={"output_dir": tmp})
            thumb_res = asyncio.run(
                vid.execute(Task(description="Create thumbnail for AI tutorial", required_capabilities=["create_thumbnail"], params={"output_dir": tmp}))
            )
            self.assertTrue(thumb_res.success, thumb_res.error)
            self.assertTrue(os.path.exists(thumb_res.output_path))

            tm = TrainingMode("test_prof")
            tm.add_action("hotkey", {"keys": ["ctrl", "k"]})
            wf_path = tm.save_workflow(output_dir=tmp)
            self.assertEqual(len(TrainingMode.load_workflow(wf_path)), 1)

            vv = VisualVerifier()
            import numpy as np

            a = np.zeros((32, 32, 3), dtype=np.uint8)
            b = a.copy()
            b[4:12, 4:12] = 255
            self.assertTrue(vv.verify_state("changed", before_image=a, screen_image=b))
            self.assertFalse(vv.verify_state("unchanged", before_image=a, screen_image=a))

            # 6. AutonomousAgent memory persistence + reflection
            auto = AutonomousAgent(config={"disable_router": True, "llm": _MockLLM("Your preferred theme is Solarized Dark.")})
            mem_res = asyncio.run(auto.execute(Task(description="Remember that my favorite IDE theme is Solarized Dark")))
            self.assertTrue(mem_res.success)
            ref_res = asyncio.run(auto.execute(Task(description="Reflect on my preferences and theme")))
            self.assertTrue(ref_res.success)
            self.assertIn("Solarized Dark", ref_res.data["output"])


class TestMultiAgentCoordinator(unittest.TestCase):
    def setUp(self):
        reset_multi_agent_coordinator()

    def tearDown(self):
        reset_multi_agent_coordinator()

    def test_parallel_waves_data_passing_and_events(self):
        async def _run():
            reg = AgentRegistry()
            a1 = _SlowAgent("a1", delay=0.15)
            a2 = _SlowAgent("a2", delay=0.15)
            a3 = _SlowAgent("a3", delay=0.05)
            reg.register_agent(a1)
            reg.register_agent(a2)
            reg.register_agent(a3)

            coord = get_multi_agent_coordinator(reg)
            events_two_arg = []
            events_one_arg = []
            coord.subscribe_events(lambda etype, payload: events_two_arg.append((etype, payload)))
            coord.subscribe_events(lambda evt: events_one_arg.append(evt))

            plan = [
                {"step_id": "s1", "agent_id": "a1", "task": "Run a1", "depends_on": []},
                {"step_id": "s2", "agent_id": "a2", "task": "Run a2", "depends_on": []},
                {"step_id": "s3", "agent_id": "a3", "task": "Combine {s1.output} & {s2.output}", "depends_on": ["s1", "s2"]},
            ]

            t0 = time.monotonic()
            outcome = await coord.execute_dag(plan, chain_id="chain-123")
            elapsed = time.monotonic() - t0
            return outcome, elapsed, events_two_arg, events_one_arg, reg, coord

        outcome, elapsed, events2, events1, reg, coord = asyncio.run(_run())
        self.assertEqual(outcome["status"], "completed")
        self.assertEqual(len(outcome["steps"]), 3)
        # s1 (0.15s) and s2 (0.15s) ran concurrently, plus s3 (0.05s) -> well under serial 0.35s
        self.assertLess(elapsed, 0.30)
        # Upstream interpolation reached s3
        self.assertIn("done:a1", outcome["result"]["output"])
        self.assertIn("done:a2", outcome["result"]["output"])
        # Active tasks cleared after completion
        self.assertEqual(len(coord.active_tasks), 0)
        # Task history queryable
        self.assertEqual(len(coord.list_tasks()), 3)
        # Events emitted in both arity formats
        emitted_types = [e[0] for e in events2]
        self.assertIn("agent.task_started", emitted_types)
        self.assertIn("agent.task_completed", emitted_types)
        self.assertIn("agent.status_changed", emitted_types)
        self.assertEqual(len(events1), len(events2))

    def test_execute_step_contract_and_error_recovery(self):
        async def _run():
            reg = AgentRegistry()
            ok_agent = _SlowAgent("ok", delay=0.01, fail=False)
            bad_agent = _SlowAgent("bad", delay=0.01, fail=True)
            reg.register_agent(ok_agent)
            reg.register_agent(bad_agent)

            coord = MultiAgentCoordinator(reg)
            events = []
            coord.subscribe_events(lambda et, pl: events.append((et, pl)))

            res_ok = await coord.execute_step(
                description="Run ok step",
                capability="cap_ok",
                chain_context={"previous_output": "hello"},
                chain_id="chain-xyz",
            )
            res_bad = await coord.execute_agent("bad", Task(description="Trigger error", max_retries=0))
            return res_ok, res_bad, ok_agent, bad_agent, events, coord

        res_ok, res_bad, ok_agent, bad_agent, events, coord = asyncio.run(_run())
        self.assertTrue(res_ok.success)
        self.assertIn("upstream=hello", res_ok.data["output"])
        self.assertEqual(ok_agent.completed_tasks, 1)

        # Error recovery restores IDLE & clears active_tasks
        self.assertFalse(res_bad.success)
        self.assertEqual(bad_agent.status, AgentStatus.IDLE)
        self.assertEqual(bad_agent.active_tasks, 0)
        self.assertEqual(bad_agent.failed_tasks, 1)
        self.assertEqual(len(coord.active_tasks), 0)
        self.assertTrue(any(et == "agent.task_failed" for et, _ in events))

    def test_cycle_detection_and_cancellation(self):
        async def _run():
            reg = AgentRegistry()
            slow = _SlowAgent("slow", delay=2.0)
            reg.register_agent(slow)
            coord = MultiAgentCoordinator(reg)

            # Cycle check
            cycle_out = await coord.execute_dag([
                {"step_id": "a", "agent_id": "slow", "task": "a", "depends_on": ["b"]},
                {"step_id": "b", "agent_id": "slow", "task": "b", "depends_on": ["a"]},
            ])

            # Cancel running task
            task = Task(description="slow task")
            bg = asyncio.create_task(coord.execute_agent("slow", task))
            await asyncio.sleep(0.05)
            cancelled = coord.cancel_task(task.task_id)
            res = await bg
            return cycle_out, cancelled, res, coord.get_task(task.task_id), slow

        cycle_out, cancelled, res, task_rec, slow = asyncio.run(_run())
        self.assertEqual(cycle_out["status"], "error")
        self.assertTrue(cancelled)
        self.assertFalse(res.success)
        self.assertEqual(task_rec["status"], "cancelled")
        self.assertEqual(slow.status, AgentStatus.IDLE)

    def test_process_command_with_llm_planner_and_fallback(self):
        async def _run():
            reg = AgentRegistry()
            a1 = _SlowAgent("alpha", delay=0.01)
            a2 = _SlowAgent("beta", delay=0.01)
            reg.register_agent(a1)
            reg.register_agent(a2)

            planner_llm = _MockLLM(
                json.dumps({
                    "steps": [
                        {"step_id": "step_1", "agent_id": "alpha", "task": "Run alpha", "depends_on": []},
                        {"step_id": "step_2", "agent_id": "beta", "task": "Use {step_1.output}", "depends_on": ["step_1"]},
                    ]
                })
            )
            coord = MultiAgentCoordinator(reg, llm=planner_llm)
            llm_out = await coord.process_command("First run alpha then beta")

            # Offline fallback when LLM returns None
            coord_offline = MultiAgentCoordinator(reg, llm=_MockLLM("not valid json"))
            fb_out = await coord_offline.process_command("Run alpha and then run beta")
            return llm_out, fb_out

        llm_out, fb_out = asyncio.run(_run())
        self.assertEqual(llm_out["status"], "completed")
        self.assertEqual(len(llm_out["steps"]), 2)
        self.assertIn("done:alpha", llm_out["result"]["output"])

        self.assertEqual(fb_out["status"], "completed")
        self.assertEqual(len(fb_out["steps"]), 2)


if __name__ == "__main__":
    unittest.main()
