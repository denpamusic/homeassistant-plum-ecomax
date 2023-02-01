"""Test Plum ecoMAX diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio import __version__
from pyplumio.devices.ecomax import EcoMAX
import pytest

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_TCP,
    DOMAIN,
)
from custom_components.plum_ecomax.diagnostics import (
    REDACTED,
    async_get_config_entry_diagnostics,
)


@pytest.mark.usefixtures("mixers")
async def test_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    ecomax_p: EcoMAX,
    config_data: dict[str, str],
    device_data: dict[str, str],
) -> None:
    """Test config entry diagnostics."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    hass.data[DOMAIN][config_entry.entry_id] = mock_connection
    result = await async_get_config_entry_diagnostics(hass, config_entry)
    assert result["pyplumio"]["version"] == __version__
    assert result["entry"] == {
        "title": "Mock Title",
        "data": {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
            CONF_DEVICE: config_data.get(CONF_DEVICE),
            CONF_HOST: REDACTED,
            CONF_PORT: config_data.get(CONF_PORT),
            CONF_UID: REDACTED,
            CONF_PRODUCT_TYPE: device_data.get(CONF_PRODUCT_TYPE),
            CONF_MODEL: device_data.get(CONF_MODEL),
            CONF_SOFTWARE: device_data.get(CONF_SOFTWARE),
            CONF_SUB_DEVICES: device_data.get(CONF_SUB_DEVICES),
        },
    }
    ecomax_data = dict(ecomax_p.data)
    ecomax_data[ATTR_PASSWORD] = REDACTED
    ecomax_data[ATTR_MIXERS] = {x: y.data for x, y in ecomax_data[ATTR_MIXERS].items()}
    assert result["data"][ATTR_PRODUCT].uid == REDACTED
    assert result["data"] == ecomax_data
