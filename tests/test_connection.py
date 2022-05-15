"""Test the Plum ecoMAX connection."""
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.const import (
    CONF_CAPABILITIES,
    CONF_SOFTWARE,
    CONF_UID,
    DOMAIN,
)

from .const import MOCK_CONFIG_DATA, MOCK_DEVICE_DATA


async def test_async_setup(connection: EcomaxTcpConnection) -> None:
    """Test async setup for connection."""
    with patch(
        "custom_components.plum_ecomax.connection.async_get_source_ip",
        return_value="2.2.2.2",
    ), patch(
        "custom_components.plum_ecomax.connection.pyplumio.TcpConnection.set_eth"
    ) as mock_set_eth, patch(
        "custom_components.plum_ecomax.connection.pyplumio.TcpConnection.on_closed"
    ) as mock_on_closed:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA),
            entry_id="test",
        )
        await connection.async_setup(config_entry)
        assert connection.software == MOCK_DEVICE_DATA[CONF_SOFTWARE]
        assert connection.model == "ecoMAX 350P2"
        assert connection.uid == MOCK_DEVICE_DATA[CONF_UID]
        assert connection.capabilities == MOCK_DEVICE_DATA[CONF_CAPABILITIES]
        mock_set_eth.assert_called_once_with(ip="2.2.2.2")
        mock_on_closed.assert_called_once_with(connection.connection_closed)
