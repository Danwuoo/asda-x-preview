from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class AuditStoreManager:
    """Persist versioned records as JSON files."""

    def __init__(self, root: str = "storage/versioned_decisions") -> None:
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def _path(self, version_id: str) -> str:
        return os.path.join(self.root, f"{version_id}.json")

    def save(self, version_id: str, record: Dict[str, Any]) -> None:
        with open(self._path(version_id), "w", encoding="utf-8") as f:
            json.dump(record, f)

    def load(self, version_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(version_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
