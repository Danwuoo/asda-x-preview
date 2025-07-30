import os
import sys
from contextlib import contextmanager
import types

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))  # noqa: E402
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

from src.decision import (  # noqa: E402
    ExecutionContext,
    LLMAgentExecutor,
    PromptBuilder,
    LLMInferenceEngine,
    RefinementLoop,
)
from src.decision.output_schema import LLMOutputSchema  # noqa: E402
from src.inference.llm_agent import (  # noqa: E402
    LLMAgent,
    LLMModelRegistry,
    PromptInput,
    PromptOutput,
)

# Patch trace logging like other tests
from src.core import global_logger as gl  # noqa: E402
from src.core import trace_logger as tl  # noqa: E402


class DummyLogger:
    def __init__(self) -> None:
        self.events = []

    def log_event(self, event) -> None:
        self.events.append(event)


@contextmanager
def log_node_execution(
    logger,
    node_name,
    version,
    governance_tags=None,
    input_hash=None,
):
    event = types.SimpleNamespace(
        node_name=node_name,
        version=version,
        output_hash=None,
    )
    try:
        yield event
    finally:
        logger.log_event(event)


@pytest.fixture(autouse=True)
def _patch_loggers(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(gl, "trace_logger", dummy)
    monkeypatch.setattr(tl, "log_node_execution", log_node_execution)
    yield


class DummyModel:
    def __init__(self, reply: str) -> None:
        self.model_id = "dummy"
        self.reply = reply

    async def generate(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        return PromptOutput(text=self.reply, model_id=self.model_id)


@pytest.mark.asyncio
async def test_basic_execution():
    registry = LLMModelRegistry()
    registry.register("d", DummyModel('{"type": "noop"}'))
    agent = LLMAgent(registry, default_model_id="d")

    builder = PromptBuilder()
    engine = LLMInferenceEngine(agent)
    executor = LLMAgentExecutor(builder, engine, version_id="v1")

    context = ExecutionContext(task_context={"a": 1}, session_id="s")
    output = await executor.execute(context)
    assert isinstance(output, LLMOutputSchema)
    assert output.action_plan["type"] == "noop"
    assert output.metadata["version_id"] == "v1"


@pytest.mark.asyncio
async def test_refinement_limit(monkeypatch):
    registry = LLMModelRegistry()
    registry.register("d", DummyModel("final"))
    agent = LLMAgent(registry, default_model_id="d")

    builder = PromptBuilder()
    engine = LLMInferenceEngine(agent)
    loop = RefinementLoop()

    async def fake_refine(prompt: str):
        return "refined", 1

    monkeypatch.setattr(loop, "refine", fake_refine)
    executor = LLMAgentExecutor(builder, engine, refine_loop=loop)

    context = ExecutionContext(task_context={}, session_id="s")
    output = await executor.execute(context)
    assert output.metadata["refinement_rounds"] == 1
