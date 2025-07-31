from __future__ import annotations


class RiskTriggerRouter:
    """Decide follow-up action based on drift score."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def handle(self, drift_score: float) -> str:
        if drift_score > self.threshold:
            return "refine_and_retry"
        return "accept"
