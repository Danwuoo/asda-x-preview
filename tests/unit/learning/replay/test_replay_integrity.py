import os
import sys
import tempfile
from datetime import datetime, timezone

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.replay import ReplayEntry, ReplayMemoryManager, ReplaySimulator  # noqa: E402


def test_integrity_persist_decision_trace():
    with tempfile.TemporaryDirectory() as tmp:
        manager = ReplayMemoryManager(os.path.join(tmp, "replay.db"))
        entry = ReplayEntry(
            replay_id="r2",
            timestamp=datetime.now(timezone.utc),
            input_event={},
            parsed_prompt="hello",
            decision_trace={"chain": [1, 2]},
        )
        manager.save_entry(entry)
        loaded = manager.load_entry("r2")
        sim = ReplaySimulator(loaded)
        ctx = sim.build_context()
        assert ctx["prompt"] == "hello"
        assert ctx["decision_trace"] == {"chain": [1, 2]}
