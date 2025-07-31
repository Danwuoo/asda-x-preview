"""Utilities to rebuild prompts and environment for a replay entry."""

from __future__ import annotations

from typing import Any, Dict

from .replay_schema import ReplayEntry


class ReplaySimulator:
    """Reconstruct execution context from stored replay data."""

    def __init__(self, entry: ReplayEntry) -> None:
        self.entry = entry

    def build_context(self) -> Dict[str, Any]:
        """Return a lightweight context dictionary for the replay."""
        return {
            "prompt": self.entry.parsed_prompt,
            "knowledge": self.entry.retrieved_knowledge,
            "decision_trace": self.entry.decision_trace,
        }
