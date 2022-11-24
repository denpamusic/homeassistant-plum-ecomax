"""Fixtures for Plum ecoMAX test suite."""

from typing import Generator
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio import Connection
from pyplumio.devices import Device, Mixer
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductInfo
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DOMAIN

from .const import MOCK_CONFIG


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="mock_device")
def fixture_mock_device() -> Generator[Device, None, None]:
    """Mock device instance."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device"
    ) as mock_device:
        mock_product_info = Mock(spec=ProductInfo)
        mock_mixer = AsyncMock(spec=Mixer)
        mock_mixer.index = 0
        mock_mixer.data = {
            "test_mixer_data": "test_mixer_value",
        }
        mock_device.data = {
            "test_data": "test_value",
            "product": mock_product_info,
            "password": "0000",
            "mixers": [mock_mixer],
        }
        mock_device.set_value = AsyncMock()
        yield mock_device


@pytest.fixture(name="async_add_entities")
def fixture_async_add_entities() -> Generator[AddEntitiesCallback, None, None]:
    """Mock add entities callback."""
    with patch(
        "homeassistant.helpers.entity_platform.AddEntitiesCallback"
    ) as mock_async_add_entities:
        yield mock_async_add_entities


@pytest.fixture(name="bypass_hass_write_ha_state")
def fixture_bypass_hass_write_ha_state() -> Generator[None, None, None]:
    """Bypass writing state to hass."""
    with patch("homeassistant.helpers.entity.Entity.async_write_ha_state"):
        yield


@pytest.fixture(name="bypass_model_check")
def fixture_bypass_model_check() -> Generator[None, None, None]:
    """Bypass controller model check."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type", 0
    ):
        yield


@pytest.fixture(name="connection")
def fixture_connection() -> Connection:
    """Create mock pyplumio connection."""
    return AsyncMock(spec=Connection)


@pytest.fixture(name="config_entry")
def fixture_config_entry(
    hass: HomeAssistant, connection: Connection
) -> MockConfigEntry:
    """Create mock config entry and add it to hass."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = EcomaxConnection(
        hass, config_entry, connection
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture(name="boiler_parameter")
def fixture_boiler_parameter() -> Parameter:
    """Create mock boiler parameter."""
    parameter = AsyncMock(spec=Parameter)
    parameter.value = 1
    parameter.min_value = 0
    parameter.max_value = 1
    return parameter
