from __future__ import annotations

"""Data schema for replay records."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReplayEntry(BaseModel):
    """Structured record capturing a single decision episode."""

    replay_id: str = Field(description="Globally unique ID for this replay entry")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the decision occurred",
    )
    input_event: Dict[str, Any] = Field(description="Original event data")
    parsed_prompt: Optional[str] = Field(default=None, description="Normalized prompt")
    retrieved_knowledge: Optional[List[str]] = Field(
        default=None, description="RAG chunk identifiers or content"
    )
    decision_trace: Optional[Dict[str, Any]] = Field(
        default=None, description="DAG of the reasoning process"
    )
    action_output: Optional[Dict[str, Any]] = Field(
        default=None, description="Action taken or suggestion produced"
    )
    feedback_signal: Optional[str] = Field(
        default=None, description="Environment feedback after execution"
    )
    version_id: Optional[str] = Field(
        default=None, description="Model or strategy version used"
    )
    drift_tag: Optional[str] = Field(default=None, description="Semantic drift tag")
    replay_label: Optional[str] = Field(
        default=None, description="User or system classification of this replay"
    )


__all__ = ["ReplayEntry"]
