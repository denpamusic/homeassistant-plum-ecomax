"""Test Plum ecoMAX number platform."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.number import EcomaxNumber, async_setup_entry


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
    """Test setup and update number entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    numbers = args[0]
    number = numbers.pop(0)

    # Check that number values is unknown and update them.
    assert isinstance(number, EcomaxNumber)
    assert number.native_value is None
    assert number.native_min_value is None
    assert number.native_max_value is None
    await number.async_update(boiler_parameter)
    assert number.native_value == 1
    assert number.native_min_value == 0
    assert number.native_max_value == 1

    # Change number value.
    await number.async_set_native_value(2.2)
    mock_device.set_value.assert_called_once_with(number.entity_description.key, 2.2)
    assert number.native_value == 2
