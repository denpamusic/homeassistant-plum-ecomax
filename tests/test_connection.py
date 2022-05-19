"""Test the Plum ecoMAX connection."""
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.helpers.entity import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.const import (
    CONF_CAPABILITIES,
    CONF_HOST,
    CONF_PORT,
    CONF_SOFTWARE,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
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
    assert connection.ecomax is None
