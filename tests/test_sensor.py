"""Test Plum ecoMAX sensor."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.sensor import (
    EcomaxMeter,
    EcomaxSensor,
    SensorStateClass,
    async_setup_entry,
)


@patch("custom_components.plum_ecomax.sensor.on_change")
@patch("custom_components.plum_ecomax.sensor.throttle")
async def test_async_setup_and_update_entry(
    mock_throttle,
    mock_on_change,
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
    bypass_model_check,
    mock_device,
) -> None:
    """Test setup and update sensor entry."""

    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        assert await async_setup_entry(hass, config_entry, async_add_entities)
        await hass.async_block_till_done()

    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    sensors: list[EcomaxSensor] = []
    for sensor in args[0]:
        if sensor.entity_description.key in ("mixer_temp", "heating_temp"):
            sensors.append(sensor)

        if sensor.entity_description.key == "fuel_burned":
            meter = sensor

    for sensor in sensors:
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
        mock_throttle.assert_called_once_with(mock_on_change.return_value, seconds=10)
        mock_on_change.assert_called_once_with(callback)
        mock_throttle.reset_mock()
        mock_on_change.reset_mock()

    # Check meter.
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
        ("EM860p", "fuel_burned"),
        ("EM350P-R2", "fuel_burned"),
        ("ecoMAX 850i", "fireplace_temp"),
    ):
        with patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.model",
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
        "custom_components.plum_ecomax.connection.EcomaxConnection.model",
        "unknown",
    ):
        assert not await async_setup_entry(hass, config_entry, mock_async_add_entities)
        assert "Couldn't setup platform" in caplog.text
