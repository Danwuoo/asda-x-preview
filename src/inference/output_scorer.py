from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .cit_controller import compute_similarity


class SimilarityMetric(str, Enum):
    """Supported similarity metrics."""

    JACCARD = "jaccard"
    LEVENSHTEIN = "levenshtein"
    BERTSCORE = "bertscore"


class ScoringRequest(BaseModel):
    """Input for scoring outputs."""

    output_a: str
    output_b: str
    task_type: Optional[str] = None
    metrics: List[str] = Field(
        default_factory=lambda: [SimilarityMetric.JACCARD.value]
    )
    weight: Dict[str, float] = Field(default_factory=dict)


class ScoringResult(BaseModel):
    """Result returned by the scorer."""

    overall_score: float
    passed: bool
    details: Dict[str, float | bool]
    reasoning: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def score_similarity(text_a: str, text_b: str, metric: str) -> float:
    """Compute semantic similarity between two texts."""
    return compute_similarity(text_a, text_b, metric)


def score_fluency(text: str) -> float:
    """Estimate fluency using a simple words-per-sentence heuristic."""
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
    words = len(text.split())
    avg_len = words / sentences
    if avg_len <= 20:
        return 1.0
    return max(0.0, 20.0 / avg_len)


def score_json_format(text: str) -> float:
    """Return 1.0 if text is valid JSON else 0.0."""
    try:
        json.loads(text)
        return 1.0
    except Exception:
        return 0.0


def aggregate_score(
    details: Dict[str, float | bool], weights: Dict[str, float]
) -> float:
    """Combine metric scores using provided weights."""
    total = 0.0
    weight_sum = 0.0
    for metric, value in details.items():
        if isinstance(value, bool):
            score = 1.0 if value else 0.0
        else:
            score = float(value)
        w = weights.get(metric, 1.0)
        total += score * w
        weight_sum += w
    if weight_sum == 0:
        return 0.0
    return total / weight_sum


class OutputScorer:
    """Main interface for evaluating output quality."""

    def score(self, request: ScoringRequest) -> ScoringResult:
        details: Dict[str, float | bool] = {}
        for metric in request.metrics:
            metric_l = metric.lower()
            if metric_l in {
                SimilarityMetric.JACCARD.value,
                SimilarityMetric.LEVENSHTEIN.value,
                SimilarityMetric.BERTSCORE.value,
            }:
                details[metric_l] = score_similarity(
                    request.output_a, request.output_b, metric_l
                )
            elif metric_l == "fluency":
                details[metric_l] = score_fluency(request.output_b)
            elif metric_l == "json_check":
                details[metric_l] = score_json_format(request.output_b) == 1.0
            else:
                raise ValueError(f"Unsupported metric: {metric}")

        weights = request.weight or {m: 1.0 for m in details}
        overall = aggregate_score(details, weights)
        passed = overall >= 0.5
        reasoning = "Weighted average applied to metrics."
        return ScoringResult(
            overall_score=overall,
            passed=passed,
            details=details,
            reasoning=reasoning,
        )


__all__ = [
    "SimilarityMetric",
    "ScoringRequest",
    "ScoringResult",
    "score_similarity",
    "score_fluency",
    "score_json_format",
    "aggregate_score",
    "OutputScorer",
]
