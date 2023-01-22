"""Test Plum ecoMAX connection."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from pyplumio import SerialConnection, TcpConnection
from pyplumio.devices import Device, Mixer
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo
import pytest

from custom_components.plum_ecomax.connection import (
    ATTR_MODULES,
    DEVICE_TIMEOUT,
    VALUE_TIMEOUT,
    EcomaxConnection,
    async_check_connection,
    async_get_connection_handler,
    async_get_sub_devices,
)
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_PRODUCT,
    CONF_SUB_DEVICES,
    DOMAIN,
    ECOMAX,
)
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


async def test_async_check_connection(mock_device: Device) -> None:
    """Test helper function to check the connection."""
    mock_connection = AsyncMock(spec=TcpConnection)
    mock_connection.host = "localhost"
    mock_connection.get_device = AsyncMock()
    mock_connection.get_device.return_value = mock_device
    mock_product = Mock(spec=ProductInfo)
    mock_modules = Mock(spec=ConnectedModules)
    mock_device.get_value.side_effect = (
        mock_product,
        mock_modules,
        True,
    )
    result = await async_check_connection(mock_connection)
    calls = (
        call(ATTR_PRODUCT, timeout=VALUE_TIMEOUT),
        call(ATTR_MODULES, timeout=VALUE_TIMEOUT),
    )
    mock_device.get_value.assert_has_calls(calls)
    mock_connection.close.assert_awaited_once()
    assert result == ("localhost", mock_product, mock_modules, [ATTR_MIXERS])


async def test_async_get_sub_devices(mock_device: Device) -> None:
    """Test helper function to check get connected sub-devices."""
    mock_device.get_value.return_value = {0: Mock(spec=Mixer)}
    mock_device.get_value.side_effect = (None, asyncio.TimeoutError)
    sub_devices = await async_get_sub_devices(mock_device)
    assert ATTR_MIXERS in sub_devices

    # Test with timeout while trying to get mixers.
    sub_devices = await async_get_sub_devices(mock_device)
    assert not sub_devices


async def test_async_setup(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    caplog,
) -> None:
    """Test connection setup."""
    mock_connection_handler = AsyncMock(spec=TcpConnection)
    mock_connection_handler.host = "localhost"
    mock_device = AsyncMock(spec=Device)
    mock_device.get_value = AsyncMock(side_effect=asyncio.TimeoutError)
    mock_connection_handler.get_device = AsyncMock(
        side_effect=(mock_device, asyncio.TimeoutError)
    )
    connection = EcomaxConnection(hass, config_entry, mock_connection_handler)

    # Test device not ready.
    with pytest.raises(ConfigEntryNotReady):
        assert connection.device is None

    await connection.async_setup()

    mock_connection_handler.connect.assert_awaited_once()
    mock_connection_handler.get_device.assert_awaited_once_with(
        ECOMAX, timeout=DEVICE_TIMEOUT
    )

    # Check connection class properties.
    assert connection.host == "localhost"
    assert not hasattr(connection, "nonexistent")
    assert connection.device == mock_device
    assert connection.model == "ecoMAX 123A"
    assert connection.uid == "D251PAKR3GCPZ1K8G05G0"
    assert connection.software == "1.13.5.A1"
    assert connection.name == "localhost"
    assert connection.connection == mock_connection_handler
    assert connection.device_info == DeviceInfo(
        name=connection.name,
        identifiers={(DOMAIN, connection.uid)},
        manufacturer="Plum Sp. z o.o.",
        model=f"{connection.model}",
        sw_version=connection.software,
        configuration_url="http://example.com",
    )

    # Check with device timeout.
    with pytest.raises(asyncio.TimeoutError):
        await connection.async_setup()

    # Check name with serial connection.
    mock_connection_handler = AsyncMock(spec=SerialConnection)
    connection = EcomaxConnection(hass, config_entry, mock_connection_handler)
    mock_connection_handler.device = "/dev/ttyUSB0"
    assert connection.name == "/dev/ttyUSB0"


async def test_async_update_sub_device(
    hass: HomeAssistant, config_entry: ConfigEntry, mock_device: Device
) -> None:
    """Test function to update connected sub-devices."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    with patch(
        "custom_components.plum_ecomax.connection.async_get_sub_devices",
        return_value=[ATTR_MIXERS],
    ) as mock_async_get_sub_devices:
        await connection.async_update_sub_devices()

    mock_async_get_sub_devices.assert_awaited_once_with(mock_device)
    assert config_entry.data[CONF_SUB_DEVICES] == [ATTR_MIXERS]
