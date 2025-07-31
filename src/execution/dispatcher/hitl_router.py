from __future__ import annotations

from typing import Any, Dict

from ..hitl import HITLConsole


class HITLRouter:
    """Send tasks to a Human-In-The-Loop console."""

    def __init__(self, console: HITLConsole | None = None) -> None:
        self.console = console or HITLConsole()

    def send(self, action_plan: Dict[str, Any]) -> None:
        self.console.review(action_plan)


__all__ = ["HITLRouter"]
