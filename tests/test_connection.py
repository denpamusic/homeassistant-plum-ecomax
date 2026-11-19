"""Test Plum ecoMAX connection."""

from functools import partial
import logging
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pyplumio.connection import SerialConnection
from pyplumio.devices.ecomax import EcoMAX
import pytest

from custom_components.plum_ecomax.connection import (
    ATTR_SENSORS,
    WAIT_FOR_DEVICE_SECONDS,
    WAIT_FOR_SETUP_SECONDS,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
    async_resolve_host_name,
)
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_THERMOSTATS,
    ATTR_WATER_HEATER,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_UID,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DeviceType,
)


@pytest.mark.parametrize(
    ("host", "ip"), (("example.com", "8.8.8.8"), ("8.8.8.8", "8.8.8.8"))
)
@patch("aiohttp.resolver.AsyncResolver.resolve")
@patch("aiohttp.resolver.AsyncResolver.close")
async def test_async_resolve_host_name(
    mock_close, mock_resolve, host: str, ip: str, hass: HomeAssistant
) -> None:
    """Test resolving a host name."""
    mock_resolve.side_effect = ([{CONF_HOST: ip}], None)
    result = await async_resolve_host_name(hass, host)
    assert result == ip
    mock_resolve.assert_awaited_once_with(host)
    mock_close.assert_awaited_once()
    result2 = await async_resolve_host_name(hass, host)
    assert result2 is None


@pytest.mark.parametrize(
    "connection_type",
    (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL),
)
async def test_async_get_connection_handler(
    connection_type: str,
    tcp_config_data: dict[str, Any],
    serial_config_data: dict[str, Any],
) -> None:
    """Test helper function to get connection handler."""
    connection_partial = partial(async_get_connection_handler, connection_type)
    if connection_type == CONNECTION_TYPE_TCP:
        connection = await connection_partial(tcp_config_data)
        expected_url = (
            f"socket://{tcp_config_data[CONF_HOST]}:{tcp_config_data[CONF_PORT]}"
        )
    else:
        connection = await connection_partial(serial_config_data)
        expected_url = serial_config_data[CONF_DEVICE]

    assert isinstance(connection, SerialConnection)
    assert connection.url == expected_url


@pytest.mark.usefixtures("mixers", "thermostats", "water_heater")
async def test_async_get_sub_devices(ecomax_p: EcoMAX, caplog) -> None:
    """Test helper function to check get connected sub-devices."""
    caplog.set_level(logging.INFO)

    assert await async_get_sub_devices(ecomax_p) == [
        ATTR_MIXERS,
        ATTR_THERMOSTATS,
        ATTR_WATER_HEATER,
    ]

    assert "Detected 2 mixers" in caplog.text
    assert "Detected 1 thermostat" in caplog.text
    assert "Detected indirect water heater" in caplog.text


async def test_async_setup(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    tcp_config_data: dict[str, Any],
) -> None:
    """Test connection setup."""
    mock_ecomax = AsyncMock(spec=EcoMAX)
    mock_ecomax.wait_for = AsyncMock(side_effect=(None, TimeoutError))
    mock_connection = Mock(spec=SerialConnection)
    mock_connection.configure_mock(url=tcp_config_data.get(CONF_HOST))
    mock_connection.device.return_value.__aenter__ = AsyncMock(
        side_effect=(mock_ecomax, mock_ecomax, TimeoutError)
    )
    mock_connection.device.return_value.__aexit__ = AsyncMock(return_value=False)
    connection = EcomaxConnection(hass, config_entry, mock_connection)

    # Test config not ready when device property is not set.
    with pytest.raises(ConfigEntryNotReady) as exc_info:
        connection.device

    assert exc_info.value.translation_key == "device_not_ready"
    assert exc_info.value.translation_placeholders == {"device": "ecoMAX 850P2-C"}
    await connection.async_setup()
    mock_connection.connect.assert_awaited_once()
    mock_connection.device.assert_called_once_with(
        DeviceType.ECOMAX, timeout=WAIT_FOR_DEVICE_SECONDS
    )
    mock_ecomax.wait_for.assert_awaited_once_with(
        ATTR_SENSORS, timeout=WAIT_FOR_SETUP_SECONDS
    )

    # Check connection class properties for tcp connection.
    assert not hasattr(connection, "nonexistent")
    assert connection.url == tcp_config_data.get(CONF_HOST)
    assert connection.model == tcp_config_data.get(CONF_MODEL)
    assert connection.uid == tcp_config_data.get(CONF_UID)
    assert connection.software == tcp_config_data.get(CONF_SOFTWARE)
    assert connection.name == config_entry.title
    assert connection.device == mock_ecomax
    assert connection.product_type == tcp_config_data.get(CONF_PRODUCT_TYPE)
    assert connection.product_id == tcp_config_data.get(CONF_PRODUCT_ID)

    # Check with sensors wait_for timeout.
    with pytest.raises(TimeoutError):
        await connection.async_setup()

    # Check with device timeout.
    with pytest.raises(TimeoutError):
        await connection.async_setup()
