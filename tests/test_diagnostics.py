"""Test Plum ecoMAX diagnostics."""

from homeassistant.core import HomeAssistant
from pyplumio import __version__ as pyplumio_version
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Test get config entry diagnostics data."""
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["entry"]["title"] == "Mock Title"
    assert diagnostics["pyplumio"]["version"] == pyplumio_version
    assert diagnostics["data"]["product"] == "test_product"
    assert diagnostics["data"]["modules"] == "test_modules"
    assert diagnostics["data"]["data"] == "test_data"
    assert diagnostics["data"]["parameters"] == "test_parameters"
    assert diagnostics["data"]["mixers"] == "test_mixers"
