"""Test Plum ecoMAX switch platform."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import ATTR_ECOMAX_CONTROL
from custom_components.plum_ecomax.switch import EcomaxSwitch, async_setup_entry


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
    """Test setup and update switch entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    switch = [x for x in args[0] if x.entity_description.key == ATTR_ECOMAX_CONTROL][0]

    # Check that switch state is unknown and update it.
    assert isinstance(switch, EcomaxSwitch)
    assert switch.is_on is None
    await switch.async_update(boiler_parameter)
    assert switch.is_on

    # Turn the switch off.
    await switch.async_turn_off()
    mock_device.set_value.assert_called_once_with(
        switch.entity_description.key,
        switch.entity_description.state_off,
        await_confirmation=False,
    )
    assert not switch.is_on
    mock_device.reset_mock()

    # Turn the switch back on.
    await switch.async_turn_on()
    mock_device.set_value.assert_called_once_with(
        switch.entity_description.key,
        switch.entity_description.state_on,
        await_confirmation=False,
    )
    assert switch.is_on


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
        (0, "schedule_water_heater_switch"),
        (1, "summer_mode"),
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
