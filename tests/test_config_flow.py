"""Test Plum ecoMAX config flow."""

from collections.abc import Generator
from dataclasses import replace
from typing import Any, Final, cast
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant import config_entries
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number.const import NumberDeviceClass, NumberMode
from homeassistant.components.sensor.const import (
    CONF_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_BASE,
    CONF_DEVICE_CLASS,
    CONF_MODE,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.const import ProductType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.structures.product_info import ProductInfo
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import (
    ATTR_ENTITIES,
    ATTR_REGDATA,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_KEY,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SOURCE_DEVICE,
    CONF_STEP,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def bypass_async_migrate_entry():
    """Bypass async migrate entry."""
    with patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True):
        yield


@pytest.fixture(autouse=True)
def bypass_connection_setup():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"):
        yield


@pytest.fixture()
def bypass_async_setup_entry() -> Generator[Any, Any, Any]:
    """Bypass async setup entry."""
    with patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.mark.usefixtures("water_heater")
async def test_form_tcp(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the TCP form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Catch connection error.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        side_effect=ConnectionFailedError,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {CONF_BASE: "cannot_connect"}

    # Catch connection timeout.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        side_effect=TimeoutError,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {CONF_BASE: "timeout_connect"}

    # Catch unknown exception.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        side_effect=Exception,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {CONF_BASE: "unknown"}

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.device.return_value.__aenter__ = AsyncMock(return_value=ecomax_p)
    mock_connection.device.return_value.__aexit__ = AsyncMock()

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Discover connected modules.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    await hass.async_block_till_done()
    assert result4["type"] is FlowResultType.SHOW_PROGRESS
    assert result4["step_id"] == "discover"

    # Finish the config flow.
    result5 = await hass.config_entries.flow.async_configure(result4["flow_id"])
    assert result5["type"] is FlowResultType.CREATE_ENTRY
    assert result5["title"] == "ecoMAX 850P2-C"
    assert result5["data"] == {
        CONF_HOST: "localhost",
        CONF_PORT: DEFAULT_PORT,
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
        CONF_UID: "TEST",
        CONF_MODEL: "ecoMAX 850P2-C",
        CONF_PRODUCT_TYPE: ProductType.ECOMAX_P,
        CONF_PRODUCT_ID: 4,
        CONF_SOFTWARE: {
            "module_a": "6.10.32.K1",
            "module_b": None,
            "module_c": None,
            "ecolambda": "0.8.0",
            "ecoster": None,
            "panel": "6.30.36",
        },
        CONF_SUB_DEVICES: ["water_heater"],
    }


@pytest.mark.usefixtures("water_heater")
async def test_form_serial(
    hass: HomeAssistant, ecomax_p: EcoMAX, serial_user_input: dict[str, Any]
) -> None:
    """Test that we get the serial form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    # Get the serial connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "serial"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Catch connection error.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        side_effect=ConnectionFailedError,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], serial_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {CONF_BASE: "cannot_connect"}

    # Catch connection timeout.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        side_effect=TimeoutError,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], serial_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {CONF_BASE: "timeout_connect"}

    # Catch unknown exception.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        side_effect=Exception,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], serial_user_input
        )
        await hass.async_block_till_done()

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=SerialConnection)
    mock_connection.device.return_value.__aenter__ = AsyncMock(return_value=ecomax_p)
    mock_connection.device.return_value.__aexit__ = AsyncMock()

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], serial_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Discover connected modules.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    await hass.async_block_till_done()
    assert result4["type"] is FlowResultType.SHOW_PROGRESS
    assert result4["step_id"] == "discover"

    # Finish the config flow.
    result5 = await hass.config_entries.flow.async_configure(result4["flow_id"])
    assert result5["type"] is FlowResultType.CREATE_ENTRY
    assert result5["title"] == "ecoMAX 850P2-C"
    assert result5["data"] == {
        CONF_DEVICE: DEFAULT_DEVICE,
        CONF_BAUDRATE: DEFAULT_BAUDRATE,
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
        CONF_UID: "TEST",
        CONF_MODEL: "ecoMAX 850P2-C",
        CONF_PRODUCT_TYPE: ProductType.ECOMAX_P,
        CONF_PRODUCT_ID: 4,
        CONF_SOFTWARE: {
            "module_a": "6.10.32.K1",
            "module_b": None,
            "module_c": None,
            "ecolambda": "0.8.0",
            "ecoster": None,
            "panel": "6.30.36",
        },
        CONF_SUB_DEVICES: ["water_heater"],
    }


async def test_abort_device_not_found(
    hass: HomeAssistant, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the device not found message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.device.return_value.__aenter__ = AsyncMock(side_effect=TimeoutError)
    mock_connection.device.return_value.__aexit__ = AsyncMock()

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Fail with device not found.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "no_devices_found"


async def test_abort_unsupported_product(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the unsupported product message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.device.return_value.__aenter__ = AsyncMock(return_value=ecomax_p)
    mock_connection.device.return_value.__aexit__ = AsyncMock()

    # Identify the device.
    unknown_device_type = 2
    await ecomax_p.dispatch(
        "product", replace(ecomax_p.data["product"], type=unknown_device_type)
    )
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Fail with unsupported device.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "unsupported_product"


async def test_abort_discovery_failed(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the discovery failure message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.device.return_value.__aenter__ = AsyncMock(return_value=ecomax_p)
    mock_connection.device.return_value.__aexit__ = AsyncMock()

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Discover connected modules.
    with patch("pyplumio.devices.ecomax.EcoMAX.get", side_effect=TimeoutError):
        result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
        await hass.async_block_till_done()

    assert result4["type"] is FlowResultType.SHOW_PROGRESS
    assert result4["step_id"] == "discover"

    # Fail with module discovery failure.
    result5 = await hass.config_entries.flow.async_configure(result4["flow_id"])
    assert result5["type"] is FlowResultType.ABORT
    assert result5["reason"] == "discovery_failed"


async def test_abort_already_configured(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the device already configured message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.device.return_value.__aenter__ = AsyncMock(return_value=ecomax_p)
    mock_connection.device.return_value.__aexit__ = AsyncMock()

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Fail with device already configured.
    mock_config_entry = Mock(spec=config_entries.ConfigEntry)
    product = cast(ProductInfo, ecomax_p.get_nowait("product"))
    mock_config_entry.unique_id = product.uid
    mock_config_entry.source = config_entries.SOURCE_USER
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entry_for_domain_unique_id",
        return_value=mock_config_entry,
    ):
        result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])

    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "already_configured"


COMMON_TYPE_MENU_OPTIONS: Final = [
    "add_sensor",
    "add_binary_sensor",
    "add_number",
    "add_switch",
]


async def setup_options_flow(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> ConfigFlowResult:
    """Initialize the options flow for a config entry."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    return result


async def test_abort_config_entry_not_ready(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test abort when config ready is not ready."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entry_not_ready"


@pytest.mark.parametrize(
    (
        "source_device",
        "expected_types",
        "platform",
        "user_input",
        "expected_data",
        "expected_errors",
    ),
    (
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.BINARY_SENSOR,
            {
                CONF_NAME: "Custom binary sensor",
                CONF_KEY: "custom_binary_sensor",
                CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
            },
            {
                "custom_binary_sensor": {
                    CONF_NAME: "Custom binary sensor",
                    CONF_KEY: "custom_binary_sensor",
                    CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
                    CONF_SOURCE_DEVICE: "ecomax",
                }
            },
            None,
        ),
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                CONF_UPDATE_INTERVAL: 10,
            },
            {
                "custom_sensor": {
                    CONF_NAME: "Custom sensor",
                    CONF_KEY: "custom_sensor",
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                    CONF_SOURCE_DEVICE: "ecomax",
                    CONF_UPDATE_INTERVAL: 10,
                }
            },
            None,
        ),
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                CONF_UPDATE_INTERVAL: 10,
            },
            {},
            {
                CONF_UNIT_OF_MEASUREMENT: (
                    "'L' is not a valid unit for device class "
                    "'temperature'; expected one of 'K', '°C', '°F'"
                )
            },
        ),
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfPower.WATT,
                CONF_DEVICE_CLASS: SensorDeviceClass.POWER,
                CONF_STATE_CLASS: SensorStateClass.TOTAL,
                CONF_UPDATE_INTERVAL: 10,
            },
            {},
            {
                CONF_STATE_CLASS: (
                    "'total' is not a valid state class for device class 'power'; "
                    "expected 'measurement'"
                )
            },
        ),
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.NUMBER,
            {
                CONF_NAME: "Custom number",
                CONF_KEY: "custom_number",
                CONF_MODE: NumberMode.BOX,
                CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                CONF_DEVICE_CLASS: NumberDeviceClass.TEMPERATURE,
            },
            {
                "custom_number": {
                    CONF_NAME: "Custom number",
                    CONF_KEY: "custom_number",
                    CONF_MODE: NumberMode.BOX,
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: NumberDeviceClass.TEMPERATURE,
                    CONF_SOURCE_DEVICE: "ecomax",
                    CONF_STEP: 1,
                }
            },
            None,
        ),
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.NUMBER,
            {
                CONF_NAME: "Custom number",
                CONF_KEY: "custom_number",
                CONF_MODE: NumberMode.BOX,
                CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                CONF_DEVICE_CLASS: NumberDeviceClass.TEMPERATURE,
            },
            {},
            {
                CONF_UNIT_OF_MEASUREMENT: (
                    "'L' is not a valid unit for device class "
                    "'temperature'; expected one of 'K', '°C', '°F'"
                )
            },
        ),
        (
            "ecomax",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SWITCH,
            {
                CONF_NAME: "Custom switch",
                CONF_KEY: "custom_switch",
            },
            {
                "custom_switch": {
                    CONF_NAME: "Custom switch",
                    CONF_KEY: "custom_switch",
                    CONF_SOURCE_DEVICE: "ecomax",
                }
            },
            None,
        ),
        (
            "mixer_0",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom mixer sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                CONF_UPDATE_INTERVAL: 15,
            },
            {
                "custom_sensor": {
                    CONF_NAME: "Custom mixer sensor",
                    CONF_KEY: "custom_sensor",
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                    CONF_SOURCE_DEVICE: "mixer_0",
                    CONF_UPDATE_INTERVAL: 15,
                }
            },
            None,
        ),
        (
            "mixer_0",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom mixer sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                CONF_DEVICE_CLASS: SensorDeviceClass.BATTERY,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                CONF_UPDATE_INTERVAL: 15,
            },
            {},
            {
                CONF_UNIT_OF_MEASUREMENT: (
                    "'L' is not a valid unit for device class 'battery'; expected '%'"
                )
            },
        ),
        (
            "mixer_0",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom mixer sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                CONF_DEVICE_CLASS: SensorDeviceClass.WATER,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                CONF_UPDATE_INTERVAL: 15,
            },
            {},
            {
                CONF_STATE_CLASS: (
                    "'measurement' is not a valid state class for device class "
                    "'water'; expected one of 'total', 'total_increasing'"
                )
            },
        ),
        (
            "thermostat_0",
            COMMON_TYPE_MENU_OPTIONS,
            Platform.SENSOR,
            {
                CONF_NAME: "Custom thermostat sensor",
                CONF_KEY: "custom_sensor",
                CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                CONF_UPDATE_INTERVAL: 20,
            },
            {
                "custom_sensor": {
                    CONF_NAME: "Custom thermostat sensor",
                    CONF_KEY: "custom_sensor",
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                    CONF_SOURCE_DEVICE: "thermostat_0",
                    CONF_UPDATE_INTERVAL: 20,
                }
            },
            None,
        ),
        (
            ATTR_REGDATA,
            ["add_sensor", "add_binary_sensor"],
            Platform.BINARY_SENSOR,
            {
                CONF_NAME: "Custom regdata binary",
                CONF_KEY: "1538",
                CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
            },
            {
                "1538": {
                    CONF_NAME: "Custom regdata binary",
                    CONF_KEY: "1538",
                    CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
                    CONF_SOURCE_DEVICE: ATTR_REGDATA,
                }
            },
            None,
        ),
        (
            ATTR_REGDATA,
            ["add_sensor", "add_binary_sensor"],
            Platform.SENSOR,
            {
                CONF_NAME: "Custom regdata sensor",
                CONF_KEY: "1792",
                CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
            },
            {
                "1792": {
                    CONF_NAME: "Custom regdata sensor",
                    CONF_KEY: "1792",
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                    CONF_UPDATE_INTERVAL: 10,
                    CONF_SOURCE_DEVICE: ATTR_REGDATA,
                }
            },
            None,
        ),
    ),
    ids=[
        "ecoMAX binary sensor",
        "ecoMAX sensor",
        "ecoMAX sensor with invalid unit",
        "ecoMAX sensor with invalid state class",
        "ecoMAX number",
        "ecoMAX number with invalid unit",
        "ecoMAX switch",
        "mixer sensor",
        "mixer sensor with invalid unit",
        "mixer sensor with invalid state class",
        "thermostat sensor",
        "regdata binary sensor",
        "regdata sensor",
    ],
)
@pytest.mark.usefixtures(
    "connection", "ecomax_860p3_o", "mixers", "thermostats", "custom_fields"
)
async def test_add_entity(
    source_device: str,
    expected_types: list[str],
    platform: Platform,
    user_input: dict[str, Any],
    expected_data: dict[Platform, Any],
    expected_errors: dict[str, str] | None,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test adding an entity to an existing config entry."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Get the add entity form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "add_entity"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Get the entity type menu.
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {CONF_SOURCE_DEVICE: source_device}
    )
    assert result3["type"] is FlowResultType.MENU
    assert result3["step_id"] == "entity_type"
    assert result3["menu_options"] == expected_types

    # Get the entity details form.
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input={"next_step_id": f"add_{platform}"}
    )
    assert result4["type"] is FlowResultType.FORM
    assert result4["step_id"] == "entity_details"

    # Add the entity.
    result5 = await hass.config_entries.options.async_configure(
        result4["flow_id"], user_input
    )
    if expected_errors:
        assert result5["type"] is FlowResultType.FORM
        assert result5["errors"] == expected_errors
    else:
        assert result5["type"] is FlowResultType.CREATE_ENTRY
        assert result5["data"] == {ATTR_ENTITIES: {platform: expected_data}}


@pytest.mark.usefixtures("ecomax_860p3_o", "mixers")
async def test_add_entity_with_disconnected_mixer(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry, connection
) -> None:
    """Test adding an entity when mixer is disconnected after device selection."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Get the add entity form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "add_entity"}
    )

    # Get the entity type menu.
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {CONF_SOURCE_DEVICE: "mixer_1"}
    )

    del connection.device.data["mixers"][1]

    # Expect error on getting the entity details form.
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.config_entries.options.async_configure(
            result3["flow_id"], user_input={"next_step_id": "add_binary_sensor"}
        )

    assert exc_info.value.translation_key == "device_disconnected"
    assert exc_info.value.translation_placeholders == {"device": "mixer 1"}


@pytest.mark.usefixtures("ecomax_860p3_o", "custom_fields")
async def test_add_entity_with_missing_number(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry, connection
) -> None:
    """Test adding an entity when mixer is disconnected after device selection."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Get the add entity form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "add_entity"}
    )

    # Get the entity type menu.
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {CONF_SOURCE_DEVICE: "ecomax"}
    )

    # Get the entity details form.
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input={"next_step_id": "add_number"}
    )

    ecomax_data = dict(connection.device.data)
    del ecomax_data["custom_number"]

    # Expect error on adding the entity if selected number is missing.
    with (
        patch("pyplumio.devices.ecomax.EcoMAX.data", ecomax_data),
        pytest.raises(HomeAssistantError) as exc_info,
    ):
        await hass.config_entries.options.async_configure(
            result4["flow_id"],
            {
                CONF_NAME: "Custom number",
                CONF_KEY: "custom_number",
                CONF_MODE: NumberMode.BOX,
                CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                CONF_DEVICE_CLASS: NumberDeviceClass.TEMPERATURE,
            },
        )

    assert exc_info.value.translation_key == "entity_not_found"
    assert exc_info.value.translation_placeholders == {
        "entity": "custom_number",
        "device": "ecomax",
    }


@pytest.mark.parametrize("key", ("heating_pump", "custom_binary_sensor"))
@pytest.mark.usefixtures("connection", "ecomax_860p3_o", "custom_fields")
async def test_add_entity_with_colliding_key(
    key: str, hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry
) -> None:
    """Test raising an error on key collision."""
    await setup_config_entry(
        {
            ATTR_ENTITIES: {
                Platform.BINARY_SENSOR: {
                    "custom_binary_sensor": {
                        CONF_NAME: "Custom binary sensor",
                        CONF_KEY: "custom_binary_sensor",
                        CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
                        CONF_SOURCE_DEVICE: "ecomax",
                    }
                }
            }
        }
    )
    result = await setup_options_flow(hass, config_entry)

    # Get the add entity form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "add_entity"}
    )

    # Get the entity type menu.
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {CONF_SOURCE_DEVICE: "ecomax"}
    )

    # Get the entity details form.
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input={"next_step_id": "add_binary_sensor"}
    )

    # Expect error on adding the entity if key is colliding.
    with pytest.raises(InvalidData) as exc_info:
        await hass.config_entries.options.async_configure(
            result4["flow_id"],
            {
                CONF_NAME: "Colliding key",
                CONF_KEY: key,
                CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
            },
        )

    assert exc_info.value.path == ["key"]


@pytest.mark.usefixtures("connection", "ecomax_base")
async def test_abort_no_entities_to_add(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test aborting add entity when there are no entities to add."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Get the add entity form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "add_entity"}
    )

    # Get the entity type menu.
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {CONF_SOURCE_DEVICE: "ecomax"}
    )

    # Get the entity details form.
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input={"next_step_id": "add_binary_sensor"}
    )
    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "no_entities_to_add"


@pytest.mark.parametrize(
    ("platform", "entity_details", "user_input", "expected_data"),
    (
        (
            Platform.BINARY_SENSOR,
            {
                "custom_binary_sensor": {
                    CONF_NAME: "Custom binary sensor",
                    CONF_KEY: "custom_binary_sensor",
                    CONF_SOURCE_DEVICE: "ecomax",
                    CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
                }
            },
            {
                CONF_NAME: "Custom binary sensor 2",
                CONF_KEY: "custom_binary_sensor2",
                CONF_DEVICE_CLASS: BinarySensorDeviceClass.PROBLEM,
            },
            {
                "custom_binary_sensor2": {
                    CONF_NAME: "Custom binary sensor 2",
                    CONF_KEY: "custom_binary_sensor2",
                    CONF_SOURCE_DEVICE: "ecomax",
                    CONF_DEVICE_CLASS: BinarySensorDeviceClass.PROBLEM,
                }
            },
        ),
        (
            Platform.SENSOR,
            {
                "1792": {
                    CONF_NAME: "Custom regdata sensor",
                    CONF_KEY: "1792",
                    CONF_SOURCE_DEVICE: ATTR_REGDATA,
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                    CONF_STATE_CLASS: SensorStateClass.MEASUREMENT,
                    CONF_UPDATE_INTERVAL: 10,
                }
            },
            {
                CONF_NAME: "Custom regdata sensor 2",
                CONF_KEY: "1792",
                CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                CONF_DEVICE_CLASS: SensorDeviceClass.VOLUME,
                CONF_STATE_CLASS: SensorStateClass.TOTAL,
                CONF_UPDATE_INTERVAL: 15,
            },
            {
                "1792": {
                    CONF_NAME: "Custom regdata sensor 2",
                    CONF_KEY: "1792",
                    CONF_SOURCE_DEVICE: ATTR_REGDATA,
                    CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                    CONF_DEVICE_CLASS: SensorDeviceClass.VOLUME,
                    CONF_STATE_CLASS: SensorStateClass.TOTAL,
                    CONF_UPDATE_INTERVAL: 15,
                }
            },
        ),
        (
            Platform.NUMBER,
            {
                "custom_number": {
                    CONF_NAME: "Custom mixer number",
                    CONF_KEY: "custom_number",
                    CONF_MODE: NumberMode.BOX,
                    CONF_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
                    CONF_DEVICE_CLASS: NumberDeviceClass.TEMPERATURE,
                    CONF_SOURCE_DEVICE: "mixer_0",
                    CONF_STEP: 1,
                }
            },
            {
                CONF_NAME: "Custom mixer number 2",
                CONF_KEY: "custom_number",
                CONF_MODE: NumberMode.AUTO,
                CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                CONF_DEVICE_CLASS: NumberDeviceClass.VOLUME,
            },
            {
                "custom_number": {
                    CONF_NAME: "Custom mixer number 2",
                    CONF_KEY: "custom_number",
                    CONF_MODE: NumberMode.AUTO,
                    CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
                    CONF_DEVICE_CLASS: NumberDeviceClass.VOLUME,
                    CONF_SOURCE_DEVICE: "mixer_0",
                    CONF_STEP: 1,
                }
            },
        ),
        (
            Platform.SWITCH,
            {
                "custom_switch": {
                    CONF_NAME: "Custom thermostat switch",
                    CONF_KEY: "custom_switch",
                    CONF_SOURCE_DEVICE: "thermostat_0",
                }
            },
            {
                CONF_NAME: "Custom thermostat switch 2",
                CONF_KEY: "custom_switch",
            },
            {
                "custom_switch": {
                    CONF_NAME: "Custom thermostat switch 2",
                    CONF_KEY: "custom_switch",
                    CONF_SOURCE_DEVICE: "thermostat_0",
                }
            },
        ),
    ),
    ids=["ecoMAX binary sensor", "regdata sensor", "mixer number", "thermostat switch"],
)
@pytest.mark.usefixtures(
    "connection", "ecomax_860p3_o", "mixers", "thermostats", "custom_fields"
)
async def test_edit_entity(
    platform: Platform,
    entity_details: dict[str, Any],
    user_input: dict[str, Any],
    expected_data: dict[str, Any],
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test editing an existing entity in a config entry."""
    await setup_config_entry({ATTR_ENTITIES: {platform: entity_details}})
    result = await setup_options_flow(hass, config_entry)

    # Get the entity select form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "edit_entity"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Get the entity details form.
    result3 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"entity_id": f"{platform}.{entity_details.popitem()[0]}"},
    )
    assert result3["type"] is FlowResultType.FORM
    assert result3["step_id"] == "entity_details"

    # Edit the entity.
    result5 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input=user_input
    )
    assert result5["type"] is FlowResultType.CREATE_ENTRY
    assert result5["data"] == {ATTR_ENTITIES: {platform: expected_data}}


@pytest.mark.usefixtures("connection", "ecomax_860p3_o", "custom_fields")
async def test_edit_entity_with_invalid_source_device(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry
) -> None:
    """Test editing an existing entity in a config entry."""
    await setup_config_entry(
        {
            ATTR_ENTITIES: {
                Platform.BINARY_SENSOR: {
                    "custom_binary_sensor": {
                        CONF_NAME: "Custom binary sensor",
                        CONF_KEY: "custom_binary_sensor",
                        CONF_SOURCE_DEVICE: "unsupported_device",
                        CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
                    }
                }
            }
        }
    )
    result = await setup_options_flow(hass, config_entry)

    # Get the entity select form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "edit_entity"}
    )

    # Expect error on getting the entity details form.
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.config_entries.options.async_configure(
            result2["flow_id"],
            user_input={"entity_id": "binary_sensor.custom_binary_sensor"},
        )

    assert exc_info.value.translation_key == "unsupported_device"
    assert exc_info.value.translation_placeholders == {"device": "unsupported_device"}


@pytest.mark.usefixtures("connection", "bypass_async_setup_entry")
async def test_abort_no_entities_to_edit(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test aborting edit entity when there are no entities to edit."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Get the entity select form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "edit_entity"}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_entities_to_edit_or_remove"


@pytest.mark.usefixtures("connection", "ecomax_860p3_o")
async def test_remove_entity(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_config_entry
) -> None:
    """Test removing an existing entity from the config entry."""
    custom_sensor = {
        "custom_sensor": {
            CONF_NAME: "Custom sensor",
            CONF_KEY: "custom_sensor",
            CONF_SOURCE_DEVICE: "ecomax",
            CONF_UNIT_OF_MEASUREMENT: UnitOfVolume.LITERS,
            CONF_DEVICE_CLASS: SensorDeviceClass.VOLUME,
            CONF_STATE_CLASS: SensorStateClass.TOTAL,
            CONF_UPDATE_INTERVAL: 10,
        }
    }

    await setup_config_entry(
        {
            ATTR_ENTITIES: {
                Platform.BINARY_SENSOR: {
                    "custom_binary_sensor": {
                        CONF_NAME: "Custom binary sensor",
                        CONF_KEY: "custom_binary_sensor",
                        CONF_SOURCE_DEVICE: "ecomax",
                        CONF_DEVICE_CLASS: BinarySensorDeviceClass.RUNNING,
                    }
                },
                Platform.SENSOR: custom_sensor,
            }
        }
    )
    await hass.async_block_till_done()
    result = await setup_options_flow(hass, config_entry)

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get("binary_sensor.ecomax_custom_binary_sensor")

    # Get the entity select form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "remove_entity"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] is None

    # Remove the entity.
    result3 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"entity_id": "binary_sensor.custom_binary_sensor"},
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"] == {
        ATTR_ENTITIES: {Platform.BINARY_SENSOR: {}, Platform.SENSOR: custom_sensor}
    }

    assert not entity_registry.async_get("binary_sensor.ecomax_custom_binary_sensor")


@pytest.mark.usefixtures("connection", "bypass_async_setup_entry")
async def test_abort_no_entities_to_remove(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_config_entry,
) -> None:
    """Test aborting remove entity when there are no entities to remove."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Get the entity select form.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "remove_entity"}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_entities_to_edit_or_remove"


@patch("custom_components.plum_ecomax.config_flow.async_get_sub_devices")
@patch("homeassistant.config_entries.ConfigEntries.async_update_entry")
@patch("homeassistant.config_entries.ConfigEntries.async_reload")
@pytest.mark.usefixtures("connection", "ecomax_860p3_o", "bypass_async_setup_entry")
async def test_rediscover_devices(
    mock_async_reload,
    mock_async_update_entry,
    mock_async_get_sub_devices,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_config_entry,
    connection,
) -> None:
    """Test rediscovering devices for the config entry."""
    await setup_config_entry()
    result = await setup_options_flow(hass, config_entry)

    # Rediscover devices.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "rediscover_devices"}
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY

    mock_async_get_sub_devices.assert_awaited_once_with(connection.device)
    expected_data = dict(config_entry.data)
    expected_data[CONF_SUB_DEVICES] = mock_async_get_sub_devices.return_value
    mock_async_update_entry.assert_has_calls([call(config_entry, data=expected_data)])
    mock_async_reload.assert_awaited_once_with(config_entry.entry_id)
