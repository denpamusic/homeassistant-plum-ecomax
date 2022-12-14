"""Test Plum ecoMAX number platform."""

from unittest.mock import Mock, call, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import ATTR_MIXERS
from custom_components.plum_ecomax.number import (
    ECOMAX_I_MIXER_NUMBER_TYPES,
    ECOMAX_I_NUMBER_TYPES,
    ECOMAX_P_NUMBER_TYPES,
    MIXER_NUMBER_TYPES,
    NUMBER_TYPES,
    EcomaxNumber,
    async_setup_entry,
)


async def test_async_added_removed_to_hass(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
    mock_device,
) -> None:
    """Test adding and removing entity to/from hass."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    heating_target_temp = [
        x for x in args[0] if x.entity_description.key == "heating_target_temp"
    ][0]
    subscribe_calls = [
        call("min_heating_target_temp", heating_target_temp.async_set_min_value),
        call("max_heating_target_temp", heating_target_temp.async_set_max_value),
    ]
    await heating_target_temp.async_added_to_hass()
    assert mock_device.subscribe.call_count == 3
    mock_device.subscribe.assert_has_calls(subscribe_calls)

    mock_device.unsubscribe = Mock()
    unsubscribe_calls = [
        call("min_heating_target_temp", heating_target_temp.async_set_min_value),
        call("max_heating_target_temp", heating_target_temp.async_set_max_value),
    ]
    await heating_target_temp.async_will_remove_from_hass()
    assert mock_device.unsubscribe.call_count == 3
    mock_device.unsubscribe.assert_has_calls(unsubscribe_calls)


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    boiler_parameter: Parameter,
    bypass_hass_write_ha_state,
    mock_device,
) -> None:
    """Test setup and update number entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    numbers: list[EcomaxNumber] = []
    for number in args[0]:
        if number.entity_description.key in (
            "mixer_target_temp",
            "heating_target_temp",
        ):
            numbers.append(number)

    for number in numbers:
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
        target_device = (
            mock_device
            if number.entity_description.key == "heating_target_temp"
            else mock_device.data[ATTR_MIXERS][0]
        )
        await number.async_set_native_value(2.2)
        target_device.set_value.assert_called_once_with(
            number.entity_description.key, 2.2, await_confirmation=False
        )
        assert number.native_value == 2.2

        # Change min value.
        boiler_parameter.value = 4
        assert number.native_min_value == 0
        await number.async_set_min_value(boiler_parameter)
        assert number.native_min_value == 4

        # Change max value.
        boiler_parameter.value = 5
        assert number.native_max_value == 1
        await number.async_set_max_value(boiler_parameter)
        assert number.native_max_value == 5

        # Reset values.
        boiler_parameter.value = 1
        boiler_parameter.min_value = 0
        boiler_parameter.max_value = 1

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
        ProductType.ECOMAX_I,
    ):
        assert numbers[0].device_info["name"] == "Test Circuit 1"

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
        ProductType.ECOMAX_P,
    ):
        assert numbers[0].device_info["name"] == "Test Mixer 1"


@patch("custom_components.plum_ecomax.sensor.async_get_current_platform")
@patch("homeassistant.helpers.entity_platform.AddEntitiesCallback")
async def test_model_check(
    mock_async_add_entities,
    mock_async_get_current_platform,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device,
) -> None:
    """Test sensor model check."""
    for model_sensor in (
        (
            ProductType.ECOMAX_P,
            "mixer_target_temp",
            "fuel_calorific_value_kwh_kg",
            ECOMAX_P_NUMBER_TYPES,
        ),
        (
            ProductType.ECOMAX_I,
            "mixer_target_temp",
            "night_mixer_target_temp",
            ECOMAX_I_NUMBER_TYPES + ECOMAX_I_MIXER_NUMBER_TYPES,
        ),
    ):
        product_type, first_number_key, last_number_key, number_types = model_sensor
        number_types_length = len(NUMBER_TYPES) + len(MIXER_NUMBER_TYPES)
        with patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
            product_type,
        ):
            await async_setup_entry(hass, config_entry, mock_async_add_entities)
            args, _ = mock_async_add_entities.call_args
            numbers = args[0]
            assert len(numbers) == (number_types_length + len(number_types))
            first_number = numbers[0]
            last_number = numbers[-1]
            assert first_number.entity_description.key == first_number_key
            assert last_number.entity_description.key == last_number_key


@patch("homeassistant.helpers.entity_platform.AddEntitiesCallback")
async def test_model_check_with_unknown_model(
    mock_async_add_entities,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    caplog,
    mock_device,
) -> None:
    """Test model check with the unknown model."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type", 2
    ):
        assert not await async_setup_entry(hass, config_entry, mock_async_add_entities)
        assert "Couldn't setup platform" in caplog.text
