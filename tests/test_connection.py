"""Test the Plum ecoMAX connection."""
import logging
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
import pyplumio
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import (
    EcomaxSerialConnection,
    EcomaxTcpConnection,
)
from custom_components.plum_ecomax.const import (
    CONF_CAPABILITIES,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SOFTWARE,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
    CONNECTION_CHECK_TRIES,
)

from .const import MOCK_CONFIG


async def test_async_setup(
    connection: EcomaxTcpConnection,
    device_info: DeviceInfo,
    config_entry: MockConfigEntry,
) -> None:
    """Test async setup for connection."""
    with patch(
        "custom_components.plum_ecomax.connection.async_get_source_ip",
        return_value="2.2.2.2",
    ), patch(
        "custom_components.plum_ecomax.connection.pyplumio.TcpConnection.set_eth"
    ) as mock_set_eth, patch(
        "custom_components.plum_ecomax.connection.pyplumio.TcpConnection.on_closed"
    ) as mock_on_closed:
        # Set up mock config entry and run async_setup.
        await connection.async_setup(config_entry)

    # Check that attributes was correctly set.
    assert connection.software == MOCK_CONFIG[CONF_SOFTWARE]
    assert connection.model == "ecoMAX 350P2"
    assert connection.uid == MOCK_CONFIG[CONF_UID]
    assert connection.capabilities == MOCK_CONFIG[CONF_CAPABILITIES]
    assert connection.update_interval == MOCK_CONFIG[CONF_UPDATE_INTERVAL]
    assert connection.device_info == device_info
    assert connection.host == MOCK_CONFIG[CONF_HOST]
    assert connection.port == MOCK_CONFIG[CONF_PORT]

    # Finally check that set_eth was called and connection
    # closed callback was successfully added.
    mock_set_eth.assert_called_once_with(ip="2.2.2.2")
    mock_on_closed.assert_called_once_with(connection.connection_closed)


async def test_async_unload(connection: EcomaxTcpConnection) -> None:
    """Test async unload."""
    mock_hass = AsyncMock()
    connection = EcomaxTcpConnection(
        host=MOCK_CONFIG[CONF_HOST],
        port=MOCK_CONFIG[CONF_PORT],
        hass=mock_hass,
    )
    await connection.async_unload()

    # Check that connection will be closed on async_unload.
    mock_hass.async_add_executor_job.assert_called_once_with(connection.close)


async def test_update_entities_callbacks(connection: EcomaxTcpConnection):
    """Test entity update callbacks."""
    # Set up mocks for DeviceCollection and Connection objects.
    mock_devices = Mock()
    mock_devices.has.return_value = True
    mock_devices.ecomax.data = {"test": 1}

    # Register callback and update entities once. Next make sure, that
    # callback was called once and ecomax object was correctly set.
    mock_callback = AsyncMock()
    connection.register_callback(mock_callback)
    await connection.update_entities(devices=mock_devices, connection=connection)
    assert mock_devices.ecomax.data["test"] == 1
    mock_callback.assert_called_once()

    # Remove callback and update entities once more.
    mock_callback.reset_mock()
    connection.remove_callback(mock_callback)
    await connection.update_entities(devices=mock_devices, connection=connection)

    # Make sure that callback was not called this time around.
    mock_callback.assert_not_called()


async def test_connection_closed_callback(connection: EcomaxTcpConnection):
    """Test callback fired on connection close."""
    mock_callback = AsyncMock()
    mock_connection = Mock()
    connection.register_callback(mock_callback)
    connection.ecomax = True
    await connection.connection_closed(mock_connection)
    mock_callback.assert_called_once()
    assert not connection.ecomax.data
    assert not connection.ecomax.parameters


async def test_get_connection(hass: HomeAssistant):
    """Test getter for PyPlumIO connection instance."""
    connection = EcomaxTcpConnection(hass=hass, host="1.1.1.1")
    assert isinstance(connection.get_connection(), pyplumio.TcpConnection)
    connection = EcomaxSerialConnection(hass=hass)
    assert isinstance(connection.get_connection(), pyplumio.SerialConnection)
    assert connection.device == "/dev/ttyUSB0"


async def test_connection_check(hass: HomeAssistant, caplog):
    """Test connection check with supported and unsupported device."""
    # Crete PyPlumIO connection mock and inject it.
    mock_pyplumio_connection = Mock()
    mock_pyplumio_connection.task = AsyncMock()
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxTcpConnection.get_connection",
        return_value=mock_pyplumio_connection,
    ):
        connection = EcomaxTcpConnection(hass=hass, host="1.1.1.1")

    # Call connection check and get underlying callback.
    await connection.check()
    mock_pyplumio_connection.task.assert_called_once()
    args, kwargs = mock_pyplumio_connection.task.call_args
    assert kwargs == {"interval": 1, "reconnect_on_failure": False}

    # Get check callback and create mock device.
    callback = args[0]
    devices = Mock()
    devices.ecomax = Mock()
    devices.ecomax.data = {}
    devices.ecomax.parameters = {}
    devices.ecomax.uid = MOCK_CONFIG[CONF_UID]
    devices.ecomax.software = MOCK_CONFIG[CONF_SOFTWARE]
    devices.ecomax.product = MOCK_CONFIG[CONF_MODEL]
    devices.ecomax.data = {"test1": 1, "water_heater_temp": 50}
    devices.ecomax.parameters = {"test2": 2, "test3": 4}

    # Call callback and ensure, that all properties is set
    # and connection is closed.
    await callback(devices, mock_pyplumio_connection)
    assert connection.uid == MOCK_CONFIG[CONF_UID]
    assert connection.software == MOCK_CONFIG[CONF_SOFTWARE]
    assert connection.model == "ecoMAX 350P2"
    assert connection.capabilities == [
        "fuel_burned",
        "test1",
        "water_heater_temp",
        "test2",
        "test3",
        "water_heater",
    ]
    mock_pyplumio_connection.close.assert_called_once()
    mock_pyplumio_connection.close.reset_mock()

    # Test when callback is called with unsupported device.
    devices.ecomax = Mock()
    devices.ecomax.data = devices.ecomax.parameters = {}

    # Try until last retry.
    for _ in range(CONNECTION_CHECK_TRIES):
        await callback(devices, mock_pyplumio_connection)

    # Check that connection is not closed until last retry.
    caplog.clear()
    mock_pyplumio_connection.close.assert_not_called()
    await callback(devices, mock_pyplumio_connection)
    assert caplog.record_tuples == [
        (
            "custom_components.plum_ecomax.connection",
            logging.ERROR,
            "Connection succeeded, but device failed to respond.",
        )
    ]
    mock_pyplumio_connection.close.assert_called_once()
