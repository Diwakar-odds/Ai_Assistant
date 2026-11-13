"""
Pulsar AI Assistant - Web API Server
Package: backend
===================================
Web API server containing routes blueprints, background services,
WebSocket handlers, Flask application server, and web logging/utils.
"""

import sys
import os
import importlib
import importlib.util

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_services_dir = os.path.join(_backend_dir, "services")
for _p in (_backend_dir, _services_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import core_ai
except Exception:
    pass


class _BackendServicesRedirector:
    """
    Transparent redirector:
    Resolves `backend.<service>` imports directly to `backend.services.<service>`
    without requiring redundant files in `backend/` root.
    """
    _DIRECT_MODULES = {"routes", "services", "utils", "websockets", "app", "modern_web_backend"}

    def find_spec(self, fullname, path, target=None):
        parts = fullname.split(".")
        if len(parts) == 2 and parts[0] == "backend":
            subname = parts[1]
            if subname not in self._DIRECT_MODULES:
                service_fullname = f"backend.services.{subname}"
                try:
                    spec = importlib.util.find_spec(service_fullname)
                    if spec and spec.loader:
                        return importlib.util.spec_from_loader(fullname, _AliasLoader(service_fullname))
                except Exception:
                    pass
        return None


class _AliasLoader:
    def __init__(self, target_name):
        self.target_name = target_name

    def create_module(self, spec):
        return importlib.import_module(self.target_name)

    def exec_module(self, module):
        pass


if not any(isinstance(finder, _BackendServicesRedirector) for finder in sys.meta_path):
    sys.meta_path.insert(0, _BackendServicesRedirector())
