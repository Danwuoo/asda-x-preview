import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.decision.cit.embedding import InstructionEmbedder  # noqa: E402
from src.decision.cit.drift_evaluator import (  # noqa: E402
    SemanticDriftEvaluator,
)


def test_drift_evaluator():
    evaluator = SemanticDriftEvaluator(InstructionEmbedder())
    drift = evaluator.embedding_drift(["a b", "a b"])
    assert drift == 0.0
    sim = evaluator.action_similarity(["a b", "a c"])
    assert 0.0 <= sim <= 1.0
