from pydantic import BaseModel

from src.core.dag_engine import DAGFlowBuilder, NodeWrapper


class InModel(BaseModel):
    text: str


class OutModel(BaseModel):
    text: str


def uppercase_node(data: dict) -> dict:
    return {"text": data["text"].upper()}


def create_wrapper() -> NodeWrapper:
    return NodeWrapper(
        uppercase_node,
        name="upper",
        version="1.0",
        input_model=InModel,
        output_model=OutModel,
    )


def test_node_wrapper():
    wrapper = create_wrapper()
    result = wrapper({"text": "hello"})
    assert result == {"text": "HELLO"}


def test_dag_flow_builder():
    wrapper = create_wrapper()
    builder = DAGFlowBuilder()
    builder.register(wrapper)
    flow = builder.build_default_flow()
    output = flow.invoke({"text": "hi"})
    assert output == {"text": "HI"}

