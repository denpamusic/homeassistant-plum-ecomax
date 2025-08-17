"""Test the switch platform."""

from unittest.mock import patch

from homeassistant.components.switch import (
    DOMAIN as SWITCH,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import (
    EcomaxNumber,
    EcomaxNumberDescription,
    EcomaxSwitch,
    EcomaxSwitchDescription,
)
from pyplumio.parameters.mixer import (
    MixerNumber,
    MixerNumberDescription,
    MixerSwitch,
    MixerSwitchDescription,
)
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_CONTROL
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
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


@pytest.fixture(autouse=True)
def set_connected(connected):
    """Assume connected."""


@pytest.fixture(name="async_turn_on")
async def fixture_async_turn_on():
    """Turn switch on."""

    async def async_turn_on(hass: HomeAssistant, entity_id: str):
        await hass.services.async_call(
            SWITCH,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_turn_on


@pytest.fixture(name="async_turn_off")
async def fixture_async_turn_off():
    """Turn switch off."""

    async def async_turn_off(hass: HomeAssistant, entity_id: str):
        await hass.services.async_call(
            SWITCH,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_turn_off


@pytest.mark.usefixtures("ecomax_p", "ecomax_control")
async def test_ecomax_control_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test ecoMAX control switch."""
    await setup_integration(hass, config_entry)
    controller_switch_entity_id = "switch.ecomax_controller_switch"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(controller_switch_entity_id)
    assert entry
    assert entry.translation_key == "controller_switch"

    # Get initial value.
    state = hass.states.get(controller_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Controller switch"

    # Dispatch new value.
    await connection.device.dispatch(
        ATTR_ECOMAX_CONTROL,
        EcomaxSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=EcomaxNumberDescription(ATTR_ECOMAX_CONTROL),
        ),
    )
    state = hass.states.get(controller_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, controller_switch_entity_id)

    assert isinstance(state, State)
    mock_set_nowait.assert_called_once_with(ATTR_ECOMAX_CONTROL, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, controller_switch_entity_id)

    assert isinstance(state, State)
    mock_set_nowait.assert_called_once_with(ATTR_ECOMAX_CONTROL, STATE_ON)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_disinfection_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test water heater disinfection switch."""
    await setup_integration(hass, config_entry)
    water_heater_disinfection_switch_entity_id = (
        "switch.ecomax_water_heater_disinfection_switch"
    )
    water_heater_disinfection_switch_key = "water_heater_disinfection"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_disinfection_switch_entity_id)
    assert entry
    assert entry.translation_key == "water_heater_disinfection_switch"

    # Get initial value.
    state = hass.states.get(water_heater_disinfection_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Water heater disinfection switch"
    )

    # Dispatch new value.
    await connection.device.dispatch(
        water_heater_disinfection_switch_key,
        EcomaxSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=EcomaxSwitchDescription(water_heater_disinfection_switch_key),
        ),
    )
    state = hass.states.get(water_heater_disinfection_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, water_heater_disinfection_switch_entity_id)

    mock_set_nowait.assert_called_once_with(
        water_heater_disinfection_switch_key, STATE_OFF
    )
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, water_heater_disinfection_switch_entity_id)

    mock_set_nowait.assert_called_once_with(
        water_heater_disinfection_switch_key, STATE_ON
    )
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_pump_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test water heater pump switch."""
    await setup_integration(hass, config_entry)
    water_heater_pump_switch_entity_id = "switch.ecomax_water_heater_pump_switch"
    water_heater_pump_switch_key = "water_heater_work_mode"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_pump_switch_entity_id)
    assert entry
    assert entry.translation_key == "water_heater_pump_switch"

    # Get initial value.
    state = hass.states.get(water_heater_pump_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater pump switch"

    # Dispatch new value.
    await connection.device.dispatch(
        water_heater_pump_switch_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=2, min_value=0, max_value=2),
            description=EcomaxNumberDescription(water_heater_pump_switch_key),
        ),
    )
    state = hass.states.get(water_heater_pump_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, water_heater_pump_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_pump_switch_key, 0)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, water_heater_pump_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_pump_switch_key, 2)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_weather_control_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test weather control switch."""
    await setup_integration(hass, config_entry)
    weather_control_switch_entity_id = "switch.ecomax_weather_control_switch"
    weather_control_switch_key = "weather_control"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(weather_control_switch_entity_id)
    assert entry
    assert entry.translation_key == "weather_control_switch"

    # Get initial value.
    state = hass.states.get(weather_control_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Weather control switch"

    # Dispatch new value.
    await connection.device.dispatch(
        weather_control_switch_key,
        EcomaxSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=EcomaxNumberDescription(weather_control_switch_key),
        ),
    )
    state = hass.states.get(weather_control_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(weather_control_switch_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(weather_control_switch_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_fuzzy_logic_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test fuzzy logic switch."""
    await setup_integration(hass, config_entry)
    fuzzy_logic_switch_entity_id = "switch.ecomax_fuzzy_logic_switch"
    fuzzy_logic_switch_key = "fuzzy_logic"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuzzy_logic_switch_entity_id)
    assert entry
    assert entry.translation_key == "fuzzy_logic_switch"

    # Get initial value.
    state = hass.states.get(fuzzy_logic_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuzzy logic switch"

    # Dispatch new value.
    await connection.device.dispatch(
        fuzzy_logic_switch_key,
        EcomaxSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=EcomaxNumberDescription(fuzzy_logic_switch_key),
        ),
    )
    state = hass.states.get(fuzzy_logic_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, fuzzy_logic_switch_entity_id)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_switch_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, fuzzy_logic_switch_entity_id)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_switch_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p")
async def test_heating_schedule_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test heating schedule switch."""
    await setup_integration(hass, config_entry)
    heating_schedule_switch_entity_id = "switch.ecomax_heating_schedule_switch"
    heating_schedule_switch_key = "heating_schedule_switch"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(heating_schedule_switch_entity_id)
    assert entry
    assert entry.translation_key == "heating_schedule_switch"

    # Get initial value.
    state = hass.states.get(heating_schedule_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Heating schedule switch"

    # Dispatch new value.
    await connection.device.dispatch(
        heating_schedule_switch_key,
        EcomaxSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=EcomaxNumberDescription(heating_schedule_switch_key),
        ),
    )
    state = hass.states.get(heating_schedule_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, heating_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(heating_schedule_switch_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, heating_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(heating_schedule_switch_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_schedule_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test water heater schedule switch."""
    await setup_integration(hass, config_entry)
    water_heater_schedule_switch_entity_id = (
        "switch.ecomax_water_heater_schedule_switch"
    )
    water_heater_schedule_switch_key = "water_heater_schedule_switch"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_schedule_switch_entity_id)
    assert entry
    assert entry.translation_key == "water_heater_schedule_switch"

    # Get initial value.
    state = hass.states.get(water_heater_schedule_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater schedule switch"

    # Dispatch new value.
    await connection.device.dispatch(
        water_heater_schedule_switch_key,
        EcomaxSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=EcomaxNumberDescription(water_heater_schedule_switch_key),
        ),
    )
    state = hass.states.get(water_heater_schedule_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, water_heater_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_schedule_switch_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, water_heater_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_schedule_switch_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_enable_in_summer_mode_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test enable in summer mode switch."""
    await setup_integration(hass, config_entry)
    enable_in_summer_mode_entity_id = "switch.ecomax_mixer_1_enable_in_summer_mode"
    enable_in_summer_mode_key = "summer_work"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(enable_in_summer_mode_entity_id)
    assert entry
    assert entry.translation_key == "enable_in_summer_mode"

    # Get initial value.
    state = hass.states.get(enable_in_summer_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Enable in summer mode"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        enable_in_summer_mode_key,
        MixerSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=MixerSwitchDescription(enable_in_summer_mode_key),
        ),
    )

    state = hass.states.get(enable_in_summer_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_enable_in_summer_mode_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test enable in summer mode switch."""
    await setup_integration(hass, config_entry)
    enable_in_summer_mode_entity_id = "switch.ecomax_circuit_1_enable_in_summer_mode"
    enable_in_summer_mode_key = "summer_work"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(enable_in_summer_mode_entity_id)
    assert entry
    assert entry.translation_key == "enable_in_summer_mode"

    # Get initial value.
    state = hass.states.get(enable_in_summer_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 1 Enable in summer mode"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        enable_in_summer_mode_key,
        MixerSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=MixerSwitchDescription(enable_in_summer_mode_key),
        ),
    )

    state = hass.states.get(enable_in_summer_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_weather_control_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test mixer weather control switch."""
    await setup_integration(hass, config_entry)
    mixer_weather_control_switch_entity_id = (
        "switch.ecomax_mixer_1_weather_control_switch"
    )
    mixer_weather_control_switch_key = "weather_control"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(mixer_weather_control_switch_entity_id)
    assert entry
    assert entry.translation_key == "weather_control_switch"

    # Get initial value.
    state = hass.states.get(mixer_weather_control_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Weather control switch"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        mixer_weather_control_switch_key,
        MixerSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=MixerSwitchDescription(mixer_weather_control_switch_key),
        ),
    )
    state = hass.states.get(mixer_weather_control_switch_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, mixer_weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(mixer_weather_control_switch_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, mixer_weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(mixer_weather_control_switch_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_disable_pump_on_thermostat_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test disable pump on thermostat switch."""
    await setup_integration(hass, config_entry)
    disable_pump_on_thermostat_entity_id = (
        "switch.ecomax_mixer_1_disable_pump_on_thermostat"
    )
    disable_pump_on_thermostat_key = "disable_pump_on_thermostat"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(disable_pump_on_thermostat_entity_id)
    assert entry
    assert entry.translation_key == "disable_pump_on_thermostat"

    # Get initial value.
    state = hass.states.get(disable_pump_on_thermostat_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Mixer 1 Disable pump on thermostat"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        disable_pump_on_thermostat_key,
        MixerSwitch(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=MixerSwitchDescription(disable_pump_on_thermostat_key),
        ),
    )

    state = hass.states.get(disable_pump_on_thermostat_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, disable_pump_on_thermostat_entity_id)

    mock_set_nowait.assert_called_once_with(disable_pump_on_thermostat_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, disable_pump_on_thermostat_entity_id)

    mock_set_nowait.assert_called_once_with(disable_pump_on_thermostat_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_enable_circuit_switch(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test enable circuit switch."""
    await setup_integration(hass, config_entry)
    enable_circuit_entity_id = "switch.ecomax_circuit_1_enable_circuit"
    enable_circuit_key = "enable_circuit"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(enable_circuit_entity_id)
    assert entry
    assert entry.translation_key == "enable_circuit"

    # Get initial value.
    state = hass.states.get(enable_circuit_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 1 Enable circuit"

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        enable_circuit_key,
        MixerNumber(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=1),
            description=MixerNumberDescription(enable_circuit_key),
        ),
    )

    state = hass.states.get(enable_circuit_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, enable_circuit_entity_id)

    mock_set_nowait.assert_called_once_with(enable_circuit_key, 0)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, enable_circuit_entity_id)

    mock_set_nowait.assert_called_once_with(enable_circuit_key, 1)
    assert isinstance(state, State)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_enable_circuit_switch_is_unavailable_for_second_circuit(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test enable circuit switch is not available for second circuit."""
    await setup_integration(hass, config_entry)
    enable_circuit_entity_id = "switch.ecomax_circuit_2_enable_circuit"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(enable_circuit_entity_id)
    assert not entry


@pytest.mark.parametrize(
    ("source_device", "entity_id", "friendly_name"),
    (
        (
            "ecomax",
            "switch.ecomax_test_custom_switch",
            "ecoMAX Test custom switch",
        ),
        (
            "mixer_0",
            "switch.ecomax_mixer_1_test_custom_switch",
            "ecoMAX Mixer 1 Test custom switch",
        ),
        (
            "mixer_1",
            "switch.ecomax_mixer_2_test_custom_switch",
            "ecoMAX Mixer 2 Test custom switch",
        ),
        (
            "thermostat_0",
            "switch.ecomax_thermostat_1_test_custom_switch",
            "ecoMAX Thermostat 1 Test custom switch",
        ),
    ),
)
@pytest.mark.usefixtures("ecomax_p", "mixers", "thermostats", "custom_fields")
async def test_custom_switches(
    source_device: str,
    entity_id: str,
    friendly_name: str,
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_turn_off,
    async_turn_on,
) -> None:
    """Test custom switches."""
    custom_switch_key = "custom_switch"
    await setup_integration(
        hass,
        config_entry,
        options={
            "entities": {
                Platform.SWITCH: {
                    custom_switch_key: {
                        "name": "Test custom switch",
                        "key": custom_switch_key,
                        "source_device": source_device,
                    }
                }
            }
        },
    )

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == friendly_name

    # Dispatch new state.
    new_state = EcomaxSwitch(
        device=connection.device,
        values=ParameterValues(value=1, min_value=0, max_value=1),
        description=EcomaxSwitchDescription(custom_switch_key),
    )
    await dispatch_value(
        connection.device, custom_switch_key, new_state, source_device=source_device
    )
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, entity_id)

    mock_set_nowait.assert_called_once_with(custom_switch_key, STATE_OFF)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, entity_id)

    mock_set_nowait.assert_called_once_with(custom_switch_key, STATE_ON)
    assert isinstance(state, State)
    assert state.state == STATE_ON
