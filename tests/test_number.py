"""Test Plum ecoMAX number platform."""

from unittest.mock import Mock, call, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.number import EcomaxNumber, async_setup_entry


@patch("custom_components.plum_ecomax.connection.EcomaxConnection.name", "test")
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
    mock_device.data = {}
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
        await number.async_set_native_value(2.2)
        mock_device.set_value.assert_called_once_with(
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


@patch("custom_components.plum_ecomax.sensor.async_get_current_platform")
@patch("homeassistant.helpers.entity_platform.AddEntitiesCallback")
async def test_model_check(
    mock_async_add_entities,
    mock_async_get_current_platform,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device,
):
    """Test sensor model check."""
    for model_sensor in (
        (0, "fuel_calorific_value_kwh_kg"),
        (1, "max_mixer_target_temp"),
    ):
        with patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
            model_sensor[0],
        ):
            await async_setup_entry(hass, config_entry, mock_async_add_entities)
            args, _ = mock_async_add_entities.call_args
            sensor = args[0].pop()
            assert sensor.entity_description.key == model_sensor[1]


@patch("homeassistant.helpers.entity_platform.AddEntitiesCallback")
async def test_model_check_with_unknown_model(
    mock_async_add_entities,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    caplog,
    mock_device,
):
    """Test model check with the unknown model."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type", 2
    ):
        assert not await async_setup_entry(hass, config_entry, mock_async_add_entities)
        assert "Couldn't setup platform" in caplog.text
