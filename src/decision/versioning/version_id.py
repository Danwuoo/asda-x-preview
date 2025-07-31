from __future__ import annotations

import uuid
from hashlib import sha256
from typing import Any, Dict


class VersionIDGenerator:
    """Generate deterministic version ids from decision content."""

    def generate(self, decision: Dict[str, Any]) -> str:
        """Return a unique version id string."""
        content = str(sorted(decision.items())).encode("utf-8")
        checksum = sha256(content).hexdigest()[:8]
        return f"v{uuid.uuid4().hex[:8]}-{checksum}"
