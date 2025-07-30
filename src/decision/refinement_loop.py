from __future__ import annotations

from typing import Optional, Tuple

from src.inference.self_refiner import SelfRefiner


class RefinementLoop:
    """Wrapper to refine prompts using :class:`SelfRefiner`."""

    def __init__(self, refiner: Optional[SelfRefiner] = None) -> None:
        self.refiner = refiner

    async def refine(self, prompt: str) -> Tuple[str, int]:
        if self.refiner is None:
            return prompt, 0
        session = await self.refiner.refine(prompt)
        refined = session.final_output or session.initial_output
        return refined, len(session.steps)


__all__ = ["RefinementLoop"]
