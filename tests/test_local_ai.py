"""Quick smoke test for Local GGUF AI installation."""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT_DIR / "core_ai" / "src"
BACKEND_DIR = ROOT_DIR / "backend"
for p in (str(CORE_SRC), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


class TestLocalGGUFSetup(unittest.TestCase):
    def test_gguf_manager_imports(self):
        from ai_assistant.ai.gguf_model_manager import GGUFModelManager, get_gguf_manager, llama_cpp_available
        from ai_assistant.ai.llm_provider import GGUFProvider, LLMFactory

        self.assertIsNotNone(GGUFModelManager)
        self.assertIsNotNone(GGUFProvider)
        self.assertIn("gguf", LLMFactory.PROVIDERS)
        self.assertIsInstance(llama_cpp_available(), bool)

        mgr = get_gguf_manager()
        status = mgr.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn("available", status)

    def test_gguf_discovery(self):
        from settings_manager import discover_gguf_models
        models = discover_gguf_models()
        self.assertIsInstance(models, list)


if __name__ == "__main__":
    unittest.main()
