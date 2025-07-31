from __future__ import annotations

import json
import os
from typing import Dict


class ConsistencyReporter:
    """Persist CIT results to a JSONL file."""

    def __init__(self, path: str) -> None:
        self.path = path

    def report(self, data: Dict) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
