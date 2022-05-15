"""Test the Plum ecoMAX config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM

from custom_components.plum_ecomax.config_flow import CannotConnect, UnsupportedDevice
from custom_components.plum_ecomax.const import (
    CONF_CAPABILITIES,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SOFTWARE,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DOMAIN,
)

TEST_MODEL = "ecoMAX 350P2"
TEST_UID = "D251PAKR3GCPZ1K8G05G0"
TEST_SOFTWARE = "1.13.5.Z1"
TEST_CAPABILITIES = ["fuel_burned", "heating_temp"]
TEST_HOST = "example.com"
TEST_PORT = 8899
TEST_DEVICE = "/dev/ttyUSB0"


async def test_form_tcp(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.check",
        return_value=True,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.model",
        TEST_MODEL,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.uid",
        TEST_UID,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.software",
        TEST_SOFTWARE,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.capabilities",
        TEST_CAPABILITIES,
    ), patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_UPDATE_INTERVAL: 10,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == TEST_HOST
    assert result2["data"] == {
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
        CONF_DEVICE: TEST_DEVICE,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
        CONF_UPDATE_INTERVAL: 10,
        CONF_UID: TEST_UID,
        CONF_MODEL: TEST_MODEL,
        CONF_SOFTWARE: TEST_SOFTWARE,
        CONF_CAPABILITIES: TEST_CAPABILITIES,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_serial(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.check",
        return_value=True,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.model",
        TEST_MODEL,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.uid",
        TEST_UID,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.software",
        TEST_SOFTWARE,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.capabilities",
        TEST_CAPABILITIES,
    ), patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
                CONF_DEVICE: TEST_DEVICE,
                CONF_UPDATE_INTERVAL: 10,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == TEST_DEVICE
    assert result2["data"] == {
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
        CONF_DEVICE: TEST_DEVICE,
        CONF_PORT: TEST_PORT,
        CONF_UPDATE_INTERVAL: 10,
        CONF_UID: TEST_UID,
        CONF_MODEL: TEST_MODEL,
        CONF_SOFTWARE: TEST_SOFTWARE,
        CONF_CAPABILITIES: TEST_CAPABILITIES,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.check",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_UPDATE_INTERVAL: 10,
            },
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unsupported_device(hass: HomeAssistant) -> None:
    """Test we handle unsupported device error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.check",
        return_value=True,
    ), patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_UPDATE_INTERVAL: 10,
            },
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unsupported_device"}
