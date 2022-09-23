"""Test Plum ecoMAX connection."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from pyplumio import SerialConnection, TcpConnection
from pyplumio.devices import Device
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo
import pytest

from custom_components.plum_ecomax.connection import (
    EcomaxConnection,
    async_check_connection,
    async_get_connection_handler,
)
from custom_components.plum_ecomax.const import DOMAIN, ECOMAX
from tests.const import MOCK_CONFIG_DATA, MOCK_CONFIG_DATA_SERIAL


@patch("pyplumio.ethernet_parameters")
@patch(
    "custom_components.plum_ecomax.connection.async_get_source_ip",
    new_callable=AsyncMock,
    return_value="1.1.1.1",
)
async def test_async_get_connection_handler(
    mock_async_get_source_ip, mock_ethernet_parameters, hass: HomeAssistant
) -> None:
    """Test helper function to get connection handler."""
    connection = await async_get_connection_handler(hass, MOCK_CONFIG_DATA)
    assert isinstance(connection, TcpConnection)
    mock_async_get_source_ip.assert_awaited_once_with(
        hass, target_ip=IPV4_BROADCAST_ADDR
    )
    mock_ethernet_parameters.assert_called_once_with(ip="1.1.1.1")
    connection_serial = await async_get_connection_handler(
        hass, MOCK_CONFIG_DATA_SERIAL
    )
    assert isinstance(connection_serial, SerialConnection)


async def test_async_check_connection() -> None:
    """Test helper function to check the connection."""
    mock_connection = AsyncMock(spec=TcpConnection)
    mock_connection.host = "localhost"
    mock_device = AsyncMock(spec=Device)
    mock_connection.get_device = AsyncMock()
    mock_connection.get_device.return_value = mock_device
    mock_product = Mock(spec=ProductInfo)
    mock_modules = Mock(spec=ConnectedModules)
    mock_schedules = Mock()
    mock_device.get_value.side_effect = (
        mock_product,
        mock_modules,
        True,
        True,
        "fuel_burned",
        "boiler_control",
        asyncio.TimeoutError,
        mock_schedules,
    )
    mock_device.data = {
        "test_sensor": "test_value",
        "water_heater_temp": 50,
        "test_parameter": "test_value",
    }
    result = await async_check_connection(mock_connection)
    calls = (
        call("product"),
        call("modules"),
        call("sensors"),
        call("parameters"),
        call("fuel_burned", timeout=5),
        call("boiler_control", timeout=5),
        call("password", timeout=5),
        call("schedules", timeout=5),
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
            "schedules",
            "water_heater",
        ],
    )


async def test_async_setup(
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
    await connection.async_setup()

    mock_connection_handler.connect.assert_awaited_once()
    mock_connection_handler.get_device.assert_awaited_once_with(ECOMAX, timeout=20)

    # Check connection class properties.
    assert connection.host == "localhost"
    assert not hasattr(connection, "nonexistent")
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
    with pytest.raises(asyncio.TimeoutError):
        await connection.async_setup()

    # Check name with serial connection.
    mock_connection_handler = AsyncMock(spec=SerialConnection)
    connection = EcomaxConnection(hass, config_entry, mock_connection_handler)
    mock_connection_handler.device = "/dev/ttyUSB0"
    assert connection.name == "/dev/ttyUSB0"


@patch(
    "custom_components.plum_ecomax.connection.async_get_device_capabilities",
    new_callable=AsyncMock,
)
async def test_async_update_capabilities(
    mock_async_get_device_capabilities,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    caplog,
):
    """Test update capabilities."""
    mock_connection_handler = AsyncMock(spec=TcpConnection)
    mock_connection_handler.get_device = AsyncMock(spec=Device)
    connection = EcomaxConnection(hass, config_entry, mock_connection_handler)
    await connection.async_setup()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_update_entry"
    ) as mock_async_update_entry:
        await connection.async_update_device_capabilities()

    mock_async_update_entry.assert_called_once()
    mock_async_get_device_capabilities.assert_awaited_once()
    assert "Updated device capabilities list" in caplog.text
