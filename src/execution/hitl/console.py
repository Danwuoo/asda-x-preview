from __future__ import annotations

from typing import Any, Dict

from .interface import ReviewInterface
from .handler import ReviewActionHandler
from .feedback import FeedbackRecorder


class HITLConsole:
    """Orchestrate the human review flow."""

    def __init__(
        self,
        interface: ReviewInterface | None = None,
        handler: ReviewActionHandler | None = None,
        recorder: FeedbackRecorder | None = None,
    ) -> None:
        self.interface = interface or ReviewInterface()
        self.handler = handler or ReviewActionHandler()
        self.recorder = recorder or FeedbackRecorder()

    def review(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Review a decision and return the chosen action."""
        self.interface.render(decision)
        result = self.handler.handle(decision)
        self.recorder.record(decision.get("trace_id", ""), result)
        return result


__all__ = ["HITLConsole"]
