import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.core.dag_engine import DAGFlowBuilder, DAGState
from src.core.node_interface import asda_node, BaseInputSchema, BaseOutputSchema
from src.core.trace_logger import (
    JSONLSink,
    SQLiteTraceSink,
    StreamPublisherSink,
    TraceEvent,
    NodeStatus,
    TraceLogger,
    log_node_execution,
)


# --- Test Fixtures ---

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp

@pytest.fixture
def jsonl_sink(temp_dir):
    path = os.path.join(temp_dir, "trace.jsonl")
    return JSONLSink(path)

@pytest.fixture
def sqlite_sink(temp_dir):
    path = os.path.join(temp_dir, "trace.db")
    return SQLiteTraceSink(path)


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
        TraceEvent(trace_id="t1", node_name="n1") # Missing version, status, runtime


# --- Sink Tests ---

def test_jsonl_sink_writes_event(jsonl_sink):
    """Test that the JSONLSink correctly writes an event to a file."""
    event = TraceEvent(
        trace_id="t1", span_id="s1", node_name="n1", version="v1",
        status=NodeStatus.SUCCESS, runtime_ms=10.0
    )
    jsonl_sink(event)
    jsonl_sink.close() # Ensure file is flushed and closed

    with open(jsonl_sink.path, "r") as f:
        line = f.readline()
        data = json.loads(line)
    assert data["trace_id"] == "t1"
    assert data["node_name"] == "n1"

def test_sqlite_sink_writes_event(sqlite_sink):
    """Test that the SQLiteTraceSink correctly inserts an event into the DB."""
    event = TraceEvent(
        trace_id="t2", span_id="s2", node_name="n2", version="v2",
        status=NodeStatus.FAILURE, runtime_ms=20.0, error_message="It broke",
        governance_tags=["critical", "pii"]
    )
    sqlite_sink(event)

    conn = sqlite3.connect(sqlite_sink.path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traces WHERE trace_id=?", ("t2",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "t2"  # trace_id
    assert row[2] == "n2"  # node_name
    assert row[4] == "failure"  # status
    assert row[9] == "It broke"  # error_message
    assert row[10] == "critical,pii" # governance_tags

@patch('zmq.Context')
def test_stream_publisher_sends_event(mock_context):
    """Test that the StreamPublisherSink sends a message over ZMQ."""
    mock_socket = MagicMock()
    mock_context.return_value.socket.return_value = mock_socket

    sink = StreamPublisherSink()
    event = TraceEvent(
        trace_id="t3", span_id="s3", node_name="n3", version="v3",
        status=NodeStatus.SUCCESS, runtime_ms=30.0
    )
    sink(event)

    # Check that send_multipart was called with the correct topic and message
    mock_socket.send_multipart.assert_called_once()
    args, _ = mock_socket.send_multipart.call_args
    topic, message = args[0]
    assert topic == b"/asda/success/n3"
    assert json.loads(message.decode('utf-8'))["trace_id"] == "t3"


# --- Integration Tests ---

# Define simple schemas for testing the decorator
class SimpleInput(BaseInputSchema):
    message: str

class SimpleOutput(BaseOutputSchema):
    reply: str

@pytest.fixture
def configured_test_logger(jsonl_sink):
    """Fixture to provide a TraceLogger configured with a JSONLSink."""
    return TraceLogger(sinks=[jsonl_sink])

def test_asda_node_decorator_logs_event(configured_test_logger, temp_dir):
    """Test that the asda_node decorator correctly logs a TraceEvent."""
    # Temporarily patch the global logger used by the node_interface
    with patch('src.core.node_interface.trace_logger', configured_test_logger):

        @asda_node(name="test_node", version="1.0", input_node="start_node")
        def my_test_node(data: SimpleInput) -> SimpleOutput:
            return SimpleOutput(reply=f"Received: {data.message}")

        # Simulate a DAG execution
        builder = DAGFlowBuilder()
        builder.add_node("test_node", my_test_node)

        # This is a simplified state. In a real scenario, LangGraph manages this.
        initial_state = DAGState(
            initial_input=None, # Not used since we specify input_node
            node_outputs={"start_node": SimpleInput(message="hello")},
            trace_id="",
        )

        # Execute the node
        result_state = my_test_node(initial_state)

        # Verify the output
        assert "test_node" in result_state["node_outputs"]
        assert result_state["node_outputs"]["test_node"].reply == "Received: hello"

        # Verify the log was written
        configured_test_logger.shutdown()
        sink_path = configured_test_logger.sinks[0].path
        with open(sink_path, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["node_name"] == "test_node"
        assert log_entry["status"] == "success"
        assert log_entry["version"] == "1.0"
        assert log_entry["input_hash"] is not None
        assert log_entry["output_hash"] is not None

def test_dag_integration_with_connected_nodes(configured_test_logger):
    """Test a two-node DAG to ensure trace_id is consistent."""
    with patch('src.core.node_interface.trace_logger', configured_test_logger):

        @asda_node(name="node_a", version="1.0")
        def node_a(data: SimpleInput) -> SimpleOutput:
            return SimpleOutput(reply=data.message.upper())

        @asda_node(name="node_b", version="1.0", input_node="node_a")
        def node_b(data: SimpleOutput) -> SimpleOutput:
            return SimpleOutput(reply=f"From A: {data.reply}")

        # Simulate execution
        state = DAGState(initial_input=SimpleInput(message="test"), trace_id="")

        # Run node_a
        state_after_a = node_a(state)
        state.node_outputs.update(state_after_a["node_outputs"])

        # Run node_b
        state_after_b = node_b(state)
        state.node_outputs.update(state_after_b["node_outputs"])

        # Check logs
        configured_test_logger.shutdown()
        sink_path = configured_test_logger.sinks[0].path
        with open(sink_path, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2
        log_a = json.loads(lines[0])
        log_b = json.loads(lines[1])

        assert log_a["node_name"] == "node_a"
        assert log_b["node_name"] == "node_b"
        assert log_a["trace_id"] == log_b["trace_id"]
        assert log_a["trace_id"] != ""
