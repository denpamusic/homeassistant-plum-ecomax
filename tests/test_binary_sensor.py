"""Test Plum ecoMAX binary sensor platform."""


from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.binary_sensor import (
    EcomaxBinarySensor,
    async_setup_entry,
)


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup and update binary sensor entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    binary_sensors = async_add_entities.call_args[0][0]
    binary_sensor = binary_sensors.pop(0)

    # Check that binary sensor state is unknown and update it.
    assert isinstance(binary_sensor, EcomaxBinarySensor)
    assert binary_sensor.is_on is None
    await binary_sensor.async_update(True)
    assert binary_sensor.is_on
