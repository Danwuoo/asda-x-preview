"""Replay Trace Handler for ASDA-X.

This module records node execution traces and allows replaying
previous DAG runs. It stores traces as JSONL files by default and can
also persist them in SQLite for quick lookup.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import jsonlines
from pydantic import BaseModel, Field
from tinydb import TinyDB, Query


class NodeExecutionTrace(BaseModel):
    """Record of a single node execution."""

    node_name: str
    version: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    status: str = "success"
    runtime_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_msg: Optional[str] = None


class ReplayMetadata(BaseModel):
    """Metadata describing replay state of a trace."""

    replay_count: int = 0
    source_trace_id: Optional[str] = None
    generated_for: List[str] = Field(default_factory=list)


class TraceRecord(BaseModel):
    """Container for a full DAG execution trace."""

    trace_id: str
    task_name: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    executed_nodes: List[NodeExecutionTrace] = Field(default_factory=list)
    replay_info: ReplayMetadata = Field(default_factory=ReplayMetadata)


class ReplayWriter:
    """Persist traces to disk using JSONL or SQLite."""

    def __init__(
        self, store: str = "data/replay", use_sqlite: bool = False
    ) -> None:
        self.store = store
        self.use_sqlite = use_sqlite
        self._conn: Optional[sqlite3.Connection] = None
        self._db: Optional[TinyDB] = None
        os.makedirs(self.store, exist_ok=True)
        if self.use_sqlite:
            path = os.path.join(self.store, "replay.db")
            self._conn = sqlite3.connect(path)
            self._ensure_table()
        else:
            self._db = TinyDB(os.path.join(self.store, "replay.json"))
        self._current: Optional[TraceRecord] = None

    def _ensure_table(self) -> None:
        assert self._conn is not None
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS replay_trace (
                trace_id TEXT PRIMARY KEY,
                data TEXT
            )"""
        )
        self._conn.commit()

    def init_trace(
        self, trace_id: Optional[str] = None, task_name: str = ""
    ) -> str:
        """Start a new trace and return its id."""

        trace_id = trace_id or str(uuid.uuid4())
        self._current = TraceRecord(trace_id=trace_id, task_name=task_name)
        return trace_id

    def record_node_output(
        self,
        node_name: str,
        input: Dict[str, Any],
        output: Optional[Dict[str, Any]],
        version: str,
        *,
        status: str = "success",
        runtime_ms: Optional[float] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        """Append a node execution record to the current trace."""

        if self._current is None:
            raise RuntimeError("init_trace must be called first")
        entry = NodeExecutionTrace(
            node_name=node_name,
            version=version,
            input=input,
            output=output,
            status=status,
            runtime_ms=runtime_ms,
            error_msg=error_msg,
        )
        self._current.executed_nodes.append(entry)

    def finalize_trace(self) -> TraceRecord:
        """Write the current trace to storage."""

        if self._current is None:
            raise RuntimeError("init_trace must be called first")
        self._current.end_time = datetime.now(timezone.utc)
        record = self._current
        os.makedirs(self.store, exist_ok=True)
        path = os.path.join(self.store, f"trace_{record.trace_id}.jsonl")
        with jsonlines.open(path, mode="w") as writer:
            writer.write(json.loads(record.model_dump_json()))
        if self.use_sqlite and self._conn is not None:
            self._conn.execute(
                "INSERT OR REPLACE INTO replay_trace VALUES (?, ?)",
                (record.trace_id, record.model_dump_json()),
            )
            self._conn.commit()
        elif self._db is not None:
            self._db.insert(json.loads(record.model_dump_json()))
        self._current = None
        return record


class ReplayReader:
    """Load existing traces by id."""

    def __init__(
        self, store: str = "data/replay", use_sqlite: bool = False
    ) -> None:
        self.store = store
        self.use_sqlite = use_sqlite
        self._conn: Optional[sqlite3.Connection] = None
        if self.use_sqlite:
            path = os.path.join(self.store, "replay.db")
            if os.path.exists(path):
                self._conn = sqlite3.connect(path)

    def load(self, trace_id: str) -> TraceRecord:
        """Load trace from storage."""

        if self.use_sqlite and self._conn is not None:
            cur = self._conn.execute(
                "SELECT data FROM replay_trace WHERE trace_id=?", (trace_id,)
            )
            row = cur.fetchone()
            if row:
                data = json.loads(row[0])
                return TraceRecord.parse_obj(data)
        path = os.path.join(self.store, f"trace_{trace_id}.jsonl")
        if os.path.exists(path):
            with jsonlines.open(path, mode="r") as reader:
                data = reader.read()
            return TraceRecord.parse_obj(data)
        if self._db is not None:
            result = self._db.search(Query().trace_id == trace_id)
            if result:
                return TraceRecord.parse_obj(result[0])
        raise FileNotFoundError(trace_id)


@dataclass
class DAGReplayer:
    """Replay a DAG run using stored input/output."""

    reader: ReplayReader
    flow_builder: Any
    executed: List[NodeExecutionTrace] = field(default_factory=list)

    def replay(self, trace_id: str, *, execute: bool = False) -> TraceRecord:
        """Reload a trace and optionally re-run each node."""

        record = self.reader.load(trace_id)
        if execute:
            builder = self.flow_builder()
            runner = builder.build_default_flow()
            data: Dict[str, Any] = (
                record.executed_nodes[0].input if record.executed_nodes else {}
            )
            for node_trace in record.executed_nodes:
                node = next(
                    (
                        n
                        for n in runner.nodes
                        if getattr(n, "wrapper", None).name
                        == node_trace.node_name
                    ),
                    None,
                )
                if node:
                    data = node(data)
                self.executed.append(node_trace)
        return record


__all__ = [
    "NodeExecutionTrace",
    "ReplayMetadata",
    "TraceRecord",
    "ReplayWriter",
    "ReplayReader",
    "DAGReplayer",
]
