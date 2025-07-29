import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))  # noqa: E402
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

from src.inference.output_scorer import (  # noqa: E402
    OutputScorer,
    ScoringRequest,
    score_similarity,
    score_json_format,
)


def test_score_similarity_jaccard():
    score = score_similarity("hello world", "hello world", "jaccard")
    assert pytest.approx(score, 0.001) == 1.0


def test_score_json_format():
    assert score_json_format('{"a": 1}') == 1.0
    assert score_json_format("{") == 0.0


def test_output_scorer_aggregate():
    req = ScoringRequest(
        output_a='{"a": 1}',
        output_b='{"a": 1}',
        metrics=["jaccard", "json_check"],
        weight={"jaccard": 0.8, "json_check": 0.2},
    )
    scorer = OutputScorer()
    result = scorer.score(req)
    assert result.passed is True
    assert result.overall_score == pytest.approx(1.0)
