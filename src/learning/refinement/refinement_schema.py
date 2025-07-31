from __future__ import annotations

"""Data schema for self-refinement rounds."""

from pydantic import BaseModel, Field


class RefinementEntry(BaseModel):
    """Record of a single refinement iteration."""

    task_id: str = Field(description="Associated task identifier")
    round: int = Field(description="Refinement round number")
    initial_output: str = Field(description="Original draft output")
    review_comment: str = Field(description="Critic feedback for the draft")
    revised_output: str = Field(
        description="Output rewritten after review",
    )
    improvement_score: float = Field(
        description="Similarity score between drafts",
    )
    final_flag: bool = Field(
        default=False,
        description="Flag if this is the last round",
    )


__all__ = ["RefinementEntry"]
