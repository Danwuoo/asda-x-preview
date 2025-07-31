import os
import sys
from datetime import datetime, timezone

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.replay import ReplayEntry  # noqa: E402


def test_drift_tag_preserved():
    entry = ReplayEntry(
        replay_id="d1",
        timestamp=datetime.now(timezone.utc),
        input_event={},
        drift_tag="major",
    )
    assert entry.drift_tag == "major"
