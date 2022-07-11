"""Test Plum ecoMAX connection."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from pyplumio import SerialConnection, TcpConnection
from pyplumio.devices import Device
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo

from custom_components.plum_ecomax.connection import (
    EcomaxConnection,
    check_connection,
    get_connection_handler,
)
from custom_components.plum_ecomax.const import DOMAIN
from tests.const import MOCK_CONFIG_DATA, MOCK_CONFIG_DATA_SERIAL


@patch("pyplumio.ethernet_parameters")
@patch(
    "custom_components.plum_ecomax.connection.async_get_source_ip",
    new_callable=AsyncMock,
    return_value="1.1.1.1",
)
async def test_get_connection_handler(
    mock_async_get_source_ip, mock_ethernet_parameters, hass: HomeAssistant
) -> None:
    """Test helper function to get connection handler."""
    connection = await get_connection_handler(hass, MOCK_CONFIG_DATA)
    assert isinstance(connection, TcpConnection)
    mock_async_get_source_ip.assert_awaited_once_with(
        hass, target_ip=IPV4_BROADCAST_ADDR
    )
    mock_ethernet_parameters.assert_called_once_with(ip="1.1.1.1")
    connection_serial = await get_connection_handler(hass, MOCK_CONFIG_DATA_SERIAL)
    assert isinstance(connection_serial, SerialConnection)


async def test_check_connection() -> None:
    """Test helper function to check the connection."""
    mock_connection = AsyncMock(spec=TcpConnection)
    mock_connection.host = "localhost"
    mock_device = AsyncMock(spec=Device)
    mock_connection.get_device = AsyncMock()
    mock_connection.get_device.return_value = mock_device
    mock_product = Mock(spec=ProductInfo)
    mock_modules = Mock(spec=ConnectedModules)
    mock_device.get_value.side_effect = (
        mock_product,
        mock_modules,
        {"test_sensor": "test_value", "water_heater_temp": 50},
        {"test_parameter": "test_value"},
        "fuel_burned",
        "boiler_control",
        asyncio.TimeoutError,
    )
    result = await check_connection(mock_connection)
    calls = (
        call("product"),
        call("modules"),
        call("sensors"),
        call("parameters"),
        call("fuel_burned"),
        call("boiler_control"),
        call("password"),
    )
    mock_device.get_value.assert_has_calls(calls)
    mock_connection.close.assert_awaited_once()
    assert result == (
        "localhost",
        mock_product,
        mock_modules,
        [
            "product",
            "modules",
            "test_sensor",
            "water_heater_temp",
            "test_parameter",
            "fuel_burned",
            "boiler_control",
            "water_heater",
        ],
    )


@patch("homeassistant.core.EventBus.async_listen_once")
async def test_async_setup(
    mock_async_listen_once,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    caplog,
) -> None:
    """Test connection setup."""
    mock_connection_handler = AsyncMock(spec=TcpConnection)
    mock_connection_handler.host = "localhost"
    mock_device = AsyncMock(spec=Device)
    mock_connection_handler.get_device = AsyncMock(
        side_effect=(mock_device, asyncio.TimeoutError)
    )
    connection = EcomaxConnection(hass, config_entry, mock_connection_handler)
    assert await connection.async_setup()
    mock_async_listen_once.assert_called_once()

    # Test hass stop callback.
    args, _ = mock_async_listen_once.call_args
    event, callback = args
    assert event == EVENT_HOMEASSISTANT_STOP
    await callback()
    mock_connection_handler.close.assert_awaited_once()

    mock_connection_handler.connect.assert_awaited_once()
    mock_connection_handler.get_device.assert_awaited_once_with("ecomax")

    # Check connection class properties.
    assert connection.host == "localhost"
    assert connection.nonexistent is None
    assert connection.device == mock_device
    assert connection.model == "ecoMAX TEST"
    assert connection.uid == "D251PAKR3GCPZ1K8G05G0"
    assert connection.software == "1.13.5.A1"
    assert connection.capabilities == ["fuel_burned", "heating_temp"]
    assert connection.name == "localhost"
    assert connection.connection == mock_connection_handler
    assert connection.device_info == DeviceInfo(
        name=connection.name,
        identifiers={(DOMAIN, connection.uid)},
        manufacturer="Plum Sp. z o.o.",
        model=f"{connection.model}",
        sw_version=connection.software,
    )

    # Check with device timeout.
    assert not await connection.async_setup()
    assert "ecomax device not found" in caplog.text

    # Check name with serial connection.
    mock_connection_handler = AsyncMock(spec=SerialConnection)
    connection = EcomaxConnection(hass, config_entry, mock_connection_handler)
    mock_connection_handler.device = "/dev/ttyUSB0"
    assert connection.name == "/dev/ttyUSB0"
