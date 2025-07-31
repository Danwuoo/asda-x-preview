"""Continual learning utilities including EWC support."""

from .ewc import EWC
from .task_registry import TaskRegistry
from .learner import train_task

__all__ = ["EWC", "TaskRegistry", "train_task"]
