from __future__ import annotations

from typing import Any, Dict

from deepdiff import DeepDiff


class DecisionDiffer:
    """Compare two decision dictionaries."""

    def compare(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        diff = DeepDiff(old or {}, new or {}, verbose_level=2)
        return diff.to_dict()
