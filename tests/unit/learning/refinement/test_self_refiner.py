import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.refinement.self_refiner import SelfRefiner  # noqa: E402


class DummyAgent:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def run(self, prompt: str) -> str:
        return self.outputs.pop(0)


def test_single_round_refinement():
    agent = DummyAgent(["draft", "review", "revised"])
    refiner = SelfRefiner(agent)
    records = refiner.run_refinement_loop("t1", "prompt", rounds=1)
    assert len(records) == 1
    rec = records[0]
    assert rec.review_comment == "review"
    assert rec.revised_output == "revised"
    assert rec.final_flag is True
