"""Test Plum ecoMAX base entity."""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.filters import Filter
from pyplumio.structures.sensor_data import ATTR_HEATING_TEMP
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DOMAIN, ModuleType
from custom_components.plum_ecomax.entity import (
    MANUFACTURER,
    EcomaxEntity,
    EcomaxEntityDescription,
    async_register_entities,
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


async def test_async_register_entities_cancels_scheduled_add_on_unload(
    hass: HomeAssistant, ecomax_p: EcoMAX, config_entry: MockConfigEntry
) -> None:
    """Test scheduled deferred add handle is cancelled on unload before next tick."""
    mock_connection = Mock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_connection.entry = config_entry
    mock_connection.uid = "TEST"

    deferred_entity = EcomaxEntity(
        connection=mock_connection,
        description=EcomaxEntityDescription(
            key="race_key",
            name="Race key",
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

    await ecomax_p.dispatch("race_key", 1)
    unload_callbacks[0]()
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
