from __future__ import annotations

from itertools import combinations
from typing import Sequence

from .embedding import InstructionEmbedder


class SemanticDriftEvaluator:
    """Compute similarity and drift between outputs."""

    def __init__(self, embedder: InstructionEmbedder | None = None) -> None:
        self.embedder = embedder or InstructionEmbedder()

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def embedding_drift(self, outputs: Sequence[str]) -> float:
        """Return 1 - average Jaccard similarity across outputs."""
        if len(outputs) < 2:
            return 0.0
        embeds = [self.embedder.embed(o) for o in outputs]
        sims = [
            self._jaccard(embeds[i], embeds[j])
            for i, j in combinations(range(len(embeds)), 2)
        ]
        if not sims:
            return 0.0
        return 1 - sum(sims) / len(sims)

    def action_similarity(self, outputs: Sequence[str]) -> float:
        """Return average Jaccard similarity across outputs."""
        if len(outputs) < 2:
            return 1.0
        embeds = [self.embedder.embed(o) for o in outputs]
        sims = [
            self._jaccard(embeds[i], embeds[j])
            for i, j in combinations(range(len(embeds)), 2)
        ]
        return sum(sims) / len(sims)
