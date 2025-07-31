from __future__ import annotations

"""Control logic for multi-pass refinement."""

from typing import List, Optional

from .self_refiner import SelfRefiner
from .refinement_schema import RefinementEntry


class MultiPassRunner:
    """Execute refinement loops until convergence or max rounds."""

    def __init__(
        self,
        refiner: SelfRefiner,
        max_rounds: int = 3,
        score_delta: float = 0.01,
    ) -> None:
        self.refiner = refiner
        self.max_rounds = max_rounds
        self.score_delta = score_delta

    def run(
        self,
        task_id: str,
        prompt: str,
        *,
        context: str = "",
        indicators: Optional[List[str]] = None,
    ) -> List[RefinementEntry]:
        """Run the configured refinement process."""
        return self.refiner.run_refinement_loop(
            task_id,
            prompt,
            rounds=self.max_rounds,
            context=context,
            indicators=indicators,
            score_delta=self.score_delta,
        )


__all__ = ["MultiPassRunner"]
