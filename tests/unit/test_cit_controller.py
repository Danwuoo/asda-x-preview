import os
import sys
import types
from contextlib import contextmanager

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))  # noqa: E402
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

from src.inference.cit_controller import (
    CITController,
    CITConfig,
    compute_similarity,
)  # noqa: E402
from src.inference.llm_agent import (
    LLMAgent,
    LLMModelRegistry,
    PromptInput,
    PromptOutput,
)  # noqa: E402

from src.core import global_logger as gl  # noqa: E402
from src.core import trace_logger as tl  # noqa: E402


class DummyLogger:
    def __init__(self) -> None:
        self.events = []

    def log_event(self, event) -> None:
        self.events.append(event)


@contextmanager
def log_node_execution(logger, node_name, version, governance_tags=None, input_hash=None):
    event = types.SimpleNamespace(node_name=node_name, version=version, output_hash=None)
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

    async def generate(self, prompt: PromptInput, stream: bool = False) -> PromptOutput:
        return PromptOutput(text=self.reply, model_id=self.model_id)


@pytest.mark.asyncio
async def test_cit_controller_pass(monkeypatch):
    registry = LLMModelRegistry()
    registry.register("d", DummyModel("same"))
    agent = LLMAgent(registry, default_model_id="d")
    controller = CITController(agent, CITConfig(metric="jaccard", threshold=0.5))

    logged = []
    monkeypatch.setattr(
        "src.inference.cit_controller.log_cit_trace", lambda report: logged.append(report)
    )

    report = await controller.check_pair("prompt1", "prompt2", task_id="t")
    assert report.passed is True
    assert len(logged) == 1


@pytest.mark.asyncio
async def test_cit_controller_fail(monkeypatch):
    registry = LLMModelRegistry()
    registry.register("d", DummyModel("hi"))
    registry.register("e", DummyModel("bye"))
    agent = LLMAgent(registry, default_model_id="d")
    controller = CITController(agent, CITConfig(metric="jaccard", threshold=0.9))

    outputs = [
        PromptOutput(text="hi", model_id="d"),
        PromptOutput(text="bye", model_id="e"),
    ]

    async def run_patch(prompt: PromptInput, model_id=None, stream=False):
        return outputs.pop(0)

    monkeypatch.setattr(agent, "run", run_patch)
    logged = []
    monkeypatch.setattr(
        "src.inference.cit_controller.log_cit_trace", lambda report: logged.append(report)
    )

    report = await controller.check_pair("a", "b", task_id="t")
    assert report.passed is False
    assert len(logged) == 1


def test_compute_similarity_jaccard():
    score = compute_similarity("hello world", "hello there", "jaccard")
    assert 0 < score < 1
