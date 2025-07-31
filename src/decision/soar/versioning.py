from __future__ import annotations

import uuid
from hashlib import sha256
from typing import Any, Dict


class VersionTagger:
    """Add version metadata to playbooks."""

    def tag(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        version = uuid.uuid4().hex
        pb_bytes = str(playbook).encode("utf-8")
        checksum = sha256(pb_bytes).hexdigest()
        playbook.setdefault("metadata", {})
        playbook["metadata"].update({"version": version, "checksum": checksum})
        return playbook
