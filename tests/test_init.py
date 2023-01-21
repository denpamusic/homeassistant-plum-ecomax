"""Test Plum ecoMAX setup process."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import dt as dt_util
from pyplumio.devices import Device
from pyplumio.structures.alerts import Alert
import pytest

from custom_components.plum_ecomax import (
    ATTR_ALERTS,
    DATE_STR_FORMAT,
    async_migrate_entry,
    async_setup_entry,
    async_setup_events,
    async_unload_entry,
    format_model_name,
)
from custom_components.plum_ecomax.connection import (
    DEVICE_TIMEOUT,
    VALUE_TIMEOUT,
    EcomaxConnection,
)
from custom_components.plum_ecomax.const import (
    ATTR_CODE,
    ATTR_DEVICE_ID,
    ATTR_FROM,
    ATTR_PRODUCT,
    ATTR_TO,
    CONF_CAPABILITIES,
    CONF_MODEL,
    CONF_PRODUCT_TYPE,
    DOMAIN,
    ECOMAX,
    EVENT_PLUM_ECOMAX_ALERT,
)


@patch("custom_components.plum_ecomax.async_setup_services")
@patch(
    "custom_components.plum_ecomax.EcomaxConnection.async_setup",
    side_effect=(None, asyncio.TimeoutError),
)
@patch(
    "custom_components.plum_ecomax.connection.EcomaxConnection.close",
    create=True,
    new_callable=AsyncMock,
)
async def test_setup_and_unload_entry(
    mock_close,
    mock_async_setup,
    mock_async_setup_services,
    mock_device: Device,
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


async def test_setup_events(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup events."""
    connection = hass.data[DOMAIN][config_entry.entry_id]
    with patch("custom_components.plum_ecomax.delta") as mock_delta:
        await async_setup_events(hass, connection)

    mock_device.subscribe.assert_called_once_with(ATTR_ALERTS, mock_delta.return_value)
    args, _ = mock_delta.call_args

    # Test calling the callback with an alert.
    callback = args[0]
    utcnow = dt_util.utcnow()
    alert = Alert(code=0, from_dt=utcnow, to_dt=utcnow)
    mock_device_entry = Mock()
    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get_device",
        return_value=mock_device_entry,
    ), patch("homeassistant.core.EventBus.async_fire") as mock_async_fire:
        await callback([alert])
        mock_device.get_value.assert_called_once_with(
            ATTR_PRODUCT, timeout=VALUE_TIMEOUT
        )
        mock_async_fire.assert_called_once_with(
            EVENT_PLUM_ECOMAX_ALERT,
            {
                ATTR_DEVICE_ID: mock_device_entry.id,
                ATTR_CODE: 0,
                ATTR_FROM: utcnow.strftime(DATE_STR_FORMAT),
                ATTR_TO: utcnow.strftime(DATE_STR_FORMAT),
            },
        )

    # Test with timeout error while getting product info.
    mock_device.get_value = AsyncMock(side_effect=asyncio.TimeoutError)
    await callback([alert])
    await async_setup_events(hass, connection)
    assert "Event dispatch failed" in caplog.text


async def test_migrate_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, mock_device: Device
) -> None:
    """Test migrating entry from version 1 to version 5."""
    config_entry.version = 1
    mock_product = Mock()
    mock_product.type = 0
    mock_device.get_value = AsyncMock(return_value=mock_product)
    data = {**config_entry.data}
    data[CONF_MODEL] = "EM123A"
    data[CONF_CAPABILITIES] = {"test"}
    hass.config_entries.async_update_entry(config_entry, data=data)
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.connect",
        new_callable=AsyncMock,
        create=True,
    ) as mock_connect, patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.close",
        new_callable=AsyncMock,
        create=True,
    ) as mock_close, patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.get_device",
        create=True,
        return_value=mock_device,
        new_callable=AsyncMock,
    ) as mock_get_device:
        assert await async_migrate_entry(hass, config_entry)

    mock_connect.assert_awaited_once()
    mock_close.assert_awaited_once()
    mock_get_device.assert_awaited_once_with(ECOMAX, timeout=DEVICE_TIMEOUT)
    data = {**config_entry.data}
    data[CONF_PRODUCT_TYPE] = 0
    assert data[CONF_MODEL] == "ecoMAX 123A"
    assert CONF_CAPABILITIES not in data
    assert config_entry.version == 5


async def test_format_model_name() -> None:
    """Test model name formatter."""
    model_names = (
        ("EM350P2-ZF", "ecoMAX 350P2-ZF"),
        ("ecoMAXX800R3", "ecoMAXX 800R3"),
        ("ecoMAX 850i", "ecoMAX 850i"),
        ("ignore", "ignore"),
    )

    for raw, formatted in model_names:
        assert format_model_name(raw) == formatted
