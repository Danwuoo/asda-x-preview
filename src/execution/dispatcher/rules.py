from __future__ import annotations

import os
import yaml


class DispatchRuleEngine:
    """Apply YAML-defined rules to decide dispatch routes."""

    def __init__(
        self, rule_path: str = "configs/execution/dispatch_rules.yaml"
    ) -> None:
        if os.path.exists(rule_path):
            with open(rule_path, "r", encoding="utf-8") as f:
                self.rules = yaml.safe_load(f) or {}
        else:
            self.rules = {}

    def decide(
        self, risk_level: str, action_type: str, confidence: float
    ) -> str:
        level_rules = self.rules.get(risk_level, {})
        return level_rules.get(
            action_type, level_rules.get("default", "hitl")
        )


__all__ = ["DispatchRuleEngine"]
