import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.core.config import Settings, TracingSettings
from src.core.dag_engine import DAGState
from src.core.node_interface import asda_node, BaseInputSchema, BaseOutputSchema
from src.core.trace_logger import (
    JSONLSink,
    SQLiteTraceSink,
    StreamPublisherSink,
    TraceEvent,
    NodeStatus,
    TraceLogger,
)
from src.core import global_logger

# --- Test Fixtures ---

@pytest.fixture
def clean_logger(tmp_path):
    """
    Provides a cleanly configured logger for each test, pointing to a temporary directory.
    This avoids state leakage between tests.
    """
    # 1. Define settings for a temporary logger
    log_file = tmp_path / "trace.jsonl"
    db_file = tmp_path / "trace.db"
    test_settings = Settings(
        tracing=TracingSettings(
            jsonl_enabled=True,
            sqlite_enabled=True,
            stream_enabled=False,
            jsonl_path=str(log_file),
            sqlite_path=str(db_file),
        )
    )

    # 2. Patch the global settings object
    with patch('src.core.global_logger.settings', test_settings):
        # 3. Re-initialize the global logger with the new settings
        # This creates new sinks pointing to the temp directory
        logger = global_logger.setup_global_logger()

        # 4. Monkeypatch the trace_logger in node_interface to use our new instance
        with patch('src.core.node_interface.trace_logger', logger):
            yield logger # Test runs with the clean logger

    # 5. Teardown: shutdown the logger to close file handles
    logger.shutdown()


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
        TraceEvent(trace_id="t1", node_name="n1")


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


# --- Integration Tests ---

class SimpleInput(BaseInputSchema):
    message: str

class SimpleOutput(BaseOutputSchema):
    reply: str

@asda_node(name="node_a", version="1.0")
def node_a(data: SimpleInput) -> SimpleOutput:
    return SimpleOutput(reply=data.message.upper())

@asda_node(name="node_b", version="1.0", input_node="node_a")
def node_b(data: SimpleOutput) -> SimpleOutput:
    return SimpleOutput(reply=f"From A: {data.reply}")


def test_asda_node_decorator_logs_event(clean_logger):
    """Test that the asda_node decorator correctly logs a TraceEvent."""
    state = DAGState(initial_input=SimpleInput(message="hello"), trace_id="")
    result_state = node_a(state)

    # Verify the log was written
    clean_logger.shutdown() # Ensure logs are flushed

    log_path = clean_logger.sinks[0].path # JSONLSink is the first sink
    with open(log_path, "r") as f:
        log_entry = json.loads(f.readline())

    assert log_entry["node_name"] == "node_a"
    assert log_entry["status"] == "success"
    assert log_entry["version"] == "1.0"
    assert log_entry["input_hash"] is not None

def test_dag_integration_with_connected_nodes(clean_logger):
    """Test a two-node DAG to ensure trace_id is consistent."""
    state = DAGState(initial_input=SimpleInput(message="test"), trace_id="")

    state_after_a = node_a(state)
    state.node_outputs.update(state_after_a["node_outputs"])
    state_after_b = node_b(state)

    clean_logger.shutdown()

    log_path = clean_logger.sinks[0].path
    with open(log_path, "r") as f:
        lines = f.readlines()

    assert len(lines) == 2
    log_a = json.loads(lines[0])
    log_b = json.loads(lines[1])

    assert log_a["node_name"] == "node_a"
    assert log_b["node_name"] == "node_b"
    assert log_a["trace_id"] == log_b["trace_id"]
    assert log_a["trace_id"] != ""
