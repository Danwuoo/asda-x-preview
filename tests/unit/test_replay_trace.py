import tempfile

from src.core.replay_trace import (
    NodeExecutionTrace,
    ReplayWriter,
    ReplayReader,
)


def test_trace_record_schema():
    node = NodeExecutionTrace(node_name="test", version="1.0", input={"a": 1})
    data = node.dict()
    assert data["node_name"] == "test"
    assert data["version"] == "1.0"


def test_replay_writer_and_reader():
    with tempfile.TemporaryDirectory() as tmp:
        writer = ReplayWriter(store=tmp)
        trace_id = writer.init_trace(task_name="demo")
        writer.record_node_output(
            "node1",
            {"a": 1},
            {"b": 2},
            "1.0",
        )
        writer.finalize_trace()

        reader = ReplayReader(store=tmp)
        record = reader.load(trace_id)
        assert record.task_name == "demo"
        assert len(record.executed_nodes) == 1
        assert record.executed_nodes[0].output == {"b": 2}
