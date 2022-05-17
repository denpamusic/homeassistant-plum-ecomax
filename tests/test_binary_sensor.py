"""Test Plum ecoMAX sensor."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest
import pytest_asyncio
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.binary_sensor import (
    EcomaxBinarySensor,
    async_setup_entry,
)


@pytest_asyncio.fixture(name="test_binary_sensor")
async def fixture_test_binary_sensor(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> EcomaxBinarySensor:
    """Setup sensor entities and get a single sensor."""
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()
    binary_sensors = add_entities_callback.call_args[0][0]
    binary_sensor = [
        x for x in binary_sensors if x.entity_description.key == "heating_pump"
    ]
    yield binary_sensor[0]


@pytest.mark.asyncio
async def test_async_setup_and_update_entry(
    test_binary_sensor: EcomaxBinarySensor,
) -> None:
    """Test setup and update binary sensor entry."""
    # Check that sensor state is unknown and update it.
    assert isinstance(test_binary_sensor, EcomaxBinarySensor)
    assert test_binary_sensor.is_on is None
    await test_binary_sensor.async_update()

    # Check that entity state changed and was written to hass.
    assert test_binary_sensor.is_on
