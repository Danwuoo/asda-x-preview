import os
import sys
CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))  # noqa: E402
sys.path.insert(0, PROJECT_ROOT)

import httpx  # noqa: E402
import types  # noqa: E402
from contextlib import contextmanager  # noqa: E402

# Stub logger and trace modules to avoid heavy dependencies
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

import pytest  # noqa: E402
import pytest_httpx  # noqa: E402


@pytest.fixture(autouse=True)
def _patch_loggers(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(gl, "trace_logger", dummy)
    monkeypatch.setattr(tl, "log_node_execution", log_node_execution)
    monkeypatch.setattr(llm_agent_mod, "trace_logger", dummy)
    monkeypatch.setattr(llm_agent_mod, "log_node_execution", log_node_execution)
    monkeypatch.setattr(sys.modules[__name__], "trace_logger", dummy)
    yield

from src.inference import llm_agent as llm_agent_mod  # noqa: E402
from src.inference.llm_agent import (  # noqa: E402
    LLMAgent,
    LLMModelRegistry,
    PromptInput,
    WatsonXModel,
)
from src.core.global_logger import trace_logger  # noqa: E402


@pytest.mark.asyncio
async def test_single_prompt(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    httpx_mock.add_response(url="http://mock", json={"generated_text": "hi"})
    registry = LLMModelRegistry()
    registry.register("wx", WatsonXModel("wx", "http://mock", "key"))
    agent = LLMAgent(registry, default_model_id="wx")

    output = await agent.run(PromptInput(prompt="hello"))
    assert output.text == "hi"
    assert output.model_id == "wx"


@pytest.mark.asyncio
async def test_model_selection(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    httpx_mock.add_response(url="http://a", json={"generated_text": "a"}, is_optional=True)
    httpx_mock.add_response(url="http://b", json={"generated_text": "b"})
    reg = LLMModelRegistry()
    reg.register("a", WatsonXModel("a", "http://a", "key"))
    reg.register("b", WatsonXModel("b", "http://b", "key"))
    agent = LLMAgent(reg, default_model_id="a")

    out = await agent.run(PromptInput(prompt="test"), model_id="b")
    assert out.text == "b"
    assert out.model_id == "b"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_streaming_mode(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    def gen():
        yield b"hello "
        yield b"world"

    async def callback(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=pytest_httpx.IteratorStream(gen()))

    httpx_mock.add_callback(callback, url="http://stream")
    reg = LLMModelRegistry()
    reg.register("s", WatsonXModel("s", "http://stream", "key"))
    agent = LLMAgent(reg, default_model_id="s")

    out = await agent.run(PromptInput(prompt="test"), stream=True)
    assert out.text == "hello world"


@pytest.mark.asyncio
async def test_trace_logging(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    httpx_mock.add_response(url="http://mock", json={"generated_text": "trace"})
    trace_logger.events.clear()
    reg = LLMModelRegistry()
    reg.register("wx", WatsonXModel("wx", "http://mock", "key"))
    agent = LLMAgent(reg, default_model_id="wx")

    await agent.run(PromptInput(prompt="hello"))
    assert len(trace_logger.events) == 1
    assert trace_logger.events[0].node_name == "llm_agent"

