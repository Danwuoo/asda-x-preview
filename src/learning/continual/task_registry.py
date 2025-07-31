from __future__ import annotations

"""Registry of task snapshots for continual learning."""

from typing import Dict, Tuple

import torch


class TaskRegistry:
    """In-memory store of EWC statistics per task."""

    def __init__(self) -> None:
        self.params: Dict[str, Dict[str, torch.Tensor]] = {}
        self.fishers: Dict[str, Dict[str, torch.Tensor]] = {}

    def add(self, task_id: str, ewc) -> None:
        self.params[task_id] = {n: p.clone().detach() for n, p in ewc.params.items()}
        self.fishers[task_id] = {n: f.clone().detach() for n, f in ewc.fisher.items()}

    def has_task(self, task_id: str) -> bool:
        return task_id in self.params

    def load(self, task_id: str) -> Tuple[Dict[str, torch.Tensor], Dict[str, torch.Tensor]]:
        if task_id not in self.params:
            raise KeyError(task_id)
        return self.params[task_id], self.fishers[task_id]


__all__ = ["TaskRegistry"]
