"""Test the number platform."""

import json
from math import isclose
from pathlib import Path
from typing import cast
from unittest.mock import patch

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_STEP,
    ATTR_VALUE,
    DEVICE_CLASS_UNITS,
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
    REVOLUTIONS_PER_MINUTE,
    STATE_UNAVAILABLE,
    Platform,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pyplumio.const import ProductType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.parameters import NumberDescription, ParameterDescription, ParameterValues
from pyplumio.parameters.ecomax import (
    EXTENDED_PARAMETER_TYPES,
    PARAMETER_TYPES as ECOMAX_PARAMETER_TYPES,
    EcomaxNumber,
    EcomaxNumberDescription,
)
from pyplumio.parameters.mixer import (
    PARAMETER_TYPES as MIXER_PARAMETER_TYPES,
    MixerNumber,
    MixerNumberDescription,
)
from pyplumio.structures.ecomax_extended_parameters import (
    ATTR_ECOMAX_EXTENDED_PARAMETERS,
)
import pytest

from custom_components.plum_ecomax.connection import (
    WAIT_FOR_EXTENDED_PARAMETERS_SECONDS,
    EcomaxConnection,
)
from custom_components.plum_ecomax.const import (
    ATTR_CONTROL_MODE,
    ATTR_ENTITIES,
    DOMAIN as PLUM_ECOMAX_DOMAIN,
    EXTENDED_PARAMETER_REPLACEMENTS,
)
from custom_components.plum_ecomax.number import (
    MIXER_NUMBER_TYPES,
    NUMBER_TYPES,
    EcomaxNumberEntityDescription,
    async_make_extended_number_description,
)
from tests.conftest import ECOMAX_860P4_MODEL, FLOAT_TOLERANCE, dispatch_value


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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test target heating temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test minimum heating temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test maximum heating temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test grate mode temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test fuzzy logic minimum power number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test fuzzy logic maximum power number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test fuel calorific value number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test mixer target mixer temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test mixer minimum mixer temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test mixer maximum mixer temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test cicuit target circuit temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test circuit minimum circuit temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test circuit maximum circuit temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test cicuit day target circuit temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test cicuit night target circuit temperature number."""
    await setup_config_entry()
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
    setup_config_entry,
    async_set_value,
) -> None:
    """Test custom numbers."""
    custom_number_key = "custom_number"
    await setup_config_entry(
        {
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
        }
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


# Configuration numbers (ecoMAX P service parameters), as (key, entity_id).
# Translation keys of these entities are equal to their keys.
ECOMAX_P_CONFIG_NUMBERS: tuple[tuple[str, str], ...] = (
    ("heating_hysteresis", "number.ecomax_heating_hysteresis"),
    ("h1_hysteresis", "number.ecomax_h1_hysteresis"),
    ("h2_hysteresis", "number.ecomax_h2_hysteresis"),
    ("heating_pump_enable_temp", "number.ecomax_heating_pump_enable_temperature"),
    ("water_heater_hysteresis", "number.ecomax_water_heater_hysteresis"),
    ("airflow_power_100", "number.ecomax_airflow_power_100"),
    ("airflow_power_50", "number.ecomax_airflow_power_50"),
    ("airflow_power_30", "number.ecomax_airflow_power_30"),
    ("boiler_power_100", "number.ecomax_maximum_boiler_power_100"),
    ("boiler_power_50", "number.ecomax_intermediate_boiler_power_50"),
    ("boiler_power_30", "number.ecomax_minimum_boiler_power_30"),
    ("max_fan_boiler_power", "number.ecomax_fan_power_at_maximum_boiler_power"),
    ("min_fan_boiler_power", "number.ecomax_fan_power_at_minimum_boiler_power"),
    ("fuel_feeding_work_100", "number.ecomax_fuel_feeding_work_100"),
    ("fuel_feeding_work_50", "number.ecomax_fuel_feeding_work_50"),
    ("fuel_feeding_work_30", "number.ecomax_fuel_feeding_work_30"),
    ("fuel_feeding_pause_100", "number.ecomax_fuel_feeding_pause_100"),
    ("fuel_feeding_pause_50", "number.ecomax_fuel_feeding_pause_50"),
    ("fuel_feeding_pause_30", "number.ecomax_fuel_feeding_pause_30"),
    ("cycle_duration", "number.ecomax_feeder_cycle_duration"),
    ("min_boiler_power", "number.ecomax_boiler_power_lower_limit"),
    ("max_boiler_power", "number.ecomax_boiler_power_upper_limit"),
    ("min_fan_power", "number.ecomax_minimum_airflow_power"),
    ("max_fan_power", "number.ecomax_maximum_airflow_power"),
    ("reduction_airflow_temp", "number.ecomax_airflow_reduction_temperature"),
    ("fan_power_gain", "number.ecomax_fan_power_gain"),
    (
        "fuzzy_logic_fuel_flow_correction",
        "number.ecomax_fuzzy_logic_fuel_flow_correction",
    ),
    ("fuel_flow_correction", "number.ecomax_fuel_flow_correction"),
    ("airflow_correction_100", "number.ecomax_airflow_correction_100"),
    ("feeder_correction_100", "number.ecomax_feeder_correction_100"),
    ("airflow_correction_50", "number.ecomax_airflow_correction_50"),
    ("feeder_correction_50", "number.ecomax_feeder_correction_50"),
    ("airflow_correction_30", "number.ecomax_airflow_correction_30"),
    ("feeder_correction_30", "number.ecomax_feeder_correction_30"),
    ("grate_airflow_power", "number.ecomax_grate_airflow_power"),
    ("grate_heating_hysteresis", "number.ecomax_grate_heating_hysteresis"),
    ("grate_fan_work", "number.ecomax_grate_fan_work_time"),
    ("grate_fan_pause", "number.ecomax_grate_fan_pause_time"),
    ("grate_fuel_detection_time", "number.ecomax_grate_no_fuel_detection_time"),
    ("kindling_airflow_power", "number.ecomax_kindling_airflow_power"),
    ("kindling_low_airflow_power", "number.ecomax_kindling_low_airflow_power"),
    ("kindling_airflow_delay", "number.ecomax_kindling_airflow_delay"),
    ("kindling_test_time", "number.ecomax_ignition_test_time"),
    ("kindling_feeder_work", "number.ecomax_kindling_feeding_time"),
    ("kindling_feeder_dose", "number.ecomax_kindling_fuel_dose"),
    ("kindling_time", "number.ecomax_kindling_time"),
    ("warming_up_time", "number.ecomax_igniter_warming_up_time"),
    (
        "kindling_finish_exhaust_temp",
        "number.ecomax_kindling_finish_exhaust_temperature",
    ),
    (
        "kindling_finish_threshold_temp",
        "number.ecomax_kindling_finish_threshold_temperature",
    ),
    ("kindling_fumes_delta_temp", "number.ecomax_kindling_delta"),
    ("kindling_delta_temp", "number.ecomax_kindling_boiler_temperature_delta"),
    ("kindling_min_power_time", "number.ecomax_glowing_time"),
    ("stabilization_time", "number.ecomax_stabilization_time"),
    ("stabilization_airflow_power", "number.ecomax_airflow_power_after_kindling"),
    ("supervision_time", "number.ecomax_supervision_time"),
    ("supervision_feeder_work", "number.ecomax_supervision_feeding_time"),
    ("supervision_feeder_dose", "number.ecomax_supervision_fuel_dose"),
    ("supervision_feeder_pause", "number.ecomax_supervision_feeding_pause"),
    ("supervision_cycle_duration", "number.ecomax_supervision_cycle_duration"),
    ("supervision_airflow_power", "number.ecomax_supervision_airflow_power"),
    ("supervision_fan_pause", "number.ecomax_supervision_fan_pause_time"),
    ("supervision_fan_work", "number.ecomax_supervision_fan_work_time"),
    ("increase_fan_support_mode", "number.ecomax_increased_fan_support_mode"),
    ("burning_off_max_time", "number.ecomax_maximum_burning_off_time"),
    ("burning_off_min_time", "number.ecomax_minimum_burning_off_time"),
    ("burning_off_time", "number.ecomax_burning_off_time"),
    ("burning_off_airflow_power", "number.ecomax_burning_off_airflow_power"),
    ("burning_off_fan_work", "number.ecomax_burning_off_fan_work_time"),
    ("burning_off_fan_pause", "number.ecomax_burning_off_fan_pause_time"),
    ("start_burning_off", "number.ecomax_burning_off_start"),
    ("stop_burning_off", "number.ecomax_burning_off_stop"),
    ("cleaning_begin_time", "number.ecomax_kindling_cleaning_time"),
    ("burning_off_cleaning_time", "number.ecomax_burning_off_cleaning_time"),
    ("cleaning_airflow_power", "number.ecomax_cleaning_airflow_power"),
    ("warming_up_pause_time", "number.ecomax_warming_up_pause_time"),
    ("warming_up_cycle_time", "number.ecomax_warming_up_cycle_time"),
    ("remind_time", "number.ecomax_reminder_time"),
    ("lambda_correction_range", "number.ecomax_lambda_airflow_correction_range"),
    ("oxygen_100", "number.ecomax_oxygen_100"),
    ("oxygen_50", "number.ecomax_oxygen_50"),
    ("oxygen_30", "number.ecomax_oxygen_30"),
    ("fuzzy_logic_oxygen_correction", "number.ecomax_fuzzy_logic_oxygen_correction"),
    ("max_fuel_flow", "number.ecomax_feeder_capacity"),
    ("feeder_calibration", "number.ecomax_feeder_calibration"),
    ("fuel_detection_time", "number.ecomax_no_fuel_detection_time"),
    ("fuel_detection_exhaust_temp", "number.ecomax_no_fuel_exhaust_temperature"),
    ("feed2_h1", "number.ecomax_feeder_2_h1"),
    ("feed2_h2", "number.ecomax_feeder_2_h2"),
    ("feed2_h3", "number.ecomax_feeder_2_h3"),
    ("feed2_h4", "number.ecomax_feeder_2_h4"),
    ("feed2_work", "number.ecomax_feeder_2_work_time"),
    ("feed2_pause", "number.ecomax_feeder_2_pause_time"),
    ("pause_heating_for_water_heater", "number.ecomax_heating_pause_for_water_heater"),
    ("thermostat_pause", "number.ecomax_thermostat_pause_time"),
    ("thermostat_work", "number.ecomax_thermostat_work_time"),
    (
        "increase_heating_temp_for_water_heater",
        "number.ecomax_boiler_temperature_increase_for_water_heater_and_mixer",
    ),
    ("heating_curve", "number.ecomax_heating_curve"),
    ("heating_curve_shift", "number.ecomax_heating_curve_shift"),
    ("weather_factor", "number.ecomax_room_temperature_factor"),
    ("thermostat_operation", "number.ecomax_thermostat_operation"),
    (
        "thermostat_decrease_target_temp",
        "number.ecomax_thermostat_target_temperature_decrease",
    ),
    ("boiler_alert_temp", "number.ecomax_boiler_cooling_temperature"),
    ("max_feeder_temp", "number.ecomax_maximum_feeder_temperature"),
    ("external_boiler_temp", "number.ecomax_reserve_boiler_temperature"),
    ("alert_notify", "number.ecomax_alarm_signaling"),
    ("pump_hysteresis", "number.ecomax_pump_hysteresis"),
    ("min_water_heater_target_temp", "number.ecomax_minimum_water_heater_temperature"),
    ("max_water_heater_target_temp", "number.ecomax_maximum_water_heater_temperature"),
    ("summer_mode_enable_temp", "number.ecomax_summer_mode_enable_temperature"),
    ("summer_mode_disable_temp", "number.ecomax_summer_mode_disable_temperature"),
    ("water_heater_work_extension", "number.ecomax_water_heater_work_extension"),
    ("circulation_pause", "number.ecomax_circulation_pump_pause_time"),
    ("circulation_work", "number.ecomax_circulation_pump_work_time"),
    ("circulation_start_temp", "number.ecomax_circulation_start_temperature"),
    ("max_buffer_temp", "number.ecomax_maximum_buffer_temperature"),
    ("min_buffer_temp", "number.ecomax_minimum_buffer_temperature"),
    ("buffer_hysteresis", "number.ecomax_buffer_hysteresis"),
    ("buffer_load_start", "number.ecomax_buffer_loading_start_temperature"),
    ("buffer_load_stop", "number.ecomax_buffer_loading_stop_temperature"),
)

MIXER_CONFIG_NUMBERS: tuple[tuple[str, str], ...] = (
    (
        "thermostat_decrease_target_temp",
        "number.ecomax_mixer_1_thermostat_target_temperature_decrease",
    ),
    ("heating_curve", "number.ecomax_mixer_1_heating_curve"),
    ("heating_curve_shift", "number.ecomax_mixer_1_heating_curve_shift"),
    ("weather_factor", "number.ecomax_mixer_1_room_temperature_factor"),
    ("mixer_input_dead_zone", "number.ecomax_mixer_1_mixer_dead_zone"),
    ("thermostat_mode", "number.ecomax_mixer_1_thermostat_selection"),
)

ECOMAX_P_PARAMETERS: dict[str, ParameterDescription] = {
    description.name: description
    for description in ECOMAX_PARAMETER_TYPES[ProductType.ECOMAX_P]
}
MIXER_P_PARAMETERS: dict[str, ParameterDescription] = {
    description.name: description
    for description in MIXER_PARAMETER_TYPES[ProductType.ECOMAX_P]
}


@pytest.fixture(name="config_numbers")
async def fixture_config_numbers(ecomax_p: EcoMAX, mixers: EcoMAX) -> EcoMAX:
    """Inject ecoMAX P and mixer configuration numbers."""
    await ecomax_p.load(
        {
            key: EcomaxNumber(
                device=ecomax_p,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=cast(EcomaxNumberDescription, ECOMAX_P_PARAMETERS[key]),
            )
            for key, _ in ECOMAX_P_CONFIG_NUMBERS
        }
    )
    await ecomax_p.mixers[0].load(
        {
            key: MixerNumber(
                device=ecomax_p,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=cast(MixerNumberDescription, MIXER_P_PARAMETERS[key]),
            )
            for key, _ in MIXER_CONFIG_NUMBERS
        }
    )
    return ecomax_p


@pytest.mark.parametrize(
    ("descriptions", "table"),
    (
        (NUMBER_TYPES, ECOMAX_P_CONFIG_NUMBERS),
        (MIXER_NUMBER_TYPES, MIXER_CONFIG_NUMBERS),
    ),
)
def test_config_numbers_table_is_complete(
    descriptions: tuple[EcomaxNumberEntityDescription, ...],
    table: tuple[tuple[str, str], ...],
) -> None:
    """Test that every configuration number is covered by the test table."""
    assert [key for key, _ in table] == [
        description.key
        for description in descriptions
        if description.entity_category == EntityCategory.CONFIG
    ]


@pytest.mark.parametrize(
    ("source_device", "key", "entity_id"),
    [("ecomax", key, entity_id) for key, entity_id in ECOMAX_P_CONFIG_NUMBERS]
    + [("mixer_0", key, entity_id) for key, entity_id in MIXER_CONFIG_NUMBERS],
)
@pytest.mark.usefixtures("ecomax_p", "mixers", "config_numbers")
async def test_config_number(
    source_device: str,
    key: str,
    entity_id: str,
    hass: HomeAssistant,
    connection: EcomaxConnection,
    setup_config_entry,
    async_set_value,
) -> None:
    """Test ecoMAX P and mixer configuration numbers."""
    await setup_config_entry()
    if source_device == "ecomax":
        description = ECOMAX_P_PARAMETERS[key]
        number_cls: type[EcomaxNumber | MixerNumber] = EcomaxNumber
    else:
        description = MIXER_P_PARAMETERS[key]
        number_cls = MixerNumber

    assert isinstance(description, NumberDescription)

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.translation_key == key
    assert entry.entity_category == EntityCategory.CONFIG
    assert entry.disabled_by is None

    # Get initial state.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state != STATE_UNAVAILABLE
    assert isclose(
        state.attributes[ATTR_STEP], description.step, rel_tol=FLOAT_TOLERANCE
    )
    unit_of_measurement = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    if description.unit_of_measurement:
        # Units follow pyplumio.
        assert unit_of_measurement == getattr(
            description.unit_of_measurement, "value", description.unit_of_measurement
        )

    if device_class := state.attributes.get(ATTR_DEVICE_CLASS):
        assert (
            unit_of_measurement in DEVICE_CLASS_UNITS[NumberDeviceClass(device_class)]
        )

    # Dispatch new state.
    new_state = number_cls(
        device=connection.device,
        values=ParameterValues(value=15, min_value=10, max_value=20),
        description=description,
    )
    await dispatch_value(connection.device, key, new_state, source_device=source_device)
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert isclose(float(state.state), new_state.value, rel_tol=FLOAT_TOLERANCE)
    assert isclose(
        state.attributes[ATTR_MIN], new_state.min_value, rel_tol=FLOAT_TOLERANCE
    )
    assert isclose(
        state.attributes[ATTR_MAX], new_state.max_value, rel_tol=FLOAT_TOLERANCE
    )

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, entity_id, new_state.max_value)

    mock_set_nowait.assert_called_once_with(key, new_state.max_value)
    assert isinstance(state, State)
    assert isclose(float(state.state), new_state.max_value, rel_tol=FLOAT_TOLERANCE)


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_config_number_disabled(hass: HomeAssistant, setup_config_entry) -> None:
    """Test that configuration numbers not sent by the controller are disabled."""
    await setup_config_entry()
    entity_registry = er.async_get(hass)
    for entity_id in (
        "number.ecomax_airflow_power_100",
        "number.ecomax_mixer_1_heating_curve",
    ):
        entry = entity_registry.async_get(entity_id)
        assert entry, entity_id
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(entity_id) is None


EXTENDED_NUMBER_KEYS: tuple[str, ...] = tuple(
    description.name
    for description in EXTENDED_PARAMETER_TYPES[(41, ECOMAX_860P4_MODEL)].values()
    if description.name != ATTR_CONTROL_MODE
)

REPLACED_NUMBER_KEYS: tuple[str, ...] = tuple(
    key
    for key in EXTENDED_PARAMETER_REPLACEMENTS
    if key in {description.key for description in NUMBER_TYPES}
)


def get_number_entity_id(hass: HomeAssistant, key: str) -> str | None:
    """Return the number entity id by the key."""
    entity_registry = er.async_get(hass)
    return entity_registry.async_get_entity_id(
        Platform.NUMBER, PLUM_ECOMAX_DOMAIN, f"TEST-{key}"
    )


def test_extended_numbers_table_is_complete() -> None:
    """Test that every extended number has a valid unit and a name."""
    strings = json.loads(
        (
            Path(__file__).parents[1] / "custom_components/plum_ecomax/strings.json"
        ).read_text(encoding="utf-8")
    )
    for parameter in EXTENDED_PARAMETER_TYPES[(41, ECOMAX_860P4_MODEL)].values():
        if parameter.name == ATTR_CONTROL_MODE:
            continue

        description = async_make_extended_number_description(parameter)
        if description.device_class:
            assert (
                description.native_unit_of_measurement
                in DEVICE_CLASS_UNITS[description.device_class]
            ), parameter.name

        assert parameter.name in strings["entity"]["number"]


@pytest.mark.usefixtures("ecomax_p", "extended_parameters")
async def test_extended_numbers(hass: HomeAssistant, setup_config_entry) -> None:
    """Test that extended numbers replace legacy numbers for ecoMAX 860P4."""
    await setup_config_entry()
    assert_legacy_numbers(hass, extended=True)
    entity_registry = er.async_get(hass)
    assert len(EXTENDED_NUMBER_KEYS) == 60
    for key in EXTENDED_NUMBER_KEYS:
        entity_id = get_number_entity_id(hass, key)
        assert entity_id, key
        entry = entity_registry.async_get(entity_id)
        assert entry
        assert entry.translation_key == key
        assert entry.entity_category == EntityCategory.CONFIG
        assert entry.disabled_by is None
        state = hass.states.get(entity_id)
        assert isinstance(state, State)
        assert state.attributes[ATTR_MODE] == NumberMode.BOX

    assert not get_number_entity_id(hass, ATTR_CONTROL_MODE)


@pytest.mark.parametrize(
    (
        "key",
        "entity_id",
        "expected_state",
        "unit_of_measurement",
        "device_class",
        "new_value",
    ),
    (
        (
            "fan_speed_100",
            "number.ecomax_fan_speed_100",
            (1700, 1360, 2850, 10),
            REVOLUTIONS_PER_MINUTE,
            None,
            1500,
        ),
        (
            "draft_100",
            "number.ecomax_draft_100",
            (19, 15, 255, 1),
            UnitOfPressure.PA,
            NumberDeviceClass.PRESSURE,
            20,
        ),
        (
            "supervision_boiler_output",
            "number.ecomax_supervision_boiler_output",
            (2.8, 0.2, 51.0, 0.2),
            UnitOfPower.KILO_WATT,
            NumberDeviceClass.POWER,
            3.2,
        ),
        (
            "draft_correction",
            "number.ecomax_draft_measurement_correction",
            (1, -100, 100, 1),
            UnitOfPressure.PA,
            NumberDeviceClass.PRESSURE,
            -5,
        ),
        (
            "hopper_capacity",
            "number.ecomax_hopper_capacity",
            (90, 5, 1275, 5),
            UnitOfMass.KILOGRAMS,
            NumberDeviceClass.WEIGHT,
            95,
        ),
        (
            "kindling_temp_delta",
            "number.ecomax_kindling_temperature_delta",
            (5.0, 0.1, 6.0, 0.1),
            UnitOfTemperature.CELSIUS,
            NumberDeviceClass.TEMPERATURE_DELTA,
            4.5,
        ),
        (
            "kindling_fan_speed",
            "number.ecomax_kindling_fan_speed",
            (1000, 700, 2850, 10),
            REVOLUTIONS_PER_MINUTE,
            None,
            1100,
        ),
        (
            "stabilization_fan_speed",
            "number.ecomax_stabilization_fan_speed",
            (1000, 700, 2850, 10),
            REVOLUTIONS_PER_MINUTE,
            None,
            1200,
        ),
        (
            "thermostat_decrease_boiler_temp",
            "number.ecomax_thermostat_boiler_temperature_decrease",
            (0, 0, 30, 1),
            UnitOfTemperature.CELSIUS,
            NumberDeviceClass.TEMPERATURE_DELTA,
            5,
        ),
        (
            "moving_grate_work_time",
            "number.ecomax_moving_grate_work_time",
            (27, 10, 250, 1),
            UnitOfTime.SECONDS,
            NumberDeviceClass.DURATION,
            30,
        ),
    ),
)
@pytest.mark.usefixtures("ecomax_p", "extended_parameters")
async def test_extended_number(
    key: str,
    entity_id: str,
    expected_state: tuple[float, float, float, float],
    unit_of_measurement: str,
    device_class: NumberDeviceClass | None,
    new_value: float,
    hass: HomeAssistant,
    setup_config_entry,
    async_set_value,
) -> None:
    """Test ecoMAX 860P4 extended numbers."""
    await setup_config_entry()
    assert get_number_entity_id(hass, key) == entity_id

    # Get initial state.
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    value, min_value, max_value, step = expected_state
    assert isclose(float(state.state), value, rel_tol=FLOAT_TOLERANCE)
    assert isclose(state.attributes[ATTR_MIN], min_value, rel_tol=FLOAT_TOLERANCE)
    assert isclose(state.attributes[ATTR_MAX], max_value, rel_tol=FLOAT_TOLERANCE)
    assert isclose(state.attributes[ATTR_STEP], step, rel_tol=FLOAT_TOLERANCE)
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == unit_of_measurement
    assert state.attributes.get(ATTR_DEVICE_CLASS) == device_class

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, entity_id, new_value)

    mock_set_nowait.assert_called_once_with(key, new_value)
    assert isinstance(state, State)
    assert isclose(float(state.state), new_value, rel_tol=FLOAT_TOLERANCE)


def assert_legacy_numbers(hass: HomeAssistant, extended: bool) -> None:
    """Assert that legacy numbers are replaced only by extended numbers."""
    assert len(REPLACED_NUMBER_KEYS) == 22
    for key in REPLACED_NUMBER_KEYS:
        assert bool(get_number_entity_id(hass, key)) is not extended, key

    for key in EXTENDED_NUMBER_KEYS:
        assert bool(get_number_entity_id(hass, key)) is extended, key

    # Legacy numbers without the extended replacement are kept.
    assert get_number_entity_id(hass, "fuel_calorific_value")


@pytest.mark.usefixtures("ecomax_p", "extended_parameters", "mixers")
async def test_extended_numbers_keep_mixer_numbers(
    hass: HomeAssistant, setup_config_entry
) -> None:
    """Test that extended numbers replace only the boiler legacy numbers."""
    await setup_config_entry()
    assert not get_number_entity_id(hass, "thermostat_decrease_target_temp")
    assert (
        get_number_entity_id(hass, "mixer-0-thermostat_decrease_target_temp")
        == "number.ecomax_mixer_1_thermostat_target_temperature_decrease"
    )


@pytest.mark.usefixtures("ecomax_p", "ecomax_860p4")
async def test_legacy_numbers_without_extended_parameters(
    hass: HomeAssistant, connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test that legacy numbers are kept when extended table never arrives."""
    wait_for = connection.device.wait_for

    async def _wait_for(name: str, timeout: float | None = None) -> None:
        """Never receive the extended parameters."""
        if name == ATTR_ECOMAX_EXTENDED_PARAMETERS:
            raise TimeoutError

        await wait_for(name, timeout=timeout)

    with patch.object(
        connection.device, "wait_for", side_effect=_wait_for
    ) as mock_wait_for:
        await setup_config_entry()

    mock_wait_for.assert_any_await(
        ATTR_ECOMAX_EXTENDED_PARAMETERS,
        timeout=WAIT_FOR_EXTENDED_PARAMETERS_SECONDS,
    )
    assert_legacy_numbers(hass, extended=False)


@pytest.mark.parametrize("product", ("ecomax_p", "ecomax_860p3_o"), indirect=True)
@pytest.mark.usefixtures("product")
async def test_legacy_numbers_for_other_products(
    hass: HomeAssistant, setup_config_entry
) -> None:
    """Test that legacy numbers are unchanged for other products."""
    await setup_config_entry()
    assert_legacy_numbers(hass, extended=False)
