"""Test Plum ecoMAX diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio.devices import Device

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DOMAIN
from custom_components.plum_ecomax.diagnostics import (
    REDACTED,
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry):
    """Test config entry diagnostics."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = AsyncMock(spec=Device)
    mock_connection.device.data = {"test_data": "test_value"}
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = mock_connection
    result = await async_get_config_entry_diagnostics(hass, config_entry)
    assert "pyplumio" in result
    assert result["entry"] == {
        "title": "Mock Title",
        "data": {
            "connection_type": "TCP",
            "device": "/dev/ttyUSB0",
            "host": REDACTED,
            "port": 8899,
            "uid": REDACTED,
            "model": "EMTEST",
            "software": "1.13.5.A1",
            "capabilities": ["fuel_burned", "heating_temp"],
        },
    }
    assert result["data"] == {"test_data": "test_value"}
