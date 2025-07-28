import os
import sys
import time

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
from fastapi.testclient import TestClient  # noqa: E402
from src.core.orchestrator_api import app  # noqa: E402

client = TestClient(app)


def test_dag_execution_with_api():
    payload = {"task_name": "demo", "input_context": {"message": "ping"}}
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id
    time.sleep(0.1)  # allow background task
    status = client.get(f"/status/{trace_id}")
    assert status.json()["status"] == "completed"
    result = client.get(f"/result/{trace_id}")
    assert result.status_code == 200
    assert "output" in result.json()


def test_replay_execution():
    payload = {"task_name": "demo", "input_context": {"message": "again"}}
    resp = client.post("/run", json=payload)
    trace_id = resp.json()["trace_id"]
    time.sleep(0.1)
    replay = client.get(f"/replay/{trace_id}")
    new_id = replay.json()["trace_id"]
    assert new_id != trace_id
    time.sleep(0.1)
    new_status = client.get(f"/status/{new_id}")
    assert new_status.json()["status"] == "completed"
