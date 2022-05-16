"""Test Plum ecoMAX setup process."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax import async_setup_entry, async_unload_entry
from custom_components.plum_ecomax.connection import (
    EcomaxSerialConnection,
    EcomaxTcpConnection,
)
from custom_components.plum_ecomax.const import CONF_CONNECTION_TYPE, DOMAIN

from .const import MOCK_CONFIG_DATA, MOCK_CONFIG_DATA_SERIAL, MOCK_DEVICE_DATA


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """Test setup and unload of config entry."""
    # Set up mock config entries for TCP and serial.
    config_entry_tcp = MockConfigEntry(
        domain=DOMAIN,
        data=dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA),
        entry_id="test",
    )

    config_entry_serial = MockConfigEntry(
        domain=DOMAIN,
        data=dict(MOCK_CONFIG_DATA_SERIAL, **MOCK_DEVICE_DATA),
        entry_id="test2",
    )

    types = (EcomaxTcpConnection, EcomaxSerialConnection)
    for index, config_entry in enumerate((config_entry_tcp, config_entry_serial)):
        # Get specific connection class.
        cls = types[index]

        with patch(
            "custom_components.plum_ecomax." + cls.__name__ + ".async_setup",
            return_value=True,
        ) as mock_async_setup:
            # Set up and check entry.
            assert await async_setup_entry(hass, config_entry)
            assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
            assert isinstance(hass.data[DOMAIN][config_entry.entry_id], cls)
            mock_async_setup.assert_called_once()

        # Unload entries and verify that they are no longer present in data.
        with patch(
            "custom_components.plum_ecomax." + cls.__name__ + ".async_unload",
            return_value=True,
        ) as mock_async_unload:
            assert await async_unload_entry(hass, config_entry)
            assert config_entry.entry_id not in hass.data[DOMAIN]
            mock_async_unload.assert_called_once()


async def test_setup_entry_unknown_connection_type(hass: HomeAssistant) -> None:
    """Test setup with unknown connection type."""
    data = dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA)
    data[CONF_CONNECTION_TYPE] = "unknown"

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        entry_id="test",
    )

    assert not await async_setup_entry(hass, config_entry)


async def test_unload_entry_without_setup(hass: HomeAssistant) -> None:
    """Test unload missing entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA),
        entry_id="test",
    )

    with pytest.raises(KeyError):
        assert await async_unload_entry(hass, config_entry)
