import os
import sys
sys.path.insert(0, os.path.abspath("src"))
from pydantic import BaseModel

from core.dag_engine import NodeWrapper, register_node


class InModel(BaseModel):
    value: int


class OutModel(BaseModel):
    value: int


@register_node("add_one", "v1", InModel, OutModel)
def add_one(inp: InModel) -> OutModel:
    return OutModel(value=inp.value + 1)


def test_node_wrapper():
    assert isinstance(add_one, NodeWrapper)
    result = add_one(InModel(value=1))
    assert result.value == 2
