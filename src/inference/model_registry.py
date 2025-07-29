from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Type

import httpx
import yaml
from pydantic import BaseModel, Field

from .llm_agent import PromptInput, PromptOutput


class LLMInterface(Protocol):
    """Unified interface for LLM model invocation."""

    model_id: str

    async def invoke(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        ...


class WatsonXModel:
    """Minimal watsonx.ai API wrapper."""

    def __init__(self, model_id: str, endpoint: str, api_key: str) -> None:
        self.model_id = model_id
        self.endpoint = endpoint
        self.api_key = api_key

    async def invoke(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "prompt": prompt.prompt,
            "temperature": prompt.temperature,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.endpoint, json=payload, headers=headers
            )
            resp.raise_for_status()
            if stream:
                text = ""
                async for chunk in resp.aiter_text():
                    text += chunk
                raw = text
            else:
                data = resp.json()
                text = data.get("generated_text") or data.get("result", "")
                raw = data
        return PromptOutput(text=text, model_id=self.model_id, raw=raw)


class OpenLLMModel:
    """Wrapper for a locally hosted OpenLLM endpoint."""

    def __init__(self, model_id: str, host: str) -> None:
        self.model_id = model_id
        self.host = host

    async def invoke(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        payload = {
            "prompt": prompt.prompt,
            "temperature": prompt.temperature,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.host, json=payload)
            resp.raise_for_status()
            if stream:
                text = ""
                async for chunk in resp.aiter_text():
                    text += chunk
                raw = text
            else:
                data = resp.json()
                text = data.get("generated_text") or data.get("result", "")
                raw = data
        return PromptOutput(text=text, model_id=self.model_id, raw=raw)


class LocalHFModel:
    """Placeholder for a local HuggingFace model."""

    def __init__(self, model_id: str, path: str) -> None:
        self.model_id = model_id
        self.path = path

    async def invoke(
        self, prompt: PromptInput, stream: bool = False
    ) -> PromptOutput:
        text = f"[local:{self.model_id}] {prompt.prompt}"
        return PromptOutput(text=text, model_id=self.model_id)


class ModelConfig(BaseModel):
    """Configuration entry for a model."""

    model_id: str
    provider: str
    endpoint: Optional[str] = None
    engine: Optional[str] = None
    path: Optional[str] = None
    api_key: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    default: bool = False
    params: Dict[str, Any] = Field(default_factory=dict)


_PROVIDER_MAP: Dict[str, Type[LLMInterface]] = {
    "watsonx": WatsonXModel,
    "openllm": OpenLLMModel,
    "huggingface": LocalHFModel,
}


class ModelRegistry:
    """Registry managing multiple LLM models."""

    def __init__(self) -> None:
        self._models: Dict[str, LLMInterface] = {}
        self._tags: Dict[str, List[str]] = {}
        self.default_model_id: Optional[str] = None

    def register(
        self,
        model: LLMInterface,
        tags: Optional[List[str]] = None,
        default: bool = False,
    ) -> None:
        self._models[model.model_id] = model
        self._tags[model.model_id] = tags or []
        if default or self.default_model_id is None:
            self.default_model_id = model.model_id

    def get(self, model_id: str) -> LLMInterface:
        if model_id not in self._models:
            raise ValueError(f"Model '{model_id}' not registered")
        return self._models[model_id]

    def get_model_for_task(
        self,
        model_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> LLMInterface:
        if model_id:
            return self.get(model_id)
        if tags:
            for mid, t in self._tags.items():
                if set(tags).issubset(set(t)):
                    return self._models[mid]
        if self.default_model_id:
            return self._models[self.default_model_id]
        raise ValueError("No model found for the given criteria")

    @classmethod
    def from_configs(cls, configs: List[ModelConfig]) -> "ModelRegistry":
        registry = cls()
        for cfg in configs:
            model = create_model_from_config(cfg)
            registry.register(model, tags=cfg.tags, default=cfg.default)
        return registry


def load_model_configs(path: str | Path) -> List[ModelConfig]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [ModelConfig(**c) for c in data.get("models", [])]


def create_model_from_config(cfg: ModelConfig) -> LLMInterface:
    provider_cls = _PROVIDER_MAP.get(cfg.provider)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {cfg.provider}")

    kwargs = {"model_id": cfg.model_id}
    if cfg.endpoint:
        kwargs["endpoint"] = cfg.endpoint
    if cfg.api_key:
        kwargs["api_key"] = cfg.api_key
    if cfg.engine and "engine" in inspect.signature(provider_cls).parameters:
        kwargs["engine"] = cfg.engine
    if cfg.path:
        kwargs["path"] = cfg.path
    kwargs.update(cfg.params)
    return provider_cls(**kwargs)  # type: ignore[arg-type]


__all__ = [
    "LLMInterface",
    "ModelConfig",
    "WatsonXModel",
    "OpenLLMModel",
    "LocalHFModel",
    "ModelRegistry",
    "load_model_configs",
    "create_model_from_config",
]
