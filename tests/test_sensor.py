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
) -> None:
    """Test setup and update sensor entry."""

    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    sensors = args[0]
    sensor = sensors.pop(0)
    meter = sensors.pop()

    # Check that sensor state is unknown and update it.
    assert isinstance(sensor, EcomaxSensor)
    assert sensor.native_value is None
    await sensor.async_update(65)
    assert sensor.native_value == 65

    # Check sensor callbacks.
    callback = AsyncMock()
    assert sensor.entity_description.filter_fn(callback) == mock_throttle.return_value
    mock_throttle.assert_called_once_with(mock_on_change.return_value, seconds=10)
    mock_on_change.assert_called_once_with(callback)

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
