import os
import sys

import pytest
import yaml

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.inference.model_registry import (  # noqa: E402
    ModelRegistry,
    load_model_configs,
    _PROVIDER_MAP,
)
from src.inference.llm_agent import PromptInput, PromptOutput  # noqa: E402


class DummyModel:
    def __init__(self, model_id: str, reply: str = "ok") -> None:
        self.model_id = model_id
        self.reply = reply

    async def invoke(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        return PromptOutput(text=self.reply, model_id=self.model_id)


@pytest.fixture(autouse=True)
def patch_provider_map(monkeypatch):
    mapping = dict(_PROVIDER_MAP)
    mapping["dummy"] = DummyModel
    monkeypatch.setattr(
        sys.modules["src.inference.model_registry"], "_PROVIDER_MAP", mapping
    )
    yield


@pytest.mark.asyncio
async def test_register_and_get():
    reg = ModelRegistry()
    model = DummyModel("d1")
    reg.register(model, tags=["test"], default=True)
    assert reg.get("d1") is model
    assert reg.get_model_for_task() is model


@pytest.mark.asyncio
async def test_tag_selection():
    reg = ModelRegistry()
    m1 = DummyModel("a")
    m2 = DummyModel("b")
    reg.register(m1, tags=["fast"])
    reg.register(m2, tags=["secure"], default=True)
    chosen = reg.get_model_for_task(tags=["fast"])
    assert chosen is m1


@pytest.mark.asyncio
async def test_load_from_config(tmp_path):
    cfg = {
        "models": [
            {
                "model_id": "c1",
                "provider": "dummy",
                "tags": ["x"],
                "default": True,
                "params": {"reply": "hi"},
            }
        ]
    }
    path = tmp_path / "cfg.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    configs = load_model_configs(path)
    reg = ModelRegistry.from_configs(configs)
    model = reg.get_model_for_task()
    assert model.model_id == "c1"
    out = await model.invoke(PromptInput(prompt="test"))
    assert out.text == "hi"


@pytest.mark.asyncio
async def test_instance_cache():
    reg = ModelRegistry()
    model = DummyModel("dup")
    reg.register(model)
    assert reg.get("dup") is reg.get("dup")
