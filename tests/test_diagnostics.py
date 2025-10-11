"""Test Plum ecoMAX diagnostics."""

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio import __version__
from pyplumio.devices.ecomax import EcoMAX
import pytest

from custom_components.plum_ecomax import PlumEcomaxData
from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_TCP,
)
from custom_components.plum_ecomax.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.usefixtures("ecomax_860p3_o", "mixers", "connection")
async def test_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    ecomax_p: EcoMAX,
    tcp_config_data: dict[str, Any],
) -> None:
    """Test config entry diagnostics."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    config_entry.runtime_data = PlumEcomaxData(mock_connection)
    result = await async_get_config_entry_diagnostics(hass, config_entry)
    assert result["pyplumio"]["version"] == __version__
    assert result["entry"] == {
        "title": config_entry.title,
        "data": {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
            CONF_HOST: REDACTED,
            CONF_PORT: tcp_config_data.get(CONF_PORT),
            CONF_UID: REDACTED,
            CONF_PRODUCT_TYPE: tcp_config_data.get(CONF_PRODUCT_TYPE),
            CONF_PRODUCT_ID: tcp_config_data.get(CONF_PRODUCT_ID),
            CONF_MODEL: tcp_config_data.get(CONF_MODEL),
            CONF_SOFTWARE: tcp_config_data.get(CONF_SOFTWARE),
            CONF_SUB_DEVICES: tcp_config_data.get(CONF_SUB_DEVICES),
        },
        "options": {},
    }
    ecomax_data = dict(ecomax_p.data)
    ecomax_data[ATTR_PASSWORD] = REDACTED
    ecomax_data[ATTR_MIXERS] = {x: y.data for x, y in ecomax_data[ATTR_MIXERS].items()}
    assert result["data"][ATTR_PRODUCT][CONF_UID] == REDACTED
    assert ecomax_data[ATTR_PRODUCT].uid != REDACTED

    # Check that redactor doesn't fail on missing key.
    del ecomax_data[ATTR_PASSWORD]
    with patch("pyplumio.devices.ecomax.EcoMAX.data", ecomax_data):
        result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert ATTR_PASSWORD not in result["data"]
