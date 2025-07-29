"""Observability and tracing utilities for ASDA-X."""

from __future__ import annotations

import atexit
import logging
import sqlite3
import time
import uuid
import zmq
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Protocol

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from pydantic import BaseModel, Field, ConfigDict


# --- OpenTelemetry Setup ---

def setup_opentelemetry(service_name: str = "asda-x") -> None:
    """Configure OpenTelemetry for the application."""
    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

# Call setup at import time
setup_opentelemetry()
tracer = trace.get_tracer("asda.tracer")


# --- Trace Event Schema ---

class NodeStatus(str, Enum):
    """Execution status of a node."""
    SUCCESS = "success"
    FAILURE = "failure"
    INTERRUPTED = "interrupted"
    VALIDATION_ERROR = "validation_error"


class TraceEvent(BaseModel):
    """
    Structured event logged for each node execution.
    This model defines the core data structure for observability.
    """
    trace_id: str = Field(description="The unique ID for the entire DAG task.")
    span_id: str = Field(description="The unique ID for this specific node execution (span).")
    node_name: str = Field(description="Name of the currently executing node.")
    version: str = Field(description="Version of the node logic.")
    status: NodeStatus = Field(description="Execution status: success, failure, etc.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the event.",
    )
    runtime_ms: float = Field(description="Execution time in milliseconds.")
    input_hash: Optional[str] = Field(None, description="SHA256 hash of the node's input data.")
    output_hash: Optional[str] = Field(None, description="SHA256 hash of the node's output data.")
    error_message: Optional[str] = Field(None, description="Summary of the error, if any.")
    governance_tags: List[str] = Field(
        default_factory=list, description="Tags for governance, risk, and compliance."
    )

    model_config = ConfigDict(use_enum_values=True)


# --- Log Sinks ---

class TraceSink(Protocol):
    """Protocol for a class that can sink trace events."""
    def __call__(self, event: TraceEvent) -> None:
        ...
    def close(self) -> None:
        ...


class JSONLSink:
    """Write trace events to a JSONL file."""
    def __init__(self, path: str):
        self.path = path
        self.file = open(self.path, "a", encoding="utf-8")
        atexit.register(self.close)

    def __call__(self, event: TraceEvent) -> None:
        self.file.write(event.model_dump_json() + "\n")
        self.file.flush()

    def close(self) -> None:
        if not self.file.closed:
            self.file.close()


class SQLiteTraceSink:
    """Persist trace events in a SQLite database."""
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._ensure_table()
        atexit.register(self.close)

    def _ensure_table(self) -> None:
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT, span_id TEXT, node_name TEXT, version TEXT, status TEXT,
                timestamp TEXT, runtime_ms REAL, input_hash TEXT, output_hash TEXT,
                error_message TEXT, governance_tags TEXT
            )"""
        )
        self.conn.commit()

    def __call__(self, event: TraceEvent) -> None:
        tags_str = ",".join(event.governance_tags)
        self.conn.execute(
            "INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.trace_id, event.span_id, event.node_name, event.version,
                event.status, event.timestamp.isoformat(), event.runtime_ms,
                event.input_hash, event.output_hash, event.error_message, tags_str
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


class StreamPublisherSink:
    """Publish trace events to a ZeroMQ PUB socket."""
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://{host}:{port}")
        atexit.register(self.close)

    def __call__(self, event: TraceEvent) -> None:
        topic = f"/asda/{event.status}/{event.node_name}"
        message = event.model_dump_json()
        self.socket.send_multipart([topic.encode("utf-8"), message.encode("utf-8")])

    def close(self) -> None:
        self.socket.close()
        self.context.term()


# --- Core Logger ---

def _to_dict_factory(obj: Any, **kwargs) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def get_logger(
    sinks: Optional[List[TraceSink]] = None,
    log_level: int = logging.INFO,
) -> structlog.stdlib.BoundLogger:
    """
    Configures and returns a structlog logger.
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(serializer=_to_dict_factory),
    ]

    structlog.configure(
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        processors=processors,
        cache_logger_on_first_use=True,
    )

    # This is a placeholder for a more robust sink handling mechanism
    # In a real app, this would be driven by a config file.
    if sinks:
        # This part is conceptual for direct sink integration.
        # A more advanced implementation might use a custom processor.
        pass

    return structlog.get_logger("asda.trace")


class TraceLogger:
    """
    Central logger for node events. This class is now a wrapper around structlog
    and OpenTelemetry to provide a simplified interface for our specific needs.
    """
    def __init__(self, sinks: List[TraceSink]):
        self.sinks = sinks
        self.logger = get_logger()

    def log_event(self, event: TraceEvent) -> None:
        """Logs a structured TraceEvent."""
        for sink in self.sinks:
            sink(event)

        event_dict = event.model_dump()
        self.logger.info(
            "node_execution",
            **event_dict,
            extra_context={"trace_id": event.trace_id, "span_id": event.span_id}
        )

    def shutdown(self) -> None:
        """Gracefully close all sinks."""
        for sink in self.sinks:
            sink.close()


@contextmanager
def log_node_execution(
    logger: TraceLogger,
    node_name: str,
    version: str,
    trace_id_override: Optional[str] = None,
    governance_tags: Optional[List[str]] = None,
    input_hash: Optional[str] = None,
) -> Any:
    """
    A context manager to automatically log the execution of a node.
    It handles timing, exception capture, and OpenTelemetry span creation.
    """
    start_time = time.perf_counter()
    status = NodeStatus.SUCCESS
    error_message = None
    output_hash = None

    # Start a new span
    with tracer.start_as_current_span(node_name) as span:
        ctx = trace.get_current_span().get_span_context()
        trace_id = trace_id_override or f"0x{ctx.trace_id:032x}"
        span_id = f"0x{ctx.span_id:016x}"

        span.set_attributes({
            "node.name": node_name,
            "node.version": version,
        })

        event = None
        try:
            # Create the event object early so it can be updated
            event = TraceEvent(
                trace_id=trace_id,
                span_id=span_id,
                node_name=node_name,
                version=version,
                status=status, # Will be updated in finally
                runtime_ms=0, # Will be updated in finally
                input_hash=input_hash,
                governance_tags=governance_tags or [],
            )
            yield event
        except Exception as e:
            status = NodeStatus.FAILURE
            error_message = str(e)
            if event:
                event.status = status
                event.error_message = error_message
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, description=str(e)))
            raise
        finally:
            runtime_ms = (time.perf_counter() - start_time) * 1000
            if event:
                event.runtime_ms = runtime_ms
                event.status = status
                logger.log_event(event)


# --- Exports ---
__all__ = [
    "TraceEvent",
    "NodeStatus",
    "TraceLogger",
    "log_node_execution",
    "JSONLSink",
    "SQLiteTraceSink",
    "StreamPublisherSink",
    "setup_opentelemetry",
    "tracer",
]
