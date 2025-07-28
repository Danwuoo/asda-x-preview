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
    if settings.tracing.jsonl_enabled:
        sinks.append(JSONLSink(path=settings.tracing.jsonl_path))
    if settings.tracing.sqlite_enabled:
        sinks.append(SQLiteTraceSink(path=settings.tracing.sqlite_path))
    if settings.tracing.stream_enabled:
        sinks.append(StreamPublisherSink(host=settings.tracing.stream_host, port=settings.tracing.stream_port))
    return sinks

def setup_global_logger() -> TraceLogger:
    """
    Configures and returns the global logger instance.
    This should be called once at application startup.
    """
    sinks = get_configured_sinks()
    logger = TraceLogger(sinks=sinks)
    return logger

# The global logger is now initialized by calling setup_global_logger().
# We provide a default instance here for modules that import it directly,
# but it can be replaced by a configured instance.
trace_logger = setup_global_logger()
