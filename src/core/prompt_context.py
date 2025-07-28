from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, List, Optional, Literal, Dict

from jinja2 import Template
from langdetect import detect
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Simple entity extracted from inputs."""

    type: str
    value: str


class PromptContext(BaseModel):
    """Normalized context schema for downstream LLM tasks."""

    source_type: Literal["log", "stix", "text", "graph"]
    agent_id: str
    time: datetime
    entities: List[Entity] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    risk_score: Optional[float] = None
    context_summary: str = ""


class BaseParser:
    """Base class for parsers."""

    source_type: str

    def parse(self, data: Any) -> PromptContext:
        """Parse input into a PromptContext."""
        raise NotImplementedError


class LogParser(BaseParser):
    source_type = "log"

    def parse(self, data: Any) -> PromptContext:
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict):
            raise TypeError("LogParser expects dict or JSON string")

        time_str = data.get("time") or datetime.utcnow().isoformat()
        return PromptContext(
            source_type=self.source_type,
            agent_id=data.get("agent_id", "unknown"),
            time=datetime.fromisoformat(time_str),
            entities=[Entity(type="message", value=data.get("message", ""))],
            actions=data.get("actions", []),
            context_summary=data.get("message", ""),
        )


class StixParser(BaseParser):
    source_type = "stix"

    def parse(self, data: Any) -> PromptContext:
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict) or "objects" not in data:
            raise TypeError("StixParser expects STIX bundle dict")

        objects = data.get("objects", [])
        entities = [
            Entity(type=obj.get("type", "object"), value=obj.get("id", ""))
            for obj in objects
        ]
        summary = ", ".join(obj.get("type", "") for obj in objects)
        return PromptContext(
            source_type=self.source_type,
            agent_id=data.get("id", "unknown"),
            time=datetime.utcnow(),
            entities=entities,
            actions=[],
            context_summary=summary,
        )


class FreeTextParser(BaseParser):
    source_type = "text"

    _time_regex = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")

    def parse(self, data: Any) -> PromptContext:
        if not isinstance(data, str):
            data = str(data)
        match = self._time_regex.search(data)
        if match:
            time_val = datetime.fromisoformat(match.group(1))
        else:
            time_val = datetime.utcnow()

        lang = detect(data)
        return PromptContext(
            source_type=self.source_type,
            agent_id="unknown",
            time=time_val,
            entities=[],
            actions=[],
            context_summary=f"{lang}: {data}",
        )


class ContextParserFactory:
    """Detect input format and delegate to specific parser."""

    parsers = {
        "log": LogParser(),
        "stix": StixParser(),
        "text": FreeTextParser(),
    }

    @classmethod
    def parse(cls, data: Any) -> PromptContext:
        if isinstance(data, str):
            stripped = data.strip()
            if stripped.startswith("{"):
                try:
                    obj = json.loads(stripped)
                    if "objects" in obj:
                        return cls.parsers["stix"].parse(obj)
                    return cls.parsers["log"].parse(obj)
                except json.JSONDecodeError:
                    pass
            return cls.parsers["text"].parse(data)
        if isinstance(data, dict):
            if "objects" in data:
                return cls.parsers["stix"].parse(data)
            return cls.parsers["log"].parse(data)
        return cls.parsers["text"].parse(str(data))


def parse_input_context(data: Dict[str, Any] | str) -> PromptContext:
    """Public helper to normalize incoming context payloads."""
    return ContextParserFactory.parse(data)


class PromptComposer:
    """Render prompt text from context using templates."""

    def __init__(self, template: str) -> None:
        self.template = Template(template)

    def compose(self, context: PromptContext) -> str:
        return self.template.render(**context.dict())


class InjectionSanitizer:
    """Basic prompt injection detector."""

    _pattern = re.compile(r"(\{\{|#include|---)")

    def check(self, text: str) -> None:
        if self._pattern.search(text):
            raise ValueError("Possible prompt injection detected")


__all__ = [
    "Entity",
    "PromptContext",
    "ContextParserFactory",
    "parse_input_context",
    "PromptComposer",
    "InjectionSanitizer",
]
