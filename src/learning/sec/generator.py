from __future__ import annotations

"""Convert replay traces into SEC micro tasks."""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from src.learning.replay import ReplayEntry

from .sec_schema import SECTask, VersionContext
from .templates import render_template


CATEGORY_MAP = {
    "misclassification": "intrusion_categorization",
    "prompt_injection": "input_sanitation",
}


def _choose_category(replay: ReplayEntry) -> str:
    """Select task category based on replay label."""
    label = (replay.replay_label or "").lower()
    return CATEGORY_MAP.get(label, "intrusion_categorization")


def replay_to_sec(replay: ReplayEntry) -> SECTask:
    """Generate a :class:`SECTask` from a :class:`ReplayEntry`."""
    category = _choose_category(replay)
    template_context: Dict[str, Any] = {
        "attack_type": replay.feedback_signal or "unknown",
        "input": replay.input_event,
    }
    instruction = render_template(category, template_context)
    task_id = f"SEC-{datetime.utcnow().year}-{uuid4().hex[:6]}"

    version_ctx = VersionContext(
        model=replay.version_id or "unknown",
        decision_hash=replay.replay_id,
    )

    return SECTask(
        task_id=task_id,
        replay_id=replay.replay_id,
        category=category,
        instruction=instruction,
        input=replay.input_event,
        expected_output=replay.feedback_signal or "",
        feedback=replay.replay_label,
        version_context=version_ctx,
        tags=["generated_from:replay"],
        difficulty="medium",
    )


__all__ = ["replay_to_sec"]
