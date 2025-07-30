from __future__ import annotations

from typing import Optional

from src.inference.llm_agent import LLMAgent, PromptInput, PromptOutput


class LLMInferenceEngine:
    """Simple wrapper around :class:`LLMAgent` for inference."""

    def __init__(
        self, agent: LLMAgent, model_id: Optional[str] = None
    ) -> None:
        self.agent = agent
        self.model_id = model_id

    async def infer(self, prompt: str) -> PromptOutput:
        return await self.agent.run(
            PromptInput(prompt=prompt),
            model_id=self.model_id,
        )


__all__ = ["LLMInferenceEngine"]
