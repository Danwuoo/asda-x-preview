import pytest
from pydantic import ValidationError
import os
import json
from unittest.mock import patch, MagicMock

from src.core.node_interface import (
    BaseInputSchema,
    BaseOutputSchema,
    NodeMeta,
    asda_node,
    register_node,
    list_registered_nodes,
    NODE_REGISTRY,
    trace_logger,
)

# Test Schemas
class MyInput(BaseInputSchema):
    a: int
    b: int

class MyOutput(BaseOutputSchema):
    result: int

# Test Node
@asda_node(name="my_test_node", version="v1.1", tags=["test"], capture_io=True)
def my_test_node(input_data: MyInput) -> MyOutput:
    """A simple test node that adds two numbers."""
    result = input_data.a + input_data.b
    return MyOutput(result=result)

@asda_node(name="my_test_node", version="v1.2", tags=["test"], capture_io=True)
def my_test_node_v1_2(input_data: MyInput) -> MyOutput:
    """A simple test node that multiplies two numbers."""
    result = input_data.a * input_data.b
    return MyOutput(result=result)


class TestNodeInterface:
    def setup_method(self):
        NODE_REGISTRY.clear()
        if os.path.exists("data/trace_events.jsonl"):
            os.remove("data/trace_events.jsonl")

    def teardown_method(self):
        if os.path.exists("data/trace_events.jsonl"):
            os.remove("data/trace_events.jsonl")

    def test_decorator_wraps_function_correctly(self):
        input_data = MyInput(a=5, b=10)
        output = my_test_node(input_data)
        assert isinstance(output, MyOutput)
        assert output.result == 15

    def test_input_output_validation(self):
        with pytest.raises(ValidationError):
            my_test_node({"a": "not_an_int", "b": 10})

    def test_node_metadata_is_present(self):
        input_data = MyInput(a=1, b=2)
        output = my_test_node(input_data)
        assert isinstance(output.node_meta, NodeMeta)
        assert output.node_meta.node_name == "my_test_node"
        assert output.node_meta.version == "v1.1"
        assert "test" in output.node_meta.tags
        assert output.node_meta.replay_trace_id == input_data.trace_id

    def test_io_capture_and_tracing(self):
        input_data = MyInput(a=5, b=10)
        my_test_node(input_data)

        assert os.path.exists("data/trace_events.jsonl")
        with open("data/trace_events.jsonl", "r") as f:
            trace_event = json.load(f)

        assert trace_event["node_name"] == "my_test_node"
        assert trace_event["version"] == "v1.1"
        assert trace_event["status"] == "success"
        assert trace_event["input_hash"] is not None
        assert trace_event["output_hash"] is not None

    def test_no_io_capture(self):
        @asda_node(capture_io=False)
        def no_capture_node(input_data: MyInput) -> MyOutput:
            return MyOutput(result=input_data.a + input_data.b)

        no_capture_node(MyInput(a=1, b=2))
        assert not os.path.exists("data/trace_events.jsonl")

    def test_validation_error_logging(self):
        with patch.object(trace_logger, 'log') as mock_log:
            with pytest.raises(ValidationError):
                my_test_node({"a": "invalid", "b": 2})

            mock_log.assert_called_once()
            trace_event = mock_log.call_args[0][0]
            assert trace_event.status == "validation_error"
            assert "validation error" in trace_event.error_msg

    def test_multi_version_registration(self):
        register_node(my_test_node, name="my_test_node_v1.1")
        register_node(my_test_node_v1_2, name="my_test_node_v1.2")

        assert "my_test_node_v1.1" in list_registered_nodes()
        assert "my_test_node_v1.2" in list_registered_nodes()

        input_data = MyInput(a=3, b=4)

        # Execute v1.1
        output_v1_1 = NODE_REGISTRY["my_test_node_v1.1"](input_data)
        assert output_v1_1.result == 7

        # Execute v1.2
        output_v1_2 = NODE_REGISTRY["my_test_node_v1.2"](input_data)
        assert output_v1_2.result == 12
