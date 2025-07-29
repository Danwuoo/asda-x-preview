import os
import sys
from datetime import datetime

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))  # noqa: E402
sys.path.insert(0, PROJECT_ROOT)  # noqa: E402
from src.inference.prompt_schema import (  # noqa: E402
    PromptInput,
    PromptOutput,
    PromptType,
    PromptMetadata,
    PromptTrace,
)


def test_prompt_input_defaults():
    meta = PromptMetadata(source="manual")
    prompt = PromptInput(
        prompt_text="hello",
        metadata=meta,
        prompt_type=PromptType.TASK,
    )
    assert prompt.temperature == 0.7
    assert prompt.max_tokens == 1024
    assert prompt.metadata.source == "manual"


def test_prompt_output_schema():
    out = PromptOutput(output_text="hi", output_type="text")
    assert out.output_text == "hi"
    assert isinstance(out.generated_at, datetime)


def test_prompt_trace_composition():
    meta = PromptMetadata(source="test", task_id="t1")
    inp = PromptInput(
        prompt_text="hi",
        metadata=meta,
        prompt_type=PromptType.TASK,
    )
    out = PromptOutput(output_text="ok", output_type="text")
    trace = PromptTrace(input=inp, output=out, metadata=meta)
    assert trace.input.prompt_text == "hi"
    assert trace.output.output_text == "ok"
