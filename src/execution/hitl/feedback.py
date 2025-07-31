from __future__ import annotations

from typing import Any, Dict, List


class FeedbackRecorder:
    """Record reviewer feedback for audit."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def record(self, trace_id: str, result: Dict[str, Any]) -> None:
        entry = {"trace_id": trace_id, **result}
        self.records.append(entry)


__all__ = ["FeedbackRecorder"]
