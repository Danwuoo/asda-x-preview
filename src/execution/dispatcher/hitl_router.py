from __future__ import annotations

from typing import Any, Dict


class HITLRouter:
    """Send tasks to a Human-In-The-Loop console."""

    def send(self, action_plan: Dict[str, Any]) -> None:
        # Placeholder for HITL integration
        pass


__all__ = ["HITLRouter"]
