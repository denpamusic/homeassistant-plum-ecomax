"""Test Plum ecoMAX config flow."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_BASE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.const import ProductType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import ConnectionFailedError
import pytest

from custom_components.plum_ecomax.const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
)


@pytest.fixture(autouse=True)
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
    assert result["type"] == FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] == FlowResultType.FORM
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

    assert result3["type"] == FlowResultType.FORM
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

    assert result3["type"] == FlowResultType.FORM
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

    assert result3["type"] == FlowResultType.FORM
    assert result3["errors"] == {CONF_BASE: "unknown"}

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.get = AsyncMock(return_value=ecomax_p)

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )

    assert result3["type"] == FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Discover connected modules.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    await hass.async_block_till_done()
    assert result4["type"] == FlowResultType.SHOW_PROGRESS
    assert result4["step_id"] == "discover"

    # Finish the config flow.
    result5 = await hass.config_entries.flow.async_configure(result4["flow_id"])
    assert result5["type"] == FlowResultType.CREATE_ENTRY
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
    assert result["type"] == FlowResultType.MENU

    # Get the serial connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "serial"}
    )
    assert result2["type"] == FlowResultType.FORM
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

    assert result3["type"] == FlowResultType.FORM
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

    assert result3["type"] == FlowResultType.FORM
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
    mock_connection.get = AsyncMock(return_value=ecomax_p)

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], serial_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Discover connected modules.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    await hass.async_block_till_done()
    assert result4["type"] == FlowResultType.SHOW_PROGRESS
    assert result4["step_id"] == "discover"

    # Finish the config flow.
    result5 = await hass.config_entries.flow.async_configure(result4["flow_id"])
    assert result5["type"] == FlowResultType.CREATE_ENTRY
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
    assert result["type"] == FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.get = AsyncMock(side_effect=TimeoutError)

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Fail with device not found.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    assert result4["type"] == FlowResultType.ABORT
    assert result4["reason"] == "no_devices_found"


async def test_abort_unsupported_device(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the unsupported device message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.get = AsyncMock(return_value=ecomax_p)

    # Identify the device.
    unknown_device_type = 2
    with (
        patch(
            "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
            return_value=mock_connection,
        ),
        patch.object(ecomax_p.data["product"], "type", unknown_device_type),
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Fail with unsupported device.
    result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
    assert result4["type"] == FlowResultType.ABORT
    assert result4["reason"] == "unsupported_device"


async def test_abort_discovery_failed(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the discovery failure message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.get = AsyncMock(return_value=ecomax_p)

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Discover connected modules.
    with patch("pyplumio.devices.ecomax.EcoMAX.get", side_effect=TimeoutError):
        result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])
        await hass.async_block_till_done()

    assert result4["type"] == FlowResultType.SHOW_PROGRESS
    assert result4["step_id"] == "discover"

    # Fail with module discovery failure.
    result5 = await hass.config_entries.flow.async_configure(result4["flow_id"])
    assert result5["type"] == FlowResultType.ABORT
    assert result5["reason"] == "discovery_failed"


async def test_abort_already_configured(
    hass: HomeAssistant, ecomax_p: EcoMAX, tcp_user_input: dict[str, Any]
) -> None:
    """Test that we get the device already configured message."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU

    # Get the TCP connection form.
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tcp"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] is None

    # Create the PyPlumIO connection mock.
    mock_connection = Mock(spec=TcpConnection)
    mock_connection.get = AsyncMock(return_value=ecomax_p)

    # Identify the device.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_get_connection_handler",
        return_value=mock_connection,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], tcp_user_input
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.SHOW_PROGRESS
    assert result3["step_id"] == "identify"

    # Fail with device already configured.
    mock_config_entry = Mock(spec=config_entries.ConfigEntry)
    mock_config_entry.unique_id = ecomax_p.get_nowait("product").uid
    mock_config_entry.source = config_entries.SOURCE_USER
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entry_for_domain_unique_id",
        return_value=mock_config_entry,
    ):
        result4 = await hass.config_entries.flow.async_configure(result3["flow_id"])

    assert result4["type"] == FlowResultType.ABORT
    assert result4["reason"] == "already_configured"
