import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.refinement.refinement_schema import (  # noqa: E402
    RefinementEntry,
)


def test_refinement_entry_serialization():
    entry = RefinementEntry(
        task_id="t",
        round=1,
        initial_output="d1",
        review_comment="good",
        revised_output="d2",
        improvement_score=0.5,
        final_flag=True,
    )
    data = entry.model_dump()
    assert data["task_id"] == "t"
    assert data["final_flag"] is True
