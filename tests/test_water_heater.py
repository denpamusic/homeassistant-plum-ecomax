"""Test the water heater platform."""

from unittest.mock import patch

from freezegun import freeze_time
from homeassistant.components.water_heater import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_OPERATION_LIST,
    ATTR_OPERATION_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    DOMAIN as WATER_HEATER,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE,
    STATE_ECO,
    STATE_PERFORMANCE,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pyplumio.structures.ecomax_parameters import (
    EcomaxParameter,
    EcomaxParameterDescription,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.water_heater import (
    HA_TO_EM_STATE,
    WATER_HEATER_MODES,
)


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


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture(name="async_set_operation_mode")
async def fixture_async_set_operation_mode():
    """Sets the water heater operation mode."""

    async def async_set_operation_mode(
        hass: HomeAssistant, entity_id: str, operation_mode: str
    ):
        await hass.services.async_call(
            WATER_HEATER,
            SERVICE_SET_OPERATION_MODE,
            {ATTR_ENTITY_ID: entity_id, ATTR_OPERATION_MODE: operation_mode},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_set_operation_mode


@pytest.fixture(name="async_set_temperature")
async def fixture_async_set_temperature():
    """Sets the water heater temperature."""

    async def async_set_temperature(
        hass: HomeAssistant, entity_id: str, temperature: float
    ):
        await hass.services.async_call(
            WATER_HEATER,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: entity_id, ATTR_TEMPERATURE: temperature},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_set_temperature


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_indirect_water_heater(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_operation_mode,
    async_set_temperature,
    frozen_time,
) -> None:
    """Test indirect water heater."""
    await setup_integration(hass, config_entry)
    indirect_water_heater_entity_id = "water_heater.ecomax_indirect_water_heater"
    water_heater_target_temperature_key = "water_heater_target_temp"
    water_heater_current_temperature_key = "water_heater_temp"
    water_heater_operation_mode_key = "water_heater_work_mode"
    water_heater_hysteresis_key = "water_heater_hysteresis"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(indirect_water_heater_entity_id)
    assert (
        entry.supported_features
        == WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    assert entry

    # Get initial value.
    state = hass.states.get(indirect_water_heater_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Indirect water heater"
    assert state.attributes[ATTR_MIN_TEMP] == 10
    assert state.attributes[ATTR_MAX_TEMP] == 80
    assert state.attributes[ATTR_OPERATION_LIST] == WATER_HEATER_MODES
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 0
    assert state.attributes[ATTR_TEMPERATURE] == 50
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 50
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 45
    assert state.attributes[ATTR_OPERATION_MODE] == STATE_OFF

    # Dispatch new water heater temperature.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(water_heater_current_temperature_key, 51)
    state = hass.states.get(indirect_water_heater_entity_id)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 51

    # Dispatch new water heater target temperature.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(
        water_heater_target_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=55,
            min_value=10,
            max_value=80,
            description=EcomaxParameterDescription(water_heater_target_temperature_key),
        ),
    )
    state = hass.states.get(indirect_water_heater_entity_id)
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 55
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 50

    # Dispatch new operation mode.
    await connection.device.dispatch(
        water_heater_operation_mode_key,
        EcomaxParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=2,
            description=EcomaxParameterDescription(water_heater_operation_mode_key),
        ),
    )
    state = hass.states.get(indirect_water_heater_entity_id)
    assert state.state == STATE_PERFORMANCE
    assert state.attributes[ATTR_OPERATION_MODE] == STATE_PERFORMANCE

    # Dispatch new hysteresis value.
    await connection.device.dispatch(
        water_heater_hysteresis_key,
        EcomaxParameter(
            device=connection.device,
            value=10,
            min_value=0,
            max_value=15,
            description=EcomaxParameterDescription(water_heater_hysteresis_key),
        ),
    )
    state = hass.states.get(indirect_water_heater_entity_id)
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 45

    # Test that water heater operation mode can be set.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_operation_mode(
            hass, indirect_water_heater_entity_id, STATE_ECO
        )

    mock_set_nowait.assert_called_once_with(
        water_heater_operation_mode_key, HA_TO_EM_STATE[STATE_ECO]
    )
    assert state.state == STATE_ECO

    # Test that water heater temperature can be set.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_temperature(hass, indirect_water_heater_entity_id, 60)

    mock_set_nowait.assert_called_once_with(water_heater_target_temperature_key, 60)
    assert state.state == STATE_ECO

    # Test without water heater.
    await hass.config_entries.async_remove(config_entry.entry_id)
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_water_heater",
        False,
    ):
        await setup_integration(hass, config_entry)

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(indirect_water_heater_entity_id)
    assert not entry
