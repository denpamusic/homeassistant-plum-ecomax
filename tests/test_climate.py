"""Test the climate platform."""

from unittest.mock import patch

from freezegun import freeze_time
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    ATTR_TARGET_TEMP_STEP,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE,
    PRESET_COMFORT,
    PRESET_ECO,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pyplumio.helpers.parameter import ParameterValues
from pyplumio.structures.thermostat_parameters import (
    ThermostatParameter,
    ThermostatParameterDescription,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.climate import (
    CLIMATE_MODES,
    HA_PRESET_TO_EM_TEMP,
    HA_TO_EM_MODE,
    PRESET_AIRING,
    PRESET_SCHEDULE,
)
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


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture(name="async_set_preset_mode")
async def fixture_async_set_preset_mode():
    """Set the climate preset mode."""

    async def async_set_preset_mode(
        hass: HomeAssistant, entity_id: str, preset_mode: str
    ):
        await hass.services.async_call(
            CLIMATE,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: preset_mode},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_set_preset_mode


@pytest.fixture(name="async_set_temperature")
async def fixture_async_set_temperature():
    """Set the climate temperature."""

    async def async_set_temperature(
        hass: HomeAssistant, entity_id: str, temperature: float
    ):
        await hass.services.async_call(
            CLIMATE,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: entity_id, ATTR_TEMPERATURE: temperature},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_set_temperature


@pytest.mark.usefixtures("ecomax_p", "thermostats")
async def test_thermostat(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_preset_mode,
    frozen_time,
    caplog,
) -> None:
    """Test thermostat."""
    await setup_integration(hass, config_entry)
    thermostat_entity_id = "climate.ecomax_thermostat"
    thermostat_state_key = "state"
    thermostat_contacts_key = "contacts"
    thermostat_current_temperature_key = "current_temp"
    thermostat_target_temperature_key = "target_temp"
    thermostat_night_target_temperature_key = "night_target_temp"
    thermostat_mode_key = "mode"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(thermostat_entity_id)
    assert entry
    assert entry.translation_key == "ecomax_climate"
    assert (
        entry.supported_features
        == ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    # Get initial value.
    state = hass.states.get(thermostat_entity_id)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.HEAT]
    assert state.attributes[ATTR_MIN_TEMP] == 10
    assert state.attributes[ATTR_MAX_TEMP] == 35
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 0.1
    assert state.attributes[ATTR_PRESET_MODES] == CLIMATE_MODES
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 0
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_SCHEDULE
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Thermostat"

    # Dispatch new room temperature.
    frozen_time.move_to("12:00:10")
    await connection.device.thermostats[0].dispatch(
        thermostat_current_temperature_key, 18
    )
    state = hass.states.get(thermostat_entity_id)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 18

    # Dispatch new thermostat state.
    await connection.device.thermostats[0].dispatch(
        thermostat_state_key, HA_TO_EM_MODE[PRESET_ECO]
    )
    state = hass.states.get(thermostat_entity_id)
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_ECO

    # Dispatch unknown thermostat state and check for log message.
    await connection.device.thermostats[0].dispatch(thermostat_state_key, 99)
    assert "Unknown climate preset 99" in caplog.text

    # Dispatch new thermostat contacts state.
    await connection.device.thermostats[0].dispatch(thermostat_contacts_key, True)
    state = hass.states.get(thermostat_entity_id)
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

    # Dispatch new thermostat target temperature.
    await connection.device.thermostats[0].dispatch(
        thermostat_night_target_temperature_key,
        ThermostatParameter(
            offset=0,
            device=connection.device,
            values=ParameterValues(value=110, min_value=100, max_value=350),
            description=ThermostatParameterDescription(
                thermostat_night_target_temperature_key, multiplier=10, size=2
            ),
        ),
    )
    await connection.device.thermostats[0].dispatch(
        thermostat_target_temperature_key, 11
    )
    state = hass.states.get(thermostat_entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 11

    # Test that thermostat preset mode can be set.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_preset_mode(hass, thermostat_entity_id, PRESET_COMFORT)

    mock_set_nowait.assert_called_once_with(
        thermostat_mode_key, HA_TO_EM_MODE[PRESET_COMFORT]
    )
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_COMFORT

    # Test without thermostat.
    await hass.config_entries.async_remove(config_entry.entry_id)
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_thermostats",
        False,
    ):
        await setup_integration(hass, config_entry)

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(thermostat_entity_id)
    assert not entry


@pytest.mark.usefixtures("ecomax_p", "thermostats")
async def test_thermostat_presets(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_preset_mode,
    async_set_temperature,
    caplog,
) -> None:
    """Test thermostat presets."""
    await setup_integration(hass, config_entry)
    thermostat_entity_id = "climate.ecomax_thermostat"
    thermostat_mode_key = "mode"
    thermostat_target_temperature_key = "target_temp"
    thermostat_day_target_temperature_key = "day_target_temp"
    thermostat_night_target_temperature_key = "night_target_temp"

    # Test that correct target temperature is being set depending on the preset.
    for preset, temperature in HA_PRESET_TO_EM_TEMP.items():
        with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
            await async_set_preset_mode(hass, thermostat_entity_id, preset)
            await async_set_temperature(hass, thermostat_entity_id, 19)

        mock_set_nowait.assert_any_call(temperature, 19)

    # Test that target temperature name doesn't change when
    # in airing mode.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await async_set_preset_mode(hass, thermostat_entity_id, PRESET_ECO)
        await async_set_preset_mode(hass, thermostat_entity_id, PRESET_AIRING)
        await async_set_temperature(hass, thermostat_entity_id, 19)

    mock_set_nowait.assert_any_call(thermostat_night_target_temperature_key, 19)

    # Test that airing mode is correctly set.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await connection.device.thermostats[0].dispatch(
            thermostat_mode_key,
            ThermostatParameter(
                offset=0,
                device=connection.device,
                values=ParameterValues(value=4, min_value=0, max_value=7),
                description=ThermostatParameterDescription(
                    thermostat_mode_key, multiplier=1, size=2
                ),
            ),
        )

    state = hass.states.get(thermostat_entity_id)
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_AIRING

    # Test that exiting airing mode works.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await connection.device.thermostats[0].dispatch(
            thermostat_mode_key,
            ThermostatParameter(
                offset=0,
                device=connection.device,
                values=ParameterValues(value=0, min_value=0, max_value=7),
                description=ThermostatParameterDescription(
                    thermostat_mode_key, multiplier=1, size=2
                ),
            ),
        )

    state = hass.states.get(thermostat_entity_id)
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_SCHEDULE

    # Test that target temperature name is correct when
    # in day mode (schedule).
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await async_set_preset_mode(hass, thermostat_entity_id, PRESET_SCHEDULE)
        await connection.device.thermostats[0].dispatch(
            thermostat_target_temperature_key, 16
        )
        await async_set_temperature(hass, thermostat_entity_id, 17)

    mock_set_nowait.assert_any_call(thermostat_day_target_temperature_key, 17)

    # Test that target temperature name is correct when
    # in night mode (schedule).
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await async_set_preset_mode(hass, thermostat_entity_id, PRESET_SCHEDULE)
        await connection.device.thermostats[0].dispatch(
            thermostat_target_temperature_key, 10
        )
        await async_set_temperature(hass, thermostat_entity_id, 12)

    mock_set_nowait.assert_any_call(thermostat_night_target_temperature_key, 12)

    # Test that target temperature name doesn't change when
    # changing only target temperature.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await async_set_preset_mode(hass, thermostat_entity_id, PRESET_SCHEDULE)
        await connection.device.thermostats[0].dispatch(
            thermostat_target_temperature_key, 21
        )
        await async_set_temperature(hass, thermostat_entity_id, 10)

    mock_set_nowait.assert_any_call(thermostat_night_target_temperature_key, 10)
