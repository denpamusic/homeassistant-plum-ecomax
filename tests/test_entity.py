"""Test Plum ecoMAX base entity."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.helpers.entity import DeviceInfo
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.filters import Filter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax import EcomaxEntity, EcomaxEntityDescription
from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DOMAIN, MANUFACTURER, ModuleType


@patch.object(EcomaxEntity, "async_update")
async def test_base_entity(
    mock_async_update: Any, ecomax_p: EcoMAX, config_entry: MockConfigEntry
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

    # Test adding entity to hass.
    with patch.object(mock_connection.device, "subscribe") as mock_subscribe:
        await entity.async_added_to_hass()

    mock_filter.assert_called_once()
    mock_subscribe.assert_has_calls([call("heating_temp", mock_filter)])

    # Test removing entity from the hass.
    with patch.object(mock_connection.device, "unsubscribe") as mock_unsubscribe:
        await entity.async_will_remove_from_hass()

    mock_unsubscribe.assert_called_once_with("heating_temp", mock_async_update)

    # Test device property.
    assert entity.device == mock_connection.device

    # Test available property.
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
    entity.entity_description = EcomaxEntityDescription(
        key="test_data2", name="ecoMAX Data 2"
    )
    assert not entity.entity_registry_enabled_default
