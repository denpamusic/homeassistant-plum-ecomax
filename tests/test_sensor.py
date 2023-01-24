"""Test Plum ecoMAX sensor."""


import asyncio
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.devices import Device
from pyplumio.helpers.product_info import ConnectedModules, ProductType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import VALUE_TIMEOUT
from custom_components.plum_ecomax.sensor import (
    ECOMAX_I_SENSOR_TYPES,
    ECOMAX_P_SENSOR_TYPES,
    METER_TYPES,
    MIXER_SENSOR_TYPES,
    SENSOR_TYPES,
    EcomaxMeter,
    EcomaxSensor,
    SensorStateClass,
    async_setup_entry,
)


@patch("custom_components.plum_ecomax.sensor.on_change")
@patch("custom_components.plum_ecomax.sensor.throttle")
@patch("custom_components.plum_ecomax.sensor.async_setup_module_entites")
async def test_async_setup_and_update_entry(
    mock_async_get_module_entities,
    mock_throttle,
    mock_on_change,
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    bypass_hass_write_ha_state,
    bypass_model_check,
    caplog,
) -> None:
    """Test setup and update sensor entry."""
    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        assert await async_setup_entry(hass, config_entry, async_add_entities)
        await hass.async_block_till_done()

    async_add_entities.assert_called_once()
    mock_async_get_module_entities.assert_awaited_once()
    args, _ = async_add_entities.call_args
    for sensor in [
        x
        for x in args[0]
        if x.entity_description.key in ("current_temp", "heating_temp")
    ]:
        # Check that sensor state is unknown and update it.
        assert isinstance(sensor, EcomaxSensor)
        assert sensor.native_value is None
        await sensor.async_update(65)
        assert sensor.native_value == 65

        # Check sensor callbacks.
        callback = AsyncMock()
        assert (
            sensor.entity_description.filter_fn(callback) == mock_throttle.return_value
        )
        mock_throttle.assert_called_once_with(
            mock_on_change.return_value, seconds=VALUE_TIMEOUT
        )
        mock_on_change.assert_called_once_with(callback)
        mock_throttle.reset_mock()
        mock_on_change.reset_mock()

    # Check meter.
    meter = [x for x in args[0] if x.entity_description.key == "fuel_burned"][0]
    mock_last_sensor_data = Mock()
    mock_last_sensor_data.native_value = 2
    mock_last_sensor_data.native_unit_of_measurement = "kg"
    with patch(
        "custom_components.plum_ecomax.sensor.EcomaxSensor.async_added_to_hass"
    ) as mock_added_to_hass, patch(
        "custom_components.plum_ecomax.sensor.RestoreSensor.async_get_last_sensor_data",
        side_effect=(None, mock_last_sensor_data),
        return_value=None,
    ) as mock_get_last_sensor_data:
        await meter.async_added_to_hass()
        assert meter.native_value == 0
        await meter.async_added_to_hass()
        assert meter.native_value == 2
        assert meter.unit_of_measurement == "kg"

    assert mock_added_to_hass.await_count == 2
    assert mock_get_last_sensor_data.await_count == 2

    # Check meter calibration and reset.
    await meter.async_calibrate_meter(5)
    assert meter.native_value == 5
    with patch.object(EcomaxMeter, "state_class", SensorStateClass.TOTAL), patch(
        "homeassistant.util.dt.utcnow"
    ) as mock_utcnow:
        await meter.async_reset_meter()

    mock_utcnow.assert_called_once()
    assert meter.native_value == 0
    await meter.async_update(3)
    assert meter.native_value == 3


async def test_async_setup_entry_with_device_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup sensor entry with device sensors timeout."""
    mock_device.get_value.side_effect = asyncio.TimeoutError
    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        assert not await async_setup_entry(hass, config_entry, async_add_entities)

    assert "Couldn't load device sensors" in caplog.text


async def test_async_setup_entry_with_mixer_sensors_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    mock_device: Device,
    caplog,
) -> None:
    """Test setup sensor entry with mixer sensors timeout."""
    mock_device.get_value.side_effect = (
        None,
        Mock(spec=ConnectedModules),
        asyncio.TimeoutError,
    )
    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    assert "Couldn't load mixer sensors" in caplog.text


async def test_model_check(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device: Device,
):
    """Test sensor model check."""
    for model_sensor in (
        (ProductType.ECOMAX_P, "heating_temp", "fuel_burned", ECOMAX_P_SENSOR_TYPES),
        (
            ProductType.ECOMAX_I,
            "heating_temp",
            "fireplace_temp",
            ECOMAX_I_SENSOR_TYPES,
        ),
    ):
        product_type, first_sensor_key, last_sensor_key, sensor_types = model_sensor
        sensor_types_length = len(SENSOR_TYPES) + len(MIXER_SENSOR_TYPES)
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
            sensors = args[0]
            assert len(sensors) == (
                sensor_types_length
                + len(sensor_types)
                + (len(METER_TYPES) if product_type == 0 else 0)
            )
            first_sensor = sensors[0]
            last_sensor = sensors[-1]
            assert first_sensor.entity_description.key == first_sensor_key
            assert last_sensor.entity_description.key == last_sensor_key


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
