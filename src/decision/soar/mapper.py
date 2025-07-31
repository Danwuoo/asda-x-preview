from __future__ import annotations

from typing import Any, Dict


class ActionParameterMapper:
    """Map decision data to playbook parameters."""

    def map_parameters(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        # In a real implementation this would be more complex
        return decision.get("parameters", {})
