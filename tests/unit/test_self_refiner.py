import os
import sys
import types
from contextlib import contextmanager

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))  # noqa: E402
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

from src.inference.self_refiner import SelfRefiner, RefineConfig  # noqa: E402
from src.inference.llm_agent import (  # noqa: E402
    LLMAgent,
    LLMModelRegistry,
    PromptInput,
    PromptOutput,
)
from src.core import global_logger as gl  # noqa: E402
from src.core import trace_logger as tl  # noqa: E402


class DummyLogger:
    def __init__(self) -> None:
        self.events = []

    def log_event(self, event) -> None:
        self.events.append(event)


@contextmanager
def log_node_execution(
    logger, node_name, version, governance_tags=None, input_hash=None
):
    event = types.SimpleNamespace(
        node_name=node_name, version=version, output_hash=None
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
    def __init__(self, replies):
        self.model_id = "dummy"
        self.replies = list(replies)

    async def generate(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        text = self.replies.pop(0)
        return PromptOutput(text=text, model_id=self.model_id)


@pytest.mark.asyncio
async def test_single_round(monkeypatch):
    model = DummyModel(["draft", "critique", "final"])
    reg = LLMModelRegistry()
    reg.register("d", model)
    agent = LLMAgent(registry=reg, default_model_id="d")

    logged = []
    monkeypatch.setattr(
        "src.inference.self_refiner.RefineLogger.__call__",
        lambda self, s: logged.append(s),
    )

    refiner = SelfRefiner(agent, RefineConfig(max_rounds=1))
    session = await refiner.refine("prompt")

    assert session.initial_output == "draft"
    assert len(session.steps) == 1
    assert session.steps[0].critique == "critique"
    assert session.steps[0].refined_output == "final"
    assert session.final_output == "final"
    assert len(logged) == 1


@pytest.mark.asyncio
async def test_multi_round(monkeypatch):
    replies = ["draft", "c1", "r1", "c2", "r2"]
    model = DummyModel(replies)
    reg = LLMModelRegistry()
    reg.register("d", model)
    agent = LLMAgent(registry=reg, default_model_id="d")

    logged = []
    monkeypatch.setattr(
        "src.inference.self_refiner.RefineLogger.__call__",
        lambda self, s: logged.append(s),
    )

    cfg = RefineConfig(max_rounds=2, score_threshold=0.99)
    refiner = SelfRefiner(agent, cfg)
    session = await refiner.refine("prompt")

    assert len(session.steps) == 2
    assert session.stopping_reason == "max_rounds"
    assert session.final_output == "r2"
    assert len(logged) == 1
