from __future__ import annotations

"""Data schema for SEC micro tasks."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VersionContext(BaseModel):
    """Model and decision version identifiers."""

    model: str = Field(description="Model identifier used")
    decision_hash: str = Field(description="Hash of the decision trace")


class SECTask(BaseModel):
    """Structured record capturing a single SEC training task."""

    task_id: str = Field(
        description="Globally unique task identifier",
    )
    replay_id: str = Field(
        description="Replay entry this task originated from",
    )
    category: str = Field(description="Training task category")
    instruction: str = Field(description="Instruction text for the model")
    input: Dict[str, Any] | str = Field(
        description="Input payload for the task",
    )
    expected_output: str = Field(description="Expected model answer")
    feedback: Optional[str] = Field(
        default=None,
        description="Replay feedback",
    )
    version_context: VersionContext = Field(description="Version metadata")
    tags: List[str] = Field(
        default_factory=list,
        description="Auxiliary labels",
    )
    difficulty: str = Field(
        default="medium",
        description="Relative task difficulty",
    )


__all__ = ["SECTask", "VersionContext"]
