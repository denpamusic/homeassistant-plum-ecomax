"""Test Plum ecoMAX switch."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest
import pytest_asyncio
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.switch import EcomaxSwitch, async_setup_entry


@pytest_asyncio.fixture(name="test_switch")
async def fixture_test_switch(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> EcomaxSwitch:
    """Setup switch entities and get a single switch."""
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()
    switches = add_entities_callback.call_args[0][0]
    switch = [x for x in switches if x.entity_description.key == "boiler_control"]
    yield switch[0]


@pytest.mark.asyncio
async def test_async_setup_and_update_entry(test_switch: EcomaxSwitch) -> None:
    """Test setup and update switch entry."""
    # Check that switch state is unknown and update it.
    assert isinstance(test_switch, EcomaxSwitch)
    assert test_switch.is_on is None
    await test_switch.async_update()

    # Check that entity state changed and was written to hass.
    assert test_switch.is_on


@pytest.mark.asyncio
async def test_async_switch_on_off(
    test_switch: EcomaxSwitch,
    mock_connection: EcomaxTcpConnection,
):
    """Test turning switch off and then on."""
    await test_switch.async_turn_off()
    assert not test_switch.is_on
    assert (
        mock_connection.ecomax.boiler_control
        == test_switch.entity_description.state_off
    )

    await test_switch.async_turn_on()
    assert test_switch.is_on
    assert (
        mock_connection.ecomax.boiler_control == test_switch.entity_description.state_on
    )
