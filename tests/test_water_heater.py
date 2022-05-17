"""Test Plum ecoMAX water heater."""

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_PERFORMANCE,
    WaterHeaterEntityFeature,
)
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import DOMAIN, WATER_HEATER_MODES
from custom_components.plum_ecomax.water_heater import (
    EcomaxWaterHeater,
    async_setup_entry,
)


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


async def test_async_set_temperature_and_mode(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup of target temperature and operation mode."""
    # Setup sensor and check that entities were added.
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()

    # Get single sensor.
    water_heaters = add_entities_callback.call_args[0][0]
    water_heater = [
        water_heater
        for water_heater in water_heaters
        if water_heater.entity_description.key == "water_heater"
    ][0]

    # Check that sensor state is unknown and update it.
    assert isinstance(water_heater, EcomaxWaterHeater)
    assert water_heater.temperature_unit == TEMP_CELSIUS
    assert water_heater.precision == PRECISION_WHOLE
    assert (
        water_heater.supported_features
        == WaterHeaterEntityFeature.TARGET_TEMPERATURE
        + WaterHeaterEntityFeature.OPERATION_MODE
    )
    assert water_heater.operation_list == WATER_HEATER_MODES
    assert water_heater.min_temp is None
    assert water_heater.max_temp is None
    assert water_heater.current_temperature is None
    assert water_heater.target_temperature is None
    assert water_heater.target_temperature_high is None
    assert water_heater.target_temperature_low is None
    assert water_heater.current_operation is None

    # Update entity and check that attributes was correctly set.
    await water_heater.async_update()
    assert water_heater.min_temp == 40
    assert water_heater.max_temp == 60
    assert water_heater.current_temperature == 50
    assert water_heater.target_temperature == 50
    assert water_heater.target_temperature_high == 50
    assert water_heater.target_temperature_low == 45
    assert water_heater.current_operation == STATE_PERFORMANCE

    # Unset hysteresis and check that low bound is correctly set.
    connection = hass.data[DOMAIN][config_entry.entry_id]
    connection.ecomax.water_heater_hysteresis = None
    await water_heater.async_update()
    assert water_heater.target_temperature_low == 50

    # Set new target temperature and check that it was correctly set.
    await water_heater.async_set_temperature(temperature=60)
    assert water_heater.target_temperature == 60
    assert connection.ecomax.water_heater_set_temp == 60

    # Set operation mode and check that it was correctly set.
    await water_heater.async_set_operation_mode(STATE_OFF)
    assert water_heater.current_operation == STATE_OFF
    assert connection.ecomax.water_heater_work_mode == 0

    # Unset target temperature and check that attributes is unknown.
    connection.ecomax.water_heater_set_temp = None
    await water_heater.async_update()
    assert water_heater.min_temp is None
    assert water_heater.max_temp is None
    assert water_heater.target_temperature is None
    assert water_heater.target_temperature_high is None
    assert water_heater.target_temperature_low is None
    assert water_heater.current_operation is None
