"""Test Plum ecoMAX connection."""

from functools import partial
import logging
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pyplumio import RequestError
from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.const import FrameType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PARAMETERS
import pytest

from custom_components.plum_ecomax.connection import (
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    WAIT_FOR_DEVICE_SECONDS,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
    async_resolve_host_name,
)
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_REGDATA,
    ATTR_THERMOSTATS,
    ATTR_WATER_HEATER,
    CONF_HOST,
    CONF_MODEL,
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
    ("connection_type", "connection_cls"),
    ((CONNECTION_TYPE_TCP, TcpConnection), (CONNECTION_TYPE_SERIAL, SerialConnection)),
)
@patch("pyplumio.EthernetParameters")
@patch("custom_components.plum_ecomax.connection.async_resolve_host_name")
@patch("custom_components.plum_ecomax.connection.async_get_source_ip")
async def test_async_get_connection_handler(
    mock_async_get_source_ip,
    mock_async_resolve_host_name,
    mock_ethernet_parameters,
    connection_type: str,
    connection_cls: type[Connection],
    hass: HomeAssistant,
    tcp_config_data: dict[str, Any],
    serial_config_data: dict[str, Any],
) -> None:
    """Test helper function to get connection handler."""
    connection_partial = partial(async_get_connection_handler, connection_type, hass)
    if connection_type == CONNECTION_TYPE_TCP:
        connection = await connection_partial(tcp_config_data)
        resolver_func = mock_async_resolve_host_name
        mock_async_resolve_host_name.assert_awaited_once_with(hass, host="localhost")
    else:
        connection = await connection_partial(serial_config_data)
        resolver_func = mock_async_get_source_ip
        mock_async_get_source_ip.assert_awaited_once_with(
            hass, target_ip=IPV4_BROADCAST_ADDR
        )

    assert isinstance(connection, connection_cls)
    mock_ethernet_parameters.assert_called_once_with(ip=resolver_func.return_value)


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
    mock_ecomax.wait_for = AsyncMock(side_effect=(True, True, True, TimeoutError))
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.configure_mock(host=tcp_config_data.get(CONF_HOST))
    mock_connection.device.return_value.__aenter__ = AsyncMock(
        side_effect=(mock_ecomax, TimeoutError)
    )
    mock_connection.device.return_value.__aexit__ = AsyncMock()
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

    # Check connection class properties for tcp connection.
    assert not hasattr(connection, "nonexistent")
    assert connection.host == tcp_config_data.get(CONF_HOST)
    assert connection.model == tcp_config_data.get(CONF_MODEL)
    assert connection.uid == tcp_config_data.get(CONF_UID)
    assert connection.software == tcp_config_data.get(CONF_SOFTWARE)
    assert connection.name == config_entry.title
    assert connection.device == mock_ecomax
    assert connection.product_type == tcp_config_data.get(CONF_PRODUCT_TYPE)
    assert connection.product_id == tcp_config_data.get(CONF_PRODUCT_ID)

    # Check with device timeout.
    with pytest.raises(TimeoutError):
        await connection.async_setup()


@patch("custom_components.plum_ecomax.connection.EcomaxConnection.device")
@pytest.mark.parametrize(
    ("request_result", "expected_result", "error_message"),
    (
        (True, True, None),
        (
            RequestError("error message", FrameType.REQUEST_THERMOSTAT_PARAMETERS),
            False,
            f"Request for '{ATTR_THERMOSTAT_PARAMETERS}' "
            f"with {repr(FrameType.REQUEST_THERMOSTAT_PARAMETERS)} failed",
        ),
    ),
)
async def test_async_setup_thermostats(
    mock_device,
    request_result: bool | RequestError,
    expected_result: bool,
    error_message: str | None,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    caplog,
) -> None:
    """Test setup thermostats with cache."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    mock_device.request = AsyncMock(side_effect=(request_result,))
    assert await connection.async_setup_thermostats() is expected_result
    assert await connection.async_setup_thermostats() is expected_result
    mock_device.request.assert_awaited_once_with(
        name=ATTR_THERMOSTAT_PARAMETERS,
        frame_type=FrameType.REQUEST_THERMOSTAT_PARAMETERS,
        retries=DEFAULT_RETRIES,
        timeout=DEFAULT_TIMEOUT,
    )
    if error_message:
        assert error_message in caplog.text


@patch("custom_components.plum_ecomax.connection.EcomaxConnection.device")
@pytest.mark.parametrize(
    ("request_result", "expected_result", "error_message"),
    (
        (True, True, None),
        (
            RequestError("error message", FrameType.REQUEST_MIXER_PARAMETERS),
            False,
            f"Request for '{ATTR_MIXER_PARAMETERS}' "
            f"with {repr(FrameType.REQUEST_MIXER_PARAMETERS)} failed",
        ),
    ),
)
async def test_async_setup_mixers(
    mock_device,
    request_result: bool | RequestError,
    expected_result: bool,
    error_message: str | None,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    caplog,
) -> None:
    """Test setup mixers with cache."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    mock_device.request = AsyncMock(side_effect=(request_result,))
    assert await connection.async_setup_mixers() is expected_result
    assert await connection.async_setup_mixers() is expected_result
    mock_device.request.assert_awaited_once_with(
        name=ATTR_MIXER_PARAMETERS,
        frame_type=FrameType.REQUEST_MIXER_PARAMETERS,
        retries=DEFAULT_RETRIES,
        timeout=DEFAULT_TIMEOUT,
    )
    if error_message:
        assert error_message in caplog.text


@patch("custom_components.plum_ecomax.connection.EcomaxConnection.device")
@pytest.mark.parametrize(
    ("request_result", "expected_result", "error_message"),
    (
        (True, True, None),
        (
            RequestError("error message", FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
            False,
            f"Request for '{ATTR_REGDATA}' "
            f"with {repr(FrameType.REQUEST_REGULATOR_DATA_SCHEMA)} failed",
        ),
    ),
)
async def test_async_setup_regdata(
    mock_device,
    request_result: bool | RequestError,
    expected_result: bool,
    error_message: str | None,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    caplog,
) -> None:
    """Test setup regdata with cache."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=TcpConnection))
    mock_device.request = AsyncMock(side_effect=(request_result,))
    assert await connection.async_setup_regdata() is expected_result
    assert await connection.async_setup_regdata() is expected_result
    mock_device.request.assert_awaited_once_with(
        name=ATTR_REGDATA,
        frame_type=FrameType.REQUEST_REGULATOR_DATA_SCHEMA,
        retries=DEFAULT_RETRIES,
        timeout=DEFAULT_TIMEOUT,
    )
    if error_message:
        assert error_message in caplog.text
