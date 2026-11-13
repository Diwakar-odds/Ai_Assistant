"""
Core AI - Central AI Engine for AI Assistant
===========================================
This package encapsulates all artificial intelligence, agents, voice,
vision, automation, integrations, knowledge graphs, and workflow orchestrations.
"""

import sys
import os

__version__ = "4.0.0"

# Expose package directory for path resolution
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

# Ensure core_ai is accessible directly for internal subpackage lookups (e.g. from utils...)
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# Ensure PROJECT_ROOT is in sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Backward Compatibility Shim:
# Allow legacy code importing `ai_assistant.<module>` to resolve seamlessly to `core_ai.<module>`.
def _install_compatibility_shims():
    class _CompatibilityLoader:
        def find_spec(self, fullname, path, target=None):
            if fullname == "ai_assistant" or fullname.startswith("ai_assistant."):
                core_ai_name = fullname.replace("ai_assistant", "core_ai", 1)
                try:
                    import importlib
                    from importlib.machinery import ModuleSpec
                    target_mod = importlib.import_module(core_ai_name)
                    is_pkg = hasattr(target_mod, "__path__")
                    locations = list(target_mod.__path__) if is_pkg else None
                    spec = ModuleSpec(fullname, self, is_package=is_pkg)
                    spec.submodule_search_locations = locations
                    return spec
                except Exception:
                    return None
            return None

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            fullname = module.__name__
            core_ai_name = fullname.replace("ai_assistant", "core_ai", 1)
            import importlib
            target_mod = importlib.import_module(core_ai_name)
            module.__dict__.update(target_mod.__dict__)
            if hasattr(target_mod, "__path__"):
                module.__path__ = target_mod.__path__
            sys.modules[fullname] = target_mod

    finder_installed = any(isinstance(f, _CompatibilityLoader) for f in sys.meta_path)
    if not finder_installed:
        sys.meta_path.insert(0, _CompatibilityLoader())

_install_compatibility_shims()

__all__ = [
    "PACKAGE_DIR",
    "PROJECT_ROOT",
]
