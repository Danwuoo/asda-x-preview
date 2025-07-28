"""
Global, configurable logger instance for the application.
"""

from typing import List
from src.core.config import settings
from src.core.trace_logger import (
    TraceLogger,
    TraceSink,
    JSONLSink,
    SQLiteTraceSink,
    StreamPublisherSink,
)

def get_configured_sinks() -> List[TraceSink]:
    """Returns a list of sinks based on the global settings."""
    sinks: List[TraceSink] = []
    if settings.jsonl_enabled:
        sinks.append(JSONLSink(path=settings.jsonl_path))
    if settings.sqlite_enabled:
        sinks.append(SQLiteTraceSink(path=settings.sqlite_path))
    if settings.stream_enabled:
        sinks.append(StreamPublisherSink(host=settings.stream_host, port=settings.stream_port))
    return sinks

# Global logger instance
sinks = get_configured_sinks()
trace_logger = TraceLogger(sinks=sinks)
