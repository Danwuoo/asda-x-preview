import pytest
from pydantic import ValidationError

from src.core.node_interface import (
    BaseInputSchema,
    BaseOutputSchema,
    NodeMeta,
    asda_node,
    register_node,
    list_registered_nodes,
    NODE_REGISTRY,
)


# Test Schemas
class MyInput(BaseInputSchema):
    a: int
    b: int


class MyOutput(BaseOutputSchema):
    result: int


# Test Node
@asda_node(name="my_test_node", version="v1.1", tags=["test"])
def my_test_node(input_data: MyInput) -> MyOutput:
    """A simple test node that adds two numbers."""
    result = input_data.a + input_data.b
    return MyOutput(result=result)


class TestNodeInterface:
    def setup_method(self):
        # Clear the registry before each test
        NODE_REGISTRY.clear()

    def test_decorator_wraps_function_correctly(self):
        """Ensures @asda_node wraps a function and it's still callable."""
        input_data = MyInput(a=5, b=10)
        output = my_test_node(input_data)
        assert isinstance(output, MyOutput)
        assert output.result == 15

    def test_input_output_validation(self):
        """Tests that Pydantic validation is triggered for inputs."""
        with pytest.raises(ValidationError):
            my_test_node({"a": "not_an_int", "b": 10})

    def test_node_metadata_is_present(self):
        """Validates that NodeMeta is correctly populated."""
        input_data = MyInput(a=1, b=2)
        output = my_test_node(input_data)
        assert isinstance(output.node_meta, NodeMeta)
        assert output.node_meta.node_name == "my_test_node"
        assert output.node_meta.version == "v1.1"
        assert "test" in output.node_meta.tags
        assert output.node_meta.replay_trace_id == input_data.trace_id

    def test_node_registration(self):
        """Tests the node registry functionality."""
        register_node(my_test_node, name="test_node_1")
        assert "test_node_1" in list_registered_nodes()

        with pytest.raises(ValueError):
            register_node(my_test_node, name="test_node_1") # Test duplicate registration

    def test_default_naming_and_versioning(self):
        """Tests default naming and versioning if not provided."""
        @asda_node()
        def another_node(input_data: MyInput) -> MyOutput:
            return MyOutput(result=input_data.a - input_data.b)

        output = another_node(MyInput(a=10, b=3))
        assert output.node_meta.node_name == "another_node"
        assert output.node_meta.version == "v1.0"

    def test_type_error_on_missing_input_annotation(self):
        """A node without a BaseInputSchema annotation should fail."""
        with pytest.raises(TypeError, match="must have an input parameter annotated"):
            @asda_node()
            def faulty_node(some_input: dict) -> MyOutput:
                return MyOutput(result=1)

    def test_type_error_on_missing_output_annotation(self):
        """A node without a BaseOutputSchema annotation should fail."""
        with pytest.raises(TypeError, match="must have a return type annotation"):
            @asda_node()
            def faulty_node(input_data: MyInput) -> dict:
                return {"result": 1}

            faulty_node(MyInput(a=1, b=2))
