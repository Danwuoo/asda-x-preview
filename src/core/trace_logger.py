"""Observability and tracing utilities for ASDA-X."""

from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field
import structlog


class TraceEvent(BaseModel):
    """Structured event logged for each node execution."""

    trace_id: str
    node_name: str
    version: str
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    runtime_ms: Optional[float] = None
    status: str = "success"
    timestamp: float = Field(default_factory=lambda: time.time())
    error_msg: Optional[str] = None
    governance_tags: Optional[str] = None


class JSONLSink:
    """Write trace events to a JSONL file."""

    def __init__(self, path: str) -> None:
        self.path = path

    def write(self, event: TraceEvent) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(event.json())
            f.write("\n")


class SQLiteTraceSink:
    """Persist trace events in a SQLite database."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT,
                node_name TEXT,
                version TEXT,
                input_hash TEXT,
                output_hash TEXT,
                runtime_ms REAL,
                status TEXT,
                timestamp REAL,
                error_msg TEXT,
                governance_tags TEXT
            )"""
            )

    def write(self, event: TraceEvent) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    event.trace_id,
                    event.node_name,
                    event.version,
                    event.input_hash,
                    event.output_hash,
                    event.runtime_ms,
                    event.status,
                    event.timestamp,
                    event.error_msg,
                    event.governance_tags,
                ),
            )


@dataclass
class TraceLogger:
    """Central logger for node events."""

    sink: Any

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger("asda.trace")

    def log(self, event: TraceEvent) -> None:
        self.sink.write(event)
        self.logger.info(event.status, **event.dict())

    def info(self, **kwargs: Any) -> None:
        event = TraceEvent(status="info", **kwargs)
        self.log(event)

    def error(self, **kwargs: Any) -> None:
        event = TraceEvent(status="error", **kwargs)
        self.log(event)


@contextmanager
def log_node_event(logger: TraceLogger, node_name: str, version: str) -> Any:
    """Context manager to log execution of a node."""

    trace_id = str(uuid.uuid4())
    start = time.time()
    error_msg = None
    try:
        yield trace_id
    except Exception as exc:  # pragma: no cover - rare path
        error_msg = str(exc)
        raise
    finally:
        runtime_ms = (time.time() - start) * 1000
        status = "error" if error_msg else "success"
        event = TraceEvent(
            trace_id=trace_id,
            node_name=node_name,
            version=version,
            runtime_ms=runtime_ms,
            status=status,
            error_msg=error_msg,
        )
        logger.log(event)


__all__ = [
    "TraceEvent",
    "TraceLogger",
    "log_node_event",
    "JSONLSink",
    "SQLiteTraceSink",
]
