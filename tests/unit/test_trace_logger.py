import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.core.dag_engine import DAGState
from src.core.node_interface import asda_node, BaseInputSchema, BaseOutputSchema
from src.core.trace_logger import (
    JSONLSink,
    SQLiteTraceSink,
    TraceEvent,
    NodeStatus,
    TraceLogger,
    log_node_execution,
)


# --- Schema Tests ---

def test_trace_event_creation_and_validation():
    """Test that a valid TraceEvent can be created."""
    event = TraceEvent(
        trace_id="t1", span_id="s1", node_name="n1", version="v1",
        status=NodeStatus.SUCCESS, runtime_ms=123.45
    )
    assert event.trace_id == "t1"
    assert event.status == NodeStatus.SUCCESS

def test_trace_event_missing_required_fields():
    """Test that creating a TraceEvent with missing fields raises an error."""
    with pytest.raises(ValidationError):
        TraceEvent(trace_id="t1", span_id="s1", node_name="n1", version="v1", status=NodeStatus.SUCCESS) # Missing runtime_ms

# --- Sink Tests ---

def test_jsonl_sink_writes_event(tmp_path):
    """Test that the JSONLSink correctly writes an event to a file."""
    path = tmp_path / "test.jsonl"
    sink = JSONLSink(str(path))
    event = TraceEvent(
        trace_id="t1", span_id="s1", node_name="n1", version="v1",
        status=NodeStatus.SUCCESS, runtime_ms=10.0
    )
    sink(event)
    sink.close()

    with open(path, "r") as f:
        data = json.loads(f.readline())
    assert data["trace_id"] == "t1"

def test_sqlite_sink_writes_event(tmp_path):
    """Test that the SQLiteTraceSink correctly inserts an event into the DB."""
    path = tmp_path / "test.db"
    sink = SQLiteTraceSink(str(path))
    event = TraceEvent(
        trace_id="t2", span_id="s2", node_name="n2", version="v2",
        status=NodeStatus.FAILURE, runtime_ms=20.0, error_message="It broke",
        governance_tags=["critical", "pii"]
    )
    sink(event)

    conn = sqlite3.connect(path)
    row = conn.cursor().execute("SELECT * FROM traces WHERE trace_id=?", ("t2",)).fetchone()
    conn.close()
    assert row is not None
    assert row[2] == "n2"

# --- Context Manager Test ---

def test_log_node_execution_context_manager():
    """Test the log_node_execution context manager."""
    mock_logger = MagicMock(spec=TraceLogger)

    with log_node_execution(logger=mock_logger, node_name="test_node", version="1.0") as event:
        assert event.status == NodeStatus.SUCCESS

    mock_logger.log_event.assert_called_once()
    logged_event = mock_logger.log_event.call_args[0][0]
    assert logged_event.node_name == "test_node"
    assert logged_event.status == NodeStatus.SUCCESS
    assert logged_event.runtime_ms > 0

def test_log_node_execution_with_exception():
    """Test that the context manager correctly logs failures."""
    mock_logger = MagicMock(spec=TraceLogger)

    with pytest.raises(ValueError, match="Something went wrong"):
        with log_node_execution(logger=mock_logger, node_name="failing_node", version="1.0"):
            raise ValueError("Something went wrong")

    mock_logger.log_event.assert_called_once()
    logged_event = mock_logger.log_event.call_args[0][0]
    assert logged_event.node_name == "failing_node"
    assert logged_event.status == NodeStatus.FAILURE
    assert "Something went wrong" in logged_event.error_message
