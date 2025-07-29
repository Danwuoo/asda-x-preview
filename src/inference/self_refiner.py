from __future__ import annotations

import os
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from .llm_agent import LLMAgent, PromptInput
from .cit_controller import compute_similarity


DEFAULT_CRITIQUE_TEMPLATE = (
    "You are a critic. Review the following output and describe "
    "any problems or improvements needed:\n\n{output}"
)
DEFAULT_REWRITE_TEMPLATE = (
    "Original prompt: {prompt}\n"
    "Current answer: {output}\n"
    "Critique: {critique}\n"
    "\nRewrite the answer incorporating the critique."
)


class RefineConfig(BaseModel):
    """Configuration for the refinement loop."""

    max_rounds: int = 3
    score_threshold: float = 0.9


class RefineStep(BaseModel):
    """Single refinement iteration."""

    round: int
    critique: str
    refined_output: str
    score: float


class RefineSession(BaseModel):
    """Full record of a refinement session."""

    session_id: str = Field(
        default_factory=lambda: f"refine_{uuid.uuid4().hex}"
    )
    prompt: str
    initial_output: str
    steps: List[RefineStep] = Field(default_factory=list)
    final_output: Optional[str] = None
    final_score: Optional[float] = None
    stopping_reason: Optional[str] = None


class RefineLogger:
    """Persist refinement sessions to a JSONL file."""

    def __init__(self, path: str = "data/replay/refine_trace.jsonl") -> None:
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def __call__(self, session: RefineSession) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(session.model_dump_json() + "\n")


class SelfRefiner:
    """Controller that iteratively refines LLM outputs."""

    def __init__(
        self,
        agent: LLMAgent,
        config: Optional[RefineConfig] = None,
        logger: Optional[RefineLogger] = None,
    ) -> None:
        self.agent = agent
        self.config = config or RefineConfig()
        self.logger = logger or RefineLogger()

    async def _critique(self, text: str, model_id: Optional[str]) -> str:
        prompt = DEFAULT_CRITIQUE_TEMPLATE.format(output=text)
        out = await self.agent.run(
            PromptInput(prompt=prompt), model_id=model_id
        )
        return out.text

    async def _rewrite(
        self, prompt: str, text: str, critique: str, model_id: Optional[str]
    ) -> str:
        new_prompt = DEFAULT_REWRITE_TEMPLATE.format(
            prompt=prompt, output=text, critique=critique
        )
        out = await self.agent.run(
            PromptInput(prompt=new_prompt), model_id=model_id
        )
        return out.text

    async def refine(
        self, prompt: str, model_id: Optional[str] = None
    ) -> RefineSession:
        """Run the self-refinement loop."""
        initial = await self.agent.run(
            PromptInput(prompt=prompt), model_id=model_id
        )
        session = RefineSession(prompt=prompt, initial_output=initial.text)
        current_output = initial.text
        current_score = 0.0

        for i in range(1, self.config.max_rounds + 1):
            critique = await self._critique(current_output, model_id)
            refined = await self._rewrite(
                prompt, current_output, critique, model_id
            )
            score = compute_similarity(current_output, refined, "jaccard")
            session.steps.append(
                RefineStep(
                    round=i,
                    critique=critique,
                    refined_output=refined,
                    score=score,
                )
            )
            current_output = refined
            current_score = score
            if score >= self.config.score_threshold:
                session.stopping_reason = "score_threshold"
                break
        else:
            session.stopping_reason = "max_rounds"

        session.final_output = current_output
        session.final_score = current_score
        self.logger(session)
        return session


__all__ = [
    "SelfRefiner",
    "RefineConfig",
    "RefineSession",
    "RefineStep",
    "RefineLogger",
]
