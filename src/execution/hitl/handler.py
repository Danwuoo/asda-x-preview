from __future__ import annotations

import os
from typing import Any, Dict

import yaml


class ReviewActionHandler:
    """Select an action based on risk level."""

    def __init__(
        self, mapping_path: str = "configs/hitl/risk_action_map.yaml"
    ) -> None:
        if os.path.exists(mapping_path):
            with open(mapping_path, "r", encoding="utf-8") as f:
                self.mapping: Dict[str, str] = yaml.safe_load(f) or {}
        else:
            self.mapping = {}

    def handle(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        risk = decision.get("risk_level", "medium")
        action = self.mapping.get(risk, "retry")
        return {"review_action": action}


__all__ = ["ReviewActionHandler"]
