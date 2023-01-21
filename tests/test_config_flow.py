"""Test Plum ecoMAX config flow."""
import asyncio
from unittest.mock import Mock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM
from pyplumio.exceptions import ConnectionFailedError

from custom_components.plum_ecomax.const import (
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
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

    title = MOCK_CONFIG_DATA[CONF_HOST]
    product = Mock()
    product.uid = MOCK_DEVICE_DATA[CONF_UID]
    product.model = MOCK_DEVICE_DATA[CONF_MODEL]
    product.type = MOCK_DEVICE_DATA[CONF_PRODUCT_TYPE]
    modules = Mock()
    modules.module_a = MOCK_DEVICE_DATA[CONF_SOFTWARE]
    sub_devices = MOCK_DEVICE_DATA[CONF_SUB_DEVICES]

    # Set up attribute values for EcomaxTcpConnection.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        return_value=(title, product, modules, sub_devices),
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

    title = MOCK_CONFIG_DATA_SERIAL[CONF_DEVICE]
    product = Mock()
    product.uid = MOCK_DEVICE_DATA[CONF_UID]
    product.model = MOCK_DEVICE_DATA[CONF_MODEL]
    product.type = MOCK_DEVICE_DATA[CONF_PRODUCT_TYPE]
    modules = Mock()
    modules.module_a = MOCK_DEVICE_DATA[CONF_SOFTWARE]
    sub_devices = MOCK_DEVICE_DATA[CONF_SUB_DEVICES]

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        return_value=(title, product, modules, sub_devices),
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
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        side_effect=ConnectionFailedError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA,
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_timeout_connect(hass: HomeAssistant) -> None:
    """Test we handle unsupported device error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        side_effect=asyncio.TimeoutError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA,
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "timeout_connect"}


async def test_form_unknown_error(hass: HomeAssistant) -> None:
    """Test we handle unknown error error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG_DATA,
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}
