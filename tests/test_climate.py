"""Test the climate platform."""

from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.components.climate import HVACAction
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.filters import Filter
from pyplumio.helpers.parameter import Parameter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.climate import (
    HA_TO_EM_MODE,
    PRESET_AIRING,
    PRESET_ECO,
    PRESET_SCHEDULE,
    EcomaxClimate,
    async_setup_entry,
)


@pytest.mark.usefixtures("connected", "ecomax_p", "thermostats")
async def test_async_setup_and_update_entry_for_ecomax_p(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update climate entry for ecomax_p."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    assert len(added_entities) == 1
    entity = added_entities[0]
    assert isinstance(entity, EcomaxClimate)
    assert entity.entity_description.name == "Thermostat 1"
    await entity.async_added_to_hass()

    # Test update preset mode.
    assert entity.preset_mode == PRESET_SCHEDULE
    assert entity.target_temperature_name == "day_target_temp"
    await entity.async_update_preset_mode(HA_TO_EM_MODE[PRESET_AIRING])
    assert entity.preset_mode == PRESET_AIRING
    assert entity.target_temperature_name == "day_target_temp"
    await entity.async_update_preset_mode(HA_TO_EM_MODE[PRESET_ECO])
    assert entity.preset_mode == PRESET_ECO
    assert entity.target_temperature_name == "night_target_temp"

    # Test update preset mode to unknown mode.
    await entity.async_update_preset_mode(9)
    assert entity.preset_mode == PRESET_ECO
    assert "Unknown climate preset 9" in caplog.text

    # Test update hvac action.
    assert entity.hvac_action == HVACAction.IDLE
    await entity.async_update_hvac_action(True)
    assert entity.hvac_action == HVACAction.HEATING

    # Test update current temperature.
    assert entity.current_temperature == 0
    await entity.async_update(25)
    assert entity.current_temperature == 25

    # Test update target temperature.
    assert entity.target_temperature == 16.0
    parameter = Mock(spec=Parameter)
    parameter.configure_mock(value=18.0, min_value=10.0, max_value=35.0)
    with patch(
        "custom_components.plum_ecomax.climate.Thermostat.get_parameter",
        create=True,
        return_value=parameter,
    ):
        # Since target temperature parameter is dynamic and based
        # on preset mode, we mock get_parameter call instead of using
        # value passed to the callback.
        await entity.async_update_target_temp(value=None)

    assert entity.target_temperature == 18.0
    assert entity.max_temp == 35.0
    assert entity.min_temp == 10.0

    # Test set target temperature.
    with patch(
        "custom_components.plum_ecomax.climate.Thermostat.set_value_nowait",
        new_callable=Mock(),
    ) as mock_set_value_nowait:
        await entity.async_set_temperature(temperature=15.1)

    assert entity.target_temperature == 15.1
    mock_set_value_nowait.assert_called_once_with(entity.target_temperature_name, 15.1)

    # Test set preset mode.
    with patch(
        "custom_components.plum_ecomax.climate.Thermostat.set_value_nowait",
        new_callable=Mock(),
    ), patch(
        "custom_components.plum_ecomax.climate.Thermostat.get_value", return_value=True
    ):
        await entity.async_set_preset_mode(PRESET_SCHEDULE)

    assert entity.preset_mode == PRESET_SCHEDULE
    assert entity.target_temperature_name == "night_target_temp"


@pytest.mark.usefixtures("ecomax_p", "thermostats")
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
        "custom_components.plum_ecomax.climate.throttle",
        return_value=mock_throttle,
    ), patch(
        "custom_components.plum_ecomax.climate.on_change",
        return_value=mock_on_change,
    ), patch(
        "custom_components.plum_ecomax.climate.Thermostat.subscribe"
    ) as mock_subscribe:
        await entity.async_added_to_hass()

    # Test removing entity from hass.
    mock_subscribe.assert_has_calls(
        [
            call("state", mock_on_change),
            call("contacts", mock_on_change),
            call("current_temp", mock_throttle),
            call("target_temp", mock_on_change),
        ]
    )
    assert mock_throttle.await_count == 1
    assert mock_on_change.await_count == 3

    with patch(
        "custom_components.plum_ecomax.climate.Thermostat.unsubscribe"
    ) as mock_unsubscribe:
        await entity.async_will_remove_from_hass()

    mock_unsubscribe.assert_has_calls(
        [
            call("state", entity.async_update_preset_mode),
            call("contacts", entity.async_update_hvac_action),
            call("current_temp", entity.async_update),
            call("target_temp", entity.async_update_target_temp),
        ]
    )


@pytest.mark.usefixtures("ecomax_base")
async def test_async_setup_entry_with_device_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup thermostat entry with device sensors timeout."""
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Couldn't find thermostats" in caplog.text
