"""Test the water heater platform."""

from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.water_heater import WaterHeaterEntityFeature
from homeassistant.const import PRECISION_WHOLE, STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.filters import Filter
from pyplumio.helpers.parameter import Parameter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.water_heater import (
    STATE_PERFORMANCE,
    WATER_HEATER_MODES,
    EcomaxWaterHeater,
    async_setup_entry,
)


@pytest.mark.usefixtures("connected", "ecomax_p")
async def test_async_setup_and_update_entry_for_ecomax_p(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update water_heater entry for ecomax_p."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    water_heater = args[0][0]
    assert isinstance(water_heater, EcomaxWaterHeater)
    assert water_heater.temperature_unit == UnitOfTemperature.CELSIUS
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
    assert water_heater.entity_registry_enabled_default
    assert water_heater.available

    # Update current operation.
    mock_parameter = Mock(spec=Parameter)
    mock_parameter.configure_mock(value=1, min_value=0, max_value=2)
    await water_heater.async_update_work_mode(mock_parameter)
    assert water_heater.current_operation == STATE_PERFORMANCE

    # Update target temperature.
    await water_heater.async_update_target_temp(mock_parameter)
    assert water_heater.min_temp == 0
    assert water_heater.max_temp == 2
    assert water_heater.target_temperature == 1
    assert water_heater.target_temperature_high == 1
    assert water_heater.target_temperature_low == 1

    # Update hysteresis.
    await water_heater.async_update_hysteresis(mock_parameter)
    assert water_heater.hysteresis == 1
    assert water_heater.target_temperature_low == 0

    # Update current temperature.
    await water_heater.async_update(50)
    assert water_heater.current_temperature == 50

    # Set target temperature.
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.set_value_nowait"
    ) as mock_set_value_nowait:
        await water_heater.async_set_temperature(temperature=0)

    mock_set_value_nowait.assert_called_once_with("water_heater_target_temp", 0)
    assert water_heater.target_temperature == 0

    # Set current operation.
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.set_value_nowait"
    ) as mock_set_value_nowait:
        await water_heater.async_set_operation_mode(STATE_OFF)

    mock_set_value_nowait.assert_called_once_with("water_heater_work_mode", 0)
    assert water_heater.current_operation == STATE_OFF

    # Check added/removed to/from hass callbacks.
    mock_throttle = AsyncMock(spec=Filter)
    mock_on_change = AsyncMock(spec=Filter)
    with patch(
        "custom_components.plum_ecomax.water_heater.throttle",
        return_value=mock_throttle,
    ), patch(
        "custom_components.plum_ecomax.water_heater.on_change",
        return_value=mock_on_change,
    ), patch.dict(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.data",
        {
            "water_heater_temp": 45,
            "water_heater_target_temp": 50,
            "water_heater_work_mode": 0,
            "water_heater_hysteresis": 5,
        },
    ), patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.subscribe"
    ) as mock_subscribe:
        await water_heater.async_added_to_hass()

    mock_subscribe.assert_has_calls(
        [
            call("water_heater_temp", mock_throttle),
            call("water_heater_target_temp", mock_on_change),
            call("water_heater_work_mode", mock_on_change),
            call("water_heater_hysteresis", mock_on_change),
        ]
    )
    assert mock_throttle.await_count == 1
    assert mock_on_change.await_count == 3

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.unsubscribe"
    ) as mock_unsubscribe:
        await water_heater.async_added_to_hass()
        await water_heater.async_will_remove_from_hass()

    mock_unsubscribe.assert_has_calls(
        [
            call("water_heater_temp", water_heater.async_update),
            call("water_heater_target_temp", water_heater.async_update_target_temp),
            call("water_heater_work_mode", water_heater.async_update_work_mode),
            call("water_heater_hysteresis", water_heater.async_update_hysteresis),
        ]
    )


@pytest.mark.usefixtures("ecomax_base")
async def test_async_setup_entry_with_device_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup water heater entry with device sensors timeout."""
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Couldn't load indirect water heater parameters" in caplog.text
