"""Test the water heater platform."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.filters import Filter
from pyplumio.helpers.parameter import Parameter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.water_heater import (
    STATE_PERFORMANCE,
    EcomaxWaterHeater,
    async_setup_entry,
)


@pytest.mark.usefixtures("connected", "water_heater")
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
    added_entities = args[0]
    assert len(added_entities) == 1
    entity = added_entities[0]
    assert isinstance(entity, EcomaxWaterHeater)
    assert entity.hysteresis == 0
    assert entity.entity_registry_enabled_default
    assert entity.available

    # Update current operation.
    mock_parameter = Mock(spec=Parameter)
    mock_parameter.configure_mock(value=1, min_value=0, max_value=2)
    await entity.async_update_work_mode(mock_parameter)
    assert entity.current_operation == STATE_PERFORMANCE

    # Update target temperature.
    await entity.async_update_target_temp(mock_parameter)
    assert entity.min_temp == 0
    assert entity.max_temp == 2
    assert entity.target_temperature == 1
    assert entity.target_temperature_high == 1
    assert entity.target_temperature_low == 1

    # Update hysteresis.
    await entity.async_update_hysteresis(mock_parameter)
    assert entity.hysteresis == 1
    assert entity.target_temperature_low == 0

    # Update current temperature.
    await entity.async_update(50)
    assert entity.current_temperature == 50

    # Set target temperature.
    with patch(
        "custom_components.plum_ecomax.entity.Device.set_value_nowait",
        new_callable=Mock,
    ) as mock_set_value_nowait:
        await entity.async_set_temperature(temperature=0)

    mock_set_value_nowait.assert_called_once_with("water_heater_target_temp", 0)
    assert entity.target_temperature == 0

    # Set current operation.
    with patch(
        "custom_components.plum_ecomax.entity.Device.set_value_nowait",
        new_callable=Mock,
    ) as mock_set_value_nowait:
        await entity.async_set_operation_mode(STATE_OFF)

    mock_set_value_nowait.assert_called_once_with("water_heater_work_mode", 0)
    assert entity.current_operation == STATE_OFF


@pytest.mark.usefixtures("water_heater")
async def test_async_added_removed_to_hass(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test adding and removing entity to/from hass."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    entity = added_entities[0]

    # Test adding entity to hass.
    mock_throttle = AsyncMock(spec=Filter)
    mock_on_change = AsyncMock(spec=Filter)
    with patch(
        "custom_components.plum_ecomax.water_heater.throttle",
        return_value=mock_throttle,
    ), patch(
        "custom_components.plum_ecomax.water_heater.on_change",
        return_value=mock_on_change,
    ), patch(
        "custom_components.plum_ecomax.entity.Device.subscribe"
    ) as mock_subscribe:
        await entity.async_added_to_hass()

    # Test removing entity from hass.
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
        "custom_components.plum_ecomax.entity.Device.unsubscribe"
    ) as mock_unsubscribe:
        await entity.async_will_remove_from_hass()

    mock_unsubscribe.assert_has_calls(
        [
            call("water_heater_temp", entity.async_update),
            call("water_heater_target_temp", entity.async_update_target_temp),
            call("water_heater_work_mode", entity.async_update_work_mode),
            call("water_heater_hysteresis", entity.async_update_hysteresis),
        ]
    )


@pytest.mark.usefixtures("water_heater")
async def test_async_setup_entry_with_device_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup water heater entry with device sensors timeout."""
    with patch(
        "custom_components.plum_ecomax.entity.Device.get_value",
        side_effect=asyncio.TimeoutError,
    ):
        assert not await async_setup_entry(hass, config_entry, async_add_entities)

    assert "Couldn't find water heater" in caplog.text


@pytest.mark.usefixtures("ecomax_common")
async def test_async_setup_entry_with_no_water_heater(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
):
    """Test setup water heater entry without the connected
    water heater.
    """
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
