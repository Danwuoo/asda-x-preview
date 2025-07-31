import os
import sys
from collections import namedtuple

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import torch

from src.learning.continual import EWC, TaskRegistry  # noqa: E402

Output = namedtuple("Output", ["out", "loss"])


class SimpleModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(1, 1)

    def forward(self, x, labels=None):
        out = self.linear(x)
        loss = None
        if labels is not None:
            loss = torch.nn.functional.mse_loss(out, labels)
        return Output(out, loss)


def test_registry_add_and_load():
    model = SimpleModel()
    data = [{"x": torch.randn(1, 1), "labels": torch.randn(1, 1)}]
    ewc = EWC(model, data)

    registry = TaskRegistry()
    registry.add("task1", ewc)
    assert registry.has_task("task1")

    params, fisher = registry.load("task1")
    assert isinstance(params, dict)
    assert isinstance(fisher, dict)
