from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class PromptType(str, Enum):
    """Supported categories of prompts."""

    TASK = "task"
    CRITIQUE = "critique"
    REFINE = "refine"
    INJECTION_TEST = "injection_test"
    REPLAY = "replay"


class PromptMetadata(BaseModel):
    """Metadata associated with a prompt."""

    source: Literal["replay", "dag", "test", "manual"]
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    model_version: Optional[str] = None
    user_tag: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class PromptInput(BaseModel):
    """Standardized prompt input schema."""

    prompt_text: str
    prompt_type: PromptType = PromptType.TASK
    metadata: PromptMetadata
    temperature: float = 0.7
    max_tokens: int = 1024
    system_prompt: Optional[str] = None
    context_ids: Optional[List[str]] = None

    model_config = ConfigDict(extra="allow", use_enum_values=True)


class PromptOutput(BaseModel):
    """Standardized structure for model outputs."""

    output_text: str
    output_type: Literal["text", "json", "code"] = "text"
    score: Optional[float] = None
    feedback: Optional[str] = None
    tokens_used: Optional[int] = None
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(use_enum_values=True)


class RefinementContext(BaseModel):
    """Track refinement related fields for self-refine tasks."""

    draft_output: Optional[str] = None
    critique: Optional[str] = None
    refined_output: Optional[str] = None
    iteration: Optional[int] = None


class PromptTrace(BaseModel):
    """Record of a prompt and its resulting output."""

    input: PromptInput
    output: PromptOutput
    metadata: PromptMetadata
    model_version: Optional[str] = None
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    runtime_ms: Optional[float] = None
    refinement: Optional[RefinementContext] = None

    model_config = ConfigDict(use_enum_values=True)


__all__ = [
    "PromptType",
    "PromptMetadata",
    "PromptInput",
    "PromptOutput",
    "RefinementContext",
    "PromptTrace",
]
