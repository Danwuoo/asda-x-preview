import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.decision.soar import SOARGenerator  # noqa: E402


def test_generate_stackstorm_playbook(tmp_path):
    decision = {
        "name": "isolate-host-10-1-2-3",
        "actions": [
            {"name": "isolate_host", "ref": "network.firewall.block"}
        ],
        "parameters": {"target_ip": "10.1.2.3", "duration": 1800},
    }
    gen = SOARGenerator(platform="stackstorm")
    playbook = gen.generate(decision, template="stackstorm.yaml.j2")
    assert playbook["name"] == decision["name"]
    assert playbook["actions"][0]["name"] == "isolate_host"
    assert playbook["metadata"]["generated_by"] == "asda-x-agent"
    assert "version" in playbook["metadata"]
