from __future__ import annotations

"""Simple incremental fine-tuning loop using EWC."""

from typing import Iterable

import torch

from .ewc import EWC
from .task_registry import TaskRegistry
from .utils import default_optimizer, to_dataloader


def train_task(
    model: torch.nn.Module,
    dataset: Iterable,
    task_id: str,
    registry: TaskRegistry,
    *,
    epochs: int = 1,
    lr: float = 1e-3,
    ewc_lambda: float = 0.4,
) -> None:
    """Train ``model`` on ``dataset`` and update ``registry``."""
    dataloader = to_dataloader(dataset)
    optimizer = default_optimizer(model, lr)

    prev_ewc = None
    if registry.has_task(task_id):
        params, fisher = registry.load(task_id)
        prev_ewc = EWC.from_saved(model, params, fisher)

    model.train()
    for _ in range(epochs):
        for batch in dataloader:
            optimizer.zero_grad()
            output = model(**batch)
            loss = output.loss if hasattr(output, "loss") else output[1]
            if prev_ewc is not None:
                loss = loss + ewc_lambda * prev_ewc.penalty(model)
            loss.backward()
            optimizer.step()

    new_ewc = EWC(model, dataloader)
    registry.add(task_id, new_ewc)


__all__ = ["train_task"]
