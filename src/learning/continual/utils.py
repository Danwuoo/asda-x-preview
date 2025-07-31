from __future__ import annotations

"""Helper utilities for continual learning."""

from typing import Iterable

import torch


def default_optimizer(model: torch.nn.Module, lr: float = 1e-3) -> torch.optim.Optimizer:
    """Return a simple Adam optimizer."""
    return torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)


def to_dataloader(dataset: Iterable, batch_size: int = 1):
    """Convert iterable of dicts to a dataloader."""
    return torch.utils.data.DataLoader(list(dataset), batch_size=batch_size)


__all__ = ["default_optimizer", "to_dataloader"]
