"""
Dependency Injection & Service Container
Provides a central inversion-of-control container for managing service singletons,
factories, and testing mocks.
"""

import threading
import logging
from typing import Dict, Any, Callable, TypeVar, Type, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """Thread-safe dependency injection service container."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ServiceContainer, cls).__new__(cls)
                cls._instance._services: Dict[str, Any] = {}
                cls._instance._factories: Dict[str, Callable[[], Any]] = {}
                cls._instance._singletons: Dict[str, bool] = {}
        return cls._instance

    def register_singleton(self, key: str, instance_or_factory: Any):
        """Register a singleton instance or a factory that creates a cached singleton."""
        with self._lock:
            if callable(instance_or_factory) and not isinstance(instance_or_factory, type):
                self._factories[key] = instance_or_factory
                self._singletons[key] = True
                if key in self._services:
                    del self._services[key]
            else:
                self._services[key] = instance_or_factory
                self._singletons[key] = True

    def register_factory(self, key: str, factory: Callable[[], Any]):
        """Register a transient factory that creates a new instance on each resolve."""
        with self._lock:
            self._factories[key] = factory
            self._singletons[key] = False

    def resolve(self, key: str, default: Optional[Any] = None) -> Any:
        """Resolve a registered service by key."""
        with self._lock:
            if key in self._services:
                return self._services[key]

            if key in self._factories:
                factory = self._factories[key]
                instance = factory()
                if self._singletons.get(key, False):
                    self._services[key] = instance
                return instance

            return default

    def override_for_testing(self, key: str, mock_instance: Any):
        """Override a service with a mock during testing."""
        with self._lock:
            self._services[key] = mock_instance

    def clear(self):
        """Clear all registered services and factories (useful for test resets)."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()


# Default singleton instance
container = ServiceContainer()

def get_container() -> ServiceContainer:
    """Retrieve the global service container."""
    return container
