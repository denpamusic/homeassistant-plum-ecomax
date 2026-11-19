"""Test Plum ecoMAX base entity."""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import Filter
from pyplumio.structures.sensor_data import ATTR_HEATING_TEMP
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
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


async def test_base_entity(ecomax_p: EcoMAX, config_entry: MockConfigEntry) -> None:
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

    # Test adding entity to hass.
    with patch.object(
        mock_connection.device, "subscribe", create=True
    ) as mock_subscribe:
        await entity.async_added_to_hass()

    mock_filter.assert_called_once()
    mock_subscribe.assert_has_calls([call("heating_temp", mock_filter)])

    # Test removing entity from the hass.
    with (
        patch.object(EcomaxEntity, "async_update") as mock_async_update,
        patch.object(mock_connection.device, "unsubscribe") as mock_unsubscribe,
    ):
        await entity.async_will_remove_from_hass()

    mock_unsubscribe.assert_called_once_with("heating_temp", mock_async_update)

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
    with patch.object(
        config_entry,
        "async_on_unload",
        side_effect=unload_callbacks.append,
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

    with patch.object(
        ecomax_p, "unsubscribe", wraps=ecomax_p.unsubscribe
    ) as mock_unsub:
        unload_callbacks[0]()

    mock_unsub.assert_called_once()
    await ecomax_p.dispatch("never_arrived_key", 1)
    await hass.async_block_till_done()
    mock_add_entities.assert_not_called()


@pytest.mark.usefixtures("ecomax_p")
async def test_async_register_entities_cancels_background_task_on_unload(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test scheduled deferred add background task is cancelled on unload."""
    del connection.device._data[ATTR_HEATING_TEMP]
    with (
        patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"),
        patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True),
    ):
        await setup_config_entry()

    await connection.device.dispatch(ATTR_HEATING_TEMP, 55.0)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get("sensor.ecomax_heating_temperature") is None


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


async def test_entity_unsubscribes_startup_callback_on_remove(
    ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test EcomaxEntity and RegdataEntity unsubscribe startup callbacks on remove."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.connected = Mock(spec=asyncio.Event)
    mock_connection.connected.is_set.return_value = True

    entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(key="missing_sensor", name="Missing"),
    )
    await entity.async_added_to_hass()
    startup_callback = entity._startup_callback
    assert startup_callback is not None

    with patch.object(
        ecomax_p, "unsubscribe", wraps=ecomax_p.unsubscribe
    ) as mock_unsubscribe:
        await entity.async_will_remove_from_hass()

    assert entity._startup_callback is None
    mock_unsubscribe.assert_any_call("missing_sensor", startup_callback)
    await ecomax_p.dispatch("missing_sensor", 123)
    assert not entity.available

    regdata_entity = RegdataEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(key="9001", name="Regdata 9001"),
    )
    await regdata_entity.async_added_to_hass()
    regdata_startup_callback = regdata_entity._startup_callback
    assert regdata_startup_callback is not None

    with patch.object(
        ecomax_p, "unsubscribe", wraps=ecomax_p.unsubscribe
    ) as mock_unsubscribe:
        await regdata_entity.async_will_remove_from_hass()

    assert regdata_entity._startup_callback is None
    mock_unsubscribe.assert_any_call(ATTR_REGDATA, regdata_startup_callback)
    await ecomax_p.dispatch(ATTR_REGDATA, {9001: 42})
    assert not regdata_entity.available


async def test_async_register_entities_domain_scoped_registry_lookup(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test registry lookup scopes by current platform domain."""
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


async def test_async_register_entities_waits_for_store_when_subscriber_yields(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test deferred registration awaits wait_for(key) if another subscriber yields."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    deferred_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="yielding_key",
            name="Yielding key",
        ),
    )

    saw_key_in_data: list[bool] = []

    def _record_add(entities: list[EcomaxEntity]) -> None:
        saw_key_in_data.append("yielding_key" in ecomax_p.data)

    mock_add_entities = Mock(side_effect=_record_add)
    async_register_entities(
        hass,
        config_entry,
        (deferred_entity,),
        mock_add_entities,
    )

    subscriber_started = asyncio.Event()
    release_subscriber = asyncio.Event()

    async def _yielding_subscriber(_value: Any) -> None:
        subscriber_started.set()
        await release_subscriber.wait()

    ecomax_p.subscribe("yielding_key", _yielding_subscriber)

    with patch.object(ecomax_p, "wait_for", wraps=ecomax_p.wait_for) as mock_wait_for:
        dispatch_task = hass.async_create_background_task(
            ecomax_p.dispatch("yielding_key", 99),
            name="test_yielding_dispatch",
        )
        await subscriber_started.wait()
        await hass.async_block_till_done()
        mock_add_entities.assert_not_called()

        release_subscriber.set()
        await dispatch_task
        await hass.async_block_till_done(wait_background_tasks=True)

    mock_wait_for.assert_awaited_once_with("yielding_key")
    mock_add_entities.assert_called_once_with([deferred_entity])
    assert saw_key_in_data == [True]


async def test_async_register_sub_device_entities(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test reactive sub-device registration, deduplication, and unload cleanup."""
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

    # Also test deferred sub-device key when absent at setup and yielding subscriber
    # holds EventManager.dispatch() open until wait_for completes, plus empty entities.
    thermostat_0 = Thermostat(
        write_queue=Mock(spec=asyncio.Queue), parent=ecomax_p, index=0
    )
    await thermostat_0.load({"current_temp": 21.0})

    thermostat_add_entities = Mock()
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

    thermostat_subscriber_started = asyncio.Event()
    release_thermostat_subscriber = asyncio.Event()

    async def _yielding_thermostat_subscriber(_value: Any) -> None:
        thermostat_subscriber_started.set()
        await release_thermostat_subscriber.wait()

    ecomax_p.subscribe(ATTR_THERMOSTATS, _yielding_thermostat_subscriber)

    with patch.object(ecomax_p, "wait_for", wraps=ecomax_p.wait_for) as mock_wait_for:
        dispatch_task = hass.async_create_background_task(
            ecomax_p.dispatch(ATTR_THERMOSTATS, {0: thermostat_0}),
            name="test_thermostat_dispatch",
        )
        await thermostat_subscriber_started.wait()
        await hass.async_block_till_done()
        thermostat_add_entities.assert_not_called()

        release_thermostat_subscriber.set()
        await dispatch_task
        await hass.async_block_till_done(wait_background_tasks=True)

    mock_wait_for.assert_awaited_once_with(ATTR_THERMOSTATS)
    assert thermostat_add_entities.call_count == 1
    assert [entity.index for entity in thermostat_add_entities.call_args[0][0]] == [0]

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
