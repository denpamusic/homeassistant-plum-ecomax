"""Fixtures for Plum ecoMAX test suite."""

from unittest.mock import Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.const import (
    CONF_CAPABILITIES,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SOFTWARE,
    CONF_UID,
    DOMAIN,
)

from .const import MOCK_CONFIG


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="device_info")
def fixture_device_info() -> DeviceInfo:
    """Create instance of device info."""
    return DeviceInfo(
        name=MOCK_CONFIG[CONF_HOST],
        identifiers={(DOMAIN, MOCK_CONFIG[CONF_UID])},
        manufacturer="Plum Sp. z o.o.",
        model=f"ecoMAX 350P2 (uid: {MOCK_CONFIG[CONF_UID]})",
        sw_version=MOCK_CONFIG[CONF_SOFTWARE],
    )


@pytest.fixture(name="add_entities_callback")
def fixture_add_entities_callback() -> AddEntitiesCallback:
    """Simulate add entities callback."""
    with patch(
        "homeassistant.helpers.entity_platform.AddEntitiesCallback"
    ) as mock_add_entities_callback:
        yield mock_add_entities_callback


@pytest.fixture(name="bypass_hass_write_ha_state")
def fixture_bypass_hass_write_ha_state():
    """Bypass writing state to hass."""
    with patch("homeassistant.helpers.entity.Entity.async_write_ha_state"):
        yield


@pytest.fixture(name="tcp_connection_with_data")
def fixture_tcp_connection_with_data(device_info: DeviceInfo) -> EcomaxTcpConnection:
    """Simulate ecoMAX response object."""
    mock_connection = Mock()
    mock_connection.name = MOCK_CONFIG[CONF_HOST]
    mock_connection.device_info = device_info
    mock_connection.uid = MOCK_CONFIG[CONF_UID]
    mock_connection.model = MOCK_CONFIG[CONF_MODEL]
    mock_connection.software = MOCK_CONFIG[CONF_SOFTWARE]
    mock_connection.capabilities = MOCK_CONFIG[CONF_CAPABILITIES]
    mock_connection.check.return_value = True
    mock_connection.ecomax = Mock()
    mock_connection.ecomax.heating_temp = 65
    mock_connection.ecomax.heating_pump = True
    mock_connection.ecomax.heating_set_temp = Parameter(
        name="heating_set_temp",
        value=65,
        min_=40,
        max_=80,
    )
    mock_connection.ecomax.boiler_control = Parameter(
        name="boiler_control",
        value=1,
        min_=0,
        max_=1,
    )
    mock_connection.ecomax.heating_temp_grate = None
    yield mock_connection


@pytest.fixture(name="connection")
def fixture_connection(hass: HomeAssistant) -> EcomaxTcpConnection:
    """Create instance of ecoMAX tcp connection."""
    return EcomaxTcpConnection(
        host=MOCK_CONFIG[CONF_HOST], port=MOCK_CONFIG[CONF_PORT], hass=hass
    )


@pytest.fixture(name="config_entry")
def fixture_config_entry(
    hass: HomeAssistant, tcp_connection_with_data: EcomaxTcpConnection
) -> MockConfigEntry:
    """Create mock config entry and add it to hass."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = tcp_connection_with_data
    yield config_entry
