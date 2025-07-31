from __future__ import annotations

from typing import Any, Dict

try:
    from jsonschema import Draft7Validator, ValidationError
except Exception:  # pragma: no cover - optional dependency
    class Draft7Validator:  # type: ignore
        def __init__(self, schema):
            pass

        def iter_errors(self, data):
            return []

    class ValidationError(Exception):
        pass


BASIC_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "actions": {"type": "array"},
    },
    "required": ["name", "actions"],
}


class OutputValidator:
    """Validate generated playbooks."""

    def __init__(self, schema: Dict[str, Any] | None = None) -> None:
        self.schema = schema or BASIC_SCHEMA
        self.validator = Draft7Validator(self.schema)

    def validate(self, playbook: Dict[str, Any]) -> None:
        errors = sorted(
            self.validator.iter_errors(playbook), key=lambda e: e.path
        )
        if errors:
            raise ValidationError(errors[0])
