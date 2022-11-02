"""Test Plum ecoMAX switch platform."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.switch import EcomaxSwitch, async_setup_entry


@patch(
    "custom_components.plum_ecomax.connection.EcomaxConnection.device",
    new_callable=AsyncMock,
)
async def test_async_setup_and_update_entry(
    mock_device,
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    boiler_parameter: Parameter,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup and update switch entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    switches = args[0]
    switch = switches.pop(0)

    # Check that switch state is unknown and update it.
    assert isinstance(switch, EcomaxSwitch)
    assert switch.is_on is None
    await switch.async_update(boiler_parameter)
    assert switch.is_on

    # Turn the switch off.
    await switch.async_turn_off()
    mock_device.set_value.assert_called_once_with(
        switch.entity_description.key,
        switch.entity_description.state_off,
        await_confirmation=False,
    )
    assert not switch.is_on
    mock_device.reset_mock()

    # Turn the switch back on.
    await switch.async_turn_on()
    mock_device.set_value.assert_called_once_with(
        switch.entity_description.key,
        switch.entity_description.state_on,
        await_confirmation=False,
    )
    assert switch.is_on
