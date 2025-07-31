"""Helper utilities for replay workflows."""

from __future__ import annotations

from typing import Iterable, List

from .replay_schema import ReplayEntry


def sort_by_time(entries: Iterable[ReplayEntry]) -> List[ReplayEntry]:
    """Return entries sorted by timestamp."""
    return sorted(entries, key=lambda e: e.timestamp)
