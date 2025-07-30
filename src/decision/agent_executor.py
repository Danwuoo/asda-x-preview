from __future__ import annotations

import json
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.inference.cit_controller import CITController

from .prompt_builder import PromptBuilder
from .inference_engine import LLMInferenceEngine
from .refinement_loop import RefinementLoop
from .output_schema import LLMOutputSchema


class ExecutionContext(BaseModel):
    """Carry task context and session metadata."""

    task_context: Dict[str, Any]
    session_id: str


class LLMAgentExecutor:
    """Orchestrate prompt building, inference and refinement."""

    def __init__(
        self,
        builder: PromptBuilder,
        engine: LLMInferenceEngine,
        refine_loop: Optional[RefinementLoop] = None,
        cit_controller: Optional[CITController] = None,
        version_id: str = "v0",
    ) -> None:
        self.builder = builder
        self.engine = engine
        self.refine_loop = refine_loop or RefinementLoop()
        self.cit_controller = cit_controller
        self.version_id = version_id

    async def execute(self, context: ExecutionContext) -> LLMOutputSchema:
        prompt = self.builder.build(context.task_context)
        prompt, rounds = await self.refine_loop.refine(prompt)
        result = await self.engine.infer(prompt)

        if self.cit_controller is not None:
            await self.cit_controller.check_pair(
                prompt,
                prompt,
                task_id=context.session_id,
            )

        action_plan: Dict[str, Any] = {}
        try:
            action_plan = json.loads(result.text)
        except Exception:
            pass

        metadata = {
            "version_id": self.version_id,
            "refinement_rounds": rounds,
        }
        return LLMOutputSchema(
            action_plan=action_plan,
            llm_output=result.text,
            metadata=metadata,
        )


__all__ = ["ExecutionContext", "LLMAgentExecutor"]
