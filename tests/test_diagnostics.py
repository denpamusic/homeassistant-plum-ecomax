"""Test Plum ecoMAX diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio.devices import Device

from custom_components.plum_ecomax.connection import ATTR_MODULES, EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_LAMBDA,
    ATTR_LEVEL,
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_THERMOSTATS,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    DOMAIN,
)
from custom_components.plum_ecomax.diagnostics import (
    REDACTED,
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, mock_device: Device
) -> None:
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
            CONF_UID: REDACTED,
            CONF_PRODUCT_TYPE: 0,
            CONF_MODEL: "ecoMAX 123A",
            CONF_SOFTWARE: "1.13.5.A1",
            CONF_SUB_DEVICES: [ATTR_MIXERS],
        },
    }
    assert result["data"] == {
        "test_data": "test_value",
        ATTR_LAMBDA: {ATTR_LEVEL: 166},
        ATTR_PRODUCT: mock_connection.device.data[ATTR_PRODUCT],
        ATTR_PASSWORD: REDACTED,
        ATTR_MIXERS: {0: {"test_mixer_data": "test_mixer_value"}},
        ATTR_THERMOSTATS: {0: {"test_thermostat_data": "test_thermostat_value"}},
        ATTR_MODULES: mock_connection.device.data[ATTR_MODULES],
    }
    assert mock_connection.device.data[ATTR_PRODUCT].uid == REDACTED
