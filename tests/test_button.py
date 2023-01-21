"""Test Plum ecoMAX button."""

from unittest.mock import Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.button import EcomaxButton, async_setup_entry
from custom_components.plum_ecomax.const import DOMAIN


async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and press button entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args, _ = async_add_entities.call_args
    buttons = args[0]
    button = buttons.pop(0)

    assert isinstance(button, EcomaxButton)

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection"
        + ".async_update_sub_devices"
    ) as mock_async_update_device_capabilities:
        await button.async_press()

    mock_async_update_device_capabilities.assert_awaited_once()
    assert button.entity_registry_enabled_default

    with pytest.raises(NotImplementedError):
        await button.async_update(1)

    with pytest.raises(NotImplementedError), patch.object(
        button.entity_description, "press_fn", "nonexistent"
    ):
        await button.async_press()

    connection = hass.data[DOMAIN][config_entry.entry_id]
    with patch.object(button.entity_description, "press_fn", "test_fn"), patch.object(
        connection, "test_fn", Mock(), create=True
    ) as mock_func:
        await button.async_press()

    mock_func.assert_called_once()
