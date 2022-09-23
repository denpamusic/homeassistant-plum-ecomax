"""Test Plum ecoMAX setup process."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import dt as dt_util
from pyplumio.structures.alerts import Alert
import pytest

from custom_components.plum_ecomax import (
    async_migrate_entry,
    async_setup_entry,
    async_setup_events,
    async_unload_entry,
)
from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_CODE,
    ATTR_FROM,
    ATTR_TO,
    CONF_CAPABILITIES,
    DOMAIN,
    ECOMAX_ALERT_EVENT,
)


@patch(
    "custom_components.plum_ecomax.EcomaxConnection.async_setup",
    side_effect=(None, asyncio.TimeoutError),
)
@patch("custom_components.plum_ecomax.async_setup_services")
@patch.object(EcomaxConnection, "close", create=True, new_callable=AsyncMock)
async def test_setup_and_unload_entry(
    mock_close,
    async_setup_services,
    mock_async_setup,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test setup and unload of config entry."""
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(hass.data[DOMAIN][config_entry.entry_id], EcomaxConnection)

    # Test with exception.
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, config_entry)

    # Send HA stop event and check that connection was closed.
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert mock_close.call_count == 2
    mock_close.reset_mock()

    # Unload entry and verify that it is no longer present in hass data.
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    mock_close.assert_awaited_once()
    mock_close.reset_mock()

    # Test when already unloaded.
    assert await async_unload_entry(hass, config_entry)
    mock_close.assert_not_awaited()


@patch("pyplumio.helpers.filters._Delta")
@patch("homeassistant.core.EventBus.async_fire")
async def test_setup_events(mock_async_fire, mock_delta, hass: HomeAssistant) -> None:
    """Test setup events."""
    mock_connection = Mock(spec=EcomaxConnection)
    await async_setup_events(hass, mock_connection)
    mock_subscribe = mock_connection.device.subscribe
    mock_subscribe.assert_called_once_with("alerts", mock_delta.return_value)
    args, _ = mock_delta.call_args
    callback = args[0]
    utcnow = dt_util.utcnow()
    alert = Alert(code=0, from_dt=utcnow, to_dt=None)
    await callback([alert])
    mock_async_fire.assert_called_once_with(
        ECOMAX_ALERT_EVENT, {ATTR_CODE: 0, ATTR_FROM: utcnow, ATTR_TO: None}
    )


@patch.object(EcomaxConnection, "get_device", create=True, new_callable=AsyncMock)
@patch.object(
    EcomaxConnection,
    "connect",
    create=True,
    new_callable=AsyncMock,
    side_effect=(asyncio.TimeoutError, None),
)
@patch.object(EcomaxConnection, "close", create=True, new_callable=AsyncMock)
async def test_migrate_entry(
    mock_close,
    mock_connect,
    mock_get_device,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test migrating entry to a new version."""
    config_entry.version = 1
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_update_entry"
    ) as mock_async_update_entry, patch(
        "custom_components.plum_ecomax.async_get_device_capabilities",
        new_callable=AsyncMock,
        return_value="test",
    ) as mock_async_get_device_capabilities:
        assert not await async_migrate_entry(hass, config_entry)
        config_entry.version = 1
        assert await async_migrate_entry(hass, config_entry)

    assert mock_connect.call_count == 2
    mock_async_get_device_capabilities.assert_awaited_once_with(
        mock_get_device.return_value
    )
    mock_close.assert_awaited_once()
    data = {**config_entry.data}
    data[CONF_CAPABILITIES] = "test"
    mock_async_update_entry.assert_called_once_with(config_entry, data=data)
    assert config_entry.version == 2
