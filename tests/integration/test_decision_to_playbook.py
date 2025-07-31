import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.decision.soar import SOARGenerator  # noqa: E402


def test_full_flow():
    decision = {
        "name": "isolate-host-1",
        "actions": [{"name": "iso", "ref": "net.block"}],
        "parameters": {"target_ip": "1.1.1.1"},
    }
    gen = SOARGenerator()
    pb = gen.generate(decision, template="stackstorm.yaml.j2")
    assert pb["actions"][0]["ref"] == "net.block"
