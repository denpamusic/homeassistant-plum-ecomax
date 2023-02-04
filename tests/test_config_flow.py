"""Test Plum ecoMAX config flow."""
import asyncio
from unittest.mock import Mock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_BASE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo
import pytest

from custom_components.plum_ecomax.const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_SERIAL,
    DOMAIN,
)


@pytest.fixture(name="async_setup_entry")
def fixture_async_setup_entry():
    """Mock async setup entry."""
    with patch(
        "custom_components.plum_ecomax.async_setup_entry",
        return_value=True,
    ) as async_setup_entry:
        yield async_setup_entry


async def test_form_tcp(
    hass: HomeAssistant,
    config_data: dict[str, str],
    device_data: dict[str, str],
    async_setup_entry,
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    product = Mock(spec=ProductInfo)
    product.configure_mock(
        type=device_data.get(CONF_PRODUCT_TYPE),
        model=device_data.get(CONF_MODEL),
        uid=device_data.get(CONF_UID),
    )
    modules = Mock(spec=ConnectedModules)
    modules.configure_mock(module_a=device_data.get(CONF_SOFTWARE))
    sub_devices = device_data.get(CONF_SUB_DEVICES)

    # Set up attribute values for the connection.
    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        return_value=(config_data.get(CONF_HOST), product, modules, sub_devices),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], config_data
        )
        await hass.async_block_till_done()

    # Check if entry with provided data was created and that
    # setup_entry method was called only once.
    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == config_data.get(CONF_HOST)
    assert result2["data"] == (config_data | device_data)
    async_setup_entry.assert_called_once()


async def test_form_serial(
    hass: HomeAssistant,
    config_data: dict[str, str],
    device_data: dict[str, str],
    async_setup_entry,
) -> None:
    """Test we get the form for serial connection type."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    product = Mock(spec=ProductInfo)
    product.configure_mock(
        type=device_data.get(CONF_PRODUCT_TYPE),
        model=device_data.get(CONF_MODEL),
        uid=device_data.get(CONF_UID),
    )
    modules = Mock(spec=ConnectedModules)
    modules.configure_mock(module_a=device_data.get(CONF_SOFTWARE))
    sub_devices = device_data.get(CONF_SUB_DEVICES)
    config_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_SERIAL

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        return_value=(config_data[CONF_DEVICE], product, modules, sub_devices),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            config_data,
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == config_data.get(CONF_DEVICE)
    assert result2["data"] == dict(config_data | device_data)
    async_setup_entry.assert_called_once()


async def test_form_cannot_connect(
    hass: HomeAssistant, config_data: dict[str, str]
) -> None:
    """Test that we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        side_effect=ConnectionFailedError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], config_data
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {CONF_BASE: "cannot_connect"}


async def test_form_timeout_connect(
    hass: HomeAssistant, config_data: dict[str, str]
) -> None:
    """Test that we handle timeout error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        side_effect=asyncio.TimeoutError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], config_data
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {CONF_BASE: "timeout_connect"}


async def test_form_unsupported_product(
    hass: HomeAssistant, config_data: dict[str, str]
) -> None:
    """Test that we handle unsupported device error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        return_value=(None, Mock(autospec=ProductInfo), None, None),
    ), patch(
        "custom_components.plum_ecomax.config_flow.ProductType",
        side_effect=ValueError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], config_data
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {CONF_BASE: "unsupported_product"}


async def test_form_unknown_error(
    hass: HomeAssistant, config_data: dict[str, str]
) -> None:
    """Test that we handle unknown error error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.plum_ecomax.config_flow.async_check_connection",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], config_data
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {CONF_BASE: "unknown"}
