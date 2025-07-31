import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.execution.hitl import HITLConsole  # noqa: E402


def test_console_records_action():
    console = HITLConsole()
    decision = {"trace_id": "t1", "risk_level": "low"}
    result = console.review(decision)
    assert result["review_action"] == "allow"
    assert console.recorder.records[0]["trace_id"] == "t1"
