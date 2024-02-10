"""Contains helper functions."""

import json
from typing import Any

from pytest_homeassistant_custom_component.common import load_fixture


def keys_to_int(data: dict[str, Any]) -> dict[int, Any]:
    """Cast dict keys to int."""
    return {int(k): v for k, v in data.items()}


def load_regdata_fixture(filename: str):
    """Load regdata fixture."""
    return json.loads(load_fixture(filename), object_hook=keys_to_int)
