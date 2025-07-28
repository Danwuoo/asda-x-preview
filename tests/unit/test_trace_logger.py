import os
import tempfile

from src.core.trace_logger import (
    JSONLSink,
    TraceEvent,
    TraceLogger,
    log_node_event,
)


def test_trace_event_schema():
    event = TraceEvent(trace_id="1", node_name="n", version="v")
    data = event.dict()
    assert data["trace_id"] == "1"
    assert data["node_name"] == "n"


def test_log_node_event():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "trace.jsonl")
        logger = TraceLogger(JSONLSink(path))
        with log_node_event(logger, "test", "1.0") as trace_id:
            assert trace_id
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        record = TraceEvent.parse_raw(lines[0])
        assert record.node_name == "test"
        assert record.status == "success"
