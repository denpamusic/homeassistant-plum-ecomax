"""Fixtures for Plum ecoMAX test suite."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
import pytest

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SOFTWARE,
    CONF_UID,
    DOMAIN,
)

from .const import MOCK_CONFIG_DATA, MOCK_DEVICE_DATA


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


@pytest.fixture
def device_info() -> DeviceInfo:
    """Create instance of device info."""
    return DeviceInfo(
        name=MOCK_CONFIG_DATA[CONF_HOST],
        identifiers={(DOMAIN, MOCK_DEVICE_DATA[CONF_UID])},
        manufacturer="Plum Sp. z o.o.",
        model=f"ecoMAX 350P2 (uid: {MOCK_DEVICE_DATA[CONF_UID]})",
        sw_version=MOCK_DEVICE_DATA[CONF_SOFTWARE],
    )
