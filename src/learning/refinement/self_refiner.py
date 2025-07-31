from __future__ import annotations

"""Simple implementation of a self-refinement cycle."""

from typing import Iterable, List, Optional, Protocol

from src.inference.cit_controller import compute_similarity

from .critic_prompt_builder import build_prompt
from .refinement_schema import RefinementEntry


class TextAgent(Protocol):
    """Minimal protocol for text generation."""

    def run(self, prompt: str) -> str:  # pragma: no cover - interface only
        ...


class SelfRefiner:
    """Handle draft generation, review and rewriting."""

    def __init__(self, agent: TextAgent) -> None:
        self.agent = agent

    def generate_initial(self, prompt: str) -> str:
        """Generate the initial draft from the prompt."""
        return self.agent.run(prompt)

    def review_output(
        self,
        draft: str,
        *,
        context: str = "",
        indicators: Optional[Iterable[str]] = None,
    ) -> str:
        """Return reviewer comments for the draft."""
        review_prompt = build_prompt(
            draft,
            context=context,
            indicators=indicators,
        )
        return self.agent.run(review_prompt)

    def apply_revision(self, prompt: str, draft: str, review: str) -> str:
        """Apply reviewer feedback to generate a revised draft."""
        rewrite_prompt = (
            f"Original prompt: {prompt}\n"
            f"Current answer: {draft}\n"
            f"Critique: {review}\n"
            "\nRewrite the answer incorporating the critique."
        )
        return self.agent.run(rewrite_prompt)

    def run_refinement_loop(
        self,
        task_id: str,
        prompt: str,
        *,
        rounds: int = 1,
        context: str = "",
        indicators: Optional[List[str]] = None,
        score_delta: float = 0.01,
    ) -> List[RefinementEntry]:
        """Execute a multi-pass refinement loop."""
        results: List[RefinementEntry] = []
        current = self.generate_initial(prompt)
        prev_score = 0.0

        for i in range(1, rounds + 1):
            review = self.review_output(
                current,
                context=context,
                indicators=indicators,
            )
            revised = self.apply_revision(prompt, current, review)
            score = compute_similarity(current, revised, "jaccard")
            results.append(
                RefinementEntry(
                    task_id=task_id,
                    round=i,
                    initial_output=current,
                    review_comment=review,
                    revised_output=revised,
                    improvement_score=score,
                    final_flag=False,
                )
            )
            if abs(score - prev_score) < score_delta:
                results[-1].final_flag = True
                break
            current = revised
            prev_score = score

        if results:
            results[-1].final_flag = True
        return results


__all__ = ["SelfRefiner", "TextAgent"]
