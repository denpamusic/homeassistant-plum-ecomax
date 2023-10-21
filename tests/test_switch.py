"""Test the switch platform."""

from unittest.mock import patch

from homeassistant.components.switch import (
    DOMAIN as SWITCH,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    EcomaxBinaryParameter,
    EcomaxParameter,
    EcomaxParameterDescription,
)
from pyplumio.structures.mixer_parameters import (
    MixerBinaryParameter,
    MixerParameter,
    MixerParameterDescription,
)
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


@pytest.fixture(name="async_turn_on")
async def fixture_async_turn_on():
    """Turns switch on."""

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
    """Turns switch off."""

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
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Controller switch"

    # Dispatch new value.
    await connection.device.dispatch(
        ATTR_ECOMAX_CONTROL,
        EcomaxBinaryParameter(
            device=connection.device,
            value=STATE_ON,
            min_value=STATE_OFF,
            max_value=STATE_ON,
            description=EcomaxParameterDescription(ATTR_ECOMAX_CONTROL),
        ),
    )
    state = hass.states.get(controller_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, controller_switch_entity_id)

    mock_set_nowait.assert_called_once_with(ATTR_ECOMAX_CONTROL, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, controller_switch_entity_id)

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
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Water heater disinfection switch"
    )

    # Dispatch new value.
    await connection.device.dispatch(
        water_heater_disinfection_switch_key,
        EcomaxBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription(
                water_heater_disinfection_switch_key, cls=EcomaxBinaryParameter
            ),
        ),
    )
    state = hass.states.get(water_heater_disinfection_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, water_heater_disinfection_switch_entity_id)

    mock_set_nowait.assert_called_once_with(
        water_heater_disinfection_switch_key, STATE_OFF
    )
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, water_heater_disinfection_switch_entity_id)

    mock_set_nowait.assert_called_once_with(
        water_heater_disinfection_switch_key, STATE_ON
    )
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
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater pump switch"

    # Dispatch new value.
    await connection.device.dispatch(
        water_heater_pump_switch_key,
        EcomaxParameter(
            device=connection.device,
            value=2,
            min_value=0,
            max_value=2,
            description=EcomaxParameterDescription(water_heater_pump_switch_key),
        ),
    )
    state = hass.states.get(water_heater_pump_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, water_heater_pump_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_pump_switch_key, 0)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, water_heater_pump_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_pump_switch_key, 2)
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
    weather_control_switch_key = "heating_weather_control"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(weather_control_switch_entity_id)
    assert entry
    assert entry.translation_key == "weather_control_switch"

    # Get initial value.
    state = hass.states.get(weather_control_switch_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Weather control switch"

    # Dispatch new value.
    await connection.device.dispatch(
        weather_control_switch_key,
        EcomaxBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription(weather_control_switch_key),
        ),
    )
    state = hass.states.get(weather_control_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(weather_control_switch_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(weather_control_switch_key, STATE_ON)
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
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuzzy logic switch"

    # Dispatch new value.
    await connection.device.dispatch(
        fuzzy_logic_switch_key,
        EcomaxBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription(fuzzy_logic_switch_key),
        ),
    )
    state = hass.states.get(fuzzy_logic_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, fuzzy_logic_switch_entity_id)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_switch_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, fuzzy_logic_switch_entity_id)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_switch_key, STATE_ON)
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
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Heating schedule switch"

    # Dispatch new value.
    await connection.device.dispatch(
        heating_schedule_switch_key,
        EcomaxBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription(heating_schedule_switch_key),
        ),
    )
    state = hass.states.get(heating_schedule_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, heating_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(heating_schedule_switch_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, heating_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(heating_schedule_switch_key, STATE_ON)
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
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater schedule switch"

    # Dispatch new value.
    await connection.device.dispatch(
        water_heater_schedule_switch_key,
        EcomaxBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription(water_heater_schedule_switch_key),
        ),
    )
    state = hass.states.get(water_heater_schedule_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, water_heater_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_schedule_switch_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, water_heater_schedule_switch_entity_id)

    mock_set_nowait.assert_called_once_with(water_heater_schedule_switch_key, STATE_ON)
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
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Enable in summer mode"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        enable_in_summer_mode_key,
        MixerBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription(enable_in_summer_mode_key),
        ),
    )

    state = hass.states.get(enable_in_summer_mode_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_ON)
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
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 1 Enable in summer mode"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        enable_in_summer_mode_key,
        MixerBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription(enable_in_summer_mode_key),
        ),
    )

    state = hass.states.get(enable_in_summer_mode_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, enable_in_summer_mode_entity_id)

    mock_set_nowait.assert_called_once_with(enable_in_summer_mode_key, STATE_ON)
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
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Weather control switch"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        mixer_weather_control_switch_key,
        MixerBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription(mixer_weather_control_switch_key),
        ),
    )
    state = hass.states.get(mixer_weather_control_switch_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, mixer_weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(mixer_weather_control_switch_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, mixer_weather_control_switch_entity_id)

    mock_set_nowait.assert_called_once_with(mixer_weather_control_switch_key, STATE_ON)
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
    disable_pump_on_thermostat_key = "off_therm_pump"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(disable_pump_on_thermostat_entity_id)
    assert entry
    assert entry.translation_key == "disable_pump_on_thermostat"

    # Get initial value.
    state = hass.states.get(disable_pump_on_thermostat_entity_id)
    assert state.state == STATE_OFF
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Mixer 1 Disable pump on thermostat"
    )

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        disable_pump_on_thermostat_key,
        MixerBinaryParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription(disable_pump_on_thermostat_key),
        ),
    )

    state = hass.states.get(disable_pump_on_thermostat_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, disable_pump_on_thermostat_entity_id)

    mock_set_nowait.assert_called_once_with(disable_pump_on_thermostat_key, STATE_OFF)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, disable_pump_on_thermostat_entity_id)

    mock_set_nowait.assert_called_once_with(disable_pump_on_thermostat_key, STATE_ON)
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
    enable_circuit_key = "support"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(enable_circuit_entity_id)
    assert entry
    assert entry.translation_key == "enable_circuit"

    # Get initial value.
    state = hass.states.get(enable_circuit_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 1 Enable circuit"

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        enable_circuit_key,
        MixerParameter(
            device=connection.device,
            value=1,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription(enable_circuit_key),
        ),
    )

    state = hass.states.get(enable_circuit_entity_id)
    assert state.state == STATE_ON

    # Turn off.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_off(hass, enable_circuit_entity_id)

    mock_set_nowait.assert_called_once_with(enable_circuit_key, 0)
    assert state.state == STATE_OFF

    # Turn on.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_turn_on(hass, enable_circuit_entity_id)

    mock_set_nowait.assert_called_once_with(enable_circuit_key, 1)
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
