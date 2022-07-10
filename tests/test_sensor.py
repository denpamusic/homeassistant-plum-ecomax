"""Test Plum ecoMAX sensor."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.sensor import EcomaxSensor, async_setup_entry


@patch("custom_components.plum_ecomax.sensor.debounce")
async def test_async_setup_and_update_entry(
    mock_debounce,
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup and update sensor entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    sensors = async_add_entities.call_args[0][0]
    sensor = sensors.pop(0)

    # Check that sensor state is unknown and update it.
    assert isinstance(sensor, EcomaxSensor)
    assert sensor.native_value is None
    await sensor.async_update(65)
    assert sensor.native_value == 65

    # Check sensor callbacks.
    assert sensor.callbacks == {
        sensor.entity_description.key: mock_debounce.return_value
    }
    mock_debounce.assert_called_once_with(sensor.async_update, min_calls=3)
