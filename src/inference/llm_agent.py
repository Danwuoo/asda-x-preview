from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Protocol

import httpx
from pydantic import BaseModel, Field

from src.core.global_logger import trace_logger
from src.core.trace_logger import log_node_execution


class PromptInput(BaseModel):
    """Standardized prompt input."""

    prompt: str
    temperature: float = 0.7
    tags: List[str] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)


class PromptOutput(BaseModel):
    """Standardized model output."""

    text: str
    model_id: str
    raw: Any | None = None


class LLMModel(Protocol):
    """Interface for LLM models."""

    model_id: str

    async def generate(self, prompt: PromptInput, stream: bool = False) -> PromptOutput:
        ...


class WatsonXModel:
    """Minimal watsonx.ai API wrapper."""

    def __init__(self, model_id: str, endpoint: str, api_key: str) -> None:
        self.model_id = model_id
        self.endpoint = endpoint
        self.api_key = api_key

    async def generate(self, prompt: PromptInput, stream: bool = False) -> PromptOutput:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"prompt": prompt.prompt, "temperature": prompt.temperature}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
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

    def __init__(self, model_id: str, host: str = "http://localhost:3000/generate") -> None:
        self.model_id = model_id
        self.host = host

    async def generate(self, prompt: PromptInput, stream: bool = False) -> PromptOutput:
        payload = {"prompt": prompt.prompt, "temperature": prompt.temperature}
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


class LLMModelRegistry:
    """Simple registry to manage multiple LLM models."""

    def __init__(self) -> None:
        self._models: Dict[str, LLMModel] = {}

    def register(self, model_id: str, model: LLMModel) -> None:
        self._models[model_id] = model

    def get(self, model_id: str) -> LLMModel:
        if model_id not in self._models:
            raise ValueError(f"Model '{model_id}' not registered")
        return self._models[model_id]


class LLMAgent:
    """Top level interface for invoking LLM models with tracing."""

    def __init__(self, registry: LLMModelRegistry, default_model_id: str) -> None:
        self.registry = registry
        self.default_model_id = default_model_id

    async def run(self, prompt: PromptInput, model_id: Optional[str] = None, stream: bool = False) -> PromptOutput:
        chosen = model_id or self.default_model_id
        model = self.registry.get(chosen)
        input_hash = hashlib.sha256(prompt.model_dump_json().encode()).hexdigest()
        with log_node_execution(
            logger=trace_logger,
            node_name="llm_agent",
            version=chosen,
            governance_tags=prompt.tags,
            input_hash=input_hash,
        ) as event:
            output = await model.generate(prompt, stream=stream)
            event.output_hash = hashlib.sha256(output.model_dump_json().encode()).hexdigest()
        return output


__all__ = [
    "PromptInput",
    "PromptOutput",
    "LLMModel",
    "WatsonXModel",
    "OpenLLMModel",
    "LLMModelRegistry",
    "LLMAgent",
]
