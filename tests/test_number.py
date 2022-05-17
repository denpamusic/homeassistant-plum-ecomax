"""Test Plum ecoMAX number."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import DOMAIN
from custom_components.plum_ecomax.number import EcomaxNumber, async_setup_entry


async def test_async_setup_entry(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup number entry."""

    # Setup number and check that entities were added.
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()


async def test_async_set_value(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test set number value."""

    # Setup number and check that entities were added.
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()
    numbers = add_entities_callback.call_args[0][0]
    number = [
        number
        for number in numbers
        if number.entity_description.key == "heating_set_temp"
    ][0]

    # Check that entity value is unknown.
    assert isinstance(number, EcomaxNumber)
    assert number.value is None
    assert number.min_value is None
    assert number.max_value is None

    # Update entity and check that attributes was correctly set.
    await number.async_update()
    assert number.value == 65
    assert number.min_value == 40
    assert number.max_value == 80

    # Set number to new value and check that it was correctly set.
    await number.async_set_value(70)
    connection = hass.data[DOMAIN][config_entry.entry_id]
    assert number.value == 70
    assert connection.ecomax.heating_set_temp == 70

    # Unset number parameter and check that attributes is unknown.
    connection.ecomax.heating_set_temp = None
    await number.async_update()
    assert number.value is None
    assert number.min_value is None
    assert number.max_value is None
