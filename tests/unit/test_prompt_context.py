from datetime import datetime
import pytest
import os
from src.core.prompt_context import (
    ContextParserFactory,
    InjectionSanitizer,
    PromptComposer,
    PromptContext,
    parse_input_context,
    EntitySchema,
    EventGraphSchema,
)

def test_log_parser():
    log = {"agent_id": "a1", "time": "2024-01-01T00:00:00", "message": "hello"}
    ctx = ContextParserFactory.parse(log)
    assert ctx.source_type == "log"
    assert ctx.agent_id == "a1"
    assert ctx.context_summary == "hello"
    assert ctx.entities[0].value == "hello"

import uuid

def test_stix_parser():
    bundle_id = f"bundle--{uuid.uuid4()}"
    indicator_id = f"indicator--{uuid.uuid4()}"
    stix_bundle = {
        "type": "bundle",
        "id": bundle_id,
        "objects": [
            {
                "type": "indicator",
                "id": indicator_id,
                "spec_version": "2.1",
                "pattern_type": "stix",
                "pattern": "[file:hashes.'MD5' = 'd41d8cd98f00b204e9800998ecf8427e']"
            }
        ]
    }
    ctx = ContextParserFactory.parse(stix_bundle)
    assert ctx.source_type == "stix"
    assert ctx.agent_id == bundle_id
    assert len(ctx.stix_objects) == 1
    assert ctx.stix_objects[0].id == indicator_id

def test_graph_parser():
    graph_data = {
        "nodes": [{"type": "ip", "value": "1.2.3.4"}],
        "edges": []
    }
    ctx = ContextParserFactory.parse(graph_data)
    assert ctx.source_type == "graph"
    assert ctx.graph is not None
    assert len(ctx.graph.nodes) == 1
    assert ctx.graph.nodes[0].type == "ip"

def test_free_text_parser_with_ner():
    text = "There was an attack from 1.2.3.4 on 2024-01-01T12:00:00."
    ctx = ContextParserFactory.parse(text)
    assert ctx.source_type == "text"
    assert any(entity.type == 'DATE' for entity in ctx.entities)
    assert any(entity.value == '1.2.3.4' for entity in ctx.entities)

def test_sanitizer_detection():
    sanitizer = InjectionSanitizer()
    with pytest.raises(ValueError, match="Possible prompt injection detected"):
        sanitizer.check("{{ dangerous }}")
    with pytest.raises(ValueError, match="Possible prompt injection detected"):
        sanitizer.check("<% dangerous %>")
    with pytest.raises(ValueError, match="Possible prompt injection detected"):
        sanitizer.check("exec(something)")
    sanitizer.check("This is a safe text.")

def test_prompt_composer_from_file():
    # Create a dummy template for testing
    template_dir = "tests/unit/templates"
    os.makedirs(template_dir, exist_ok=True)
    with open(os.path.join(template_dir, "test.jinja"), "w") as f:
        f.write("Agent {{agent_id}} says {{context_summary}}")

    composer = PromptComposer(template_dir=template_dir)
    ctx = PromptContext(
        source_type="text",
        agent_id="test_agent",
        time=datetime.utcnow(),
        context_summary="hello from test"
    )

    output = composer.compose("test.jinja", ctx)
    assert "Agent test_agent says hello from test" in output

    # Clean up the dummy template
    os.remove(os.path.join(template_dir, "test.jinja"))
    os.rmdir(template_dir)

def test_parse_input_context():
    data = {"agent_id": "a1", "message": "hello"}
    ctx = parse_input_context(data)
    assert ctx.agent_id == "a1"
    assert "hello" in ctx.context_summary
