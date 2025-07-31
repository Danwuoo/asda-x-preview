from __future__ import annotations

from typing import Any, Dict


class ASGAInterface:
    """Placeholder interface to governance subsystem."""

    def report(self, record: Dict[str, Any]) -> None:  # pragma: no cover
        # In real usage this would send the record to the governance system
        pass
