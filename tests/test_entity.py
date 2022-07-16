"""Test Plum ecoMAX base entity."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.helpers.entity import EntityDescription
from pyplumio.devices import Device
from pyplumio.helpers.filters import Filter

from custom_components.plum_ecomax.entity import EcomaxEntity


class TestEntity(EcomaxEntity):
    """Test entity class."""

    async def async_update(self, value) -> None:
        """Retrieve latest state."""


@patch.object(TestEntity, "async_update")
@patch(
    "custom_components.plum_ecomax.entity.EcomaxEntity.connection",
    new_callable=AsyncMock,
)
async def test_base_entity(mock_connection, mock_async_update) -> None:
    """Test base entity."""
    entity = TestEntity()
    entity.entity_description = EntityDescription("test_entity", name="Test Entity")
    mock_filter = AsyncMock(spec=Filter)
    entity.entity_description.filter_fn = Mock(return_value=mock_filter)
    mock_connection.device = Mock(spec=Device)
    mock_connection.device.test_entity = "test"

    # Test added/removed to/from hass.
    await entity.async_added_to_hass()
    entity.entity_description.filter_fn.assert_called_once()
    entity.device.register_callback.assert_called_once_with(
        "test_entity", entity.entity_description.filter_fn.return_value
    )
    mock_filter.assert_awaited_once()
    await entity.async_will_remove_from_hass()
    entity.device.remove_callback.assert_called_once_with(
        "test_entity", mock_async_update
    )

    # Test device property.
    assert entity.device == mock_connection.device

    # Test available property.
    mock_connection.device = None
    assert not entity.available
    mock_connection.reset_mock()

    # Test device info property.
    assert entity.device_info == mock_connection.device_info

    # Test enabled by default property.
    mock_connection.capabilities = set()
    assert not entity.entity_registry_enabled_default
    mock_connection.capabilities = set(["test_entity"])
    assert entity.entity_registry_enabled_default

    # Test unique id property.
    mock_connection.uid = "test_uid"
    assert entity.unique_id == "test_uid-test_entity"

    # Test name property.
    mock_connection.name = "Test Connection"
    assert entity.name == "Test Connection Test Entity"

    # Test should poll propery.
    assert not entity.should_poll
