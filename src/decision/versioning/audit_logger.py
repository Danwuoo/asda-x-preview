from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .version_id import VersionIDGenerator
from .trace_builder import ActionTraceLogger
from .diff_engine import DecisionDiffer
from .store import AuditStoreManager
from .asga_hook import ASGAInterface


@dataclass
class VersionedActionAudit:
    """Main entry for recording versioned decisions."""

    store: AuditStoreManager
    id_gen: VersionIDGenerator = field(default_factory=VersionIDGenerator)
    tracer: ActionTraceLogger = field(default_factory=ActionTraceLogger)
    differ: DecisionDiffer = field(default_factory=DecisionDiffer)
    asga: Optional[ASGAInterface] = None
    last_version: Optional[str] = None

    def record(self, decision: Dict[str, Any]) -> str:
        """Record a decision and return its version id."""
        version_id = self.id_gen.generate(decision)
        diff: Dict[str, Any] = {}
        if self.last_version is not None:
            parent = self.store.load(self.last_version)
            if parent is not None:
                diff = self.differ.compare(parent.get("action_plan"), decision)
        record = {
            "version_id": version_id,
            "parent_version": self.last_version,
            "action_plan": decision,
            "diff_from_parent": diff,
        }
        self.store.save(version_id, record)
        self.tracer.add_version(record)
        if self.asga is not None:
            self.asga.report(record)
        self.last_version = version_id
        return version_id
