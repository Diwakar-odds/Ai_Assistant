"""
Abstract base class for all Search Engine connectors.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models import SearchResult


class BaseSearchEngine(ABC):
    """Abstract search engine interface."""

    def __init__(self, name: str, timeout: float = 3.0):
        self.name = name
        self.timeout = timeout

    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Execute a search query and return normalized results."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this engine is configured and operational."""
        pass
