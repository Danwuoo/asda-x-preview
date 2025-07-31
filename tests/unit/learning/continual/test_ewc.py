import os
import sys
from collections import namedtuple

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import torch
from torch.utils.data import DataLoader, TensorDataset  # noqa: E402

from src.learning.continual import EWC  # noqa: E402

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


def test_penalty_changes_with_params():
    x = torch.randn(10, 1)
    y = torch.randn(10, 1)
    ds = TensorDataset(x, y)
    loader = DataLoader(ds, batch_size=1)
    data = [{"x": b[0], "labels": b[1]} for b in loader]

    model = SimpleModel()
    ewc = EWC(model, data)

    with torch.no_grad():
        for p in model.parameters():
            p.add_(1.0)
    penalty = ewc.penalty(model)
    assert penalty.item() > 0
