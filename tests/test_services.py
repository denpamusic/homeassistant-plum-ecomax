"""Test Plum ecoMAX services."""

from typing import Final
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import ATTR_DEVICE_ID, STATE_ON
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.service import SelectedEntities
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import ParameterNotFoundError
from pyplumio.helpers.schedule import Schedule, ScheduleDay
import pytest

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_TYPE,
    ATTR_VALUE,
    WEEKDAYS,
)
from custom_components.plum_ecomax.services import (
    ATTR_END,
    ATTR_NAME,
    ATTR_START,
    ATTR_STATE,
    ATTR_WEEKDAY,
    SERVICE_SET_PARAMETER,
    SERVICE_SET_PARAMETER_SCHEMA,
    SERVICE_SET_SCHEDULE,
    async_extract_referenced_devices,
    async_extract_target_device,
    async_setup_services,
)

DEVICE_ID: Final = "test-device"


async def test_setup_services(hass: HomeAssistant) -> None:
    """Test services setup."""
    with patch(
        "homeassistant.core.ServiceRegistry.async_register"
    ) as mock_async_register:
        assert async_setup_services(hass, AsyncMock(spec=EcomaxConnection))

    assert mock_async_register.call_count == 2


async def test_extract_target_device(hass: HomeAssistant) -> None:
    """Test extracting target device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_device_entry = Mock(spec=DeviceEntry)
    mock_device_entry.identifiers = {("test", DEVICE_ID)}

    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=mock_device_entry,
    ):
        device = async_extract_target_device(DEVICE_ID, hass, mock_connection)

    assert device == mock_connection.device


@pytest.mark.usefixtures("mixers")
async def test_extract_target_mixer_device(
    hass: HomeAssistant, ecomax_p: EcoMAX
) -> None:
    """Test extracting target mixer device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_device_entry = Mock(spec=DeviceEntry)
    mock_device_entry.identifiers = {("test", "test-mixer-0")}

    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=mock_device_entry,
    ):
        device = async_extract_target_device("test-mixer-0", hass, mock_connection)

    assert device == mock_connection.device.data[ATTR_MIXERS][0]


@pytest.mark.usefixtures("mixers")
async def test_extract_target_missing_mixer_device(
    hass: HomeAssistant, ecomax_p: EcoMAX
) -> None:
    """Test extracting missing target mixer device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = ecomax_p
    mock_device_entry = Mock(spec=DeviceEntry)
    mock_device_entry.identifiers = {("test", "test-mixer-1")}
    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=mock_device_entry,
    ):
        device = async_extract_target_device("test-mixer-1", hass, mock_connection)

    assert device == mock_connection.device


async def test_extract_missing_target_device(hass: HomeAssistant) -> None:
    """Test extracting missing target device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=False,
    ), pytest.raises(HomeAssistantError):
        async_extract_target_device(DEVICE_ID, hass, mock_connection)


async def test_extract_referenced_devices(hass: HomeAssistant) -> None:
    """Test extracting referenced devices."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = AsyncMock(spec=EcoMAX)
    mock_selected_entities = Mock(spec=SelectedEntities)
    mock_selected_entities.configure_mock(
        referenced={DEVICE_ID}, indirectly_referenced={DEVICE_ID}
    )
    mock_entity = Mock(spec=Entity)
    mock_entity.device_id = DEVICE_ID

    with patch(
        "homeassistant.helpers.entity_registry.EntityRegistry.async_get",
        return_value=mock_entity,
    ), patch(
        "custom_components.plum_ecomax.services.async_extract_target_device",
        return_value=mock_connection.device,
    ):
        devices = async_extract_referenced_devices(
            hass, mock_connection, mock_selected_entities
        )

    assert devices == {mock_connection.device}


async def test_set_parameter_service(hass: HomeAssistant) -> None:
    """Test set parameter service."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = AsyncMock(spec=EcoMAX)

    with patch(
        "homeassistant.core.ServiceRegistry.async_register"
    ) as mock_async_register:
        async_setup_services(hass, mock_connection)

    set_parameter_service_call = mock_async_register.call_args_list[0]
    _, service, func, schema = set_parameter_service_call[0]
    assert service == SERVICE_SET_PARAMETER
    assert schema == SERVICE_SET_PARAMETER_SCHEMA

    mock_service_call = AsyncMock(spec=ServiceCall)
    mock_service_call.data = {
        ATTR_NAME: "test_name",
        ATTR_VALUE: 39,
        ATTR_DEVICE_ID: DEVICE_ID,
    }
    with patch(
        "homeassistant.helpers.service.async_extract_referenced_entity_ids",
    ), patch(
        "custom_components.plum_ecomax.services.async_extract_referenced_devices",
        return_value={mock_connection.device},
    ):
        await func(mock_service_call)

    mock_connection.device.set.assert_called_once_with("test_name", 39)

    # Check that error is raised if parameter not found.
    mock_connection.device.set.side_effect = ParameterNotFoundError
    with patch(
        "homeassistant.helpers.service.async_extract_referenced_entity_ids",
    ), patch(
        "custom_components.plum_ecomax.services.async_extract_referenced_devices",
        return_value={mock_connection.device},
    ), pytest.raises(
        HomeAssistantError
    ):
        await func(mock_service_call)

    # Check for error when devices not found.
    with patch(
        "custom_components.plum_ecomax.services.async_extract_referenced_devices",
        return_value=set(),
    ), pytest.raises(HomeAssistantError):
        await func(mock_service_call)


async def test_set_schedule_service(hass: HomeAssistant) -> None:
    """Test set schedule service."""
    mock_schedule = Mock(spec=Schedule)
    mock_schedule.monday = Mock(spec=ScheduleDay)
    mock_schedule.monday.set_state.side_effect = (True, ValueError)
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = AsyncMock(spec=EcoMAX)
    mock_connection.device.get_nowait = Mock(return_value={"test_name": mock_schedule})
    mock_service_call = AsyncMock(spec=ServiceCall)
    with patch(
        "homeassistant.core.ServiceRegistry.async_register"
    ) as mock_async_register:
        async_setup_services(hass, mock_connection)

    set_schedule_service_call = mock_async_register.call_args_list[1]
    _, service, func, _ = set_schedule_service_call[0]
    assert service == SERVICE_SET_SCHEDULE
    mock_service_call.data = {
        ATTR_TYPE: "test_name",
        ATTR_WEEKDAY: WEEKDAYS[0],
        ATTR_STATE: True,
        ATTR_START: "00:00:00",
        ATTR_END: "10:00:00",
    }

    await func(mock_service_call)
    mock_schedule.monday.set_state.assert_called_once_with(STATE_ON, "00:00", "10:00")

    # Check that hass error is raised from value error.
    with pytest.raises(HomeAssistantError):
        await func(mock_service_call)

    # Check that hass error is raised when ecomax data is empty.
    mock_connection.device.get_nowait.return_value = {}
    with pytest.raises(HomeAssistantError):
        await func(mock_service_call)
