from __future__ import annotations

import os
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from pydantic import BaseModel

from .llm_agent import LLMAgent, PromptInput


class CITConfig(BaseModel):
    """Configuration for CIT checks."""

    metric: str = "jaccard"
    threshold: float = 0.75


class CITInput(BaseModel):
    """Input pair for CIT evaluation."""

    prompt_a: str
    prompt_b: str
    task_id: str = ""


class CITReport(BaseModel):
    """Report generated after a CIT check."""

    task_id: str
    prompt_a: str
    prompt_b: str
    output_a: str
    output_b: str
    score: float
    similarity_metric: str
    threshold: float
    passed: bool
    timestamp: datetime


def _jaccard(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _levenshtein(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def compute_similarity(text_a: str, text_b: str, metric: str) -> float:
    """Compute similarity between two texts using the given metric."""
    metric = metric.lower()
    if metric == "jaccard":
        return _jaccard(text_a, text_b)
    if metric == "levenshtein":
        return _levenshtein(text_a, text_b)
    if metric == "bertscore":
        try:
            from bert_score import score as bert_score

            _, _, f1 = bert_score([text_a], [text_b], lang="en")
            return float(f1[0])
        except Exception:  # pragma: no cover - heavy optional dependency
            raise ValueError("bert_score package not available")
    raise ValueError(f"Unsupported metric: {metric}")


def semantic_alignment_score(
    output_a: str, output_b: str, metric: str
) -> float:
    """Wrapper to compute the main alignment score."""
    return compute_similarity(output_a, output_b, metric)


def log_cit_trace(
    report: CITReport, path: str = "data/replay/cit_trace.jsonl"
) -> None:
    """Append the CIT report to the trace log."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(report.model_dump_json() + "\n")


class CITController:
    """Controller for Consistency and Integrity Testing (CIT)."""

    def __init__(
        self, agent: LLMAgent, config: Optional[CITConfig] = None
    ) -> None:
        self.agent = agent
        self.config = config or CITConfig()

    async def check_pair(
        self, prompt_a: str, prompt_b: str, task_id: str = ""
    ) -> CITReport:
        """Run CIT check on a pair of prompts."""
        out_a = await self.agent.run(PromptInput(prompt=prompt_a))
        out_b = await self.agent.run(PromptInput(prompt=prompt_b))
        score = semantic_alignment_score(
            out_a.text, out_b.text, self.config.metric
        )
        passed = score >= self.config.threshold
        report = CITReport(
            task_id=task_id,
            prompt_a=prompt_a,
            prompt_b=prompt_b,
            output_a=out_a.text,
            output_b=out_b.text,
            score=score,
            similarity_metric=self.config.metric,
            threshold=self.config.threshold,
            passed=passed,
            timestamp=datetime.now(timezone.utc),
        )
        log_cit_trace(report)
        return report


__all__ = [
    "CITConfig",
    "CITInput",
    "CITReport",
    "compute_similarity",
    "semantic_alignment_score",
    "log_cit_trace",
    "CITController",
]
