"""Test Plum ecoMAX system health."""

from datetime import datetime
from typing import Any, cast
from unittest.mock import Mock, patch

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pyplumio import __version__ as pyplumio_version
from pyplumio.protocol import Statistics
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax import DOMAIN
from custom_components.plum_ecomax.const import ATTR_ENTITIES


@pytest.fixture(autouse=True)
def bypass_async_migrate_entry():
    """Bypass async migrate entry."""
    with patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True):
        yield


@pytest.fixture(autouse=True)
def bypass_connection_setup():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"):
        yield


async def get_system_health_info(hass: HomeAssistant, domain: str) -> dict[str, Any]:
    """Get system health info."""
    return cast(
        dict[str, Any], await hass.data["system_health"][domain].info_callback(hass)
    )


@pytest.mark.usefixtures("ecomax_p", "custom_fields")
async def test_system_health(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_integration
) -> None:
    """Test Plum ecoMAX system health."""
    await setup_integration(
        hass,
        config_entry,
        options={
            ATTR_ENTITIES: {
                Platform.BINARY_SENSOR: {
                    "custom_binary_sensor": {
                        "name": "Test custom binary sensor",
                        "key": "custom_binary_sensor",
                        "source_device": "ecomax",
                    },
                    "custom_binary_sensor2": {
                        "name": "Test custom binary sensor 2",
                        "key": "custom_binary_sensor2",
                        "source_device": "ecomax",
                    },
                },
                Platform.SENSOR: {
                    "custom_sensor": {
                        "name": "Test custom sensor",
                        "key": "custom_sensor",
                        "source_device": "ecomax",
                        "update_interval": 10,
                    }
                },
            }
        },
    )
    assert await async_setup_component(hass, "system_health", {})
    await hass.async_block_till_done()

    data = {
        "received_frames": 23,
        "sent_frames": 5,
        "failed_frames": 1,
        "connected_since": datetime.now(),
        "connection_losses": 0,
    }

    mock_statistics = Mock(spec=Statistics)
    mock_statistics.configure_mock(**data)

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.statistics",
        mock_statistics,
        create=True,
    ):
        info = await get_system_health_info(hass, DOMAIN)

    assert info == (data | {"pyplumio_version": pyplumio_version, "custom_entities": 3})
