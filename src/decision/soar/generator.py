from __future__ import annotations

from typing import Any, Dict

from .builder import PlaybookBuilder
from .mapper import ActionParameterMapper
from .validator import OutputValidator
from .versioning import VersionTagger


class SOARGenerator:
    """Convert semantic decisions into SOAR playbooks."""

    def __init__(self, platform: str = "stackstorm") -> None:
        self.platform = platform
        self.builder = PlaybookBuilder(platform)
        self.mapper = ActionParameterMapper()
        self.validator = OutputValidator()
        self.versioner = VersionTagger()

    def generate(
        self, decision: Dict[str, Any], template: str
    ) -> Dict[str, Any]:
        params = self.mapper.map_parameters(decision)
        context = {
            "name": decision.get("name", "generated-playbook"),
            "actions": decision.get("actions", []),
            "parameters": params,
        }
        playbook = self.builder.build(template, context)
        self.validator.validate(playbook)
        return self.versioner.tag(playbook)
