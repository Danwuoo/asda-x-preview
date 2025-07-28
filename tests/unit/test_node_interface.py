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


from src.core.dag_engine import DAGState


class TestNodeInterface:
    def setup_method(self):
        NODE_REGISTRY.clear()
        # Clear any existing trace files or mock setups
        if os.path.exists("data/trace_events.jsonl"):
            os.remove("data/trace_events.jsonl")

    def test_decorator_wraps_function_correctly(self):
        state = DAGState(initial_input={"a": 5, "b": 10}, trace_id="test_trace_1")
        output_state = my_test_node(state)
        output = output_state["node_outputs"]["my_test_node"]
        assert isinstance(output, MyOutput)
        assert output.result == 15

    def test_input_validation_failure(self):
        state = DAGState(initial_input={"a": "not_an_int", "b": 10}, trace_id="test_trace_2")
        with pytest.raises(ValueError, match="Input validation failed"):
            my_test_node(state)

    def test_node_metadata_is_present(self):
        state = DAGState(initial_input={"a": 1, "b": 2}, trace_id="test_trace_3")
        output_state = my_test_node(state)
        output = output_state["node_outputs"]["my_test_node"]
        assert isinstance(output.node_meta, NodeMeta)
        assert output.node_meta.node_name == "my_test_node"
        assert output.node_meta.version == "v1.1"
        assert "test" in output.node_meta.tags
        assert output.node_meta.replay_trace_id == "test_trace_3"

    @patch("src.core.node_interface.trace_logger")
    def test_io_capture_and_tracing(self, mock_trace_logger):
        state = DAGState(initial_input={"a": 5, "b": 10}, trace_id="test_trace_4")
        my_test_node(state)

        # Check that the logger was called
        mock_trace_logger.log_event.assert_called_once()
        trace_event = mock_trace_logger.log_event.call_args[0][0]

        assert trace_event.node_name == "my_test_node"
        assert trace_event.version == "v1.1"
        assert trace_event.status == "success"
        assert trace_event.input_hash is not None
        assert trace_event.output_hash is not None

    def test_registration_and_listing(self):
        NODE_REGISTRY.clear() # Ensure clean state
        register_node(my_test_node, name="node1")
        register_node(my_test_node_v1_2, name="node2")

        nodes = list_registered_nodes()
        assert "node1" in nodes
        assert "node2" in nodes
        assert len(nodes) == 2

        # Test duplicate registration
        with pytest.raises(ValueError, match="already registered"):
            register_node(my_test_node, name="node1")

        NODE_REGISTRY.clear()
