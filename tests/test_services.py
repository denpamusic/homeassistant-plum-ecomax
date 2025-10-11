"""Test Plum ecoMAX services."""

from typing import Final, Literal
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import ATTR_DEVICE_ID, ATTR_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.mixer import Mixer
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
    async_extract_connection_from_device_entry,
    async_extract_device_from_service,
    async_get_device_from_entry,
    async_get_virtual_device,
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


@pytest.fixture(name="get_device_entries")
def fixture_get_device_entries(hass: HomeAssistant, config_entry: MockConfigEntry):
    """Return a device entries getter."""

    def _get_device_entries() -> list[dr.DeviceEntry]:
        """Get list of device entries."""
        device_registry = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(
            device_registry, config_entry.entry_id
        )
        return devices

    return _get_device_entries


@pytest.mark.usefixtures("ecomax_p", "connection")
async def test_async_extract_connection_from_device_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry
) -> None:
    """Test extracting connection instance from device entry."""
    await setup_config_entry()
    mock_device_entry = Mock(spec=dr.DeviceEntry, autospec=True)
    mock_device_entry.configure_mock(config_entries={config_entry.entry_id})
    async_extract_connection_from_device_entry(hass, mock_device_entry)

    # Test without valid connection instance.
    mock_device_entry.configure_mock(config_entries={})
    with pytest.raises(ValueError, match="No connection instance found"):
        async_extract_connection_from_device_entry(hass, mock_device_entry)


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_async_get_virtual_device(
    connection: EcomaxConnection, setup_config_entry
) -> None:
    """Test getting virtual device."""
    await setup_config_entry()
    virtual_device = async_get_virtual_device(connection, "TEST-mixer-0")
    assert isinstance(virtual_device, Mixer)
    assert virtual_device.index == 0

    # Test with invalid hub id.
    with pytest.raises(ValueError, match="Invalid hub id"):
        async_get_virtual_device(connection, "TEST2-mixer-0")

    # Test with missing virtual device.
    with pytest.raises(ValueError, match="virtual device not found"):
        async_get_virtual_device(connection, "TEST-mixer-3")


@pytest.mark.usefixtures("ecomax_p", "connection")
async def test_async_get_device_from_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry
) -> None:
    """Test getting device instance from device entry."""
    await setup_config_entry()
    mock_device_entry = Mock(spec=dr.DeviceEntry, autospec=True)
    mock_device_entry.configure_mock(
        config_entries={config_entry.entry_id},
        identifiers={("not_domain", "TEST"), (DOMAIN, "TEST")},
    )
    device = async_get_device_from_entry(hass, mock_device_entry)
    assert isinstance(device, EcoMAX)

    # Test without our domain in identifiers.
    mock_device_entry.configure_mock(
        config_entries={config_entry.entry_id}, identifiers={("not_domain", "TEST")}
    )
    with pytest.raises(ValueError, match="Invalid Plum ecoMAX device entry"):
        async_get_device_from_entry(hass, mock_device_entry)


@pytest.mark.usefixtures("ecomax_p", "connection")
async def test_async_extract_device_from_service(
    hass: HomeAssistant, setup_config_entry, get_device_entries
) -> None:
    """Test extracting device instance from service call."""
    await setup_config_entry()
    mock_service_call = Mock(spec=ServiceCall, autospec=True)
    device_entries = get_device_entries()
    mock_service_call.configure_mock(data={ATTR_DEVICE_ID: device_entries[0].id})
    device = async_extract_device_from_service(hass, mock_service_call)
    assert isinstance(device, EcoMAX)

    # Test with unknown device id.
    mock_service_call.configure_mock(data={ATTR_DEVICE_ID: "404_not_found"})
    with pytest.raises(ValueError, match="Unknown Plum ecoMAX device id"):
        async_extract_device_from_service(hass, mock_service_call)


@pytest.mark.parametrize(
    ("name", "expected_suggestion"),
    [
        ("heating_traget_temp", "heating_target_temp"),
        ("grat_heating_temp", "grate_heating_temp"),
        ("nonexistent", None),
    ],
)
def test_suggest_device_parameter_name(
    ecomax_p: EcoMAX, name: str, expected_suggestion: str | None
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
    setup_config_entry,
    get_device_entries,
) -> None:
    """Test get parameter service."""
    await setup_config_entry()
    device_entries = get_device_entries()

    # Test getting parameter for EM device.
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        {
            ATTR_DEVICE_ID: device_entries[0].id,
            ATTR_NAME: "heating_target_temp",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response == {
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

    # Test getting switch for EM device.
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        {
            ATTR_DEVICE_ID: device_entries[0].id,
            ATTR_NAME: "weather_control",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response == {
        "name": "weather_control",
        "value": "off",
        "min_value": "off",
        "max_value": "on",
        "product": ProductId(
            model="ecoMAX 850P2-C",
            uid="TEST",
        ),
    }

    # Test getting parameter for mixer.
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        {
            ATTR_DEVICE_ID: device_entries[1].id,
            ATTR_NAME: "mixer_target_temp",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response == {
        "name": "mixer_target_temp",
        "value": 0.0,
        "min_value": 0.0,
        "max_value": 1.0,
        "step": 1.0,
        "unit_of_measurement": "°C",
        "product": ProductId(
            model="ecoMAX 850P2-C",
            uid="TEST",
        ),
        "device": DeviceId(type="mixer", index=1),
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
                ATTR_DEVICE_ID: device_entries[0].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
                ATTR_NAME: "heating_target_temp",
            },
            blocking=True,
            return_response=True,
        )
        await hass.async_block_till_done()

    assert response == {
        "name": "heating_target_temp",
        "value": 0.0,
        "min_value": 0.0,
        "max_value": 1.0,
        "step": 1.0,
        "unit_of_measurement": "°C",
    }


@pytest.mark.usefixtures("ecomax_p", "connection", "mixers")
async def test_set_parameter_service(
    hass: HomeAssistant, setup_config_entry, get_device_entries
) -> None:
    """Test set parameter service."""
    await setup_config_entry()
    device_entries = get_device_entries()

    # Test setting parameter for EM device.
    with patch("pyplumio.parameters.Parameter.set_nowait") as mock_set_nowait:
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_DEVICE_ID: device_entries[0].id,
                ATTR_NAME: "heating_target_temp",
                ATTR_VALUE: 0,
            },
            blocking=True,
            return_response=True,
        )
        await hass.async_block_till_done()

    mock_set_nowait.assert_called_once_with(0.0, retries=0, timeout=15)

    assert response == {
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

    # Test setting parameter without response.
    with patch("pyplumio.parameters.Parameter.set_nowait") as mock_set_nowait:
        assert not await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_DEVICE_ID: device_entries[0].id,
                ATTR_NAME: "heating_target_temp",
                ATTR_VALUE: 5,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_set_nowait.assert_called_once_with(5.0, retries=0, timeout=15)

    # Test setting parameter for a mixer.
    with patch("pyplumio.parameters.Parameter.set_nowait") as mock_set_nowait:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PARAMETER,
            {
                ATTR_DEVICE_ID: device_entries[1].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
                ATTR_NAME: "nonexistent",
                ATTR_VALUE: 0,
            },
            blocking=True,
        )

    assert exc2_info.value.translation_key == "parameter_not_found"
    assert exc2_info.value.translation_placeholders == {"parameter": "nonexistent"}


@pytest.mark.usefixtures("ecomax_p", "connection")
async def test_get_schedule_service(
    hass: HomeAssistant, setup_config_entry, get_device_entries
) -> None:
    """Test get schedule service."""
    await setup_config_entry()
    device_entries = get_device_entries()

    # Test getting schedule for EM device.
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        {
            ATTR_DEVICE_ID: device_entries[0].id,
            ATTR_TYPE: SCHEDULES[0],
            ATTR_WEEKDAYS: [WEEKDAYS[0], WEEKDAYS[1]],
        },
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
        },
        "product": ProductId(
            model="ecoMAX 850P2-C",
            uid="TEST",
        ),
    }

    # Test getting an invalid schedule.
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_SCHEDULE,
            {
                ATTR_DEVICE_ID: device_entries[0].id,
                ATTR_TYPE: SCHEDULES[1],
                ATTR_WEEKDAYS: WEEKDAYS[0],
            },
            blocking=True,
            return_response=True,
        )

    assert exc_info.value.translation_key == "schedule_not_found"
    assert exc_info.value.translation_placeholders == {"schedule": "water_heater"}


@pytest.mark.usefixtures("ecomax_p", "connection")
async def test_set_schedule_service(
    hass: HomeAssistant, setup_config_entry, get_device_entries
) -> None:
    """Test set schedule service."""
    await setup_config_entry()
    device_entries = get_device_entries()

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
                ATTR_DEVICE_ID: device_entries[0].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
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
                ATTR_DEVICE_ID: device_entries[0].id,
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
