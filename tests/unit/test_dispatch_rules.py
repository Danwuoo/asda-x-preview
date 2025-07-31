import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.execution.dispatcher import DispatchRuleEngine  # noqa: E402


def test_rules_map_to_routes():
    engine = DispatchRuleEngine("configs/execution/dispatch_rules.yaml")
    assert engine.decide("low", "block_host", 0.1) == "auto"
    assert engine.decide("medium", "block_host", 0.5) == "hitl"
    assert engine.decide("high", "block_host", 0.95) == "block"
