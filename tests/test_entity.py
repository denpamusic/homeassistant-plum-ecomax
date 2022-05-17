"""Test Plum ecoMAX base sensor."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from custom_components.plum_ecomax.connection import (
    EcomaxConnection,
    EcomaxTcpConnection,
)
from custom_components.plum_ecomax.entity import EcomaxEntity


@pytest.fixture(name="entity_description")
def fixture_entity_description():
    """Mock entity description."""
    mock_entity_description = Mock()
    mock_entity_description.key = "test_entity"
    mock_entity_description.name = "Test Entity"
    yield mock_entity_description


@pytest.fixture(name="test_entity")
@patch.multiple(EcomaxEntity, __abstractmethods__=set())
def fixture_test_entity(
    mock_connection: EcomaxTcpConnection, entity_description
) -> EcomaxEntity:
    """Create test entity instance."""
    test_entity = EcomaxEntity()
    test_entity._connection = mock_connection
    test_entity.entity_description = entity_description
    return test_entity


async def test_enabled_by_default(test_entity: EcomaxEntity) -> None:
    """Test entity enabled by default property."""
    # Test with key that is not present in the capabilities list.
    assert not test_entity.entity_registry_enabled_default

    # Re-test with key that present in the capabilities list.
    test_entity.entity_description.key = "heating_temp"
    assert test_entity.entity_registry_enabled_default


async def test_available(
    test_entity: EcomaxEntity, mock_connection: EcomaxTcpConnection
) -> None:
    """Test entity available property."""
    # Test is entity is available.
    assert test_entity.available

    # Unset ecomax device from connection data and re-test the property.
    mock_connection.ecomax = None
    assert not test_entity.available


async def test_device_info(
    test_entity: EcomaxEntity, mock_connection: EcomaxTcpConnection
) -> None:
    """Test entity device info."""
    assert test_entity.device_info == mock_connection.device_info


async def test_unique_id_and_name(
    test_entity: EcomaxEntity, mock_connection: EcomaxTcpConnection
) -> None:
    """Test entity unique id and name properties."""
    connection = mock_connection
    assert (
        test_entity.unique_id
        == f"{connection.uid}-{test_entity.entity_description.key}"
    )
    assert (
        test_entity.name == f"{connection.name} {test_entity.entity_description.name}"
    )


async def test_should_poll(test_entity: EcomaxEntity) -> None:
    """Test whether entity should poll."""
    assert not test_entity.should_poll


@patch.multiple(EcomaxEntity, __abstractmethods__=set())
async def test_added_removed_callback(
    connection: EcomaxTcpConnection, entity_description
) -> None:
    """Test entity added and removed from hass callbacks."""
    # Crete test entity instance.
    test_entity = EcomaxEntity()
    test_entity._connection = connection
    test_entity.entity_description = entity_description

    # Create mocks to pass to the update_entities method.
    mock_devices = Mock()
    mock_devices.ecomax = Mock()
    mock_devices.ecomax.data = {"test": 1}
    mock_connection = Mock()

    with patch(
        "custom_components.plum_ecomax.entity.EcomaxEntity.async_update"
    ) as mock_async_update:
        # Call added to hass callback and check that entity was updated.
        await test_entity.async_added_to_hass()
        await connection.update_entities(mock_devices, mock_connection)
        mock_async_update.assert_called_once()
        mock_async_update.reset_mock()

        # Call removed from hass callback and
        # check that entity was not updated.
        await test_entity.async_removed_from_hass()
        await connection.update_entities(mock_devices, mock_connection)
        mock_async_update.assert_not_called()
