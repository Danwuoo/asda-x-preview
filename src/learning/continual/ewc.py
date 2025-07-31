from __future__ import annotations

"""Elastic Weight Consolidation utilities."""

from typing import Dict

import torch


class EWC:
    """Compute Fisher information and penalty for continual learning."""

    def __init__(self, model: torch.nn.Module, dataloader) -> None:
        self.params = {
            n: p.clone().detach()
            for n, p in model.named_parameters()
            if p.requires_grad
        }
        self.fisher = self._compute_fisher(model, dataloader)

    @staticmethod
    def _compute_fisher(model: torch.nn.Module, dataloader) -> Dict[str, torch.Tensor]:
        fisher: Dict[str, torch.Tensor] = {
            n: torch.zeros_like(p)
            for n, p in model.named_parameters()
            if p.requires_grad
        }
        model.eval()
        for batch in dataloader:
            model.zero_grad()
            output = model(**batch)
            loss = output.loss if hasattr(output, "loss") else output[1]
            loss.backward()
            for n, p in model.named_parameters():
                if p.requires_grad and p.grad is not None:
                    fisher[n] += p.grad.detach() ** 2
        for n in fisher:
            fisher[n] /= len(dataloader)
        return fisher

    @classmethod
    def from_saved(cls, model: torch.nn.Module, params: Dict[str, torch.Tensor], fisher: Dict[str, torch.Tensor]) -> "EWC":
        obj = cls.__new__(cls)
        obj.params = {n: p.clone().detach() for n, p in params.items()}
        obj.fisher = {n: f.clone().detach() for n, f in fisher.items()}
        return obj

    def penalty(self, model: torch.nn.Module) -> torch.Tensor:
        loss = torch.zeros(1, device=next(model.parameters()).device)
        for n, p in model.named_parameters():
            if n in self.params:
                loss += torch.sum(self.fisher[n] * (p - self.params[n]) ** 2)
        return loss


__all__ = ["EWC"]
