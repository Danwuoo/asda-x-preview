import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.execution.dispatcher import ActionDispatcher  # noqa: E402


def test_high_risk_triggers_block():
    dispatcher = ActionDispatcher()
    record = dispatcher.dispatch(
        decision_id="v1",
        action_plan={"type": "block_host", "target": "1.1.1.1"},
        risk_level="high",
        action_type="block_host",
        confidence=0.99,
        trace_id="t1",
    )
    assert record.dispatch_route == "BLOCK"
