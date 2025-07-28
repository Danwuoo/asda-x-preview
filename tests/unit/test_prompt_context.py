from datetime import datetime

import pytest

from src.core.prompt_context import (
    ContextParserFactory,
    InjectionSanitizer,
    PromptComposer,
    PromptContext,
    parse_input_context,
)


def test_log_parser():
    log = {"agent_id": "a1", "time": "2024-01-01T00:00:00", "message": "hello"}
    ctx = ContextParserFactory.parse(log)
    assert ctx.source_type == "log"
    assert ctx.agent_id == "a1"
    assert ctx.context_summary == "hello"


def test_sanitizer_detection():
    sanitizer = InjectionSanitizer()
    with pytest.raises(ValueError):
        sanitizer.check("{{ dangerous }}")
    sanitizer.check("safe text")


def test_prompt_composer():
    ctx = PromptContext(
        source_type="text",
        agent_id="a",
        time=datetime.utcnow(),
        context_summary="hi",
    )
    composer = PromptComposer("Agent {{agent_id}} says {{context_summary}}")
    out = composer.compose(ctx)
    assert "Agent a" in out


def test_parse_input_context():
    data = {"agent_id": "a1", "message": "hello"}
    ctx = parse_input_context(data)
    assert ctx.agent_id == "a1"
    assert "hello" in ctx.context_summary
