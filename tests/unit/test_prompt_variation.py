import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.decision.cit.prompt_variation import (  # noqa: E402
    PromptVariationGenerator,
)


def test_prompt_variation_basic():
    gen = PromptVariationGenerator(
        synonyms={"block": ["prevent"], "traffic": ["connections"]}
    )
    variants = gen.generate("Block traffic", num_variants=1)
    assert variants[0] == "Prevent connections"
