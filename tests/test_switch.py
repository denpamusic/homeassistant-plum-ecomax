"""Test Plum ecoMAX switch."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import DOMAIN
from custom_components.plum_ecomax.switch import EcomaxSwitch, async_setup_entry


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup and update switch entry."""
    # Setup switch and check that entities were added.
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()

    # Get single switch.
    switches = add_entities_callback.call_args[0][0]
    switch = [
        switch
        for switch in switches
        if switch.entity_description.key == "boiler_control"
    ][0]

    # Check that switch state is unknown and update it.
    assert isinstance(switch, EcomaxSwitch)
    assert switch.is_on is None
    await switch.async_update()

    # Check that entity state changed and was written to hass.
    assert switch.is_on

    # Turn switch off.
    await switch.async_turn_off()
    connection = hass.data[DOMAIN][config_entry.entry_id]
    assert not switch.is_on
    assert connection.ecomax.boiler_control == switch.entity_description.state_off

    # Turn switch on.
    await switch.async_turn_on()
    assert switch.is_on
    assert connection.ecomax.boiler_control == switch.entity_description.state_on
