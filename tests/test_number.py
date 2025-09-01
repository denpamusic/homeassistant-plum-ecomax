"""Test the number platform."""

from math import isclose
from unittest.mock import patch

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_SET_VALUE,
    NumberDeviceClass,
    NumberMode,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    Platform,
    UnitOfMass,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumber, EcomaxNumberDescription
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import ATTR_ENTITIES
from tests.conftest import FLOAT_TOLERANCE, dispatch_value


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


@pytest.fixture(name="async_set_value")
async def fixture_async_set_value():
    """Set the value."""

    async def async_set_value(hass: HomeAssistant, entity_id: str, value: float):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_set_value


@pytest.mark.usefixtures("ecomax_p")
async def test_target_heating_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test target heating temperature number."""
    await setup_integration(hass, config_entry)
    target_heating_temperature_entity_id = "number.ecomax_target_heating_temperature"
    target_heating_temperature_key = "heating_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(target_heating_temperature_entity_id)
    assert entry
    assert entry.translation_key == "target_heating_temp"

    # Get initial state.
    state = hass.states.get(target_heating_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Target heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        target_heating_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=65, min_value=30, max_value=80),
            description=EcomaxNumberDescription(target_heating_temperature_key),
        ),
    )
    state = hass.states.get(target_heating_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, target_heating_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(target_heating_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_p")
async def test_minimum_heating_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test minimum heating temperature number."""
    await setup_integration(hass, config_entry)
    minimum_heating_temperature_entity_id = "number.ecomax_minimum_heating_temperature"
    minimum_heating_temperature_key = "min_heating_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(minimum_heating_temperature_entity_id)
    assert entry
    assert entry.translation_key == "min_heating_temp"

    # Get initial state.
    state = hass.states.get(minimum_heating_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Minimum heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        minimum_heating_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=30, min_value=10, max_value=40),
            description=EcomaxNumberDescription(minimum_heating_temperature_key),
        ),
    )
    state = hass.states.get(minimum_heating_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 40

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, minimum_heating_temperature_entity_id, 40)

    mock_set_nowait.assert_called_once_with(minimum_heating_temperature_key, 40)
    assert isinstance(state, State)
    assert state.state == "40.0"


@pytest.mark.usefixtures("ecomax_p")
async def test_maximum_heating_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test maximum heating temperature number."""
    await setup_integration(hass, config_entry)
    maximum_heating_temperature_entity_id = "number.ecomax_maximum_heating_temperature"
    maximum_heating_temperature_key = "max_heating_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(maximum_heating_temperature_entity_id)
    assert entry
    assert entry.translation_key == "max_heating_temp"

    # Get initial state.
    state = hass.states.get(maximum_heating_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Maximum heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        maximum_heating_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=90, min_value=60, max_value=90),
            description=EcomaxNumberDescription(maximum_heating_temperature_key),
        ),
    )
    state = hass.states.get(maximum_heating_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "90.0"
    assert state.attributes[ATTR_MIN] == 60
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, maximum_heating_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(maximum_heating_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_p")
async def test_grate_mode_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test grate mode temperature number."""
    await setup_integration(hass, config_entry)
    grate_mode_temperature_entity_id = "number.ecomax_grate_mode_temperature"
    grate_mode_temperature_key = "grate_heating_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(grate_mode_temperature_entity_id)
    assert entry
    assert entry.translation_key == "grate_mode_temp"

    # Get initial state.
    state = hass.states.get(grate_mode_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Grate mode temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        grate_mode_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=65, min_value=30, max_value=80),
            description=EcomaxNumberDescription(grate_mode_temperature_key),
        ),
    )
    state = hass.states.get(grate_mode_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, grate_mode_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(grate_mode_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_p")
async def test_fuzzy_logic_minimum_power_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test fuzzy logic minimum power number."""
    await setup_integration(hass, config_entry)
    fuzzy_logic_minimum_power_entity_id = "number.ecomax_fuzzy_logic_minimum_power"
    fuzzy_logic_minimum_power_key = "min_fuzzy_logic_power"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuzzy_logic_minimum_power_entity_id)
    assert entry
    assert entry.translation_key == "fuzzy_logic_min_power"

    # Get initial state.
    state = hass.states.get(fuzzy_logic_minimum_power_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuzzy logic minimum power"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        fuzzy_logic_minimum_power_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=30, min_value=0, max_value=50),
            description=EcomaxNumberDescription(fuzzy_logic_minimum_power_key),
        ),
    )
    state = hass.states.get(fuzzy_logic_minimum_power_entity_id)
    assert isinstance(state, State)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 50

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, fuzzy_logic_minimum_power_entity_id, 10)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_minimum_power_key, 10)
    assert isinstance(state, State)
    assert state.state == "10.0"


@pytest.mark.usefixtures("ecomax_p")
async def test_fuzzy_logic_maximum_power_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test fuzzy logic maximum power number."""
    await setup_integration(hass, config_entry)
    fuzzy_logic_maximum_power_entity_id = "number.ecomax_fuzzy_logic_maximum_power"
    fuzzy_logic_maximum_power_key = "max_fuzzy_logic_power"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuzzy_logic_maximum_power_entity_id)
    assert entry
    assert entry.translation_key == "fuzzy_logic_max_power"

    # Get initial state.
    state = hass.states.get(fuzzy_logic_maximum_power_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuzzy logic maximum power"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        fuzzy_logic_maximum_power_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=50, min_value=30, max_value=100),
            description=EcomaxNumberDescription(fuzzy_logic_maximum_power_key),
        ),
    )
    state = hass.states.get(fuzzy_logic_maximum_power_entity_id)
    assert isinstance(state, State)
    assert state.state == "50.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 100

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, fuzzy_logic_maximum_power_entity_id, 45)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_maximum_power_key, 45)
    assert isinstance(state, State)
    assert state.state == "45.0"


@pytest.mark.usefixtures("ecomax_p")
async def test_fuel_calorific_value_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test fuel calorific value number."""
    await setup_integration(hass, config_entry)
    fuel_calorific_value_entity_id = "number.ecomax_fuel_calorific_value"
    fuel_calorific_value_key = "fuel_calorific_value"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuel_calorific_value_entity_id)
    assert entry
    assert entry.translation_key == "fuel_calorific_value"

    # Get initial state.
    state = hass.states.get(fuel_calorific_value_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuel calorific value"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "kWh/kg"
    assert state.attributes[ATTR_MIN] == 0
    assert isclose(state.attributes[ATTR_MAX], 0.1, rel_tol=FLOAT_TOLERANCE)
    assert isclose(state.attributes[ATTR_STEP], 0.1, rel_tol=FLOAT_TOLERANCE)
    assert state.attributes[ATTR_MODE] == NumberMode.BOX

    # Dispatch new state.
    await dispatch_value(
        connection.device,
        fuel_calorific_value_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=47, min_value=40, max_value=50),
            description=EcomaxNumberDescription(fuel_calorific_value_key, step=0.1),
        ),
    )
    state = hass.states.get(fuel_calorific_value_entity_id)
    assert isinstance(state, State)
    assert state.state == "4.7"
    assert isclose(state.attributes[ATTR_MIN], 4.0, rel_tol=FLOAT_TOLERANCE)
    assert isclose(state.attributes[ATTR_MAX], 5.0, rel_tol=FLOAT_TOLERANCE)

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, fuel_calorific_value_entity_id, 4.8)

    mock_set_nowait.assert_called_once_with(fuel_calorific_value_key, 4.8)
    assert isinstance(state, State)
    assert state.state == "4.8"


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_target_mixer_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test mixer target mixer temperature number."""
    await setup_integration(hass, config_entry)
    target_mixer_temperature_entity_id = (
        "number.ecomax_mixer_1_target_mixer_temperature"
    )
    target_mixer_temperature_key = "mixer_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(target_mixer_temperature_entity_id)
    assert entry
    assert entry.translation_key == "target_mixer_temp"

    # Get initial state.
    state = hass.states.get(target_mixer_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Mixer 1 Target mixer temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        target_mixer_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=65, min_value=30, max_value=80),
            description=EcomaxNumberDescription(target_mixer_temperature_key),
        ),
    )
    state = hass.states.get(target_mixer_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, target_mixer_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(target_mixer_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_minimum_mixer_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test mixer minimum mixer temperature number."""
    await setup_integration(hass, config_entry)
    minimum_mixer_temperature_entity_id = (
        "number.ecomax_mixer_1_minimum_mixer_temperature"
    )
    minimum_mixer_temperature_key = "min_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(minimum_mixer_temperature_entity_id)
    assert entry
    assert entry.translation_key == "min_mixer_temp"

    # Get initial state.
    state = hass.states.get(minimum_mixer_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Mixer 1 Minimum mixer temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        minimum_mixer_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=30, min_value=10, max_value=40),
            description=EcomaxNumberDescription(minimum_mixer_temperature_key),
        ),
    )
    state = hass.states.get(minimum_mixer_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 40

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, minimum_mixer_temperature_entity_id, 40)

    mock_set_nowait.assert_called_once_with(minimum_mixer_temperature_key, 40)
    assert isinstance(state, State)
    assert state.state == "40.0"


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_maximum_mixer_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test mixer maximum mixer temperature number."""
    await setup_integration(hass, config_entry)
    maximum_mixer_temperature_entity_id = (
        "number.ecomax_mixer_1_maximum_mixer_temperature"
    )
    maximum_mixer_temperature_key = "max_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(maximum_mixer_temperature_entity_id)
    assert entry
    assert entry.translation_key == "max_mixer_temp"

    # Get initial state.
    state = hass.states.get(maximum_mixer_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Mixer 1 Maximum mixer temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        maximum_mixer_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=90, min_value=60, max_value=90),
            description=EcomaxNumberDescription(maximum_mixer_temperature_key),
        ),
    )
    state = hass.states.get(maximum_mixer_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "90.0"
    assert state.attributes[ATTR_MIN] == 60
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, maximum_mixer_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(maximum_mixer_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_target_circuit_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test cicuit target circuit temperature number."""
    await setup_integration(hass, config_entry)
    target_circuit_temperature_entity_id = (
        "number.ecomax_circuit_1_target_circuit_temperature"
    )
    target_circuit_temperature_key = "circuit_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(target_circuit_temperature_entity_id)
    assert entry
    assert entry.translation_key == "target_circuit_temp"

    # Get initial state.
    state = hass.states.get(target_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 1 Target circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        target_circuit_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=65, min_value=30, max_value=80),
            description=EcomaxNumberDescription(target_circuit_temperature_key),
        ),
    )
    state = hass.states.get(target_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, target_circuit_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(target_circuit_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_minimum_circuit_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test circuit minimum circuit temperature number."""
    await setup_integration(hass, config_entry)
    minimum_circuit_temperature_entity_id = (
        "number.ecomax_circuit_2_minimum_circuit_temperature"
    )
    minimum_circuit_temperature_key = "min_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(minimum_circuit_temperature_entity_id)
    assert entry
    assert entry.translation_key == "min_circuit_temp"

    # Get initial state.
    state = hass.states.get(minimum_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 2 Minimum circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[1].dispatch(
        minimum_circuit_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=30, min_value=10, max_value=40),
            description=EcomaxNumberDescription(minimum_circuit_temperature_key),
        ),
    )
    state = hass.states.get(minimum_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 40

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, minimum_circuit_temperature_entity_id, 40)

    mock_set_nowait.assert_called_once_with(minimum_circuit_temperature_key, 40)
    assert isinstance(state, State)
    assert state.state == "40.0"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_maximum_circuit_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test circuit maximum circuit temperature number."""
    await setup_integration(hass, config_entry)
    maximum_circuit_temperature_entity_id = (
        "number.ecomax_circuit_2_maximum_circuit_temperature"
    )
    maximum_circuit_temperature_key = "max_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(maximum_circuit_temperature_entity_id)
    assert entry
    assert entry.translation_key == "max_circuit_temp"

    # Get initial state.
    state = hass.states.get(maximum_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 2 Maximum circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[1].dispatch(
        maximum_circuit_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=90, min_value=60, max_value=90),
            description=EcomaxNumberDescription(maximum_circuit_temperature_key),
        ),
    )
    state = hass.states.get(maximum_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "90.0"
    assert state.attributes[ATTR_MIN] == 60
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, maximum_circuit_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(maximum_circuit_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_day_target_circuit_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test cicuit day target circuit temperature number."""
    await setup_integration(hass, config_entry)
    day_target_circuit_temperature_entity_id = (
        "number.ecomax_circuit_2_day_target_circuit_temperature"
    )
    day_target_circuit_temperature_key = "day_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(day_target_circuit_temperature_entity_id)
    assert entry
    assert entry.translation_key == "day_target_circuit_temp"

    # Get initial state.
    state = hass.states.get(day_target_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 2 Day target circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[1].dispatch(
        day_target_circuit_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=65, min_value=30, max_value=80),
            description=EcomaxNumberDescription(day_target_circuit_temperature_key),
        ),
    )
    state = hass.states.get(day_target_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(
            hass, day_target_circuit_temperature_entity_id, 70
        )

    mock_set_nowait.assert_called_once_with(day_target_circuit_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_night_target_circuit_temperature_number(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test cicuit night target circuit temperature number."""
    await setup_integration(hass, config_entry)
    night_target_circuit_temperature_entity_id = (
        "number.ecomax_circuit_2_night_target_circuit_temperature"
    )
    night_target_circuit_temperature_key = "night_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(night_target_circuit_temperature_entity_id)
    assert entry
    assert entry.translation_key == "night_target_circuit_temp"

    # Get initial state.
    state = hass.states.get(night_target_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 2 Night target circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO
    assert state.attributes[ATTR_DEVICE_CLASS] == NumberDeviceClass.TEMPERATURE

    # Dispatch new state.
    await connection.device.mixers[1].dispatch(
        night_target_circuit_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=65, min_value=30, max_value=80),
            description=EcomaxNumberDescription(night_target_circuit_temperature_key),
        ),
    )
    state = hass.states.get(night_target_circuit_temperature_entity_id)
    assert isinstance(state, State)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(
            hass, night_target_circuit_temperature_entity_id, 70
        )

    mock_set_nowait.assert_called_once_with(night_target_circuit_temperature_key, 70)
    assert isinstance(state, State)
    assert state.state == "70.0"


@pytest.mark.parametrize(
    (
        "source_device",
        "entity_id",
        "friendly_name",
        "step",
        "unit_of_measurement",
        "device_class",
    ),
    (
        (
            "ecomax",
            "number.ecomax_test_custom_number",
            "ecoMAX Test custom number",
            1,
            UnitOfMass.KILOGRAMS,
            NumberDeviceClass.WEIGHT,
        ),
        (
            "mixer_0",
            "number.ecomax_mixer_1_test_custom_number",
            "ecoMAX Mixer 1 Test custom number",
            0.1,
            UnitOfTemperature.CELSIUS,
            NumberDeviceClass.TEMPERATURE,
        ),
        (
            "mixer_1",
            "number.ecomax_mixer_2_test_custom_number",
            "ecoMAX Mixer 2 Test custom number",
            2,
            UnitOfTemperature.CELSIUS,
            NumberDeviceClass.TEMPERATURE,
        ),
        (
            "thermostat_0",
            "number.ecomax_thermostat_1_test_custom_number",
            "ecoMAX Thermostat 1 Test custom number",
            10,
            None,
            None,
        ),
    ),
)
@pytest.mark.usefixtures("ecomax_p", "mixers", "thermostats", "custom_fields")
async def test_custom_numbers(
    source_device: str,
    entity_id: str,
    friendly_name: str,
    step: int | float | None,
    unit_of_measurement: str | None,
    device_class: NumberDeviceClass | None,
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    async_set_value,
) -> None:
    """Test custom numbers."""
    custom_number_key = "custom_number"
    await setup_integration(
        hass,
        config_entry,
        options={
            ATTR_ENTITIES: {
                Platform.NUMBER: {
                    custom_number_key: {
                        "name": "Test custom number",
                        "key": custom_number_key,
                        "source_device": source_device,
                        "unit_of_measurement": unit_of_measurement,
                        "device_class": device_class,
                        "step": step,
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
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == friendly_name
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 50
    assert state.attributes[ATTR_STEP] == step
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    if device_class:
        assert state.attributes[ATTR_DEVICE_CLASS] == device_class
    else:
        assert ATTR_DEVICE_CLASS not in state.attributes

    if unit_of_measurement:
        assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == unit_of_measurement
    else:
        assert ATTR_UNIT_OF_MEASUREMENT not in state.attributes

    # Dispatch new state.
    new_state = EcomaxNumber(
        device=connection.device,
        values=ParameterValues(value=45, min_value=30, max_value=80),
        description=EcomaxNumberDescription(custom_number_key),
    )
    await dispatch_value(
        connection.device, custom_number_key, new_state, source_device=source_device
    )
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state == "45.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, entity_id, 40)

    mock_set_nowait.assert_called_once_with(custom_number_key, 40)
    assert isinstance(state, State)
    assert state.state == "40.0"
