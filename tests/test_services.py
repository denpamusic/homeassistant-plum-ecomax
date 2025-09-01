"""Test Plum ecoMAX services."""

from typing import Final, Literal
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntry
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.parameters import Parameter
from pyplumio.structures.schedules import Schedule, ScheduleDay
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import ATTR_VALUE, DOMAIN, WEEKDAYS
from custom_components.plum_ecomax.services import (
    ATTR_END,
    ATTR_PRESET,
    ATTR_START,
    ATTR_TYPE,
    ATTR_WEEKDAYS,
    PRESET_DAY,
    PRESET_NIGHT,
    SCHEDULES,
    SERVICE_GET_PARAMETER,
    SERVICE_GET_SCHEDULE,
    SERVICE_SET_PARAMETER,
    SERVICE_SET_SCHEDULE,
    DeviceId,
    ProductId,
    async_extract_target_device,
    async_suggest_device_parameter_name,
    async_validate_device_parameter,
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
    with (
        patch(
            "homeassistant.helpers.device_registry.DeviceRegistry.async_get",
            return_value=False,
        ),
        pytest.raises(HomeAssistantError),
    ):
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


@pytest.mark.parametrize(
    ("name", "expected_suggestion"),
    [
        ("heating_traget_temp", "heating_target_temp"),
        ("grat_heating_temp", "grate_heating_temp"),
        ("nonexistent", None),
    ],
)
def test_suggest_device_parameter_name(
    hass: HomeAssistant, ecomax_p: EcoMAX, name: str, expected_suggestion: str | None
) -> None:
    """Test getting parameter name suggestion."""
    suggestion = async_suggest_device_parameter_name(ecomax_p, name)
    assert suggestion == expected_suggestion


RAISES: Final = "raises"


@pytest.mark.parametrize(
    ("name", "expected_result", "exception", "exception_pattern"),
    [
        ("heating_target_temp", "heating_target_temp", None, None),
        ("product", RAISES, ServiceValidationError, "property_not_writable"),
        ("nonexistent", RAISES, HomeAssistantError, "parameter_not_found"),
        ("grat_heating_temp", RAISES, HomeAssistantError, "parameter_not_found"),
    ],
)
def test_async_validate_device_parameter(
    ecomax_p: EcoMAX,
    name: str,
    expected_result: str | Literal["raises"],
    exception: type[Exception] | None,
    exception_pattern: str | None,
) -> None:
    """Test validating device parameter."""
    if expected_result != RAISES:
        parameter = async_validate_device_parameter(ecomax_p, name)
        assert isinstance(parameter, Parameter)
        assert parameter.description.name == expected_result
    else:
        assert exception is not None
        with pytest.raises(exception, match=exception_pattern):
            async_validate_device_parameter(ecomax_p, name)


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
                "value": 0,
                "min_value": 0,
                "max_value": 1,
                "step": 1.0,
                "unit_of_measurement": "°C",
                "product": ProductId(
                    model="ecoMAX 850P2-C",
                    uid="TEST",
                ),
            }
        ]
    }

    # Test getting switch for EM device.
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        {
            ATTR_ENTITY_ID: heating_temperature_entity_id,
            ATTR_NAME: "weather_control",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response == {
        "parameters": [
            {
                "name": "weather_control",
                "value": "off",
                "min_value": "off",
                "max_value": "on",
                "product": ProductId(
                    model="ecoMAX 850P2-C",
                    uid="TEST",
                ),
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
                "value": 0,
                "min_value": 0,
                "max_value": 1,
                "step": 1.0,
                "unit_of_measurement": "°C",
                "product": ProductId(
                    model="ecoMAX 850P2-C",
                    uid="TEST",
                ),
                "device": DeviceId(type="mixer", index=1),
            }
        ]
    }

    # Test parameter not found error.
    with (
        pytest.raises(HomeAssistantError) as exc_info,
        patch("pyplumio.devices.Device.get_nowait", return_value=None),
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

    assert exc_info.value.translation_key == "parameter_not_found"
    assert exc_info.value.translation_placeholders == {"parameter": "nonexistent"}

    # Test getting an invalid parameter.
    with (
        pytest.raises(ServiceValidationError) as exc_info,
        patch("pyplumio.devices.Device.get_nowait", return_value="nonexistent"),
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

    assert exc_info.value.translation_key == "property_not_writable"
    assert exc_info.value.translation_placeholders == {"property": "nonexistent"}

    # Test getting parameter with unknown product id.
    with patch(
        "pyplumio.devices.Device.get_nowait",
        side_effect=(connection.device.data["heating_target_temp"], None),
    ):
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
                "value": 0,
                "min_value": 0,
                "max_value": 1,
                "step": 1.0,
                "unit_of_measurement": "°C",
            }
        ]
    }


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
    with patch("pyplumio.parameters.Parameter.set_nowait") as mock_set_nowait:
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "heating_target_temp",
                ATTR_VALUE: 0,
            },
            blocking=True,
            return_response=True,
        )
        await hass.async_block_till_done()

    mock_set_nowait.assert_called_once_with(0.0, retries=0, timeout=15)

    assert response == {
        "parameters": [
            {
                "name": "heating_target_temp",
                "value": 0.0,
                "min_value": 0.0,
                "max_value": 1.0,
                "step": 1.0,
                "unit_of_measurement": "°C",
                "product": ProductId(
                    model="ecoMAX 850P2-C",
                    uid="TEST",
                ),
            }
        ]
    }

    # Test setting parameter without response.
    with patch("pyplumio.parameters.Parameter.set_nowait") as mock_set_nowait:
        assert not await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "heating_target_temp",
                ATTR_VALUE: 5,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_set_nowait.assert_called_once_with(5.0, retries=0, timeout=15)

    # Test setting parameter for a mixer.
    mixer_temperature_entity_id = "sensor.ecomax_mixer_1_mixer_temperature"
    with patch("pyplumio.parameters.Parameter.set_nowait") as mock_set_nowait:
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

    mock_set_nowait.assert_called_once_with(0.0, retries=0, timeout=15)

    # Test setting a parameter to an invalid value.
    with (
        pytest.raises(ServiceValidationError) as exc_info,
        patch(
            "pyplumio.parameters.Parameter.set_nowait", side_effect=ValueError
        ) as mock_set_nowait,
    ):
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

    mock_set_nowait.assert_called_once_with(100.0, retries=0, timeout=15)
    assert exc_info.value.translation_key == "invalid_parameter_value"
    assert exc_info.value.translation_placeholders == {
        "parameter": "heating_target_temp",
        "value": "100.0",
    }

    # Test setting an invalid parameter.
    with (
        pytest.raises(ServiceValidationError) as exc_info,
        patch("pyplumio.devices.Device.get_nowait", side_effect="not_a_parameter"),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_ENTITY_ID: heating_temperature_entity_id,
                ATTR_NAME: "not_a_parameter",
                ATTR_VALUE: 0,
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "property_not_writable"
    assert exc_info.value.translation_placeholders == {"property": "not_a_parameter"}

    # Test parameter not found error.
    with (
        pytest.raises(HomeAssistantError) as exc2_info,
        patch("pyplumio.devices.Device.get_nowait", return_value=None),
    ):
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

    assert exc2_info.value.translation_key == "parameter_not_found"
    assert exc2_info.value.translation_placeholders == {"parameter": "nonexistent"}


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
    mock_schedule.monday = ScheduleDay.from_iterable([True, True, False, True])
    mock_schedule.tuesday = ScheduleDay.from_iterable([True, True, True, True])
    schedules = {SCHEDULES[0]: mock_schedule}

    # Test getting schedule for EM device.
    with patch("pyplumio.devices.Device.get_nowait", return_value=schedules):
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_SCHEDULE,
            {ATTR_TYPE: SCHEDULES[0], ATTR_WEEKDAYS: [WEEKDAYS[0], WEEKDAYS[1]]},
            blocking=True,
            return_response=True,
        )
        await hass.async_block_till_done()

    assert response == {
        "schedule": {
            "monday": {
                "00:00": PRESET_DAY,
                "00:30": PRESET_DAY,
                "01:00": PRESET_NIGHT,
                "01:30": PRESET_DAY,
            },
            "tuesday": {
                "00:00": PRESET_DAY,
                "00:30": PRESET_DAY,
                "01:00": PRESET_DAY,
                "01:30": PRESET_DAY,
            },
        }
    }

    # Test getting an invalid schedule.
    with (
        pytest.raises(ServiceValidationError) as exc_info,
        patch("pyplumio.devices.Device.get_nowait", return_value=schedules),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[1],
                ATTR_WEEKDAYS: WEEKDAYS[0],
            },
            blocking=True,
            return_response=True,
        )

    assert exc_info.value.translation_key == "schedule_not_found"
    assert exc_info.value.translation_placeholders == {"schedule": "water_heater"}


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
    mock_schedule.tuesday = Mock(spec=ScheduleDay)
    mock_schedule.tuesday.set_state = Mock()
    mock_schedule.commit = AsyncMock()
    schedules = {SCHEDULES[0]: mock_schedule}

    # Test setting schedule for EM device.
    with patch("pyplumio.devices.Device.get_nowait", return_value=schedules):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[0],
                ATTR_WEEKDAYS: [WEEKDAYS[0], WEEKDAYS[1]],
                ATTR_PRESET: PRESET_DAY,
                ATTR_START: "00:00:00",
                ATTR_END: "10:00:00",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_schedule.monday.set_state.assert_called_once_with(True, "00:00", "10:00")
    mock_schedule.tuesday.set_state.assert_called_once_with(True, "00:00", "10:00")
    mock_schedule.commit.assert_called_once()

    # Test setting a schedule with an invalid time interval.
    mock_schedule.monday.set_state.side_effect = ValueError
    with (
        pytest.raises(ServiceValidationError) as exc_info,
        patch("pyplumio.devices.Device.get_nowait", return_value=schedules),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[0],
                ATTR_WEEKDAYS: WEEKDAYS[0],
                ATTR_PRESET: PRESET_DAY,
                ATTR_START: "00:00:00",
                ATTR_END: "10:00:00",
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_schedule_interval"
    assert exc_info.value.translation_placeholders == {
        "schedule": "heating",
        "start": "00:00",
        "end": "10:00",
    }

    # Test setting an invalid schedule.
    with (
        pytest.raises(ServiceValidationError) as exc_info,
        patch("pyplumio.devices.Device.get_nowait", return_value=schedules),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SCHEDULE,
            {
                ATTR_TYPE: SCHEDULES[1],
                ATTR_WEEKDAYS: WEEKDAYS[0],
                ATTR_PRESET: PRESET_DAY,
                ATTR_START: "00:00:00",
                ATTR_END: "10:00:00",
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "schedule_not_found"
    assert exc_info.value.translation_placeholders == {"schedule": "water_heater"}
