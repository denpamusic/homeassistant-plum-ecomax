"""Test Plum ecoMAX services."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import ATTR_DEVICE_ID, STATE_ON
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from pyplumio.devices import Device
from pyplumio.exceptions import ParameterNotFoundError
from pyplumio.helpers.schedule import Schedule, ScheduleDay
import pytest

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_SCHEDULES,
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
    async_setup_services,
    extract_referenced_devices,
    extract_target_device,
)


async def test_setup_services(hass: HomeAssistant, mock_device: Device) -> None:
    """Test services setup."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    with patch(
        "homeassistant.core.ServiceRegistry.async_register"
    ) as mock_async_register:
        await async_setup_services(hass, mock_connection)

    assert mock_async_register.call_count == 2


async def test_extract_target_device(hass: HomeAssistant, mock_device: Device) -> None:
    """Test extracting target device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    mock_device_entry = Mock()
    mock_device_entry.identifiers = {("test", "test-device")}

    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=mock_device_entry,
    ):
        device = extract_target_device("test-device", hass, mock_connection)

    assert device == mock_connection.device


async def test_extract_target_mixer_device(
    hass: HomeAssistant, mock_device: Device
) -> None:
    """Test extracting target mixer device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    mock_device_entry = Mock()
    mock_device_entry.identifiers = {("test", "test-mixer-0")}

    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=mock_device_entry,
    ):
        device = extract_target_device("test-mixer-0", hass, mock_connection)

    assert device == mock_connection.device.data[ATTR_MIXERS][0]


async def test_extract_target_missing_mixer_device(
    hass: HomeAssistant, mock_device: Device
) -> None:
    """Test extracting missing target mixer device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    mock_device_entry = Mock()
    mock_device_entry.identifiers = {("test", "test-mixer-1")}

    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=mock_device_entry,
    ):
        device = extract_target_device("test-mixer-1", hass, mock_connection)

    assert device == mock_connection.device


async def test_extract_missing_target_device(
    hass: HomeAssistant, mock_device: Device
) -> None:
    """Test extracting missing target device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=False,
    ), pytest.raises(HomeAssistantError):
        extract_target_device("test-device", hass, mock_connection)


async def test_extract_referenced_devices(
    hass: HomeAssistant, mock_device: Device
) -> None:
    """Test extracting referenced devices."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device
    mock_selected = Mock()
    mock_selected.referenced = mock_selected.indirectly_referenced = {"test-device"}
    mock_entity_entry = Mock()
    mock_entity_entry.device_id = "test-device"

    with patch(
        "homeassistant.helpers.entity_registry.EntityRegistry.async_get",
        return_value=mock_entity_entry,
    ), patch(
        "custom_components.plum_ecomax.services.extract_target_device",
        return_value=mock_device,
    ):
        devices = extract_referenced_devices(hass, mock_connection, mock_selected)

    assert devices == {mock_device}


async def test_set_parameter_service(hass: HomeAssistant, mock_device: Device) -> None:
    """Test set parameter service."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device

    with patch(
        "homeassistant.core.ServiceRegistry.async_register"
    ) as mock_async_register:
        await async_setup_services(hass, mock_connection)

    set_parameter_service, _ = mock_async_register.call_args_list
    args, _ = set_parameter_service
    _, service, func, schema = args
    assert service == SERVICE_SET_PARAMETER
    assert schema == SERVICE_SET_PARAMETER_SCHEMA

    mock_service_call = AsyncMock(spec=ServiceCall)
    mock_service_call.data = {
        ATTR_NAME: "test_name",
        ATTR_VALUE: 39,
        ATTR_DEVICE_ID: "test-device",
    }
    with patch(
        "homeassistant.helpers.service.async_extract_referenced_entity_ids",
    ), patch(
        "custom_components.plum_ecomax.services.extract_referenced_devices",
        return_value={mock_device},
    ):
        await func(mock_service_call)

    mock_connection.device.set_value.assert_called_once_with("test_name", 39)

    # Check that error is raised if parameter not found.
    mock_connection.device.set_value.side_effect = ParameterNotFoundError
    with patch(
        "homeassistant.helpers.service.async_extract_referenced_entity_ids",
    ), patch(
        "custom_components.plum_ecomax.services.extract_referenced_devices",
        return_value={mock_device},
    ), pytest.raises(
        HomeAssistantError
    ):
        await func(mock_service_call)

    # Check for error when devices not found.
    with patch(
        "custom_components.plum_ecomax.services.extract_referenced_devices",
        return_value=set(),
    ), pytest.raises(HomeAssistantError):
        await func(mock_service_call)


async def test_set_schedule_service(
    hass: HomeAssistant, mock_device: Device, caplog
) -> None:
    """Test set schedule service."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    mock_connection.device = mock_device
    mock_service_call = AsyncMock(spec=ServiceCall)

    with patch(
        "homeassistant.core.ServiceRegistry.async_register"
    ) as mock_async_register:
        await async_setup_services(hass, mock_connection)

    _, set_schedule_service = mock_async_register.call_args_list
    args, _ = set_schedule_service
    _, service, func, _ = args
    assert service == SERVICE_SET_SCHEDULE
    mock_service_call.data = {
        ATTR_NAME: "test_name",
        ATTR_WEEKDAY: WEEKDAYS[0],
        ATTR_STATE: True,
        ATTR_START: "00:00:00",
        ATTR_END: "10:00:00",
    }

    mock_schedule = Mock(spec=Schedule)
    mock_schedule.monday = Mock(spec=ScheduleDay)
    mock_schedule.monday.set_state.side_effect = (True, ValueError)
    mock_connection.device.data = {ATTR_SCHEDULES: {"test_name": mock_schedule}}
    await func(mock_service_call)
    mock_schedule.monday.set_state.assert_called_once_with(STATE_ON, "00:00", "10:00")
    with pytest.raises(HomeAssistantError):
        await func(mock_service_call)

    mock_connection.device.data = {}
    with pytest.raises(HomeAssistantError):
        await func(mock_service_call)
