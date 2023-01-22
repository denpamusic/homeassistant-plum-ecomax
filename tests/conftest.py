"""Fixtures for Plum ecoMAX test suite."""

from typing import Generator
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio import Connection
from pyplumio.devices import Device, Mixer, Thermostat
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import ATTR_MODULES, EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_THERMOSTATS,
    DOMAIN,
    STATE_OFF,
    STATE_ON,
)

from .const import MOCK_CONFIG


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="mock_device")
def fixture_mock_device() -> Generator[Device, None, None]:
    """Mock device instance."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.name", "Test"
    ), patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device"
    ) as mock_device:
        mock_thermostat = AsyncMock(spec=Thermostat)
        mock_thermostat.index = 0
        mock_thermostat.data = {
            "test_thermostat_data": "test_thermostat_value",
        }
        mock_mixer = AsyncMock(spec=Mixer)
        mock_mixer.index = 0
        mock_mixer.data = {
            "test_mixer_data": "test_mixer_value",
        }
        mock_device.data = {
            ATTR_PRODUCT: Mock(spec=ProductInfo),
            ATTR_MODULES: Mock(spec=ConnectedModules),
            ATTR_PASSWORD: "0000",
            ATTR_MIXERS: {0: mock_mixer},
            ATTR_THERMOSTATS: {0: mock_thermostat},
            "test_data": "test_value",
        }
        mock_device.set_value = AsyncMock()
        mock_device.get_value = AsyncMock()
        mock_device.subscribe = Mock()
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


@pytest.fixture(name="binary_parameter")
def fixture_binary_parameter() -> Parameter:
    """Create mock binary parameter."""
    parameter = AsyncMock(spec=Parameter)
    parameter.value = STATE_ON
    parameter.min_value = STATE_OFF
    parameter.max_value = STATE_ON
    return parameter


@pytest.fixture(name="numeric_parameter")
def fixture_numeric_parameter() -> Parameter:
    """Create mock numeric parameter."""
    parameter = AsyncMock(spec=Parameter)
    parameter.value = 1
    parameter.min_value = 0
    parameter.max_value = 2
    return parameter
