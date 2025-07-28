from fastapi.testclient import TestClient

from src.core.orchestrator_api import app

client = TestClient(app)


def test_test_endpoint():
    resp = client.post("/test", json={"hello": "world"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["echo"] == {"hello": "world"}
    assert data["status"] == "ok"


def test_run_and_status():
    payload = {
        "task_name": "demo",
        "input_context": {"raw_event": "ping"},
        "replay_mode": False,
        "execution_params": {},
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert trace_id
    status = client.get(f"/status/{trace_id}")
    assert status.status_code == 200
    assert status.json()["trace_id"] == trace_id
