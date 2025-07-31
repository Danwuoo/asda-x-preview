import os
import sys
from collections import namedtuple

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import torch

from src.learning.continual import TaskRegistry, train_task  # noqa: E402

Output = namedtuple("Output", ["out", "loss"])


class SimpleModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(1, 1)

    def forward(self, x, labels=None):
        out = self.linear(x)
        loss = torch.nn.functional.mse_loss(out, labels)
        return Output(out, loss)


def test_train_task_updates_registry():
    x = torch.randn(4, 1)
    y = torch.randn(4, 1)
    dataset = [{"x": a.unsqueeze(0), "labels": b.unsqueeze(0)} for a, b in zip(x, y)]

    model = SimpleModel()
    registry = TaskRegistry()
    train_task(model, dataset, "t1", registry, epochs=1)
    assert registry.has_task("t1")
