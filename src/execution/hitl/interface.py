from __future__ import annotations

import os
from typing import Any, Dict, List

import yaml
from jinja2 import Template


class ReviewInterface:
    """Render decision information for human reviewers."""

    def __init__(
        self,
        fields_cfg: str = "configs/hitl/display_fields.yaml",
        template_path: str = "templates/hitl_review_card.jinja2",
    ) -> None:
        if os.path.exists(fields_cfg):
            with open(fields_cfg, "r", encoding="utf-8") as f:
                self.fields: List[str] = yaml.safe_load(f) or []
        else:
            self.fields = []
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                self.template = Template(f.read())
        else:
            self.template = Template("{{ data }}")

    def render(self, decision: Dict[str, Any]) -> str:
        context = {field: decision.get(field) for field in self.fields}
        output = self.template.render(data=context)
        return output


__all__ = ["ReviewInterface"]
