from __future__ import annotations

import json
from typing import Any, Dict


class PromptBuilder:
    """Construct prompts from task context."""

    def __init__(self, template: str | None = None) -> None:
        self.template = template or "Task context:\n{context}"

    def build(self, task_context: Dict[str, Any]) -> str:
        context = json.dumps(task_context, ensure_ascii=False)
        return self.template.format(context=context)


__all__ = ["PromptBuilder"]
