"""Fixtures for Plum ecoMAX test suite."""

from homeassistant.core import HomeAssistant
import pytest

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.const import CONF_HOST, CONF_PORT

from .const import MOCK_CONFIG_DATA


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture
def connection(hass: HomeAssistant) -> EcomaxTcpConnection:
    """Create instance of ecoMAX tcp connection."""
    return EcomaxTcpConnection(
        host=MOCK_CONFIG_DATA[CONF_HOST], port=MOCK_CONFIG_DATA[CONF_PORT], hass=hass
    )
