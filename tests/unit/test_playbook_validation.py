import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402
from jsonschema import ValidationError  # noqa: E402
from src.decision.soar import OutputValidator  # noqa: E402


def test_validator_passes():
    validator = OutputValidator()
    valid_pb = {"name": "test", "actions": []}
    validator.validate(valid_pb)


def test_validator_fails():
    validator = OutputValidator()
    invalid_pb = {"actions": []}
    with pytest.raises(ValidationError):
        validator.validate(invalid_pb)
