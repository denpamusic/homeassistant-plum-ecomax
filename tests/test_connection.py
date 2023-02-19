"""Test Plum ecoMAX connection."""

import asyncio
import logging
from typing import Final
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from pyplumio import Connection, SerialConnection, TcpConnection
from pyplumio.const import FrameType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.structures.modules import ConnectedModules
from pyplumio.structures.product_info import ProductInfo
import pytest

from custom_components.plum_ecomax.climate import ATTR_THERMOSTATS
from custom_components.plum_ecomax.connection import (
    ATTR_MODULES,
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_check_connection,
    async_get_capabilities,
    async_get_connection_handler,
    async_get_sub_devices,
)
from custom_components.plum_ecomax.const import (
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXERS,
    ATTR_PRODUCT,
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_WATER_HEATER,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_SERIAL,
    DOMAIN,
    ECOMAX,
    MANUFACTURER,
)

SOURCE_IP: Final = "1.1.1.1"


@pytest.fixture(name="async_get_source_ip")
def fixture_async_get_source_ip():
    """Mock async get source ip."""
    with patch(
        "custom_components.plum_ecomax.connection.async_get_source_ip",
        return_value=SOURCE_IP,
    ) as async_get_source_ip:
        yield async_get_source_ip


async def test_async_get_connection_handler(
    hass: HomeAssistant, async_get_source_ip, config_data
) -> None:
    """Test helper function to get connection handler."""
    with patch("pyplumio.ethernet_parameters") as mock_ethernet_parameters:
        connection: Connection = await async_get_connection_handler(hass, config_data)

    assert isinstance(connection, TcpConnection)
    async_get_source_ip.assert_awaited_once_with(hass, target_ip=IPV4_BROADCAST_ADDR)
    mock_ethernet_parameters.assert_called_once_with(ip=SOURCE_IP)

    # Test with serial connection.
    config_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_SERIAL
    connection = await async_get_connection_handler(hass, config_data)
    assert isinstance(connection, SerialConnection)


@pytest.mark.usefixtures("mixers")
async def test_async_check_connection(
    config_data: dict[str, str], ecomax_p: EcoMAX
) -> None:
    """Test helper function to check the connection."""
    mock_product = Mock(spec=ProductInfo)
    mock_modules = Mock(spec=ConnectedModules)
    mock_ecomax = Mock(spec=EcoMAX)
    mock_ecomax.get = AsyncMock(side_effect=(mock_product, mock_modules, True))
    mock_ecomax.data = ecomax_p.data
    mock_connection = AsyncMock(spec=TcpConnection)
    mock_connection.configure_mock(host=config_data.get(CONF_HOST))
    mock_connection.get = AsyncMock(return_value=mock_ecomax)
    result = await async_check_connection(mock_connection)
    mock_ecomax.get.assert_has_calls(
        [
            call(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT),
            call(ATTR_MODULES, timeout=DEFAULT_TIMEOUT),
        ]
    )
    mock_connection.close.assert_awaited_once()
    assert result == (
        config_data.get(CONF_HOST),
        mock_product,
        mock_modules,
        [ATTR_MIXERS],
    )


@pytest.mark.usefixtures("mixers", "thermostats", "water_heater")
async def test_async_get_sub_devices(ecomax_p: EcoMAX, caplog) -> None:
    """Test helper function to check get connected sub-devices."""
    caplog.set_level(logging.INFO)

    assert await async_get_sub_devices(ecomax_p) == [
        ATTR_MIXERS,
        ATTR_THERMOSTATS,
        ATTR_WATER_HEATER,
    ]

    assert "Detected 1 mixer" in caplog.text
    assert "Detected 1 thermostat" in caplog.text
    assert "Detected indirect water heater" in caplog.text


@pytest.mark.usefixtures("ecomax_p_51")
async def test_async_get_capabilities(ecomax_p: EcoMAX, caplog) -> None:
    """Test helper function to check device capabilities."""
    caplog.set_level(logging.INFO)
    assert await async_get_capabilities(ecomax_p) == [ATTR_REGDATA]
    assert "Detected supported regulator data" in caplog.text


async def test_async_setup(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_data: dict[str, str],
    config_data: dict[str, str],
) -> None:
    """Test connection setup."""
    mock_ecomax = Mock(spec=EcoMAX)
    mock_ecomax.wait_for = AsyncMock(
        side_effect=(True, True, True, asyncio.TimeoutError)
    )
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.configure_mock(host=config_data.get(CONF_HOST))
    mock_connection.get = AsyncMock(side_effect=(mock_ecomax, asyncio.TimeoutError))
    connection = EcomaxConnection(hass, config_entry, mock_connection)

    # Test config not ready when device property is not set.
    with pytest.raises(ConfigEntryNotReady):
        assert connection.device is None

    await connection.async_setup()
    mock_connection.connect.assert_awaited_once()
    mock_connection.get.assert_awaited_once_with(ECOMAX, timeout=DEFAULT_TIMEOUT)

    # Check connection class properties for tcp connection.
    assert not hasattr(connection, "nonexistent")
    assert connection.host == config_data.get(CONF_HOST)
    assert connection.model == device_data.get(CONF_MODEL)
    assert connection.uid == device_data.get(CONF_UID)
    assert connection.software == device_data.get(CONF_SOFTWARE)
    assert connection.name == config_data.get(CONF_HOST)
    assert connection.device == mock_ecomax
    assert connection.connection == mock_connection
    assert connection.product_type == device_data.get(CONF_PRODUCT_TYPE)
    assert connection.device_info == DeviceInfo(
        name=connection.name,
        identifiers={(DOMAIN, connection.uid)},
        manufacturer=MANUFACTURER,
        model=f"{connection.model}",
        sw_version=connection.software,
        configuration_url=f"http://{config_data.get(CONF_HOST)}",
    )

    # Check with device timeout.
    with pytest.raises(asyncio.TimeoutError):
        await connection.async_setup()

    # Check connection name for serial connection.
    mock_connection = AsyncMock(spec=SerialConnection)
    mock_connection.device = config_data.get(CONF_DEVICE)
    connection = EcomaxConnection(hass, config_entry, mock_connection)
    assert connection.name == config_data.get(CONF_DEVICE)


async def test_setup_thermostats(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test setup thermostats."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device"
    ) as mock_device:
        mock_device.request = AsyncMock(side_effect=(True, asyncio.TimeoutError))
        assert await connection.setup_thermostats()
        assert not await connection.setup_thermostats()

    assert "Timed out while trying to setup thermostats" in caplog.text
    mock_device.request.assert_any_await(
        ATTR_THERMOSTAT_PARAMETERS,
        FrameType.REQUEST_THERMOSTAT_PARAMETERS,
        retries=5,
        timeout=DEFAULT_TIMEOUT,
    )


async def test_setup_mixers(
    hass: HomeAssistant, config_entry: ConfigEntry, caplog
) -> None:
    """Test setup mixers."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device"
    ) as mock_device:
        mock_device.request = AsyncMock(side_effect=(True, asyncio.TimeoutError))
        assert await connection.setup_mixers()
        assert not await connection.setup_mixers()

    assert "Timed out while trying to setup mixers" in caplog.text
    mock_device.request.assert_any_await(
        ATTR_MIXER_PARAMETERS,
        FrameType.REQUEST_MIXER_PARAMETERS,
        retries=5,
        timeout=DEFAULT_TIMEOUT,
    )


async def test_async_update_sub_device(
    hass: HomeAssistant, config_entry: ConfigEntry, ecomax_p: EcoMAX
) -> None:
    """Test function to update connected sub-devices."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload"
    ) as mock_async_reload, patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device",
        return_value=ecomax_p,
    ) as mock_device, patch(
        "custom_components.plum_ecomax.connection.async_get_sub_devices",
        return_value=[ATTR_MIXERS],
    ) as mock_async_get_sub_devices:
        await connection.async_update_sub_devices()

    mock_async_get_sub_devices.assert_awaited_once_with(mock_device)
    mock_async_reload.assert_awaited_once_with(config_entry.entry_id)
    assert config_entry.data[CONF_SUB_DEVICES] == [ATTR_MIXERS]
