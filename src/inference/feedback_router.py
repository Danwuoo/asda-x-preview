from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List

from pydantic import BaseModel, Field


class FeedbackType(str, Enum):
    """Supported feedback event categories."""

    DRIFT_DETECTED = "drift_detected"
    CIT_FAIL = "cit_fail"
    LOW_CONFIDENCE_OUTPUT = "low_confidence_output"
    HALLUCINATION_FLAGGED = "hallucination_flagged"
    REPLAY_REQUIRED = "replay_required"
    REFINE_REQUIRED = "refine_required"
    SEC_TASK_GENERATED = "sec_task_generated"


class FeedbackEvent(BaseModel):
    """Standard event payload for feedback routing."""

    event_type: FeedbackType
    task_id: str
    trace_id: str
    source_module: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


Handler = Callable[[FeedbackEvent], Awaitable[Any] | Any]


class FeedbackRouter:
    """Route feedback events to registered handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[FeedbackType, List[Handler]] = defaultdict(list)

    def register_handler(
        self, feedback_type: FeedbackType, handler_fn: Handler
    ) -> None:
        """Register a callable to handle a specific feedback type."""
        self._handlers[feedback_type].append(handler_fn)

    async def route_event(self, event: FeedbackEvent) -> None:
        """Dispatch an event to all matching handlers."""
        for handler in self._handlers.get(event.event_type, []):
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)


__all__ = [
    "FeedbackType",
    "FeedbackEvent",
    "FeedbackRouter",
]
