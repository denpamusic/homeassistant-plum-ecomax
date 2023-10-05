"""Test Plum ecoMAX services."""


from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, ATTR_STATE, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import ParameterNotFoundError
from pyplumio.helpers.schedule import Schedule, ScheduleDay
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_END,
    ATTR_START,
    ATTR_TYPE,
    ATTR_VALUE,
    ATTR_WEEKDAY,
    DOMAIN,
    WEEKDAYS,
)
from custom_components.plum_ecomax.services import (
    SCHEDULES,
    SERVICE_GET_PARAMETER,
    SERVICE_GET_SCHEDULE,
    SERVICE_SET_PARAMETER,
    SERVICE_SET_SCHEDULE,
    async_extract_target_device,
)


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


@pytest.fixture(autouse=True)
def set_connected(connected):
    """Assume connected."""


async def test_extract_missing_target_device(hass: HomeAssistant) -> None:
    """Test extracting missing target device."""
    mock_connection = AsyncMock(spec=EcomaxConnection)
    with patch(
        "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
        return_value=False,
    ), pytest.raises(HomeAssistantError):
        async_extract_target_device("nonexistent", hass, mock_connection)


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


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_get_parameter_service(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    caplog,
) -> None:
    """Test get parameter service."""
    await setup_integration(hass, config_entry)
    heating_temperature_entity_id = "sensor.ecomax_heating_temperature"

    # Test getting parameter for EM device.
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        {
            ATTR_ENTITY_ID: heating_temperature_entity_id,
            ATTR_NAME: "heating_target_temp",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response == {
        "parameters": [
            {
                "name": "heating_target_temp",
                "value": 0.0,
                "min_value": 0.0,
                "max_value": 1.0,
                "device_type": "ecomax",
                "device_uid": "TEST",
            }
        ]
    }

    # Test getting parameter for mixer.
    mixer_temperature_entity_id = "sensor.ecomax_mixer_1_mixer_temperature"
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        {
            ATTR_ENTITY_ID: mixer_temperature_entity_id,
            ATTR_NAME: "mixer_target_temp",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response == {
        "parameters": [
            {
                "name": "mixer_target_temp",
                "value": 0.0,
                "min_value": 0.0,
                "max_value": 1.0,
                "device_type": "mixer",
                "device_uid": "TEST",
                "device_index": 1,
            }
        ]
    }

    # Test getting nonexistent parameter.
    with pytest.raises(HomeAssistantError), patch(
        "pyplumio.devices.Device.get", side_effect=ParameterNotFoundError
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "nonexistent",
            },
            blocking=True,
            return_response=True,
        )

    assert "Requested parameter nonexistent not found" in caplog.text


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_set_parameter_service(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    caplog,
) -> None:
    """Test set parameter service."""
    await setup_integration(hass, config_entry)
    heating_temperature_entity_id = "sensor.ecomax_heating_temperature"

    # Test setting parameter for EM device.
    with patch("pyplumio.devices.Device.set") as mock_set:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "heating_target_temp",
                ATTR_VALUE: 0,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_set.assert_awaited_once_with("heating_target_temp", 0)

    # Test setting parameter for a mixer.
    mixer_temperature_entity_id = "sensor.ecomax_mixer_1_mixer_temperature"
    with patch("pyplumio.devices.Device.set") as mock_set:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: mixer_temperature_entity_id,
                ATTR_NAME: "mixer_target_temp",
                ATTR_VALUE: 0,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_set.assert_awaited_once_with("mixer_target_temp", 0)

    # Test setting parameter to an invalid value.
    with pytest.raises(HomeAssistantError), patch(
        "pyplumio.devices.Device.set", side_effect=ValueError
    ) as mock_set:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "heating_target_temp",
                ATTR_VALUE: 100,
            },
            blocking=True,
        )

    mock_set.assert_awaited_once_with("heating_target_temp", 100)

    # Test setting parameter to nonexistent parameter.
    with pytest.raises(HomeAssistantError), patch(
        "pyplumio.devices.Device.set", side_effect=ParameterNotFoundError
    ) as mock_set:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "nonexistent",
                ATTR_VALUE: 0,
            },
            blocking=True,
        )

    assert "Requested parameter nonexistent not found" in caplog.text


@pytest.mark.usefixtures("ecomax_p")
async def test_get_schedule_service(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test get schedule service."""
    await setup_integration(hass, config_entry)

    mock_schedule = Mock(spec=Schedule)
    mock_schedule.monday = Mock(spec=ScheduleDay)
    mock_schedule.monday.intervals = [True, True, False, True]
    schedules = {SCHEDULES[0]: mock_schedule}

    # Test getting schedule for EM device.
    with patch("pyplumio.devices.Device.get_nowait", return_value=schedules):
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_SCHEDULE,
            {ATTR_TYPE: SCHEDULES[0], ATTR_WEEKDAY: WEEKDAYS[0]},
            blocking=True,
            return_response=True,
        )
        await hass.async_block_till_done()

    assert response == {
        "schedule": {
            "00:00": True,
            "00:30": True,
            "01:00": False,
            "01:30": True,
        }
    }

    # Test getting schedule with unknown schedule type.
    with pytest.raises(HomeAssistantError), patch(
        "pyplumio.devices.Device.get_nowait", return_value=schedules
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[1],
                ATTR_WEEKDAY: WEEKDAYS[0],
            },
            blocking=True,
            return_response=True,
        )


@pytest.mark.usefixtures("ecomax_p")
async def test_set_schedule_service(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test set schedule service."""
    await setup_integration(hass, config_entry)

    mock_schedule = Mock(spec=Schedule)
    mock_schedule.monday = Mock(spec=ScheduleDay)
    mock_schedule.monday.set_state = Mock()
    mock_schedule.commit = Mock()
    schedules = {SCHEDULES[0]: mock_schedule}

    # Test setting schedule for EM device.
    with patch("pyplumio.devices.Device.get_nowait", return_value=schedules):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[0],
                ATTR_WEEKDAY: WEEKDAYS[0],
                ATTR_STATE: True,
                ATTR_START: "00:00:00",
                ATTR_END: "10:00:00",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_schedule.monday.set_state.assert_called_once_with(STATE_ON, "00:00", "10:00")
    mock_schedule.commit.assert_called_once()

    # Test setting schedule with incorrect time interval.
    mock_schedule.monday.set_state.side_effect = ValueError
    with pytest.raises(HomeAssistantError), patch(
        "pyplumio.devices.Device.get_nowait", return_value=schedules
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[0],
                ATTR_WEEKDAY: WEEKDAYS[0],
                ATTR_STATE: True,
                ATTR_START: "00:00:00",
                ATTR_END: "10:00:00",
            },
            blocking=True,
        )

    # Test setting schedule with unknown schedule type.
    with pytest.raises(HomeAssistantError), patch(
        "pyplumio.devices.Device.get_nowait", return_value=schedules
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[1],
                ATTR_WEEKDAY: WEEKDAYS[0],
                ATTR_STATE: True,
                ATTR_START: "00:00:00",
                ATTR_END: "10:00:00",
            },
            blocking=True,
        )
