"""Test Plum ecoMAX switch platform."""

import asyncio
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.devices import Device
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import ATTR_ECOMAX_CONTROL
from custom_components.plum_ecomax.switch import (
    ECOMAX_P_SWITCH_TYPES,
    SWITCH_TYPES,
    EcomaxSwitch,
    async_setup_entry,
)


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    binary_parameter: Parameter,
    mock_device: Device,
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
    await switch.async_update(binary_parameter)
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


async def test_model_check(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device: Device,
):
    """Test sensor model check."""
    for model_sensor in (
        (
            ProductType.ECOMAX_P,
            ATTR_ECOMAX_CONTROL,
            "water_heater_schedule_switch",
            ECOMAX_P_SWITCH_TYPES,
        ),
        (ProductType.ECOMAX_I, ATTR_ECOMAX_CONTROL, "summer_mode", ()),
    ):
        product_type, first_switch_key, last_switch_key, switch_types = model_sensor
        with patch(
            "custom_components.plum_ecomax.sensor.async_get_current_platform"
        ), patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
            product_type,
        ), patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.has_mixers", True
        ), patch(
            "homeassistant.helpers.entity_platform.AddEntitiesCallback"
        ) as mock_async_add_entities:
            await async_setup_entry(hass, config_entry, mock_async_add_entities)
            args, _ = mock_async_add_entities.call_args
            switches = args[0]
            assert len(switches) == (len(SWITCH_TYPES) + len(switch_types))
            first_switch = switches[0]
            last_switch = switches[-1]
            assert first_switch.entity_description.key == first_switch_key
            assert last_switch.entity_description.key == last_switch_key


async def test_async_setup_entry_with_device_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup switch entry with device sensors timeout."""
    mock_device.get_value.side_effect = asyncio.TimeoutError
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Couldn't load device switches" in caplog.text


async def test_async_setup_entry_with_mixer_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup switch entry with mixer sensors timeout."""
    mock_device.get_value.side_effect = (None, asyncio.TimeoutError)
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Control parameter not present" in caplog.text


async def test_model_check_with_unknown_model(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
):
    """Test model check with the unknown model."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type", 2
    ), patch(
        "homeassistant.helpers.entity_platform.AddEntitiesCallback"
    ) as mock_async_add_entities:
        assert not await async_setup_entry(hass, config_entry, mock_async_add_entities)

    assert "Couldn't setup platform" in caplog.text
