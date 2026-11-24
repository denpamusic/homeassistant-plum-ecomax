"""Test Plum ecoMAX base entity."""

import asyncio
from collections.abc import Callable, Mapping
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import Filter
from pyplumio.helpers.event_manager import EventCallback
from pyplumio.structures.sensor_data import ATTR_HEATING_TEMP
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_ENTITIES,
    ATTR_MIXERS,
    ATTR_REGDATA,
    ATTR_THERMOSTATS,
    DOMAIN,
    ModuleType,
)
from custom_components.plum_ecomax.entity import (
    MANUFACTURER,
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    RegdataEntity,
    ThermostatEntity,
    async_register_entities,
    async_register_sub_device_entities,
)


async def test_base_entity(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test base entity."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.software = {ModuleType.A: "6.10.32.K1"}
    mock_filter = AsyncMock(spec=Filter)
    entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="heating_temp",
            name="Heating temperature",
            always_available=False,
            filter_fn=Mock(return_value=mock_filter),
        ),
    )
    entity.hass = hass
    entity.entity_id = "sensor.test_heating_temp"

    # Test adding entity to hass.
    unsubscribe_spies: list[Mock] = []
    original_subscribe = mock_connection.device.subscribe

    def _capture_subscribe(name: str, callback: Any) -> Any:
        unsubscribe = original_subscribe(name, callback)
        unsubscribe_spy = Mock(wraps=unsubscribe)
        unsubscribe_spies.append(unsubscribe_spy)
        return unsubscribe_spy

    with patch.object(
        mock_connection.device,
        "subscribe",
        side_effect=_capture_subscribe,
    ) as mock_subscribe:
        await entity.async_added_to_hass()

    mock_filter.assert_called_once()
    mock_subscribe.assert_has_calls([call("heating_temp", mock_filter)])
    assert len(unsubscribe_spies) == 1

    # Test removing entity from hass.
    await entity.async_remove()

    unsubscribe_spies[0].assert_called_once_with()
    mock_filter.reset_mock()
    await ecomax_p.dispatch("heating_temp", 45.0)
    mock_filter.assert_not_called()

    # Test device property.
    assert entity.device == mock_connection.device

    # Test device info property.
    assert entity.device_info == DeviceInfo(
        configuration_url="http://localhost",
        identifiers={(DOMAIN, mock_connection.uid)},
        manufacturer=MANUFACTURER,
        model=mock_connection.model,
        name=mock_connection.name,
        serial_number=mock_connection.uid,
        sw_version=mock_connection.software[ModuleType.A],
    )

    # Test unique id property.
    mock_connection.uid = "test_uid"
    assert entity.unique_id == "test_uid-heating_temp"

    # Test should poll property.
    assert not entity.should_poll

    # Test enabled by default property.
    assert entity.entity_registry_enabled_default
    disabled_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="test_data2",
            name="ecoMAX Data 2",
            entity_registry_enabled_default=False,
        ),
    )
    assert not disabled_entity.entity_registry_enabled_default

    # Test exception when calling update on base entity class.
    with pytest.raises(NotImplementedError):
        await entity.async_update("test")

    # Test availability.
    mock_connection.connected = Mock(spec=asyncio.Event)
    mock_connection.connected.is_set.return_value = True
    assert entity.available
    mock_connection.connected.is_set.return_value = False
    assert not entity.available
    entity.entity_description = EcomaxEntityDescription(  # type: ignore[unreachable]
        key="heating_temp",
        name="Heating temperature",
        always_available=True,
        filter_fn=Mock(return_value=mock_filter),
    )
    assert entity.available
    mock_connection.reset_mock()

    # Test availability when source data is not available right away.
    entity2 = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="not_available_right_away",
            name="Not available right away",
            always_available=False,
            filter_fn=Mock(return_value=mock_filter),
        ),
    )
    with patch.object(mock_connection.device, "subscribe_once") as mock_subscribe_once:
        await entity2.async_added_to_hass()

    mock_subscribe_once.assert_called_once()


async def test_async_register_entities_immediate_and_deferred(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test immediate and deferred entity registration."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "TEST-existing_registry_key",
        config_entry=config_entry,
    )

    always_available_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="always_available_missing_key",
            name="Always available",
            always_available=True,
        ),
    )
    ready_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key=ATTR_HEATING_TEMP,
            name="Heating temperature",
        ),
    )
    existing_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="existing_registry_key",
            name="Existing registry entity",
        ),
    )
    deferred_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="deferred_key",
            name="Deferred entity",
        ),
    )
    immediate_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="immediate_custom_key",
            name="Immediate custom entity",
        ),
    )

    mock_add_entities = Mock()
    async_register_entities(
        hass,
        config_entry,
        (
            always_available_entity,
            ready_entity,
            existing_entity,
            deferred_entity,
        ),
        mock_add_entities,
        immediate_entities=(immediate_entity,),
    )

    mock_add_entities.assert_called_once_with(
        [
            immediate_entity,
            always_available_entity,
            ready_entity,
            existing_entity,
        ]
    )

    mock_add_entities.reset_mock()
    await ecomax_p.dispatch("deferred_key", 42)
    await hass.async_block_till_done()
    mock_add_entities.assert_called_once_with([deferred_entity])

    mock_add_entities.reset_mock()
    await ecomax_p.dispatch("deferred_key", 43)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()


async def test_async_register_entities_deferred_unload_cleanup(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test pending deferred registrations are unsubscribed on unload."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    deferred_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="never_arrived_key",
            name="Never arrived",
        ),
    )

    unload_callbacks: list[Callable[[], Any]] = []
    unsubscribe_spies: list[Mock] = []
    original_subscribe_once = ecomax_p.subscribe_once

    def _capture_subscribe_once(name: str, callback: Any) -> Any:
        unsubscribe = original_subscribe_once(name, callback)
        unsubscribe_spy = Mock(wraps=unsubscribe)
        unsubscribe_spies.append(unsubscribe_spy)
        return unsubscribe_spy

    with (
        patch.object(ecomax_p, "subscribe_once", side_effect=_capture_subscribe_once),
        patch.object(
            config_entry,
            "async_on_unload",
            side_effect=unload_callbacks.append,
        ),
    ):
        mock_add_entities = Mock()
        async_register_entities(
            hass,
            config_entry,
            (deferred_entity,),
            mock_add_entities,
        )

    mock_add_entities.assert_not_called()
    assert len(unload_callbacks) == 1
    assert len(unsubscribe_spies) == 1

    unload_callbacks[0]()

    unsubscribe_spies[0].assert_called_once_with()
    await ecomax_p.dispatch("never_arrived_key", 1)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()


@pytest.mark.usefixtures("ecomax_p")
async def test_config_entry_unload_cleans_pending_registrations(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test unloading a config entry cleans up pending entity subscriptions."""
    del connection.device._data[ATTR_HEATING_TEMP]
    with (
        patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"),
        patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True),
    ):
        await setup_config_entry()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get("sensor.ecomax_heating_temperature") is None

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    await connection.device.dispatch(ATTR_HEATING_TEMP, 55.0)
    await hass.async_block_till_done()
    assert entity_registry.async_get("sensor.ecomax_heating_temperature") is None


@pytest.mark.usefixtures("ecomax_p")
async def test_config_entry_unload_ignores_dispatches_during_close(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test dispatches during connection.close() do not add zombie entities."""
    connection.device._data.pop(ATTR_HEATING_TEMP, None)
    connection.device._data.pop(ATTR_MIXERS, None)
    with (
        patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"),
        patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True),
    ):
        await setup_config_entry()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get("sensor.ecomax_heating_temperature") is None
    assert hass.states.get("sensor.ecomax_heating_temperature") is None

    mixer_0 = Mixer(
        write_queue=Mock(spec=asyncio.Queue), parent=connection.device, index=0
    )
    await mixer_0.load({"current_temp": 35.0, "pump": True})

    runtime_connection = config_entry.runtime_data.connection
    original_close = runtime_connection.close
    close_states: list[ConfigEntryState] = []

    async def _close_with_dispatches() -> None:
        close_states.append(config_entry.state)
        assert config_entry.state is ConfigEntryState.UNLOAD_IN_PROGRESS
        await connection.device.dispatch(ATTR_HEATING_TEMP, 55.0)
        await connection.device.dispatch(ATTR_MIXERS, {0: mixer_0})
        await connection.device.wait_until_done()
        await original_close()

    with patch.object(
        runtime_connection,
        "close",
        side_effect=_close_with_dispatches,
        create=True,
    ):
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert close_states == [ConfigEntryState.UNLOAD_IN_PROGRESS]
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get("sensor.ecomax_heating_temperature") is None
    assert entity_registry.async_get("sensor.ecomax_heating_temperature") is None
    assert not any(
        "mixer-0" in registry_entry.unique_id
        for registry_entry in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
    )
    assert hass.states.get("sensor.ecomax_mixer_1_mixer_temperature") is None
    assert hass.states.get("binary_sensor.ecomax_mixer_1_mixer_pump") is None


async def test_entity_registration_respects_config_entry_state(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test deferred and sub-device registration only run for active states."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    class _TestMixerEntity(MixerEntity):
        def __init__(
            self,
            connection: EcomaxConnection,
            description: EcomaxEntityDescription,
            index: int,
        ) -> None:
            self.index = index
            super().__init__(connection, description)

    deferred_active = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="setup_in_progress_key",
            name="Setup in progress key",
        ),
    )
    deferred_inactive = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="unload_in_progress_key",
            name="Unload in progress key",
        ),
    )

    config_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    mock_add_entities = Mock()
    async_register_entities(
        hass,
        config_entry,
        (deferred_active, deferred_inactive),
        mock_add_entities,
    )

    mixer_0 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=0)
    await mixer_0.load({"pump": True})
    mixer_1 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=1)
    await mixer_1.load({"pump": True})

    mixer_add_entities = Mock()
    async_register_sub_device_entities(
        hass,
        config_entry,
        mock_connection,
        ATTR_MIXERS,
        mixer_add_entities,
        entities_fn=lambda: [
            _TestMixerEntity(
                mock_connection,
                EcomaxEntityDescription(key="pump", name=f"Mixer {index} pump"),
                index,
            )
            for index in ecomax_p.mixers
        ],
    )

    # SETUP_IN_PROGRESS allows deferred entity and sub-device registration.
    await ecomax_p.dispatch("setup_in_progress_key", 1)
    await ecomax_p.dispatch(ATTR_MIXERS, {0: mixer_0})
    await hass.async_block_till_done()
    mock_add_entities.assert_called_once_with([deferred_active])
    assert mixer_add_entities.call_count == 1
    assert [entity.index for entity in mixer_add_entities.call_args[0][0]] == [0]

    # UNLOAD_IN_PROGRESS blocks deferred entity and sub-device registration.
    mock_add_entities.reset_mock()
    mixer_add_entities.reset_mock()
    config_entry.mock_state(hass, ConfigEntryState.UNLOAD_IN_PROGRESS)
    await ecomax_p.dispatch("unload_in_progress_key", 2)
    ecomax_p.mixers[1] = mixer_1
    await ecomax_p.dispatch(ATTR_MIXERS, ecomax_p.mixers)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()
    mixer_add_entities.assert_not_called()


async def test_entity_unsubscribes_startup_callback_on_remove(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test EcomaxEntity and RegdataEntity unsubscribe all callbacks on remove."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.connected = Mock(spec=asyncio.Event)
    mock_connection.connected.is_set.return_value = True

    entity_filter = AsyncMock(spec=Filter)
    entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="missing_sensor",
            name="Missing",
            filter_fn=Mock(return_value=entity_filter),
        ),
    )
    entity.hass = hass
    entity.entity_id = "sensor.test_missing_sensor"

    startup_unsubscribes: list[Mock] = []
    update_unsubscribes: list[Mock] = []
    original_subscribe_once = ecomax_p.subscribe_once
    original_subscribe = ecomax_p.subscribe

    def _capture_subscribe_once(name: str, callback: Any) -> Any:
        unsubscribe = original_subscribe_once(name, callback)
        unsubscribe_spy = Mock(wraps=unsubscribe)
        startup_unsubscribes.append(unsubscribe_spy)
        return unsubscribe_spy

    def _capture_subscribe(name: str, callback: Any) -> Any:
        unsubscribe = original_subscribe(name, callback)
        if callback.__name__ == "_call_once":
            return unsubscribe

        unsubscribe_spy = Mock(wraps=unsubscribe)
        update_unsubscribes.append(unsubscribe_spy)
        return unsubscribe_spy

    with (
        patch.object(ecomax_p, "subscribe_once", side_effect=_capture_subscribe_once),
        patch.object(ecomax_p, "subscribe", side_effect=_capture_subscribe),
    ):
        await entity.async_added_to_hass()

    assert len(startup_unsubscribes) == 1
    assert len(update_unsubscribes) == 1

    await entity.async_remove()

    startup_unsubscribes[0].assert_called_once_with()
    update_unsubscribes[0].assert_called_once_with()
    await ecomax_p.dispatch("missing_sensor", 123)
    assert not entity.available
    entity_filter.assert_not_called()

    regdata_filter = AsyncMock(spec=Filter)
    regdata_entity = RegdataEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="9001",
            name="Regdata 9001",
            filter_fn=Mock(return_value=regdata_filter),
        ),
    )
    regdata_entity.hass = hass
    regdata_entity.entity_id = "sensor.test_regdata_9001"

    with (
        patch.object(ecomax_p, "subscribe_once", side_effect=_capture_subscribe_once),
        patch.object(
            ecomax_p, "subscribe", side_effect=_capture_subscribe
        ) as mock_subscribe,
    ):
        await regdata_entity.async_added_to_hass()

    mock_subscribe.assert_has_calls(
        [
            call(ATTR_REGDATA, regdata_entity._async_set_available),
            call(ATTR_REGDATA, regdata_filter),
        ]
    )
    assert len(startup_unsubscribes) == 1
    assert len(update_unsubscribes) == 3

    await regdata_entity.async_remove()

    update_unsubscribes[1].assert_called_once_with()
    update_unsubscribes[2].assert_called_once_with()
    await ecomax_p.dispatch(ATTR_REGDATA, {9001: 42})
    assert not regdata_entity.available
    regdata_filter.assert_not_called()

    # Non-dict regdata payload marks entity unavailable.
    non_dict_entity = RegdataEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(key="9001", name="Regdata 9001"),
    )
    non_dict_entity._attr_available = True
    await non_dict_entity._async_set_available(None)
    assert not non_dict_entity.available


@pytest.mark.usefixtures("ecomax_p")
async def test_config_entry_unload_after_startup_callbacks_fire(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test unloading cleans up EcomaxEntity and RegdataEntity subscriptions."""
    del connection.device._data[ATTR_HEATING_TEMP]
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        "TEST-heating_temp",
        config_entry=config_entry,
        suggested_object_id="ecomax_heating_temperature",
    )

    startup_unsubscribes: dict[str, list[Mock]] = {}
    update_unsubscribes: dict[str, list[Mock]] = {}
    original_subscribe_once = connection.device.subscribe_once
    original_subscribe = connection.device.subscribe

    def _capture_subscribe_once(name: str, callback: Any) -> Any:
        unsubscribe = original_subscribe_once(name, callback)
        unsubscribe_spy = Mock(wraps=unsubscribe)
        startup_unsubscribes.setdefault(name, []).append(unsubscribe_spy)
        return unsubscribe_spy

    def _capture_subscribe(name: str, callback: Any) -> Any:
        unsubscribe = original_subscribe(name, callback)
        if callback.__name__ == "_call_once":
            return unsubscribe

        unsubscribe_spy = Mock(wraps=unsubscribe)
        update_unsubscribes.setdefault(name, []).append(unsubscribe_spy)
        return unsubscribe_spy

    with (
        patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"),
        patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True),
        patch.object(
            connection.device, "subscribe_once", side_effect=_capture_subscribe_once
        ),
        patch.object(connection.device, "subscribe", side_effect=_capture_subscribe),
    ):
        await setup_config_entry(
            {
                ATTR_ENTITIES: {
                    Platform.SENSOR: {
                        "9001": {
                            "name": "Regdata 9001",
                            "key": "9001",
                            "source_device": ATTR_REGDATA,
                        }
                    }
                }
            }
        )

    heating_entity_id = "sensor.ecomax_heating_temperature"
    regdata_entity_id = "sensor.ecomax_regdata_9001"
    assert isinstance(state := hass.states.get(heating_entity_id), State)
    assert state.state == "unavailable"
    assert isinstance(state := hass.states.get(regdata_entity_id), State)
    assert state.state == "unavailable"

    # Dispatch values so startup availability and update callbacks run.
    await connection.device.dispatch(ATTR_HEATING_TEMP, 55.0)
    await connection.device.dispatch(ATTR_REGDATA, {9001: 42.0})
    await hass.async_block_till_done()

    assert isinstance(state := hass.states.get(heating_entity_id), State)
    assert state.state == "55.0"
    assert isinstance(state := hass.states.get(regdata_entity_id), State)
    assert state.state == "42.0"

    assert len(startup_unsubscribes[ATTR_HEATING_TEMP]) == 1
    assert len(update_unsubscribes[ATTR_HEATING_TEMP]) == 1
    assert ATTR_REGDATA not in startup_unsubscribes
    assert len(update_unsubscribes[ATTR_REGDATA]) == 2

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    startup_unsubscribes[ATTR_HEATING_TEMP][0].assert_called_once_with()
    update_unsubscribes[ATTR_HEATING_TEMP][0].assert_called_once_with()
    update_unsubscribes[ATTR_REGDATA][0].assert_called_once_with()
    update_unsubscribes[ATTR_REGDATA][1].assert_called_once_with()

    await connection.device.dispatch(ATTR_HEATING_TEMP, 60.0)
    await connection.device.dispatch(ATTR_REGDATA, {9001: 99.0})
    await hass.async_block_till_done()
    assert isinstance(state := hass.states.get(heating_entity_id), State)
    assert state.state == "unavailable"
    assert isinstance(state := hass.states.get(regdata_entity_id), State)
    assert state.state == "unavailable"


@pytest.mark.usefixtures("ecomax_p")
async def test_regdata_entity_availability_tracks_key_presence(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test RegdataEntity availability tracks key presence when regdata exists."""
    connection.device._data[ATTR_REGDATA] = {1: 11}
    with (
        patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"),
        patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True),
    ):
        await setup_config_entry(
            {
                ATTR_ENTITIES: {
                    Platform.SENSOR: {
                        "9001": {
                            "name": "Regdata 9001",
                            "key": "9001",
                            "source_device": ATTR_REGDATA,
                        }
                    },
                    Platform.BINARY_SENSOR: {
                        "9000": {
                            "name": "Regdata 9000",
                            "key": "9000",
                            "source_device": ATTR_REGDATA,
                        }
                    },
                }
            }
        )

    regdata_sensor_id = "sensor.ecomax_regdata_9001"
    regdata_binary_id = "binary_sensor.ecomax_regdata_9000"
    assert isinstance(state := hass.states.get(regdata_sensor_id), State)
    assert state.state == "unavailable"
    assert isinstance(state := hass.states.get(regdata_binary_id), State)
    assert state.state == "unavailable"

    await connection.device.dispatch(ATTR_REGDATA, {1: 11, 9001: 42.0, 9000: True})
    await hass.async_block_till_done()
    assert isinstance(state := hass.states.get(regdata_sensor_id), State)
    assert state.state == "42.0"
    assert isinstance(state := hass.states.get(regdata_binary_id), State)
    assert state.state == "on"

    await connection.device.dispatch(ATTR_REGDATA, {1: 11})
    await hass.async_block_till_done()
    assert isinstance(state := hass.states.get(regdata_sensor_id), State)
    assert state.state == "unavailable"
    assert isinstance(state := hass.states.get(regdata_binary_id), State)
    assert state.state == "unavailable"

    await connection.device.dispatch(ATTR_REGDATA, {1: 11, 9001: 42.0, 9000: False})
    await hass.async_block_till_done()
    assert isinstance(state := hass.states.get(regdata_sensor_id), State)
    assert state.state == "42.0"
    assert isinstance(state := hass.states.get(regdata_binary_id), State)
    assert state.state == "off"


async def test_async_register_entities_domain_scoped_registry_lookup(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test registry lookup scopes by current platform domain."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "TEST-cross_domain_key",
        config_entry=config_entry,
    )
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "TEST-same_domain_key",
        config_entry=config_entry,
    )

    cross_domain_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="cross_domain_key",
            name="Cross domain",
        ),
    )
    same_domain_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="same_domain_key",
            name="Same domain",
        ),
    )

    mock_add_entities = Mock()
    with patch.object(
        entity_platform,
        "async_get_current_platform",
        return_value=Mock(domain="sensor"),
    ):
        async_register_entities(
            hass,
            config_entry,
            (cross_domain_entity, same_domain_entity),
            mock_add_entities,
        )

    mock_add_entities.assert_called_once_with([same_domain_entity])

    mock_add_entities.reset_mock()
    await ecomax_p.dispatch("cross_domain_key", 1)
    await hass.async_block_till_done()
    mock_add_entities.assert_called_once_with([cross_domain_entity])


async def test_async_register_entities_stores_key_before_deferred_add(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test PyPlumIO stores dispatched key in device.data before deferred add runs."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    deferred_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="deferred_store_key",
            name="Deferred store key",
        ),
    )

    saw_key_in_data: list[bool] = []

    def _record_add(entities: list[EcomaxEntity]) -> None:
        saw_key_in_data.append("deferred_store_key" in ecomax_p.data)

    mock_add_entities = Mock(side_effect=_record_add)
    async_register_entities(
        hass,
        config_entry,
        (deferred_entity,),
        mock_add_entities,
    )

    await ecomax_p.dispatch("deferred_store_key", 99)
    await hass.async_block_till_done()

    mock_add_entities.assert_called_once_with([deferred_entity])
    assert saw_key_in_data == [True]


async def test_async_register_sub_device_entities(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test reactive sub-device registration, deduplication, and unload cleanup."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    class _TestMixerEntity(MixerEntity):
        def __init__(
            self,
            connection: EcomaxConnection,
            description: EcomaxEntityDescription,
            index: int,
        ) -> None:
            self.index = index
            super().__init__(connection, description)

    class _TestThermostatEntity(ThermostatEntity):
        def __init__(
            self,
            connection: EcomaxConnection,
            description: EcomaxEntityDescription,
            index: int,
        ) -> None:
            self.index = index
            super().__init__(connection, description)

    mixer_0 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=0)
    await mixer_0.load({"pump": True})
    mixer_1 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=1)
    await mixer_1.load({"pump": False})
    mixer_2 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=2)
    await mixer_2.load({"pump": True})
    await ecomax_p.load({ATTR_MIXERS: {0: mixer_0}})

    def _build_mixers() -> list[MixerEntity]:
        return [
            _TestMixerEntity(
                mock_connection,
                EcomaxEntityDescription(key="pump", name=f"Mixer {index} pump"),
                index,
            )
            for index in ecomax_p.mixers
        ]

    unload_callbacks: list[Callable[[], Any]] = []
    mock_add_entities = Mock()
    with patch.object(
        config_entry, "async_on_unload", side_effect=unload_callbacks.append
    ):
        async_register_sub_device_entities(
            hass,
            config_entry,
            mock_connection,
            ATTR_MIXERS,
            mock_add_entities,
            entities_fn=_build_mixers,
        )

    # Initial mixer 0 registered immediately.
    assert mock_add_entities.call_count == 1
    added_initial = mock_add_entities.call_args[0][0]
    assert [entity.index for entity in added_initial] == [0]

    # Duplicate dispatch for already-seen index 0 does nothing.
    mock_add_entities.reset_mock()
    await ecomax_p.dispatch(ATTR_MIXERS, {0: mixer_0})
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()

    # Dispatching new index 1 registers only index 1.
    ecomax_p.mixers[1] = mixer_1
    await ecomax_p.dispatch(ATTR_MIXERS, ecomax_p.mixers)
    await hass.async_block_till_done()
    assert mock_add_entities.call_count == 1
    added_dynamic = mock_add_entities.call_args[0][0]
    assert [entity.index for entity in added_dynamic] == [1]

    # Unloading unsubscribes so index 2 is ignored.
    mock_add_entities.reset_mock()
    unload_callbacks[0]()
    ecomax_p.mixers[2] = mixer_2
    await ecomax_p.dispatch(ATTR_MIXERS, ecomax_p.mixers)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()

    # Also test deferred sub-device key when absent at setup, confirming
    # ATTR_THERMOSTATS is already stored in ecomax_p.data inside add_entities.
    thermostat_0 = Thermostat(
        write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=0
    )
    await thermostat_0.load({"current_temp": 21.0})

    saw_thermostats_in_data: list[bool] = []
    thermostat_indexes: list[int] = []

    def _record_thermostat_add(entities: list[ThermostatEntity]) -> None:
        saw_thermostats_in_data.append(ATTR_THERMOSTATS in ecomax_p.data)
        thermostat_indexes.extend(entity.index for entity in entities)

    thermostat_add_entities = Mock(side_effect=_record_thermostat_add)
    async_register_sub_device_entities(
        hass,
        config_entry,
        mock_connection,
        ATTR_THERMOSTATS,
        thermostat_add_entities,
        custom_entities_fn=lambda: [
            _TestThermostatEntity(
                mock_connection,
                EcomaxEntityDescription(key="custom_temp", name="Custom temp"),
                index,
            )
            for index in ecomax_p.thermostats
        ],
    )
    thermostat_add_entities.assert_not_called()

    await ecomax_p.dispatch(ATTR_THERMOSTATS, {0: thermostat_0})
    await hass.async_block_till_done()

    assert thermostat_add_entities.call_count == 1
    assert thermostat_indexes == [0]
    assert saw_thermostats_in_data == [True]

    # Empty custom entities when new sub-device index arrives skips registration.
    empty_add_entities = Mock()
    async_register_sub_device_entities(
        hass,
        config_entry,
        mock_connection,
        ATTR_THERMOSTATS,
        empty_add_entities,
        custom_entities_fn=list,
    )
    empty_add_entities.assert_not_called()

    # Empty sub-device dispatch is ignored.
    await ecomax_p.dispatch(ATTR_THERMOSTATS, {})
    await hass.async_block_till_done()
    empty_add_entities.assert_not_called()


async def test_async_register_sub_device_entities_preserves_domain_scope(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test platform_domain captured at setup is preserved on dynamic discovery."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    class _TestMixerEntity(MixerEntity):
        def __init__(
            self,
            connection: EcomaxConnection,
            description: EcomaxEntityDescription,
            index: int,
        ) -> None:
            self.index = index
            super().__init__(connection, description)

    mixer_0 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=0)
    await mixer_0.load({"pump": True})
    mixer_1 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=1)
    await mixer_1.load({"pump": False})
    await ecomax_p.load({ATTR_MIXERS: {0: mixer_0}})

    entity_registry = er.async_get(hass)
    # Cross-domain entry on binary_sensor must not mark a deferred sensor
    # sub-device entity as ready outside platform context.
    entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "TEST-mixer-1-deferred_key",
        config_entry=config_entry,
    )

    built_in_seen: list[list[str]] = []
    custom_devices: list[Mixer] = []

    def _record_add(entities: list[_TestMixerEntity]) -> None:
        built_in_seen.append(
            [f"{entity.index}:{entity.entity_description.key}" for entity in entities]
        )
        for entity in entities:
            if entity.entity_description.key == "custom_pump":
                custom_devices.append(entity.device)

    mock_add_entities = Mock(side_effect=_record_add)
    with patch.object(
        entity_platform,
        "async_get_current_platform",
        return_value=Mock(domain="sensor"),
    ):
        async_register_sub_device_entities(
            hass,
            config_entry,
            mock_connection,
            ATTR_MIXERS,
            mock_add_entities,
            entities_fn=lambda: [
                entity
                for index in ecomax_p.mixers
                for entity in (
                    _TestMixerEntity(
                        mock_connection,
                        EcomaxEntityDescription(key="pump", name=f"Mixer {index} pump"),
                        index,
                    ),
                    _TestMixerEntity(
                        mock_connection,
                        EcomaxEntityDescription(
                            key="deferred_key", name=f"Mixer {index} deferred"
                        ),
                        index,
                    ),
                )
            ],
            custom_entities_fn=lambda: [
                _TestMixerEntity(
                    mock_connection,
                    EcomaxEntityDescription(
                        key="custom_pump", name=f"Mixer {index} custom"
                    ),
                    index,
                )
                for index in ecomax_p.mixers
            ],
        )

    assert built_in_seen == [["0:custom_pump", "0:pump"]]
    built_in_seen.clear()
    custom_devices.clear()

    # Mutate in-place like PyPlumIO and dispatch outside any current_platform context.
    ecomax_p.mixers[1] = mixer_1
    await ecomax_p.dispatch(ATTR_MIXERS, ecomax_p.mixers)
    await hass.async_block_till_done()

    assert built_in_seen == [["1:custom_pump", "1:pump"]]
    assert custom_devices == [mixer_1]

    # Deferred key on mixer_1 arrives later and is registered then.
    await mixer_1.dispatch("deferred_key", 123)
    await hass.async_block_till_done()
    assert built_in_seen == [["1:custom_pump", "1:pump"], ["1:deferred_key"]]


async def test_entity_always_available_skips_availability_subscription(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test always_available=True skips subscribe_once availability tracking."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.connected = Mock(spec=asyncio.Event)
    mock_connection.connected.is_set.return_value = False

    entity_filter = AsyncMock(spec=Filter)
    entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="missing_always_available_key",
            name="Always available",
            always_available=True,
            filter_fn=Mock(return_value=entity_filter),
        ),
    )
    entity.hass = hass
    entity.entity_id = "sensor.test_always_available"

    with (
        patch.object(ecomax_p, "subscribe_once") as mock_subscribe_once,
        patch.object(ecomax_p, "subscribe", wraps=ecomax_p.subscribe) as mock_subscribe,
    ):
        await entity.async_added_to_hass()

    mock_subscribe_once.assert_not_called()
    mock_subscribe.assert_called_once_with(
        "missing_always_available_key", entity_filter
    )
    assert entity.available

    await entity.async_remove()


async def test_multi_key_entity_availability_order(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test multi-key entity availability with partial or missing keys."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.connected = Mock(spec=asyncio.Event)
    mock_connection.connected.is_set.return_value = True

    class _MultiKeyEntity(EcomaxEntity):
        """Test entity backed by multiple event keys."""

        def __init__(
            self,
            connection: EcomaxConnection,
            description: EcomaxEntityDescription,
            callbacks: Mapping[str, EventCallback],
        ) -> None:
            super().__init__(connection, description)
            self._callbacks = callbacks

        def _get_callbacks(self) -> Mapping[str, EventCallback]:
            return self._callbacks

    # Case 1: missing_first precedes present_second in callback dict.
    await ecomax_p.load({"present_second": 42})
    first_cb = AsyncMock()
    second_cb = AsyncMock()
    partial_entity = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_partial",
            name="Synthetic partial",
            always_available=False,
        ),
        callbacks={
            "missing_first": first_cb,
            "present_second": second_cb,
        },
    )
    partial_entity.hass = hass
    partial_entity.entity_id = "sensor.test_partial"

    with (
        patch.object(ecomax_p, "subscribe_once") as mock_subscribe_once,
        patch.object(ecomax_p, "subscribe", wraps=ecomax_p.subscribe) as mock_subscribe,
    ):
        await partial_entity.async_added_to_hass()

    assert partial_entity.available
    mock_subscribe_once.assert_not_called()
    first_cb.assert_not_called()
    second_cb.assert_awaited_once_with(42)
    mock_subscribe.assert_has_calls(
        [
            call("missing_first", first_cb),
            call("present_second", second_cb),
        ]
    )
    await partial_entity.async_remove()

    # Case 2: zero keys present starts unavailable, subscribes availability before updates.
    cb_a = AsyncMock()
    cb_b = AsyncMock()
    missing_entity = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_missing",
            name="Synthetic missing",
            always_available=False,
        ),
        callbacks={
            "missing_key_a": cb_a,
            "missing_key_b": cb_b,
        },
    )
    missing_entity.hass = hass
    missing_entity.entity_id = "sensor.test_missing"

    call_order: list[tuple[str, str]] = []
    original_subscribe_once = ecomax_p.subscribe_once
    original_subscribe = ecomax_p.subscribe

    def _record_subscribe_once(name: str, cb: EventCallback) -> Any:
        call_order.append(("subscribe_once", name))
        return original_subscribe_once(name, cb)

    def _record_subscribe(name: str, cb: EventCallback) -> Any:
        if cb.__name__ != "_call_once":
            call_order.append(("subscribe", name))
        return original_subscribe(name, cb)

    with (
        patch.object(ecomax_p, "subscribe_once", side_effect=_record_subscribe_once),
        patch.object(ecomax_p, "subscribe", side_effect=_record_subscribe),
    ):
        await missing_entity.async_added_to_hass()

    assert not bool(missing_entity.available)
    assert call_order == [
        ("subscribe_once", "missing_key_a"),
        ("subscribe_once", "missing_key_b"),
        ("subscribe", "missing_key_a"),
        ("subscribe", "missing_key_b"),
    ]

    # When first key arrives, entity becomes available before update callback runs.
    saw_available_in_cb: list[bool] = []
    cb_a.side_effect = lambda _val: saw_available_in_cb.append(missing_entity.available)
    await ecomax_p.dispatch("missing_key_a", 99)
    assert missing_entity.available
    assert saw_available_in_cb == [True]
    cb_a.assert_awaited_once_with(99)

    await missing_entity.async_remove()


async def test_multi_key_entity_deferred_registration_and_cancellation(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test multi-key deferred registration, sibling cancellation, and unload."""
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    class _MultiKeyEntity(EcomaxEntity):
        """Test entity backed by multiple event keys."""

        def __init__(
            self,
            connection: EcomaxConnection,
            description: EcomaxEntityDescription,
            keys: tuple[str, ...],
        ) -> None:
            super().__init__(connection, description)
            self._keys = keys

        def _get_callbacks(self) -> Mapping[str, EventCallback]:
            return dict.fromkeys(self._keys, self.async_update)

    # Immediate registration when a backing key (not matching synthetic key) is present.
    await ecomax_p.load({"ready_backing_key": 1})
    ready_multi = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_ready",
            name="Synthetic ready",
        ),
        keys=("missing_backing_key", "ready_backing_key"),
    )
    deferred_multi = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_deferred",
            name="Synthetic deferred",
        ),
        keys=("multi_key_a", "multi_key_b"),
    )

    unload_callbacks: list[Callable[[], Any]] = []
    unsubscribe_spies: dict[str, Mock] = {}
    original_subscribe_once = ecomax_p.subscribe_once

    def _capture_subscribe_once(name: str, cb: EventCallback) -> Any:
        unsubscribe = original_subscribe_once(name, cb)
        unsubscribe_spy = Mock(wraps=unsubscribe)
        unsubscribe_spies[name] = unsubscribe_spy
        return unsubscribe_spy

    mock_add_entities = Mock()
    with (
        patch.object(ecomax_p, "subscribe_once", side_effect=_capture_subscribe_once),
        patch.object(
            config_entry,
            "async_on_unload",
            side_effect=unload_callbacks.append,
        ),
    ):
        async_register_entities(
            hass,
            config_entry,
            (ready_multi, deferred_multi),
            mock_add_entities,
        )

    mock_add_entities.assert_called_once_with([ready_multi])
    assert set(unsubscribe_spies) == {"multi_key_a", "multi_key_b"}
    assert len(unload_callbacks) == 1

    # First key arrival registers once and cancels sibling subscription.
    mock_add_entities.reset_mock()
    await ecomax_p.dispatch("multi_key_a", 10)
    await hass.async_block_till_done()
    mock_add_entities.assert_called_once_with([deferred_multi])
    unsubscribe_spies["multi_key_a"].assert_called_once_with()
    unsubscribe_spies["multi_key_b"].assert_called_once_with()

    # Second key arrival does not double-register.
    mock_add_entities.reset_mock()
    await ecomax_p.dispatch("multi_key_b", 20)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()

    # Calling unload callback afterwards is idempotent.
    unload_callbacks[0]()
    unsubscribe_spies["multi_key_a"].assert_called_once_with()
    unsubscribe_spies["multi_key_b"].assert_called_once_with()

    # Unloading before any key arrives cleans up all pending subscriptions.
    never_entity = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_never",
            name="Synthetic never",
        ),
        keys=("never_key_1", "never_key_2"),
    )
    unload_callbacks.clear()
    unsubscribe_spies.clear()
    mock_add_entities.reset_mock()

    with (
        patch.object(ecomax_p, "subscribe_once", side_effect=_capture_subscribe_once),
        patch.object(
            config_entry,
            "async_on_unload",
            side_effect=unload_callbacks.append,
        ),
    ):
        async_register_entities(
            hass,
            config_entry,
            (never_entity,),
            mock_add_entities,
        )

    mock_add_entities.assert_not_called()
    assert set(unsubscribe_spies) == {"never_key_1", "never_key_2"}
    assert len(unload_callbacks) == 1

    unload_callbacks[0]()
    unsubscribe_spies["never_key_1"].assert_called_once_with()
    unsubscribe_spies["never_key_2"].assert_called_once_with()

    await ecomax_p.dispatch("never_key_1", 1)
    await ecomax_p.dispatch("never_key_2", 2)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()

    # Concurrent load of multiple backing keys registers at most once.
    concurrent_plain = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_concurrent_plain",
            name="Synthetic concurrent plain",
        ),
        keys=("concurrent_plain_a", "concurrent_plain_b"),
    )
    mock_add_entities.reset_mock()
    async_register_entities(
        hass,
        config_entry,
        (concurrent_plain,),
        mock_add_entities,
    )
    await ecomax_p.load({"concurrent_plain_a": 1, "concurrent_plain_b": 2})
    await hass.async_block_till_done()
    mock_add_entities.assert_called_once_with([concurrent_plain])

    # Concurrent load of multiple backing keys registers at most once,
    # even when an earlier async subscriber yields before sibling cancellation.
    concurrent_entity = _MultiKeyEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="synthetic_concurrent",
            name="Synthetic concurrent",
        ),
        keys=("concurrent_key_a", "concurrent_key_b"),
    )
    mock_add_entities.reset_mock()

    async def _yielding_subscriber(_value: Any) -> None:
        await asyncio.sleep(0)

    unsub_yielding = ecomax_p.subscribe("concurrent_key_b", _yielding_subscriber)
    async_register_entities(
        hass,
        config_entry,
        (concurrent_entity,),
        mock_add_entities,
    )
    await ecomax_p.load({"concurrent_key_b": 2, "concurrent_key_a": 1})
    await hass.async_block_till_done()
    unsub_yielding()
    mock_add_entities.assert_called_once_with([concurrent_entity])
