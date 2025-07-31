from __future__ import annotations

from typing import Any, Dict


class AutoExecutionTrigger:
    """Placeholder for automatic execution interface."""

    def execute(self, action_plan: Dict[str, Any]) -> None:
        # In production this would call AutoExecutor or similar
        pass


__all__ = ["AutoExecutionTrigger"]
