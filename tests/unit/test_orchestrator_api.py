from fastapi.testclient import TestClient

from src.core.orchestrator_api import app

client = TestClient(app)


def test_test_endpoint():
    resp = client.post("/test", json={"hello": "world"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["echo"] == {"hello": "world"}
    assert data["status"] == "ok"


import time


def test_run_status_and_result():
    payload = {
        "task_name": "default_asda_flow",
        "input_context": {"raw_event": "ping"},
        "replay_mode": False,
        "execution_params": {},
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id

    # Wait for the task to complete
    time.sleep(1)

    status_resp = client.get(f"/status/{trace_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["trace_id"] == trace_id
    assert status_data["status"] == "completed"

    result_resp = client.get(f"/result/{trace_id}")
    assert result_resp.status_code == 200
    result_data = result_resp.json()
    assert result_data["trace_id"] == trace_id
    assert result_data["status"] == "completed"
    assert result_data["dag_output"] is not None


def test_get_nodes():
    resp = client.get("/nodes")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert isinstance(data["nodes"], list)


def test_replay():
    # First, run a task to create a trace
    payload = {
        "task_name": "default_asda_flow",
        "input_context": {"raw_event": "replay test"},
        "replay_mode": False,
        "execution_params": {},
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id

    # Wait for the original task to complete
    time.sleep(1)

    # Now, replay the trace
    replay_resp = client.get(f"/replay/{trace_id}")
    assert replay_resp.status_code == 200
    replay_trace_id = replay_resp.json()["trace_id"]
    assert replay_trace_id != trace_id

    # Wait for the replay task to complete
    time.sleep(1)

    # Check the status of the replayed task
    status_resp = client.get(f"/status/{replay_trace_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "completed"


def test_task_failure():
    payload = {
        "task_name": "non_existent_dag",
        "input_context": {"raw_event": "failure test"},
        "replay_mode": False,
        "execution_params": {},
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id

    # Wait for the task to fail
    time.sleep(1)

    status_resp = client.get(f"/status/{trace_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "failed"
    assert "not found" in status_data["error"]


def test_unknown_trace_id():
    resp = client.get("/status/unknown-trace-id")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unknown"
