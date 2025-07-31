from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel


class DispatchRecord(BaseModel):
    decision_id: str
    action_plan: Dict[str, Any]
    risk_level: str
    dispatch_route: str
    executed: bool
    rationale: str
    trace_id: str
    timestamp: datetime


class DispatchAuditLogger:
    """Simple logger writing dispatch records to JSONL."""

    def __init__(self, log_path: str = "data/dispatch_log.jsonl") -> None:
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log(self, record: DispatchRecord) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(record.json() + "\n")


__all__ = ["DispatchAuditLogger", "DispatchRecord"]
