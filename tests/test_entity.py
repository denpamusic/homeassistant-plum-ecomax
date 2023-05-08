"""Test Plum ecoMAX base entity."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.helpers.entity import EntityDescription
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.filters import Filter

from custom_components.plum_ecomax.entity import EcomaxEntity


class _TestEntity(EcomaxEntity):
    """Test entity class."""

    def __init__(self, *args, **kwargs):
        self._attr_available = True
        super().__init__(*args, **kwargs)

    async def async_update(self, value=None) -> None:
        """Retrieve latest state."""


@patch("custom_components.plum_ecomax.entity.EcomaxEntity.connection")
@patch.object(_TestEntity, "async_update")
async def test_base_entity(
    mock_async_update, mock_connection, ecomax_p: EcoMAX
) -> None:
    """Test base entity."""
    entity = _TestEntity()
    mock_description = Mock(spec=EntityDescription)
    mock_description.key = "heating_temp"
    mock_description.name = "Heating temperature"
    mock_filter = AsyncMock(spec=Filter)
    mock_description.filter_fn = Mock(return_value=mock_filter)
    entity.entity_description = mock_description
    mock_connection.device = ecomax_p

    # Test adding entity to hass.
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxEntity.connection.device.subscribe"
    ) as mock_subscribe:
        await entity.async_added_to_hass()

    mock_description.filter_fn.assert_called_once()
    mock_subscribe.assert_has_calls([call("heating_temp", mock_filter)])

    # Test removing entity from the hass.
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxEntity.connection.device.unsubscribe"
    ) as mock_unsubscribe:
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
    entity.entity_description.always_available = True
    assert entity.available
    mock_connection.reset_mock()

    # Test device info property.
    assert entity.device_info == mock_connection.device_info

    # Test unique id property.
    mock_connection.uid = "test_uid"
    assert entity.unique_id == "test_uid-heating_temp"

    # Test should poll property.
    assert not entity.should_poll

    # Test enabled by default property.
    assert entity.entity_registry_enabled_default
    entity.entity_description = EntityDescription("test_data2", name="ecoMAX Data 2")
    assert not entity.entity_registry_enabled_default
