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
    payload = {"task_name": "default_asda_flow", "input_context": {"query": "test query"}}
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id

    # Wait for the task to complete
    time.sleep(1)

    status_resp = client.get(f"/status/{trace_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"

    result_resp = client.get(f"/result/{trace_id}")
    assert result_resp.status_code == 200
    result_data = result_resp.json()
    assert result_data["status"] == "completed"
    assert "dag_output" in result_data
    dag_output = result_data["dag_output"]["node_outputs"]
    assert "executor_node" in dag_output
    assert "result" in dag_output["executor_node"]
    assert "Executed" in dag_output["executor_node"]["result"]


def test_replay_execution():
    # First, run a task to create a trace
    payload = {"task_name": "default_asda_flow", "input_context": {"query": "replay test"}}
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id

    # Wait for the original task to complete
    time.sleep(1)

    # Get the result of the original run
    original_result_resp = client.get(f"/result/{trace_id}")
    original_result_data = original_result_resp.json()
    original_output = original_result_data["dag_output"]

    # Now, replay the trace
    replay_resp = client.get(f"/replay/{trace_id}")
    assert replay_resp.status_code == 200
    replay_trace_id = replay_resp.json()["trace_id"]
    assert replay_trace_id != trace_id

    # Wait for the replay task to complete
    time.sleep(1)

    # Check the status of the replayed task
    replay_result_resp = client.get(f"/result/{replay_trace_id}")
    replay_result_data = replay_result_resp.json()
    assert replay_result_data["status"] == "completed"
    replay_output = replay_result_data["dag_output"]

    # Compare the outputs
    assert original_output == replay_output
