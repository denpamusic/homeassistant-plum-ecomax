"""Test Plum ecoMAX setup process."""

from datetime import datetime
from typing import Final, cast
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import (
    ATTR_CODE,
    ATTR_DEVICE_ID,
    ATTR_NAME,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import dt as dt_util
from pyplumio.const import AlertType
from pyplumio.structures.alerts import ATTR_ALERTS, Alert
import pytest

from custom_components.plum_ecomax import (
    PlumEcomaxData,
    async_migrate_entry,
    async_setup_entry,
    async_setup_events,
    async_unload_entry,
)
from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_FROM,
    ATTR_TO,
    CONF_CAPABILITIES,
    CONF_PRODUCT_ID,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    EVENT_PLUM_ECOMAX_ALERT,
)

DATE_FROM: Final = "2012-12-12 00:00:00"
DATE_TO: Final = "2012-12-12 01:00:00"


@pytest.fixture(autouse=True)
def bypass_async_setup_services():
    """Bypass async setup services."""
    with patch("custom_components.plum_ecomax.async_setup_services"):
        yield


@pytest.fixture(autouse=True)
def bypass_connect_and_close():
    """Bypass initiating and closing connection.."""
    with (
        patch(
            "pyplumio.connection.Connection.connect",
            create=True,
            new_callable=AsyncMock,
        ),
        patch(
            "pyplumio.connection.Connection.close",
            create=True,
            new_callable=AsyncMock,
        ),
    ):
        yield


@pytest.mark.usefixtures("connected", "ecomax_p")
async def test_setup_and_unload_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test setup and unload of config entry."""
    with patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"):
        assert await async_setup_entry(hass, config_entry)

    assert isinstance(data := config_entry.runtime_data, PlumEcomaxData)
    assert isinstance(connection := data.connection, EcomaxConnection)

    # Test with exception.
    with (
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.async_setup",
            side_effect=TimeoutError,
        ),
        pytest.raises(ConfigEntryNotReady) as exc_info,
    ):
        await async_setup_entry(hass, config_entry)

    assert exc_info.value.translation_key == "connection_timeout"
    connection.close.assert_awaited_once()
    connection.close.reset_mock()

    # Send HA stop event and check that connection was closed.
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    connection.close.assert_awaited_once()
    connection.close.reset_mock()

    # Unload entry and verify that it is no longer present in hass data.
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    connection.close.assert_awaited_once()


@pytest.mark.usefixtures("ecomax_p", "connection")
async def test_setup_events(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test setup events."""
    data = config_entry.runtime_data
    connection = data.connection
    with (
        patch("custom_components.plum_ecomax.delta") as mock_delta,
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.device.subscribe"
        ) as mock_subscribe,
    ):
        assert async_setup_events(hass, connection)

    mock_subscribe.assert_called_once_with(ATTR_ALERTS, mock_delta.return_value)
    args = mock_delta.call_args[0]
    callback = args[0]

    # Test calling the callback with an alert.
    alert = Alert(
        code=AlertType.POWER_LOSS,
        from_dt=cast(datetime, dt_util.parse_datetime(DATE_FROM)),
        to_dt=dt_util.parse_datetime(DATE_TO),
    )
    mock_device_entry = Mock()

    with (
        patch(
            "homeassistant.helpers.device_registry.DeviceRegistry.async_get_device",
            return_value=mock_device_entry,
        ),
        patch("homeassistant.core.EventBus.async_fire") as mock_async_fire,
    ):
        await callback([alert])

    mock_async_fire.assert_called_once_with(
        EVENT_PLUM_ECOMAX_ALERT,
        {
            ATTR_NAME: connection.name,
            ATTR_DEVICE_ID: mock_device_entry.id,
            ATTR_CODE: AlertType.POWER_LOSS,
            ATTR_FROM: DATE_FROM,
            ATTR_TO: DATE_TO,
        },
    )

    # Check when device is not found.
    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get_device",
        return_value=None,
    ):
        await callback([alert])

    assert "Device not found." in caplog.text


@pytest.mark.usefixtures("ecomax_p")
async def test_migrate_entry_v1_2_to_v8(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test migrating entry from version 1 or 2 to version 8."""
    config_entry.version = 1
    data = dict(config_entry.data)
    data.update({CONF_CAPABILITIES: {"test_capability"}})
    hass.config_entries.async_update_entry(config_entry, data=data)
    assert await async_migrate_entry(hass, config_entry)
    data = dict(config_entry.data)
    assert CONF_CAPABILITIES not in data
    assert CONF_SUB_DEVICES in data
    assert config_entry.version == 8
    assert "Migration to version 8 successful" in caplog.text


@pytest.mark.usefixtures("ecomax_p")
async def test_migrate_entry_v3_to_v8(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test migrating entry from version 3 to version 8."""
    config_entry.version = 3
    data = dict(config_entry.data)
    hass.config_entries.async_update_entry(config_entry, data=data)
    assert await async_migrate_entry(hass, config_entry)
    data = dict(config_entry.data)
    assert config_entry.version == 8
    assert "Migration to version 8 successful" in caplog.text


@pytest.mark.usefixtures("ecomax_p")
async def test_migrate_entry_v4_5_to_v8(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test migrating entry from version 4 or 5 to version 8."""
    config_entry.version = 4
    data = dict(config_entry.data)
    del data[CONF_SUB_DEVICES]
    hass.config_entries.async_update_entry(config_entry, data=data)
    assert await async_migrate_entry(hass, config_entry)
    data = dict(config_entry.data)
    assert CONF_CAPABILITIES not in data
    assert CONF_SUB_DEVICES in data
    assert config_entry.version == 8
    assert "Migration to version 8 successful" in caplog.text


@pytest.mark.usefixtures("ecomax_860p3_o")
async def test_migrate_entry_v6_to_v8(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test migrating entry from version 6 to version 8."""
    config_entry.version = 6
    assert await async_migrate_entry(hass, config_entry)
    data = dict(config_entry.data)
    assert CONF_PRODUCT_ID in data
    assert data[CONF_PRODUCT_ID] == 51
    assert config_entry.version == 8
    assert "Migration to version 8 successful" in caplog.text


@pytest.mark.usefixtures("ecomax_860p3_o")
async def test_migrate_entry_v7_to_v8(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test migrating entry from version 7 to version 8."""
    config_entry.version = 7
    assert await async_migrate_entry(hass, config_entry)
    data = dict(config_entry.data)
    assert CONF_SOFTWARE in data
    assert data[CONF_SOFTWARE] == {
        "module_a": "6.10.32.K1",
        "module_b": None,
        "module_c": None,
        "ecolambda": "0.8.0",
        "ecoster": None,
        "panel": "6.30.36",
    }
    assert config_entry.version == 8
    assert "Migration to version 8 successful" in caplog.text


async def test_migrate_entry_with_timeout(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test migrating entry with get_device timeout."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.get_device",
        create=True,
        side_effect=TimeoutError,
    ):
        assert not await async_migrate_entry(hass, config_entry)

    assert "Migration failed" in caplog.text
