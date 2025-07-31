from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from .rules import DispatchRuleEngine
from .auto_trigger import AutoExecutionTrigger
from .hitl_router import HITLRouter
from .interlock import EmergencyInterlock
from .logger import DispatchAuditLogger, DispatchRecord


class ActionDispatcher:
    """Route actions to execution paths based on risk and policy."""

    def __init__(
        self,
        rule_engine: DispatchRuleEngine | None = None,
        auto_trigger: AutoExecutionTrigger | None = None,
        hitl_router: HITLRouter | None = None,
        interlock: EmergencyInterlock | None = None,
        logger: DispatchAuditLogger | None = None,
    ) -> None:
        self.rule_engine = rule_engine or DispatchRuleEngine()
        self.auto_trigger = auto_trigger or AutoExecutionTrigger()
        self.hitl_router = hitl_router or HITLRouter()
        self.interlock = interlock or EmergencyInterlock()
        self.logger = logger or DispatchAuditLogger()

    def dispatch(
        self,
        decision_id: str,
        action_plan: Dict[str, Any],
        risk_level: str,
        action_type: str,
        confidence: float,
        trace_id: str,
    ) -> DispatchRecord:
        """Dispatch an action plan based on rules and risk."""

        route = self.rule_engine.decide(risk_level, action_type, confidence)
        executed = False
        rationale = ""

        if route == "auto":
            self.auto_trigger.execute(action_plan)
            executed = True
        elif route == "hitl":
            self.hitl_router.send(action_plan)
        elif route == "block":
            self.interlock.block(action_plan)
            rationale = "Blocked due to high risk"

        record = DispatchRecord(
            decision_id=decision_id,
            action_plan=action_plan,
            risk_level=risk_level,
            dispatch_route=route.upper(),
            executed=executed,
            rationale=rationale,
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
        )
        self.logger.log(record)
        return record


__all__ = ["ActionDispatcher"]
