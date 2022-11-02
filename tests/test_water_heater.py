"""Test Plum ecoMAX water heater platform."""

from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.water_heater import (
    STATE_OFF,
    STATE_PERFORMANCE,
    WaterHeaterEntityFeature,
)
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.filters import Filter
from pyplumio.helpers.parameter import Parameter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.water_heater import (
    WATER_HEATER_MODES,
    EcomaxWaterHeater,
    async_setup_entry,
)


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
    """Test setup and update water_heater entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    water_heaters = args[0]
    water_heater = water_heaters.pop(0)

    # Check that switch state is unknown and update it.
    assert isinstance(water_heater, EcomaxWaterHeater)
    assert water_heater.temperature_unit == TEMP_CELSIUS
    assert water_heater.precision == PRECISION_WHOLE
    assert water_heater.supported_features == (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        + WaterHeaterEntityFeature.OPERATION_MODE
    )
    assert water_heater.operation_list == WATER_HEATER_MODES
    assert water_heater.min_temp is None
    assert water_heater.max_temp is None
    assert water_heater.target_temperature is None
    assert water_heater.target_temperature_high is None
    assert water_heater.target_temperature_low is None
    assert water_heater.current_temperature is None
    assert water_heater.current_operation is None
    assert water_heater.hysteresis == 0

    # Update current operation.
    await water_heater.async_update_work_mode(boiler_parameter)
    assert water_heater.current_operation == STATE_PERFORMANCE

    # Update target temperature.
    await water_heater.async_update_target_temp(boiler_parameter)
    assert water_heater.min_temp == 0
    assert water_heater.max_temp == 1
    assert water_heater.target_temperature == 1
    assert water_heater.target_temperature_high == 1
    assert water_heater.target_temperature_low == 1

    # Update hysteresis.
    await water_heater.async_update_hysteresis(boiler_parameter)
    assert water_heater.hysteresis == 1
    assert water_heater.target_temperature_low == 0

    # Update current temperature.
    await water_heater.async_update(50)
    assert water_heater.current_temperature == 50

    # Set target temperature.
    await water_heater.async_set_temperature(temperature=0)
    mock_device.set_value.assert_called_once_with(
        f"{water_heater.entity_description.key}_target_temp",
        0,
        await_confirmation=False,
    )
    assert water_heater.target_temperature == 0
    mock_device.reset_mock()

    # Set current operation.
    await water_heater.async_set_operation_mode(STATE_OFF)
    mock_device.set_value.assert_called_once_with(
        f"{water_heater.entity_description.key}_work_mode", 0, await_confirmation=False
    )
    assert water_heater.current_operation == STATE_OFF

    # Check added/removed to/from hass callbacks.
    mock_throttle_filter = AsyncMock(spec=Filter)
    mock_on_change_filter = AsyncMock(spec=Filter)
    mock_device.subscribe = Mock()
    mock_device.data = {
        "water_heater_temp": 45,
        "water_heater_target_temp": 50,
        "water_heater_work_mode": 0,
        "water_heater_hysteresis": 5,
    }
    with patch(
        "custom_components.plum_ecomax.water_heater.throttle",
        return_value=mock_throttle_filter,
    ), patch(
        "custom_components.plum_ecomax.water_heater.on_change",
        return_value=mock_on_change_filter,
    ):
        await water_heater.async_added_to_hass()

    key = water_heater.entity_description.key
    register_calls = (
        call(f"{key}_temp", mock_throttle_filter),
        call(f"{key}_target_temp", mock_on_change_filter),
        call(f"{key}_work_mode", mock_on_change_filter),
        call(f"{key}_hysteresis", mock_on_change_filter),
    )
    mock_device.subscribe.assert_has_calls(register_calls, any_order=True)
    assert mock_throttle_filter.await_count == 1
    assert mock_on_change_filter.await_count == 3
    mock_device.unsubscribe = Mock()
    await water_heater.async_will_remove_from_hass()
    remove_calls = (
        call(f"{key}_temp", water_heater.async_update),
        call(f"{key}_target_temp", water_heater.async_update_target_temp),
        call(f"{key}_work_mode", water_heater.async_update_work_mode),
        call(f"{key}_hysteresis", water_heater.async_update_hysteresis),
    )
    mock_device.unsubscribe.assert_has_calls(remove_calls)
