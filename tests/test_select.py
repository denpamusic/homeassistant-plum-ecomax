"""Test the select platform."""

from unittest.mock import patch

from homeassistant.components.select.const import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_OFF
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumber, EcomaxNumberDescription
from pyplumio.parameters.mixer import MixerNumber, MixerNumberDescription
import pytest

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.select import (
    STATE_AUTO,
    STATE_HEATED_FLOOR,
    STATE_HEATING,
    STATE_PUMP_ONLY,
    STATE_SUMMER,
    STATE_WINTER,
)
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


@pytest.fixture(name="async_select_option")
async def fixture_async_select_option():
    """Select the option."""

    async def async_select_option(hass: HomeAssistant, entity_id: str, option: str):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: option},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return async_select_option


@pytest.mark.usefixtures("ecomax_p")
async def test_summer_mode_select(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    setup_config_entry,
    async_select_option,
) -> None:
    """Test summer mode select."""
    await setup_config_entry()
    summer_mode_entity_id = "select.ecomax_summer_mode"
    summer_mode_select_key = "summer_mode"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(summer_mode_entity_id)
    assert entry
    assert entry.translation_key == "summer_mode"

    # Get initial value.
    state = hass.states.get(summer_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_WINTER
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Summer mode"
    assert state.attributes[ATTR_OPTIONS] == [STATE_WINTER, STATE_SUMMER, STATE_AUTO]
    options = state.attributes[ATTR_OPTIONS]

    # Dispatch new value.
    await dispatch_value(
        connection.device,
        summer_mode_select_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=2, min_value=0, max_value=2),
            description=EcomaxNumberDescription(summer_mode_select_key),
        ),
    )
    state = hass.states.get(summer_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_AUTO

    # Select an option.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_select_option(hass, summer_mode_entity_id, STATE_SUMMER)

    mock_set_nowait.assert_called_once_with(
        summer_mode_select_key, options.index(STATE_SUMMER)
    )
    assert isinstance(state, State)
    assert state.state == STATE_SUMMER


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_work_mode_select(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    setup_config_entry,
    async_select_option,
) -> None:
    """Test mixer work mode select."""
    await setup_config_entry()
    work_mode_entity_id = "select.ecomax_mixer_1_work_mode"
    work_mode_select_key = "work_mode"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(work_mode_entity_id)
    assert entry
    assert entry.translation_key == "mixer_work_mode"

    # Get initial value.
    state = hass.states.get(work_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Work mode"
    assert state.attributes[ATTR_OPTIONS] == [
        STATE_OFF,
        STATE_HEATING,
        STATE_HEATED_FLOOR,
        STATE_PUMP_ONLY,
    ]
    options = state.attributes[ATTR_OPTIONS]

    # Dispatch new value.
    await connection.device.mixers[0].dispatch(
        work_mode_select_key,
        MixerNumber(
            device=connection.device,
            values=ParameterValues(value=0, min_value=0, max_value=2),
            description=MixerNumberDescription(work_mode_select_key),
        ),
    )
    state = hass.states.get(work_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Select an option.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_select_option(hass, work_mode_entity_id, STATE_HEATING)

    mock_set_nowait.assert_called_once_with(
        work_mode_select_key, options.index(STATE_HEATING)
    )
    assert isinstance(state, State)
    assert state.state == STATE_HEATING


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_work_mode_select(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    setup_config_entry,
    async_select_option,
) -> None:
    """Test circuit support select."""
    await setup_config_entry()
    work_mode_entity_id = "select.ecomax_circuit_2_work_mode"
    work_mode_select_key = "enable_circuit"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(work_mode_entity_id)
    assert entry
    assert entry.translation_key == "mixer_work_mode"

    # Get initial value.
    state = hass.states.get(work_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 2 Work mode"
    assert state.attributes[ATTR_OPTIONS] == [
        STATE_OFF,
        STATE_HEATING,
        STATE_HEATED_FLOOR,
    ]
    options = state.attributes[ATTR_OPTIONS]

    # Dispatch new value.
    await connection.device.mixers[1].dispatch(
        work_mode_select_key,
        MixerNumber(
            device=connection.device,
            values=ParameterValues(value=0, min_value=0, max_value=2),
            description=MixerNumberDescription(work_mode_select_key),
        ),
    )
    state = hass.states.get(work_mode_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF

    # Select an option.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_select_option(hass, work_mode_entity_id, STATE_HEATING)

    mock_set_nowait.assert_called_once_with(
        work_mode_select_key, options.index(STATE_HEATING)
    )
    assert isinstance(state, State)
    assert state.state == STATE_HEATING


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_work_mode_select_is_unavailable_for_first_circuit(
    hass: HomeAssistant, setup_config_entry
) -> None:
    """Test circuit support select is not available for first circuit."""
    await setup_config_entry()
    work_mode_entity_id = "select.ecomax_circuit_1_work_mode"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(work_mode_entity_id)
    assert not entry
