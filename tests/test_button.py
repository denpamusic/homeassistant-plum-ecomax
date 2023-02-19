"""Test the button platform."""

from unittest.mock import patch

from freezegun import freeze_time
from homeassistant.components.button import (
    DOMAIN as BUTTON,
    SERVICE_PRESS,
    ButtonDeviceClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def bypass_connection_setup():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"):
        yield


@pytest.fixture(autouse=True)
def bypass_async_migrate_entry():
    """Bypass async migrate entry."""
    with patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True):
        yield


@pytest.fixture(autouse=True)
def set_connected(connected):
    """Assume connected."""


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture(name="async_press")
async def fixture_async_press():
    """Presses the button."""

    async def async_press(hass: HomeAssistant, entity_id: str):
        await hass.services.async_call(
            BUTTON,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_press


@pytest.mark.usefixtures("connection", "ecomax_p", "frozen_time")
async def test_detect_sub_devices_button(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration,
    async_press,
) -> None:
    """Test detect sub-device button."""
    await setup_integration(hass, config_entry)
    detect_sub_devices_entity_id = "button.test_detect_sub_devices"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(detect_sub_devices_entity_id)
    assert entry

    # Get initial value.
    state = hass.states.get(detect_sub_devices_entity_id)
    assert state.state == STATE_UNKNOWN
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Detect sub-devices"
    assert state.attributes[ATTR_DEVICE_CLASS] == ButtonDeviceClass.UPDATE

    # Check that button can be pressed.
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.async_update_sub_devices"
    ) as mock_async_update_sub_devices:
        state = await async_press(hass, detect_sub_devices_entity_id)

    mock_async_update_sub_devices.assert_awaited_once()
    assert state.state == "2012-12-12T12:00:00+00:00"
