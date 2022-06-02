"""Test Plum ecoMAX diagnostics."""

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Test get config entry diagnostics data."""
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["entry"]["title"] == "Mock Title"
    assert diagnostics["data"]["sensors"] == "test_data"
    assert diagnostics["data"]["parameters"] == "test_parameters"
    assert diagnostics["data"]["schema"] == "test_schema"
    assert diagnostics["data"]["mixers"] == "test_mixers"
