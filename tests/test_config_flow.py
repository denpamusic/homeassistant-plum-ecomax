"""Test the Plum ecoMAX config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM
from pyplumio.exceptions import ConnectionFailedError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import (
    CONF_CAPABILITIES,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_SOFTWARE,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)

from .const import MOCK_CONFIG_DATA, MOCK_CONFIG_DATA_SERIAL, MOCK_DEVICE_DATA


async def test_form_tcp(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    # Set up attribute values for EcomaxTcpConnection.
    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.check",
        return_value=True,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.model",
        MOCK_DEVICE_DATA[CONF_MODEL],
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.uid",
        MOCK_DEVICE_DATA[CONF_UID],
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.software",
        MOCK_DEVICE_DATA[CONF_SOFTWARE],
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.capabilities",
        MOCK_DEVICE_DATA[CONF_CAPABILITIES],
    ), patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        # Run configure.
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA,
        )
        await hass.async_block_till_done()

    # Check if entry with provided data was created and that
    # setup_entry method was called only once.
    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == MOCK_CONFIG_DATA[CONF_HOST]
    assert result2["data"] == dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA)
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_serial(hass: HomeAssistant) -> None:
    """Test we get the form for serial connection type."""
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
        MOCK_DEVICE_DATA[CONF_MODEL],
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.uid",
        MOCK_DEVICE_DATA[CONF_UID],
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.software",
        MOCK_DEVICE_DATA[CONF_SOFTWARE],
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxSerialConnection.capabilities",
        MOCK_DEVICE_DATA[CONF_CAPABILITIES],
    ), patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA_SERIAL,
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == MOCK_CONFIG_DATA_SERIAL[CONF_DEVICE]
    assert result2["data"] == dict(MOCK_CONFIG_DATA_SERIAL, **MOCK_DEVICE_DATA)
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.check",
        side_effect=ConnectionFailedError,
    ), patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.close",
        return_value=True,
    ) as mock_connection_close:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA,
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}
    mock_connection_close.assert_called_once()


async def test_form_unknown_error(hass: HomeAssistant) -> None:
    """Test we handle unknown error error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.EcomaxTcpConnection.check",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA,
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}


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
            MOCK_CONFIG_DATA,
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unsupported_device"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test an options flow."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA),
        entry_id="test",
    )
    config_entry.add_to_hass(hass)

    # Check that we've got options form.
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    # Send test data via form.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_UPDATE_INTERVAL: 20},
    )

    # Check that entry with new options was created.
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == config_entry.title

    assert config_entry.options == {CONF_UPDATE_INTERVAL: 20}
