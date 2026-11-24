"""Test the water heater platform."""

import asyncio
from unittest.mock import Mock, patch

from freezegun import freeze_time
from homeassistant.components.climate import ATTR_TARGET_TEMP_STEP
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
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntry
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumber, EcomaxNumberDescription
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.water_heater import HA_TO_EM_STATE


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


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture(name="async_set_operation_mode")
async def fixture_async_set_operation_mode():
    """Set the water heater operation mode."""

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
    """Set the water heater temperature."""

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
    setup_config_entry,
    async_set_operation_mode,
    async_set_temperature,
    frozen_time,
) -> None:
    """Test indirect water heater."""
    await setup_config_entry()
    indirect_water_heater_entity_id = "water_heater.ecomax_indirect_water_heater"
    water_heater_target_temperature_key = "water_heater_target_temp"
    water_heater_current_temperature_key = "water_heater_temp"
    water_heater_operation_mode_key = "water_heater_work_mode"
    water_heater_hysteresis_key = "water_heater_hysteresis"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(indirect_water_heater_entity_id)
    assert isinstance(entry, RegistryEntry)
    assert (
        entry.supported_features
        == WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    assert entry.translation_key == "indirect_water_heater"

    # Get initial value.
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Indirect water heater"
    assert state.attributes[ATTR_MIN_TEMP] == 10
    assert state.attributes[ATTR_MAX_TEMP] == 80
    assert state.attributes[ATTR_OPERATION_LIST] == [
        STATE_OFF,
        STATE_PERFORMANCE,
        STATE_ECO,
    ]
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 0
    assert state.attributes[ATTR_TEMPERATURE] == 50
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 50
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 45
    assert state.attributes[ATTR_OPERATION_MODE] == STATE_OFF
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 1

    # Dispatch new water heater temperature.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(water_heater_current_temperature_key, 51)
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 51

    # Dispatch new water heater target temperature.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(
        water_heater_target_temperature_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=55, min_value=10, max_value=80),
            description=EcomaxNumberDescription(water_heater_target_temperature_key),
        ),
    )
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 55
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 50

    # Dispatch new operation mode.
    await connection.device.dispatch(
        water_heater_operation_mode_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=1, min_value=0, max_value=2),
            description=EcomaxNumberDescription(water_heater_operation_mode_key),
        ),
    )
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_PERFORMANCE
    assert state.attributes[ATTR_OPERATION_MODE] == STATE_PERFORMANCE

    # Dispatch new hysteresis value.
    await connection.device.dispatch(
        water_heater_hysteresis_key,
        EcomaxNumber(
            device=connection.device,
            values=ParameterValues(value=10, min_value=0, max_value=15),
            description=EcomaxNumberDescription(water_heater_hysteresis_key),
        ),
    )
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 45

    # Test that water heater operation mode can be set.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_operation_mode(
            hass, indirect_water_heater_entity_id, STATE_ECO
        )

    mock_set_nowait.assert_called_once_with(
        water_heater_operation_mode_key, HA_TO_EM_STATE[STATE_ECO]
    )
    assert isinstance(state, State)
    assert state.state == STATE_ECO

    # Test that water heater temperature can be set.
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        state = await async_set_temperature(hass, indirect_water_heater_entity_id, 60)

    mock_set_nowait.assert_called_once_with(water_heater_target_temperature_key, 60)
    assert isinstance(state, State)
    assert state.state == STATE_ECO

    # Test without water heater.
    await hass.config_entries.async_remove(config_entry.entry_id)
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_water_heater",
        False,
    ):
        await setup_config_entry()

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(indirect_water_heater_entity_id)
    assert not entry


@pytest.mark.usefixtures("ecomax_p")
async def test_water_heater_guards_before_parameters_arrive(
    hass: HomeAssistant,
    ecomax_p: EcoMAX,
    setup_config_entry,
    async_set_operation_mode,
    async_set_temperature,
    caplog,
) -> None:
    """Test water heater set calls warn and skip before parameters load."""
    await ecomax_p.load({"water_heater_temp": 45.0})
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_water_heater",
        True,
    ):
        await setup_config_entry()

    indirect_water_heater_entity_id = "water_heater.ecomax_indirect_water_heater"
    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await async_set_temperature(hass, indirect_water_heater_entity_id, 55)
        await async_set_operation_mode(hass, indirect_water_heater_entity_id, STATE_ECO)

    mock_set_nowait.assert_not_called()
    assert (
        "Cannot set target temperature before water heater parameters are loaded"
        in caplog.text
    )
    assert (
        "Cannot set operation mode before water heater parameters are loaded"
        in caplog.text
    )


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_unsubscribes_on_unload(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_config_entry,
    frozen_time,
) -> None:
    """Test unloading config entry unsubscribes all water heater callbacks."""
    water_heater_keys = {
        "water_heater_temp",
        "water_heater_target_temp",
        "water_heater_work_mode",
        "water_heater_hysteresis",
    }
    unsubscribe_spies: dict[str, Mock] = {}
    original_subscribe = connection.device.subscribe

    def _capture_subscribe(name: str, callback):
        unsubscribe = original_subscribe(name, callback)
        if name not in water_heater_keys:
            return unsubscribe

        unsubscribe_spy = Mock(wraps=unsubscribe)
        unsubscribe_spies[name] = unsubscribe_spy
        return unsubscribe_spy

    with patch.object(connection.device, "subscribe", side_effect=_capture_subscribe):
        await setup_config_entry()

    assert set(unsubscribe_spies) == water_heater_keys

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    for unsubscribe_spy in unsubscribe_spies.values():
        unsubscribe_spy.assert_called_once_with()

    with patch(
        "custom_components.plum_ecomax.water_heater.EcomaxWaterHeater.async_write_ha_state"
    ) as mock_write_state:
        frozen_time.move_to("12:00:10")
        await connection.device.dispatch("water_heater_temp", 52.0)
        await connection.device.dispatch(
            "water_heater_target_temp",
            EcomaxNumber(
                device=connection.device,
                values=ParameterValues(value=58, min_value=10, max_value=80),
                description=EcomaxNumberDescription("water_heater_target_temp"),
            ),
        )
        await connection.device.dispatch(
            "water_heater_work_mode",
            EcomaxNumber(
                device=connection.device,
                values=ParameterValues(value=1, min_value=0, max_value=2),
                description=EcomaxNumberDescription("water_heater_work_mode"),
            ),
        )
        await connection.device.dispatch(
            "water_heater_hysteresis",
            EcomaxNumber(
                device=connection.device,
                values=ParameterValues(value=8, min_value=0, max_value=15),
                description=EcomaxNumberDescription("water_heater_hysteresis"),
            ),
        )
        await hass.async_block_till_done()

    mock_write_state.assert_not_called()
    state = hass.states.get("water_heater.ecomax_indirect_water_heater")
    assert isinstance(state, State)
    assert state.state == "unavailable"


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_availability_on_disconnect(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    setup_config_entry,
) -> None:
    """Test water heater availability reflects connection state."""
    connected_event = asyncio.Event()
    connected_event.set()
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.connected",
        connected_event,
        create=True,
    ):
        await setup_config_entry()
        indirect_water_heater_entity_id = "water_heater.ecomax_indirect_water_heater"
        state = hass.states.get(indirect_water_heater_entity_id)
        assert isinstance(state, State)
        assert state.state == STATE_OFF

        connection.connected.clear()
        await connection.device.dispatch(
            "water_heater_work_mode",
            EcomaxNumber(
                device=connection.device,
                values=ParameterValues(value=1, min_value=0, max_value=2),
                description=EcomaxNumberDescription("water_heater_work_mode"),
            ),
        )
        await hass.async_block_till_done()
        state = hass.states.get(indirect_water_heater_entity_id)
        assert isinstance(state, State)
        assert state.state == "unavailable"

        connection.connected.set()
        await connection.device.dispatch(
            "water_heater_work_mode",
            EcomaxNumber(
                device=connection.device,
                values=ParameterValues(value=0, min_value=0, max_value=2),
                description=EcomaxNumberDescription("water_heater_work_mode"),
            ),
        )
        await hass.async_block_till_done()
        state = hass.states.get(indirect_water_heater_entity_id)
        assert isinstance(state, State)
        assert state.state == STATE_OFF


@pytest.mark.usefixtures("ecomax_p")
async def test_water_heater_deferred_registration(
    hass: HomeAssistant,
    ecomax_p: EcoMAX,
    setup_config_entry,
) -> None:
    """Test water heater registers once when first backing key arrives."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_water_heater",
        True,
    ):
        await setup_config_entry()

    indirect_water_heater_entity_id = "water_heater.ecomax_indirect_water_heater"
    entity_registry = er.async_get(hass)
    assert entity_registry.async_get(indirect_water_heater_entity_id) is None

    await ecomax_p.dispatch("water_heater_temp", 48.0)
    await hass.async_block_till_done()

    assert entity_registry.async_get(indirect_water_heater_entity_id) is not None
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 48.0

    # Subsequent sibling key does not raise or double-register.
    await ecomax_p.dispatch(
        "water_heater_work_mode",
        EcomaxNumber(
            device=ecomax_p,
            values=ParameterValues(value=1, min_value=0, max_value=2),
            description=EcomaxNumberDescription("water_heater_work_mode"),
        ),
    )
    await hass.async_block_till_done()
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.state == STATE_PERFORMANCE


@pytest.mark.usefixtures("ecomax_p")
async def test_water_heater_existing_registry_entry_without_data(
    hass: HomeAssistant,
    ecomax_p: EcoMAX,
    config_entry: MockConfigEntry,
    setup_config_entry,
    async_set_operation_mode,
    async_set_temperature,
    caplog,
) -> None:
    """Test existing water heater registers unavailable with no data and guards calls."""
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        WATER_HEATER,
        "plum_ecomax",
        "TEST-water_heater",
        config_entry=config_entry,
        suggested_object_id="ecomax_indirect_water_heater",
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_water_heater",
        True,
    ):
        await setup_config_entry()

    indirect_water_heater_entity_id = "water_heater.ecomax_indirect_water_heater"
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.state == "unavailable"

    await ecomax_p.dispatch("water_heater_temp", 45.0)
    await hass.async_block_till_done()
    state = hass.states.get(indirect_water_heater_entity_id)
    assert isinstance(state, State)
    assert state.state != "unavailable"
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 45.0

    with patch("pyplumio.devices.Device.set_nowait") as mock_set_nowait:
        await async_set_temperature(hass, indirect_water_heater_entity_id, 55)
        await async_set_operation_mode(hass, indirect_water_heater_entity_id, STATE_ECO)

    mock_set_nowait.assert_not_called()
    assert (
        "Cannot set target temperature before water heater parameters are loaded"
        in caplog.text
    )
    assert (
        "Cannot set operation mode before water heater parameters are loaded"
        in caplog.text
    )
