"""Test the binary sensor platform."""

from unittest.mock import patch

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pyplumio.const import ATTR_CONNECTED
from pyplumio.structures.sensor_data import (
    ATTR_CIRCULATION_PUMP,
    ATTR_FAN,
    ATTR_FAN2_EXHAUST,
    ATTR_FEEDER,
    ATTR_FIREPLACE_PUMP,
    ATTR_HEATING_PUMP,
    ATTR_LIGHTER,
    ATTR_PENDING_ALERTS,
    ATTR_PUMP,
    ATTR_SOLAR_PUMP,
    ATTR_WATER_HEATER_PUMP,
)
import pytest

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import ATTR_ENTITIES, ATTR_REGDATA
from tests.conftest import dispatch_value


@pytest.fixture(autouse=True)
def bypass_connection_setup():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"):
        yield


@pytest.fixture(autouse=True)
def bypass_async_migrate_entry():
    """Bypass async migrate entry."""
    with patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True):
        yield


@pytest.mark.usefixtures("ecomax_p")
async def test_heating_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test heating pump binary sensor."""
    await setup_config_entry()
    heating_pump_entity_id = "binary_sensor.ecomax_heating_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(heating_pump_entity_id)
    assert entry
    assert entry.translation_key == "heating_pump"

    # Get initial value.
    state = hass.states.get(heating_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Heating pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_HEATING_PUMP, True)
    state = hass.states.get(heating_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test water heater pump binary sensor."""
    await setup_config_entry()
    water_heater_pump_entity_id = "binary_sensor.ecomax_water_heater_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_pump_entity_id)
    assert entry
    assert entry.translation_key == "water_heater_pump"

    # Get initial value.
    state = hass.states.get(water_heater_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_WATER_HEATER_PUMP, True)
    state = hass.states.get(water_heater_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_circulation_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test circulation pump binary sensor."""
    await setup_config_entry()
    circulation_pump_entity_id = "binary_sensor.ecomax_circulation_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(circulation_pump_entity_id)
    assert entry
    assert entry.translation_key == "circulation_pump"

    # Get initial value.
    state = hass.states.get(circulation_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circulation pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_CIRCULATION_PUMP, True)
    state = hass.states.get(circulation_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_alert_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test alert binary sensor."""
    await setup_config_entry()
    alert_entity_id = "binary_sensor.ecomax_alert"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(alert_entity_id)
    assert entry
    assert entry.translation_key == "alert"
    assert entry.entity_category == EntityCategory.DIAGNOSTIC

    # Get initial value.
    state = hass.states.get(alert_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Alert"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.PROBLEM

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_PENDING_ALERTS, 2)
    state = hass.states.get(alert_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_connection_status_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test connection status binary sensor."""
    await setup_config_entry()
    connection_status_entity_id = "binary_sensor.ecomax_connection_status"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(connection_status_entity_id)
    assert entry
    assert entry.translation_key == "connection_status"
    assert entry.entity_category == EntityCategory.DIAGNOSTIC

    # Get initial value.
    state = hass.states.get(connection_status_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Connection status"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.CONNECTIVITY

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_CONNECTED, True)
    state = hass.states.get(connection_status_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_fan_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test fan binary sensor."""
    await setup_config_entry()
    fan_entity_id = "binary_sensor.ecomax_fan"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fan_entity_id)
    assert entry
    assert entry.translation_key == "fan"

    # Get initial value.
    state = hass.states.get(fan_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fan"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_FAN, True)
    state = hass.states.get(fan_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_exhaust_fan_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test exhaust fan binary sensor."""
    await setup_config_entry()
    exhaust_fan_entity_id = "binary_sensor.ecomax_exhaust_fan"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(exhaust_fan_entity_id)
    assert entry
    assert entry.translation_key == "exhaust_fan"

    # Get initial value.
    state = hass.states.get(exhaust_fan_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Exhaust fan"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_FAN2_EXHAUST, True)
    state = hass.states.get(exhaust_fan_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_feeder_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test feeder binary sensor."""
    await setup_config_entry()
    feeder_entity_id = "binary_sensor.ecomax_feeder"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(feeder_entity_id)
    assert entry
    assert entry.translation_key == "feeder"

    # Get initial value.
    state = hass.states.get(feeder_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Feeder"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_FEEDER, True)
    state = hass.states.get(feeder_entity_id)
    assert isinstance(state, State)


@pytest.mark.usefixtures("ecomax_p")
async def test_lighter_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test lighter binary sensor."""
    await setup_config_entry()
    lighter_entity_id = "binary_sensor.ecomax_lighter"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(lighter_entity_id)
    assert entry
    assert entry.translation_key == "lighter"

    # Get initial value.
    state = hass.states.get(lighter_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Lighter"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_LIGHTER, True)
    state = hass.states.get(lighter_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i")
async def test_solar_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test solar pump binary sensor."""
    await setup_config_entry()
    solar_pump_entity_id = "binary_sensor.ecomax_solar_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(solar_pump_entity_id)
    assert entry
    assert entry.translation_key == "solar_pump"

    # Get initial value.
    state = hass.states.get(solar_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Solar pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_SOLAR_PUMP, True)
    state = hass.states.get(solar_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i")
async def test_fireplace_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test fireplace pump binary sensor."""
    await setup_config_entry()
    fireplace_pump_entity_id = "binary_sensor.ecomax_fireplace_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fireplace_pump_entity_id)
    assert entry
    assert entry.translation_key == "fireplace_pump"

    # Get initial value.
    state = hass.states.get(fireplace_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fireplace pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_FIREPLACE_PUMP, True)
    state = hass.states.get(fireplace_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test mixer pump binary sensor."""
    await setup_config_entry()
    mixer_pump_entity_id = "binary_sensor.ecomax_mixer_1_mixer_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(mixer_pump_entity_id)
    assert entry
    assert entry.translation_key == "mixer_pump"

    # Get initial value.
    state = hass.states.get(mixer_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Mixer pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(ATTR_PUMP, True)
    state = hass.states.get(mixer_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_pump_binary_sensor(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test mixer pump binary sensor."""
    await setup_config_entry()
    circuit_pump_entity_id = "binary_sensor.ecomax_circuit_1_circuit_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(circuit_pump_entity_id)
    assert entry
    assert entry.translation_key == "circuit_pump"

    # Get initial value.
    state = hass.states.get(circuit_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 1 Circuit pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(ATTR_PUMP, True)
    state = hass.states.get(circuit_pump_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    ("source_device", "entity_id", "friendly_name"),
    (
        (
            "ecomax",
            "binary_sensor.ecomax_test_custom_binary_sensor",
            "ecoMAX Test custom binary sensor",
        ),
        (
            "mixer_0",
            "binary_sensor.ecomax_mixer_1_test_custom_binary_sensor",
            "ecoMAX Mixer 1 Test custom binary sensor",
        ),
        (
            "mixer_1",
            "binary_sensor.ecomax_mixer_2_test_custom_binary_sensor",
            "ecoMAX Mixer 2 Test custom binary sensor",
        ),
        (
            "thermostat_0",
            "binary_sensor.ecomax_thermostat_1_test_custom_binary_sensor",
            "ecoMAX Thermostat 1 Test custom binary sensor",
        ),
    ),
)
@pytest.mark.usefixtures("ecomax_p", "mixers", "thermostats", "custom_fields")
async def test_custom_binary_sensors(
    source_device: str,
    entity_id: str,
    friendly_name: str,
    hass: HomeAssistant,
    connection: EcomaxConnection,
    setup_config_entry,
) -> None:
    """Test custom binary sensors."""
    await setup_config_entry(
        {
            ATTR_ENTITIES: {
                Platform.BINARY_SENSOR: {
                    "custom_binary_sensor": {
                        "name": "Test custom binary sensor",
                        "key": "custom_binary_sensor",
                        "source_device": source_device,
                        "device_class": BinarySensorDeviceClass.RUNNING,
                    }
                }
            }
        }
    )

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry

    # Get initial value.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == friendly_name
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(
        connection.device, "custom_binary_sensor", True, source_device=source_device
    )
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "ecomax_860p3_o", "custom_fields")
async def test_custom_regdata_binary_sensors(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
):
    """Test custom regdata binary sensors."""
    await setup_config_entry(
        {
            ATTR_ENTITIES: {
                Platform.BINARY_SENSOR: {
                    "9000": {
                        "name": "Test custom regdata binary",
                        "key": "9000",
                        "source_device": ATTR_REGDATA,
                        "device_class": BinarySensorDeviceClass.RUNNING,
                    }
                }
            }
        }
    )

    entity_id = "binary_sensor.ecomax_test_custom_regdata_binary"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry

    # Get initial value.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Test custom regdata binary"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await dispatch_value(connection.device, ATTR_REGDATA, {9000: True})
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON
