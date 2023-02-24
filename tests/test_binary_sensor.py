"""Test the binary sensor platform."""

from unittest.mock import patch

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pyplumio.const import ATTR_CONNECTED
from pyplumio.structures.mixer_sensors import ATTR_PUMP
from pyplumio.structures.outputs import (
    ATTR_CIRCULATION_PUMP,
    ATTR_FAN,
    ATTR_FAN2_EXHAUST,
    ATTR_FEEDER,
    ATTR_FIREPLACE_PUMP,
    ATTR_HEATING_PUMP,
    ATTR_LIGHTER,
    ATTR_SOLAR_PUMP,
    ATTR_WATER_HEATER_PUMP,
)
from pyplumio.structures.pending_alerts import ATTR_PENDING_ALERTS
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection


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


@pytest.fixture(autouse=True)
def set_connected(connected):
    """Assume connected."""


@pytest.mark.usefixtures("ecomax_p")
async def test_heating_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test heating pump binary sensor."""
    await setup_integration(hass, config_entry)
    heating_pump_entity_id = "binary_sensor.test_heating_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(heating_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(heating_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Heating pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_HEATING_PUMP, True)
    state = hass.states.get(heating_pump_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test water heater pump binary sensor."""
    await setup_integration(hass, config_entry)
    water_heater_pump_entity_id = "binary_sensor.test_water_heater_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(water_heater_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Water heater pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_WATER_HEATER_PUMP, True)
    state = hass.states.get(water_heater_pump_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_circulation_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test circulation pump binary sensor."""
    await setup_integration(hass, config_entry)
    circulation_pump_entity_id = "binary_sensor.test_circulation_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(circulation_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(circulation_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Circulation pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_CIRCULATION_PUMP, True)
    state = hass.states.get(circulation_pump_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_alert_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test alert binary sensor."""
    await setup_integration(hass, config_entry)
    alert_entity_id = "binary_sensor.test_alert"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(alert_entity_id)
    assert entry
    assert entry.entity_category == EntityCategory.DIAGNOSTIC

    # Get initial value.
    state = hass.states.get(alert_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Alert"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.PROBLEM

    # Dispatch new value.
    await connection.device.dispatch(ATTR_PENDING_ALERTS, 2)
    state = hass.states.get(alert_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_connection_status_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test connection status binary sensor."""
    await setup_integration(hass, config_entry)
    connection_status_entity_id = "binary_sensor.test_connection_status"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(connection_status_entity_id)
    assert entry
    assert entry.entity_category == EntityCategory.DIAGNOSTIC

    # Get initial value.
    state = hass.states.get(connection_status_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Connection status"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.CONNECTIVITY

    # Dispatch new value.
    await connection.device.dispatch(ATTR_CONNECTED, True)
    state = hass.states.get(connection_status_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_fan_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test fan binary sensor."""
    await setup_integration(hass, config_entry)
    fan_entity_id = "binary_sensor.test_fan"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fan_entity_id)
    assert entry
    assert entry.original_icon == "mdi:fan"

    # Get initial value.
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Fan"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_FAN, True)
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_exhaust_fan_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test exhaust fan binary sensor."""
    await setup_integration(hass, config_entry)
    exhaust_fan_entity_id = "binary_sensor.test_exhaust_fan"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(exhaust_fan_entity_id)
    assert entry
    assert entry.original_icon == "mdi:fan"

    # Get initial value.
    state = hass.states.get(exhaust_fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Exhaust fan"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_FAN2_EXHAUST, True)
    state = hass.states.get(exhaust_fan_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_feeder_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test feeder binary sensor."""
    await setup_integration(hass, config_entry)
    feeder_entity_id = "binary_sensor.test_feeder"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(feeder_entity_id)
    assert entry
    assert entry.original_icon == "mdi:screw-lag"

    # Get initial value.
    state = hass.states.get(feeder_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Feeder"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_FEEDER, True)
    state = hass.states.get(feeder_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_lighter_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test lighter binary sensor."""
    await setup_integration(hass, config_entry)
    lighter_entity_id = "binary_sensor.test_lighter"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(lighter_entity_id)
    assert entry
    assert entry.original_icon == "mdi:fire"

    # Get initial value.
    state = hass.states.get(lighter_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Lighter"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_LIGHTER, True)
    state = hass.states.get(lighter_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i")
async def test_solar_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test solar pump binary sensor."""
    await setup_integration(hass, config_entry)
    solar_pump_entity_id = "binary_sensor.test_solar_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(solar_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(solar_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Solar pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_SOLAR_PUMP, True)
    state = hass.states.get(solar_pump_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i")
async def test_fireplace_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test fireplace pump binary sensor."""
    await setup_integration(hass, config_entry)
    fireplace_pump_entity_id = "binary_sensor.test_fireplace_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fireplace_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(fireplace_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Fireplace pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.dispatch(ATTR_FIREPLACE_PUMP, True)
    state = hass.states.get(fireplace_pump_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test mixer pump binary sensor."""
    await setup_integration(hass, config_entry)
    mixer_pump_entity_id = "binary_sensor.test_mixer_1_mixer_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(mixer_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(mixer_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Mixer 1 Mixer pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(ATTR_PUMP, True)
    state = hass.states.get(mixer_pump_entity_id)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test mixer pump binary sensor."""
    await setup_integration(hass, config_entry)
    circuit_pump_entity_id = "binary_sensor.test_circuit_1_circuit_pump"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(circuit_pump_entity_id)
    assert entry
    assert entry.original_icon == "mdi:pump"

    # Get initial value.
    state = hass.states.get(circuit_pump_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "test Circuit 1 Circuit pump"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.RUNNING

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(ATTR_PUMP, True)
    state = hass.states.get(circuit_pump_entity_id)
    assert state.state == STATE_ON
