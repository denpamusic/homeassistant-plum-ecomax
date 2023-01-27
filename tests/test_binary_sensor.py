"""Test Plum ecoMAX binary sensor platform."""


import asyncio
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.devices import Device
from pyplumio.helpers.product_info import ProductType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.binary_sensor import (
    BINARY_SENSOR_TYPES,
    ECOMAX_I_BINARY_SENSOR_TYPES,
    ECOMAX_I_MIXER_BINARY_SENSOR_TYPES,
    ECOMAX_P_BINARY_SENSOR_TYPES,
    ECOMAX_P_MIXER_BINARY_SENSOR_TYPES,
    EcomaxBinarySensor,
    async_setup_entry,
)


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    bypass_hass_write_ha_state,
) -> None:
    """Test setup and update binary sensor entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    for binary_sensor in [
        x for x in args[0] if x.entity_description.key in ("pump", "heating_pump")
    ]:
        # Check that binary sensor state is unknown and update it.
        assert isinstance(binary_sensor, EcomaxBinarySensor)
        assert binary_sensor.is_on is None
        await binary_sensor.async_update(True)
        assert binary_sensor.is_on


async def test_async_setup_entry_with_device_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup binary sensor entry with device sensors timeout."""
    mock_device.get_value.side_effect = asyncio.TimeoutError
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Couldn't load device binary sensors" in caplog.text


async def test_async_setup_entry_with_mixer_binary_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup binary sensor entry with mixer
    binary sensors timeout."""
    mock_device.get_value.side_effect = (None, asyncio.TimeoutError)
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Couldn't load mixer binary sensors" in caplog.text


async def test_model_check(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device: Device,
):
    """Test sensor model check."""
    for model_sensor in (
        (
            ProductType.ECOMAX_P,
            "heating_pump",
            "lighter",
            BINARY_SENSOR_TYPES
            + ECOMAX_P_BINARY_SENSOR_TYPES
            + ECOMAX_P_MIXER_BINARY_SENSOR_TYPES,
        ),
        (
            ProductType.ECOMAX_I,
            "heating_pump",
            "fireplace_pump",
            BINARY_SENSOR_TYPES
            + ECOMAX_I_BINARY_SENSOR_TYPES
            + ECOMAX_I_MIXER_BINARY_SENSOR_TYPES,
        ),
    ):
        (
            product_type,
            first_binary_sensor_key,
            last_binary_sensor_key,
            binary_sensor_types,
        ) = model_sensor
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
            binary_sensors = args[0]
            assert len(binary_sensors) == len(binary_sensor_types)
            first_binary_sensor = binary_sensors[0]
            last_binary_sensor = binary_sensors[-1]
            assert first_binary_sensor.entity_description.key == first_binary_sensor_key
            assert last_binary_sensor.entity_description.key == last_binary_sensor_key


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
