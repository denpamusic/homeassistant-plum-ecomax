"""Test the sensor platform."""

import unittest.mock as mock
from unittest.mock import Mock, call, patch

from homeassistant.components.sensor import SensorExtraStoredData, SensorStateClass
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.devices import Mixer
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.sensor import (
    ECOMAX_I_MIXER_SENSOR_TYPES,
    ECOMAX_I_SENSOR_TYPES,
    ECOMAX_P_MIXER_SENSOR_TYPES,
    ECOMAX_P_SENSOR_TYPES,
    METER_TYPES,
    MODULE_LAMBDA_SENSOR_TYPES,
    SENSOR_TYPES,
    SERVICE_CALIBRATE_METER,
    SERVICE_RESET_METER,
    EcomaxMeter,
    EcomaxSensor,
    MixerSensor,
    async_setup_entry,
)


@pytest.fixture(autouse=True)
def bypass_async_get_current_platform():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        yield


@pytest.fixture(autouse=True)
def set_connection_name():
    """Set connection name."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.name",
        "test",
        create=True,
    ):
        yield


def _lookup_sensor(entities: list[EcomaxSensor], key: str) -> EcomaxSensor:
    """Lookup sensor in the list."""
    for entity in entities:
        if entity.entity_description.key == key:
            return entity

    raise LookupError(f"Couldn't find '{key}' sensor")


@pytest.mark.usefixtures("connected", "ecomax_p", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_p(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update sensor entry for ecomax p."""
    with patch(
        "custom_components.plum_ecomax.sensor.async_get_current_platform"
    ) as mock_async_get_current_platform:
        assert await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    sensor_types = (
        SENSOR_TYPES
        + MODULE_LAMBDA_SENSOR_TYPES
        + ECOMAX_P_MIXER_SENSOR_TYPES
        + ECOMAX_P_SENSOR_TYPES
        + METER_TYPES
    )
    assert len(added_entities) == len(sensor_types)

    # Check that all sensors are present.
    for sensor_type in sensor_types:
        assert _lookup_sensor(added_entities, sensor_type.key)

    # Test ecomax sensor.
    entity = _lookup_sensor(added_entities, "heating_temp")
    assert isinstance(entity, EcomaxSensor)
    await entity.async_added_to_hass()
    assert entity.entity_registry_enabled_default
    assert entity.available
    assert entity.native_value == 0
    assert entity.native_precision == 1
    await entity.async_update(65)
    assert entity.native_value == 65

    # Test unavailable sensor.
    entity = _lookup_sensor(added_entities, "optical_temp")
    await entity.async_added_to_hass()
    assert not entity.entity_registry_enabled_default
    assert not entity.available

    # Test meter sensor.
    entity = _lookup_sensor(added_entities, "fuel_burned")
    assert isinstance(entity, EcomaxMeter)
    mock_last_sensor_data = Mock(spec=SensorExtraStoredData)
    mock_last_sensor_data.configure_mock(
        native_value=2, native_unit_of_measurement="kg"
    )
    with patch(
        "custom_components.plum_ecomax.sensor.EcomaxSensor.async_added_to_hass"
    ) as mock_added_to_hass, patch(
        "custom_components.plum_ecomax.sensor.RestoreSensor.async_get_last_sensor_data",
        side_effect=(None, mock_last_sensor_data),
        return_value=None,
    ) as mock_get_last_sensor_data:
        await entity.async_added_to_hass()
        assert entity.native_value == 0
        await entity.async_added_to_hass()
        assert entity.native_value == 2

    assert entity.unit_of_measurement == "kg"
    assert mock_added_to_hass.await_count == 2
    assert mock_get_last_sensor_data.await_count == 2

    # Check meter calibration and reset.
    await entity.async_calibrate_meter(5)
    assert entity.native_value == 5
    with patch.object(EcomaxMeter, "state_class", SensorStateClass.TOTAL), patch(
        "homeassistant.util.dt.utcnow"
    ) as mock_utcnow:
        await entity.async_reset_meter()

    mock_utcnow.assert_called_once()
    assert entity.native_value == 0
    await entity.async_update(3)
    assert entity.native_value == 3

    # Test ecomax p state sensor.
    entity = _lookup_sensor(added_entities, "state")
    assert isinstance(entity, EcomaxSensor)
    await entity.async_added_to_hass()
    assert entity.native_value == STATE_OFF

    # Test ecomax p software version sensor.
    entity = _lookup_sensor(added_entities, "modules")
    assert isinstance(entity, EcomaxSensor)
    await entity.async_added_to_hass()
    assert entity.native_value == "6.10.32.K1"

    # Test ecomax p uid sensor.
    entity = _lookup_sensor(added_entities, "product")
    assert isinstance(entity, EcomaxSensor)
    await entity.async_added_to_hass()
    assert entity.native_value == "TEST"

    # Test ecomax p mixer temperature sensor.
    entity = _lookup_sensor(added_entities, "current_temp")
    assert isinstance(entity, MixerSensor)
    assert isinstance(entity.device, Mixer)
    assert entity.unique_id == "TEST-mixer-0-current_temp"
    assert entity.index == 0
    assert "Mixer temperature" in entity.name

    # Test ecomax p mixer target temperature sensor.
    entity = _lookup_sensor(added_entities, "target_temp")
    assert isinstance(entity, MixerSensor)
    assert entity.index == 0
    assert "Mixer target temperature" in entity.name

    # Test entity services.
    platform = mock_async_get_current_platform.return_value
    platform.async_register_entity_service.assert_has_calls(
        [
            call(SERVICE_RESET_METER, mock.ANY, "async_reset_meter"),
            call(SERVICE_CALIBRATE_METER, mock.ANY, "async_calibrate_meter"),
        ]
    )


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_i(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update sensor entry for ecomax i."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    assert len(added_entities) == len(
        SENSOR_TYPES
        + MODULE_LAMBDA_SENSOR_TYPES
        + ECOMAX_I_MIXER_SENSOR_TYPES
        + ECOMAX_I_SENSOR_TYPES
    )

    # Check first and last entity.
    assert added_entities[0].entity_description.key == SENSOR_TYPES[0].key
    assert added_entities[-1].entity_description.key == ECOMAX_I_SENSOR_TYPES[-1].key

    # Test ecomax i circuit temperature sensor.
    entity = _lookup_sensor(added_entities, "current_temp")
    assert isinstance(entity, MixerSensor)
    assert entity.index == 0
    assert "Circuit temperature" in entity.name

    # Test ecomax i circuit target temperature sensor.
    entity = _lookup_sensor(added_entities, "target_temp")
    assert isinstance(entity, MixerSensor)
    assert entity.index == 0
    assert "Circuit target temperature" in entity.name


@pytest.mark.usefixtures("ecomax_p")
async def test_async_setup_and_update_entry_without_mixers(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update sensor entry for ecomax p
    without mixers.
    """
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    assert "Couldn't load mixer sensors" in caplog.text

    # Check that mixer sensor is not added.
    with pytest.raises(LookupError):
        _lookup_sensor(added_entities, "current_temp")


@pytest.mark.usefixtures("ecomax_base")
async def test_async_setup_and_update_entry_with_no_sensor_data(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update sensor entry for ecomax p
    without the sensor data.
    """
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_not_called()
    assert "Couldn't load device sensors" in caplog.text


@pytest.mark.usefixtures("ecomax_unknown")
async def test_async_setup_and_update_entry_with_unknown_ecomax_model(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update sensor entry for unknown ecomax model."""
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_not_called()
    assert "Couldn't setup platform due to unknown controller model" in caplog.text
