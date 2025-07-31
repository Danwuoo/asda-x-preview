"""Simple query helpers for replay entries."""

from __future__ import annotations

from typing import List

from .memory_manager import ReplayMemoryManager
from .replay_schema import ReplayEntry


class ReplayQueryEngine:
    """Filter replay entries by common fields."""

    def __init__(self, manager: ReplayMemoryManager) -> None:
        self.manager = manager

    def by_label(self, label: str) -> List[ReplayEntry]:
        """Return entries with the given replay label."""
        return self.manager.query_entries(replay_label=label)
