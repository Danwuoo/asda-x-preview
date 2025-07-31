import os
import sys
import types
from contextlib import contextmanager

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

from src.decision.cit import (  # noqa: E402
    CITController,
    CITConfig,
    PromptVariationGenerator,
)
from src.decision.inference_engine import LLMInferenceEngine  # noqa: E402
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
        self.model_id = "d"
        self.replies = list(replies)

    async def generate(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        text = self.replies.pop(0)
        return PromptOutput(text=text, model_id=self.model_id)


@pytest.mark.asyncio
async def test_decision_stability(monkeypatch):
    registry = LLMModelRegistry()
    registry.register("d", DummyModel(["same", "same", "same"]))
    agent = LLMAgent(registry, default_model_id="d")
    engine = LLMInferenceEngine(agent)

    gen = PromptVariationGenerator(synonyms={"block": ["prevent"]})
    cfg = CITConfig(embedding_threshold=0.5, max_variants=2)
    controller = CITController(engine, config=cfg, variation_gen=gen)

    report = await controller.check("block", task_id="t")
    assert report["status"] == "ok"
    assert len(report["prompt_variants"]) == 2
