import os
import sys
from datetime import datetime, timezone

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.replay import ReplayEntry  # noqa: E402
from src.learning.sec import replay_to_sec  # noqa: E402


def test_replay_to_sec():
    replay = ReplayEntry(
        replay_id="r1",
        timestamp=datetime.now(timezone.utc),
        input_event={"event": "x"},
        feedback_signal="lateral_movement",
        replay_label="misclassification",
        version_id="m-7b",
    )

    sec = replay_to_sec(replay)
    assert sec.replay_id == "r1"
    assert "lateral_movement" in sec.instruction
    assert sec.version_context.model == "m-7b"
