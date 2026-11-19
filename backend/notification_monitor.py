"""
Backward compatibility forwarder for backend.services.notification_monitor.
"""
import sys
from pathlib import Path

_services_dir = Path(__file__).parent / 'services'
if str(_services_dir) not in sys.path:
    sys.path.insert(0, str(_services_dir))

from services.notification_monitor import *
