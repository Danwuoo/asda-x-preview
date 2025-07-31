import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.sec import SECTask, VersionContext  # noqa: E402


def test_schema_instantiation():
    version = VersionContext(model="m1", decision_hash="abc")
    task = SECTask(
        task_id="SEC-1",
        replay_id="r1",
        category="intrusion_categorization",
        instruction="instr",
        input={"k": "v"},
        expected_output="ans",
        feedback="label",
        version_context=version,
        tags=["t"],
        difficulty="easy",
    )
    assert task.task_id == "SEC-1"
    assert task.version_context.model == "m1"
