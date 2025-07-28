import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.core.agent import run  # noqa: E402


def test_run():
    assert run() == "Agent running"
