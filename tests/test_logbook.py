"""Test Plum ecoMAX logbook events."""

from typing import Final
from unittest.mock import Mock

from homeassistant.components.logbook.const import (
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.const import ATTR_CODE, ATTR_NAME
from homeassistant.core import Event, HomeAssistant
from pyplumio.const import AlertType

from custom_components.plum_ecomax.const import (
    ATTR_FROM,
    ATTR_TO,
    DOMAIN,
    EVENT_PLUM_ECOMAX_ALERT,
)
from custom_components.plum_ecomax.logbook import async_describe_events

DATE_FROM: Final = "2012-12-12 00:00:00"
DATE_TO: Final = "2012-12-12 01:00:00"


async def test_logbook(hass: HomeAssistant) -> None:
    """Test logbook events."""
    mock_async_describe_event = Mock()
    async_describe_events(hass, mock_async_describe_event)
    mock_async_describe_event.assert_called_once()
    args = mock_async_describe_event.call_args[0]
    assert args[0] == DOMAIN
    assert args[1] == EVENT_PLUM_ECOMAX_ALERT
    callback = args[2]
    mock_event = Mock(spec=Event)
    mock_event.data = {
        ATTR_NAME: "ecoMAX",
        ATTR_CODE: AlertType.POWER_LOSS,
        ATTR_FROM: DATE_FROM,
        ATTR_TO: DATE_TO,
    }
    result = callback(mock_event)
    assert result == {
        LOGBOOK_ENTRY_NAME: "ecoMAX",
        LOGBOOK_ENTRY_MESSAGE: f"encountered power loss from {DATE_FROM} to {DATE_TO}",
    }

    # Test with no end date.
    mock_event.data = {
        ATTR_NAME: "ecoMAX",
        ATTR_CODE: AlertType.POWER_LOSS,
        ATTR_FROM: DATE_FROM,
    }
    result = callback(mock_event)
    assert result == {
        LOGBOOK_ENTRY_NAME: "ecoMAX",
        LOGBOOK_ENTRY_MESSAGE: f"encountered power loss from {DATE_FROM}",
    }
