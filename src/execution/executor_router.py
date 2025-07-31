from __future__ import annotations

from typing import Any, Dict

from .dispatcher import ActionDispatcher, DispatchRecord


def route_action(
    decision_id: str,
    action_plan: Dict[str, Any],
    risk_level: str,
    action_type: str,
    confidence: float,
    trace_id: str,
) -> DispatchRecord:
    dispatcher = ActionDispatcher()
    return dispatcher.dispatch(
        decision_id,
        action_plan,
        risk_level,
        action_type,
        confidence,
        trace_id,
    )


__all__ = ["route_action", "ActionDispatcher", "DispatchRecord"]
