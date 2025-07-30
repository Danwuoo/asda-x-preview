from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field


class LLMOutputSchema(BaseModel):
    """Standard output from :class:`LLMAgentExecutor`."""

    action_plan: Dict[str, Any] = Field(default_factory=dict)
    llm_output: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


__all__ = ["LLMOutputSchema"]
