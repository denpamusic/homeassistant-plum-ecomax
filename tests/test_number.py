"""Test the number platform."""

from unittest.mock import patch

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_SET_VALUE,
    NumberMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pyplumio.structures.ecomax_parameters import (
    EcomaxParameter,
    EcomaxParameterDescription,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import CALORIFIC_KWH_KG


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
    """Sets the value."""

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

    # Get initial state.
    state = hass.states.get(target_heating_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Target heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.dispatch(
        target_heating_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=65,
            min_value=30,
            max_value=80,
            description=EcomaxParameterDescription(target_heating_temperature_key),
        ),
    )
    state = hass.states.get(target_heating_temperature_entity_id)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Dispatch new boundaries.
    await connection.device.dispatch(
        "min_heating_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=20,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription("min_heating_target_temp"),
        ),
    )
    await connection.device.dispatch(
        "max_heating_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription("max_heating_target_temp"),
        ),
    )
    state = hass.states.get(target_heating_temperature_entity_id)
    assert state.attributes[ATTR_MIN] == 20
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, target_heating_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(target_heating_temperature_key, 70)
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

    # Get initial state.
    state = hass.states.get(minimum_heating_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Minimum heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.dispatch(
        minimum_heating_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=30,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription(minimum_heating_temperature_key),
        ),
    )
    state = hass.states.get(minimum_heating_temperature_entity_id)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 40

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, minimum_heating_temperature_entity_id, 40)

    mock_set_nowait.assert_called_once_with(minimum_heating_temperature_key, 40)
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

    # Get initial state.
    state = hass.states.get(maximum_heating_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Maximum heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.dispatch(
        maximum_heating_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription(maximum_heating_temperature_key),
        ),
    )
    state = hass.states.get(maximum_heating_temperature_entity_id)
    assert state.state == "90.0"
    assert state.attributes[ATTR_MIN] == 60
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, maximum_heating_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(maximum_heating_temperature_key, 70)
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
    grate_mode_temperature_key = "heating_temp_grate"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(grate_mode_temperature_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(grate_mode_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Grate mode temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.dispatch(
        grate_mode_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=65,
            min_value=30,
            max_value=80,
            description=EcomaxParameterDescription(grate_mode_temperature_key),
        ),
    )
    state = hass.states.get(grate_mode_temperature_entity_id)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Dispatch new boundaries.
    await connection.device.dispatch(
        "min_heating_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=20,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription("min_heating_target_temp"),
        ),
    )
    await connection.device.dispatch(
        "max_heating_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription("max_heating_target_temp"),
        ),
    )
    state = hass.states.get(grate_mode_temperature_entity_id)
    assert state.attributes[ATTR_MIN] == 20
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, grate_mode_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(grate_mode_temperature_key, 70)
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

    # Get initial state.
    state = hass.states.get(fuzzy_logic_minimum_power_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuzzy logic minimum power"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.dispatch(
        fuzzy_logic_minimum_power_key,
        EcomaxParameter(
            device=connection.device,
            value=30,
            min_value=0,
            max_value=50,
            description=EcomaxParameterDescription(fuzzy_logic_minimum_power_key),
        ),
    )
    state = hass.states.get(fuzzy_logic_minimum_power_entity_id)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 50

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, fuzzy_logic_minimum_power_entity_id, 10)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_minimum_power_key, 10)
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

    # Get initial state.
    state = hass.states.get(fuzzy_logic_maximum_power_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuzzy logic maximum power"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.dispatch(
        fuzzy_logic_maximum_power_key,
        EcomaxParameter(
            device=connection.device,
            value=50,
            min_value=30,
            max_value=100,
            description=EcomaxParameterDescription(fuzzy_logic_maximum_power_key),
        ),
    )
    state = hass.states.get(fuzzy_logic_maximum_power_entity_id)
    assert state.state == "50.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 100

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, fuzzy_logic_maximum_power_entity_id, 45)

    mock_set_nowait.assert_called_once_with(fuzzy_logic_maximum_power_key, 45)
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
    fuel_calorific_value_key = "fuel_calorific_value_kwh_kg"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuel_calorific_value_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(fuel_calorific_value_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuel calorific value"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == CALORIFIC_KWH_KG
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 0.1
    assert state.attributes[ATTR_STEP] == 0.1
    assert state.attributes[ATTR_MODE] == NumberMode.BOX

    # Dispatch new state.
    await connection.device.dispatch(
        fuel_calorific_value_key,
        EcomaxParameter(
            device=connection.device,
            value=47,
            min_value=40,
            max_value=50,
            description=EcomaxParameterDescription(
                fuel_calorific_value_key, multiplier=10
            ),
        ),
    )
    state = hass.states.get(fuel_calorific_value_entity_id)
    assert state.state == "4.7"
    assert state.attributes[ATTR_MIN] == 4.0
    assert state.attributes[ATTR_MAX] == 5.0

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, fuel_calorific_value_entity_id, 4.8)

    mock_set_nowait.assert_called_once_with(fuel_calorific_value_key, 4.8)
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

    # Get initial state.
    state = hass.states.get(target_mixer_temperature_entity_id)
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

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        target_mixer_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=65,
            min_value=30,
            max_value=80,
            description=EcomaxParameterDescription(target_mixer_temperature_key),
        ),
    )
    state = hass.states.get(target_mixer_temperature_entity_id)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Dispatch new boundaries.
    await connection.device.mixers[0].dispatch(
        "min_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=20,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription("min_target_temp"),
        ),
    )
    await connection.device.mixers[0].dispatch(
        "max_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription("max_target_temp"),
        ),
    )
    state = hass.states.get(target_mixer_temperature_entity_id)
    assert state.attributes[ATTR_MIN] == 20
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, target_mixer_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(target_mixer_temperature_key, 70)
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

    # Get initial state.
    state = hass.states.get(minimum_mixer_temperature_entity_id)
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

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        minimum_mixer_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=30,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription(minimum_mixer_temperature_key),
        ),
    )
    state = hass.states.get(minimum_mixer_temperature_entity_id)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 40

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, minimum_mixer_temperature_entity_id, 40)

    mock_set_nowait.assert_called_once_with(minimum_mixer_temperature_key, 40)
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

    # Get initial state.
    state = hass.states.get(maximum_mixer_temperature_entity_id)
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

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        maximum_mixer_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription(maximum_mixer_temperature_key),
        ),
    )
    state = hass.states.get(maximum_mixer_temperature_entity_id)
    assert state.state == "90.0"
    assert state.attributes[ATTR_MIN] == 60
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, maximum_mixer_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(maximum_mixer_temperature_key, 70)
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
    target_circuit_temperature_key = "mixer_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(target_circuit_temperature_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(target_circuit_temperature_entity_id)
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

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        target_circuit_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=65,
            min_value=30,
            max_value=80,
            description=EcomaxParameterDescription(target_circuit_temperature_key),
        ),
    )
    state = hass.states.get(target_circuit_temperature_entity_id)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Dispatch new boundaries.
    await connection.device.mixers[0].dispatch(
        "min_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=20,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription("min_target_temp"),
        ),
    )
    await connection.device.mixers[0].dispatch(
        "max_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription("max_target_temp"),
        ),
    )
    state = hass.states.get(target_circuit_temperature_entity_id)
    assert state.attributes[ATTR_MIN] == 20
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, target_circuit_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(target_circuit_temperature_key, 70)
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
        "number.ecomax_circuit_1_minimum_circuit_temperature"
    )
    minimum_circuit_temperature_key = "min_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(minimum_circuit_temperature_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(minimum_circuit_temperature_entity_id)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 1 Minimum circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        minimum_circuit_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=30,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription(minimum_circuit_temperature_key),
        ),
    )
    state = hass.states.get(minimum_circuit_temperature_entity_id)
    assert state.state == "30.0"
    assert state.attributes[ATTR_MIN] == 10
    assert state.attributes[ATTR_MAX] == 40

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, minimum_circuit_temperature_entity_id, 40)

    mock_set_nowait.assert_called_once_with(minimum_circuit_temperature_key, 40)
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
        "number.ecomax_circuit_1_maximum_circuit_temperature"
    )
    maximum_circuit_temperature_key = "max_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(maximum_circuit_temperature_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(maximum_circuit_temperature_entity_id)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 1 Maximum circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        maximum_circuit_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription(maximum_circuit_temperature_key),
        ),
    )
    state = hass.states.get(maximum_circuit_temperature_entity_id)
    assert state.state == "90.0"
    assert state.attributes[ATTR_MIN] == 60
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(hass, maximum_circuit_temperature_entity_id, 70)

    mock_set_nowait.assert_called_once_with(maximum_circuit_temperature_key, 70)
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
        "number.ecomax_circuit_1_day_target_circuit_temperature"
    )
    day_target_circuit_temperature_key = "day_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(day_target_circuit_temperature_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(day_target_circuit_temperature_entity_id)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 1 Day target circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        day_target_circuit_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=65,
            min_value=30,
            max_value=80,
            description=EcomaxParameterDescription(day_target_circuit_temperature_key),
        ),
    )
    state = hass.states.get(day_target_circuit_temperature_entity_id)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Dispatch new boundaries.
    await connection.device.mixers[0].dispatch(
        "min_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=20,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription("min_target_temp"),
        ),
    )
    await connection.device.mixers[0].dispatch(
        "max_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription("max_target_temp"),
        ),
    )
    state = hass.states.get(day_target_circuit_temperature_entity_id)
    assert state.attributes[ATTR_MIN] == 20
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(
            hass, day_target_circuit_temperature_entity_id, 70
        )

    mock_set_nowait.assert_called_once_with(day_target_circuit_temperature_key, 70)
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
        "number.ecomax_circuit_1_night_target_circuit_temperature"
    )
    night_target_circuit_temperature_key = "night_target_temp"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(night_target_circuit_temperature_entity_id)
    assert entry

    # Get initial state.
    state = hass.states.get(night_target_circuit_temperature_entity_id)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 1 Night target circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 1
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == NumberMode.AUTO

    # Dispatch new state.
    await connection.device.mixers[0].dispatch(
        night_target_circuit_temperature_key,
        EcomaxParameter(
            device=connection.device,
            value=65,
            min_value=30,
            max_value=80,
            description=EcomaxParameterDescription(
                night_target_circuit_temperature_key
            ),
        ),
    )
    state = hass.states.get(night_target_circuit_temperature_entity_id)
    assert state.state == "65.0"
    assert state.attributes[ATTR_MIN] == 30
    assert state.attributes[ATTR_MAX] == 80

    # Dispatch new boundaries.
    await connection.device.mixers[0].dispatch(
        "min_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=20,
            min_value=10,
            max_value=40,
            description=EcomaxParameterDescription("min_target_temp"),
        ),
    )
    await connection.device.mixers[0].dispatch(
        "max_target_temp",
        EcomaxParameter(
            device=connection.device,
            value=90,
            min_value=60,
            max_value=90,
            description=EcomaxParameterDescription("max_target_temp"),
        ),
    )
    state = hass.states.get(night_target_circuit_temperature_entity_id)
    assert state.attributes[ATTR_MIN] == 20
    assert state.attributes[ATTR_MAX] == 90

    # Set new state.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_value(
            hass, night_target_circuit_temperature_entity_id, 70
        )

    mock_set_nowait.assert_called_once_with(night_target_circuit_temperature_key, 70)
    assert state.state == "70.0"
