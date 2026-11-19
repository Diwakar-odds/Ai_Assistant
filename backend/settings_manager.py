"""
Backward compatibility proxy module for backend.services.settings_manager.
Maintains 100% backward compatibility for all modules importing `settings_manager`.
"""
import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.resolve()
_services_dir = _backend_dir / 'services'
for _d in (str(_backend_dir), str(_services_dir)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from services.settings_manager import *
