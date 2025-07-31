import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.refinement.self_refiner import SelfRefiner  # noqa: E402
from src.learning.refinement.multi_pass_runner import (  # noqa: E402
    MultiPassRunner,
)


class DummyAgent:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def run(self, prompt: str) -> str:
        return self.outputs.pop(0)


def test_multi_round_runner():
    agent = DummyAgent([
        "draft",
        "review1",
        "rev1",
        "review2",
        "rev2",
    ])
    refiner = SelfRefiner(agent)
    runner = MultiPassRunner(refiner, max_rounds=2)
    records = runner.run("t1", "prompt")
    assert len(records) >= 1
    assert records[-1].final_flag is True
