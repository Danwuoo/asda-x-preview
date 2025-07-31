from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


class PlaybookBuilder:
    """Render playbook templates into dictionaries."""

    def __init__(
        self, platform: str = "stackstorm", template_dir: str | None = None
    ) -> None:
        self.platform = platform
        self.template_dir = Path(template_dir or "configs/soar/templates")
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape()
        )

    def build(
        self, template_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        template = self.env.get_template(template_name)
        rendered = template.render(**context)
        return yaml.safe_load(rendered)
