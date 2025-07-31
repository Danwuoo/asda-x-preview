import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.execution.dispatcher import ActionDispatcher
from src.execution.dispatcher.logger import DispatchAuditLogger


def test_auto_execution_path(tmp_path):
    log_file = tmp_path / "dispatch.jsonl"
    dispatcher = ActionDispatcher(logger=DispatchAuditLogger(str(log_file)))
    record = dispatcher.dispatch(
        decision_id="v2",
        action_plan={"type": "echo", "msg": "hi"},
        risk_level="low",
        action_type="echo",
        confidence=0.8,
        trace_id="t2",
    )
    assert record.executed is True
    assert log_file.exists()
