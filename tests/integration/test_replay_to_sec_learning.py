import os
import sys
from collections import namedtuple

import torch

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.replay import ReplayEntry  # noqa: E402
from src.learning.sec import replay_to_sec  # noqa: E402
from src.learning.continual import TaskRegistry, train_task  # noqa: E402

Output = namedtuple("Output", ["out", "loss"])


class DummyModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(1, 1)

    def forward(self, x, labels=None):
        out = self.linear(x)
        loss = torch.nn.functional.mse_loss(out, labels)
        return Output(out, loss)


def test_replay_to_sec_to_train():
    replay = ReplayEntry(
        replay_id="r-test",
        input_event={"value": 0.5},
        feedback_signal="intrusion",
        replay_label="misclassification",
        version_id="v1",
    )

    sec_task = replay_to_sec(replay)
    dataset = [{"x": torch.tensor([[0.5]]), "labels": torch.tensor([[1.0]])}]

    model = DummyModel()
    registry = TaskRegistry()
    train_task(model, dataset, sec_task.task_id, registry, epochs=1)

    assert registry.has_task(sec_task.task_id)
