"""Test the binary sensor platform."""

from unittest.mock import patch

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, State
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


@pytest.mark.parametrize(
    (
        "entity_id",
        "event_id",
        "translation_key",
        "friendly_name",
        "device_class",
        "entity_category",
    ),
    [
        (
            "binary_sensor.ecomax_heating_pump",
            ATTR_HEATING_PUMP,
            "heating_pump",
            "ecoMAX Heating pump",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_circulation_pump",
            ATTR_CIRCULATION_PUMP,
            "circulation_pump",
            "ecoMAX Circulation pump",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_alert",
            ATTR_PENDING_ALERTS,
            "alert",
            "ecoMAX Alert",
            BinarySensorDeviceClass.PROBLEM,
            None,
        ),
        (
            "binary_sensor.ecomax_connection_status",
            ATTR_CONNECTED,
            "connection_status",
            "ecoMAX Connection status",
            BinarySensorDeviceClass.CONNECTIVITY,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "binary_sensor.ecomax_fan",
            ATTR_FAN,
            "fan",
            "ecoMAX Fan",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_exhaust_fan",
            ATTR_FAN2_EXHAUST,
            "exhaust_fan",
            "ecoMAX Exhaust fan",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_feeder",
            ATTR_FEEDER,
            "feeder",
            "ecoMAX Feeder",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_lighter",
            ATTR_LIGHTER,
            "lighter",
            "ecoMAX Lighter",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_water_heater_pump",
            ATTR_WATER_HEATER_PUMP,
            "water_heater_pump",
            "ecoMAX Water heater pump",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
    ],
)
@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_ecomax_p_binary_sensors(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    entity_id: str,
    event_id: str,
    translation_key: str,
    friendly_name: str,
    device_class: BinarySensorDeviceClass,
    entity_category: EntityCategory,
) -> None:
    """Test ecoMAX p binary sensors."""
    await setup_integration(hass, config_entry)

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry is not None
    assert entry.translation_key == translation_key

    if entity_category:
        assert entry.entity_category == entity_category

    # Get initial value.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == friendly_name
    assert state.attributes[ATTR_DEVICE_CLASS] == device_class

    # Dispatch new value.
    await connection.device.dispatch(event_id, True)
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    (
        "entity_id",
        "event_id",
        "translation_key",
        "friendly_name",
        "device_class",
        "entity_category",
    ),
    [
        (
            "binary_sensor.ecomax_solar_pump",
            ATTR_SOLAR_PUMP,
            "solar_pump",
            "ecoMAX Solar pump",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
        (
            "binary_sensor.ecomax_fireplace_pump",
            ATTR_FIREPLACE_PUMP,
            "fireplace_pump",
            "ecoMAX Fireplace pump",
            BinarySensorDeviceClass.RUNNING,
            None,
        ),
    ],
)
@pytest.mark.usefixtures("ecomax_i")
async def test_ecomax_i_binary_sensors(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    entity_id: str,
    event_id: str,
    translation_key: str,
    friendly_name: str,
    device_class: BinarySensorDeviceClass,
    entity_category: EntityCategory,
) -> None:
    """Test ecoMAX i binary sensors."""
    await setup_integration(hass, config_entry)

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.translation_key == translation_key
    if entity_category:
        assert entry.entity_category == entity_category

    # Get initial value.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == friendly_name
    assert state.attributes[ATTR_DEVICE_CLASS] == device_class

    # Dispatch new value.
    await connection.device.dispatch(event_id, True)
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
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


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_pump_binary_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test mixer pump binary sensor."""
    await setup_integration(hass, config_entry)
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
