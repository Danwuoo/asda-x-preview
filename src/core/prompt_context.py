from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, List, Optional, Literal, Dict

from jinja2 import Template
from langdetect import detect
from pydantic import BaseModel, Field


class EntitySchema(BaseModel):
    """Represents a single entity in the context."""
    type: str = Field(description="Type of the entity (e.g., ip, domain, file_hash)")
    value: Any = Field(description="Value of the entity")
    description: Optional[str] = Field(None, description="Optional description of the entity")


class EventGraphSchema(BaseModel):
    """Represents a graph of related events or entities."""
    nodes: List[EntitySchema] = Field(description="List of nodes (entities) in the graph")
    edges: List[Dict[str, Any]] = Field(description="List of edges (relationships) between nodes")


class STIXEventSchema(BaseModel):
    """Represents data extracted from a STIX object."""
    type: str = Field(description="STIX object type (e.g., indicator, malware, relationship)")
    id: str = Field(description="STIX object ID")
    description: Optional[str] = Field(None, description="Description of the STIX object")
    pattern: Optional[str] = Field(None, description="STIX pattern for indicators")
    valid_from: Optional[datetime] = Field(None, description="The time from which the STIX object is considered valid")


class PromptContext(BaseModel):
    """Normalized context schema for downstream LLM tasks."""

    source_type: Literal["log", "stix", "text", "graph"]
    agent_id: str
    time: datetime
    entities: List[EntitySchema] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    risk_score: Optional[float] = None
    context_summary: str = ""
    graph: Optional[EventGraphSchema] = None
    stix_objects: List[STIXEventSchema] = Field(default_factory=list)


class BaseParser:
    """Base class for parsers."""

    source_type: str

    def parse(self, data: Any) -> PromptContext:
        """Parse input into a PromptContext."""
        raise NotImplementedError


class LogParser(BaseParser):
    source_type = "log"

    # Regex to find common entities in logs
    _ip_regex = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    _user_regex = re.compile(r"\bUser\s'(\w+)'", re.IGNORECASE)
    _id_regex = re.compile(r"\b(id|uuid|request_id)[=:](\S+)\b", re.IGNORECASE)

    def parse(self, data: Any) -> PromptContext:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                # If it's not a JSON string, treat it as a raw log message
                pass

        if isinstance(data, str):
            message = data
            log_dict = {}
        elif isinstance(data, dict):
            message = data.get("message", "")
            log_dict = data
        else:
            raise TypeError("LogParser expects a dict, JSON string, or raw string.")

        time_str = log_dict.get("time") or datetime.utcnow().isoformat()
        time_val = datetime.fromisoformat(time_str)

        entities = []
        if message:
            entities.append(EntitySchema(type="message", value=message))
            # Extract entities from the message using regex
            ips = self._ip_regex.findall(message)
            for ip in ips:
                entities.append(EntitySchema(type="ip", value=ip))
            users = self._user_regex.findall(message)
            for user in users:
                entities.append(EntitySchema(type="user", value=user))
            ids = self._id_regex.findall(message)
            for key, val in ids:
                entities.append(EntitySchema(type=key, value=val))

        return PromptContext(
            source_type=self.source_type,
            agent_id=log_dict.get("agent_id", "unknown"),
            time=time_val,
            entities=entities,
            actions=log_dict.get("actions", []),
            context_summary=message,
        )


from stix2 import parse
class StixParser(BaseParser):
    source_type = "stix"

    def parse(self, data: Any) -> PromptContext:
        bundle = parse(data, allow_custom=True)
        if not hasattr(bundle, "objects"):
            raise TypeError("StixParser expects a STIX bundle")

        stix_objects = []
        entities = []
        for obj in bundle.objects:
            stix_obj = STIXEventSchema(
                type=obj.type,
                id=obj.id,
                description=getattr(obj, 'description', None),
                pattern=getattr(obj, 'pattern', None),
                valid_from=getattr(obj, 'valid_from', None),
            )
            stix_objects.append(stix_obj)
            entities.append(EntitySchema(type=obj.type, value=obj.id))

        summary = f"STIX bundle with {len(bundle.objects)} objects."
        return PromptContext(
            source_type=self.source_type,
            agent_id=bundle.id,
            time=datetime.utcnow(),
            entities=entities,
            stix_objects=stix_objects,
            context_summary=summary,
        )


class GraphParser(BaseParser):
    """Parse graph data into a PromptContext."""
    source_type = "graph"

    def parse(self, data: Any) -> PromptContext:
        if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
            raise TypeError("GraphParser expects a dict with 'nodes' and 'edges'")

        graph_schema = EventGraphSchema(**data)
        summary = f"Graph with {len(graph_schema.nodes)} nodes and {len(graph_schema.edges)} edges."

        return PromptContext(
            source_type=self.source_type,
            agent_id="graph_parser",
            time=datetime.utcnow(),
            entities=graph_schema.nodes,
            context_summary=summary,
            graph=graph_schema,
        )


import spacy

class FreeTextParser(BaseParser):
    source_type = "text"
    _nlp = None
    _ip_regex = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    def __init__(self):
        if FreeTextParser._nlp is None:
            try:
                FreeTextParser._nlp = spacy.load("en_core_web_sm")
            except OSError:
                raise RuntimeError("Spacy 'en_core_web_sm' model not found. Please download it.")

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
        doc = self._nlp(data)
        entities = [EntitySchema(type=ent.label_, value=ent.text) for ent in doc.ents]

        # Add IPs found by regex
        ips = self._ip_regex.findall(data)
        for ip in ips:
            # Avoid duplicating IPs that might be picked up by NER
            if not any(e.value == ip and e.type == "ip" for e in entities):
                 entities.append(EntitySchema(type="ip", value=ip))

        return PromptContext(
            source_type=self.source_type,
            agent_id="unknown",
            time=time_val,
            entities=entities,
            actions=[],
            context_summary=f"{lang}: {data}",
        )


class ContextParserFactory:
    """Detect input format and delegate to specific parser."""

    parsers = {
        "log": LogParser(),
        "stix": StixParser(),
        "text": FreeTextParser(),
        "graph": GraphParser(),
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
                    if "nodes" in obj and "edges" in obj:
                        return cls.parsers["graph"].parse(obj)
                    return cls.parsers["log"].parse(obj)
                except json.JSONDecodeError:
                    pass
            return cls.parsers["text"].parse(data)
        if isinstance(data, dict):
            if "objects" in data:
                return cls.parsers["stix"].parse(data)
            if "nodes" in data and "edges" in data:
                return cls.parsers["graph"].parse(data)
            return cls.parsers["log"].parse(data)
        return cls.parsers["text"].parse(str(data))


def parse_input_context(data: Dict[str, Any] | str) -> PromptContext:
    """Public helper to normalize incoming context payloads."""
    return ContextParserFactory.parse(data)


from jinja2 import Environment, FileSystemLoader
import os

class PromptComposer:
    """Render prompt text from context using templates."""

    def __init__(self, template_dir: str = "src/core/templates") -> None:
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def list_templates(self) -> List[str]:
        """List available templates."""
        return self.env.list_templates()

    def compose(self, template_name: str, context: PromptContext) -> str:
        """
        Composes a prompt using a specified template and context.

        :param template_name: The name of the template file to use.
        :param context: The PromptContext object with data for the template.
        :return: The rendered prompt as a string.
        """
        template = self.env.get_template(template_name)
        return template.render(**context.model_dump())


class InjectionSanitizer:
    """Detects and sanitizes potential prompt injection attacks."""

    # Greatly expanded pattern to detect a wider range of injection techniques
    _pattern = re.compile(
        r"(\{\{.*?\}\})|"  # Jinja2-like templates
        r"(<%.*?%>)|"  # EJS-like templates
        r"(#include.*)|"  # C-style includes
        r"(\b(exec|eval|system|os.system|__import__)\b)|"  # Dangerous functions
        r"(---\s*)|"  # YAML front matter
        r"(<script.*?>)|"  # HTML script tags
        r"(javascript:.*)|"  # Javascript URIs
        r"(\b(on\w+)\s*=)"  # HTML event handlers
    )

    def check(self, text: str, high_sensitivity: bool = True) -> None:
        """
        Checks for suspicious patterns in the input text.
        Raises a ValueError if a potential injection is detected.
        """
        if self._pattern.search(text):
            raise ValueError("Possible prompt injection detected due to suspicious patterns.")

        if high_sensitivity:
            # Check for mixed language scripts, which can be a sign of obfuscation
            try:
                # Use langdetect to find the primary language
                primary_lang = detect(text)
                # A simple check for non-ASCII characters in a predominantly English text
                if primary_lang == 'en' and any(ord(c) > 127 for c in text):
                    # This could be legitimate, but it's worth flagging in high-sensitivity mode
                    # A more advanced version could use a library to check for multiple scripts (e.g., Latin, Cyrillic)
                    pass  # For now, we just pass, but a warning could be logged here.
            except Exception:
                # langdetect can fail on short or ambiguous text
                pass


__all__ = [
    "EntitySchema",
    "EventGraphSchema",
    "STIXEventSchema",
    "PromptContext",
    "ContextParserFactory",
    "parse_input_context",
    "PromptComposer",
    "InjectionSanitizer",
]
