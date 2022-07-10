"""Test Plum ecoMAX setup process."""

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.plum_ecomax import async_setup_entry, async_unload_entry
from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DOMAIN


@patch("custom_components.plum_ecomax.EcomaxConnection.async_setup")
@patch.object(EcomaxConnection, "close", create=True, new_callable=AsyncMock)
async def test_setup_and_unload_entry(
    mock_close, mock_async_setup, hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test setup and unload of config entry."""
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(hass.data[DOMAIN][config_entry.entry_id], EcomaxConnection)
    mock_async_setup.assert_awaited_once()

    # Unload entry and verify that it is no longer present in hass data.
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]
    mock_close.assert_awaited_once()
    mock_close.reset_mock()

    # Test when already unloaded.
    assert await async_unload_entry(hass, config_entry)
    mock_close.assert_not_awaited()
