"""Test Plum ecoMAX diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.plum_ecomax.connection import ATTR_MODULES, EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_THERMOSTATS,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
)
from custom_components.plum_ecomax.diagnostics import (
    REDACTED,
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry, mock_device):
    """Test config entry diagnostics."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = mock_connection
    result = await async_get_config_entry_diagnostics(hass, config_entry)
    assert "pyplumio" in result
    assert result["entry"] == {
        "title": "Mock Title",
        "data": {
            CONF_CONNECTION_TYPE: "TCP",
            CONF_DEVICE: "/dev/ttyUSB0",
            CONF_HOST: REDACTED,
            CONF_PORT: 8899,
            "uid": REDACTED,
            "product_type": 0,
            "model": "ecoMAX 123A",
            "software": "1.13.5.A1",
            "capabilities": ["fuel_burned", "heating_temp", "mixers"],
        },
    }
    assert result["data"] == {
        "test_data": "test_value",
        ATTR_PRODUCT: mock_connection.device.data[ATTR_PRODUCT],
        ATTR_PASSWORD: REDACTED,
        ATTR_MIXERS: [{"test_mixer_data": "test_mixer_value"}],
        ATTR_THERMOSTATS: [{"test_thermostat_data": "test_thermostat_value"}],
        ATTR_MODULES: mock_connection.device.data[ATTR_MODULES],
    }
    assert mock_connection.device.data[ATTR_PRODUCT].uid == REDACTED
