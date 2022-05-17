"""Test Plum ecoMAX sensor."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.sensor import EcomaxSensor, async_setup_entry


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup and update sensor entry."""
    # Setup sensor and check that entities were added.
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()

    # Get single sensor.
    sensors = add_entities_callback.call_args[0][0]
    sensor = [
        sensor for sensor in sensors if sensor.entity_description.key == "heating_temp"
    ][0]

    # Check that sensor state is unknown and update it.
    assert isinstance(sensor, EcomaxSensor)
    assert sensor.native_value is None
    await sensor.async_update()

    # Check that entity state changed and was written to hass.
    assert sensor.native_value == 65
