import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.learning.sec import render_template  # noqa: E402


def test_render_template():
    result = render_template(
        "intrusion_categorization",
        {"attack_type": "lateral movement", "input": {"k": 1}},
    )
    assert "lateral movement" in result
