import os
import sys
import tempfile
from datetime import datetime, timezone

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.replay import ReplayEntry, ReplayMemoryManager  # noqa: E402


def test_save_and_load_entry():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "replay.db")
        manager = ReplayMemoryManager(db)
        entry = ReplayEntry(
            replay_id="r1",
            timestamp=datetime.now(timezone.utc),
            input_event={"a": 1},
            replay_label="TP",
        )
        manager.save_entry(entry)
        loaded = manager.load_entry("r1")
        assert loaded.replay_id == "r1"
        assert loaded.input_event == {"a": 1}


def test_query_by_label():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "replay.db")
        manager = ReplayMemoryManager(db)
        e1 = ReplayEntry(replay_id="1", timestamp=datetime.now(timezone.utc), input_event={}, replay_label="TP")
        e2 = ReplayEntry(replay_id="2", timestamp=datetime.now(timezone.utc), input_event={}, replay_label="FP")
        manager.save_entry(e1)
        manager.save_entry(e2)
        results = manager.query_entries(replay_label="TP")
        assert len(results) == 1
        assert results[0].replay_id == "1"
