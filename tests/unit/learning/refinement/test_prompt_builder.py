import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.refinement.critic_prompt_builder import (  # noqa: E402
    build_prompt,
)


def test_build_prompt_includes_parts():
    text = build_prompt("draft", context="ctx", indicators=["a", "b"])
    assert "ctx" in text
    assert "draft" in text
    assert "a" in text and "b" in text
