from src.core.node_interface import (
    BaseInputSchema,
    BaseOutputSchema,
    asda_node,
    list_registered_nodes,
)


class InSchema(BaseInputSchema):
    text: str


class OutSchema(BaseOutputSchema):
    text: str


@asda_node(name="echo", version="1.0", input_model=InSchema, output_model=OutSchema)
def echo_node(data: InSchema) -> OutSchema:
    return OutSchema(text=data.text.upper())


def test_asda_node_decorator():
    result = echo_node(InSchema(text="hi"))
    assert result.text == "HI"
    assert "echo" in list_registered_nodes()
