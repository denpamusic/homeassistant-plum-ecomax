"""Test Plum ecoMAX logbook events."""


from unittest.mock import Mock

from homeassistant.components.logbook.const import (
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant

from custom_components.plum_ecomax.const import (
    ATTR_CODE,
    ATTR_FROM,
    ATTR_TO,
    DOMAIN,
    ECOMAX_ALERT_EVENT,
)
from custom_components.plum_ecomax.logbook import async_describe_events


async def test_logbook(hass: HomeAssistant) -> None:
    """Test logbook events."""
    mock_async_describe_event = Mock()
    async_describe_events(hass, mock_async_describe_event)
    mock_async_describe_event.assert_called_once()
    args, _ = mock_async_describe_event.call_args
    assert args[0] == DOMAIN
    assert args[1] == ECOMAX_ALERT_EVENT
    callback = args[2]
    mock_event = Mock(spec=Event)
    mock_event.data = {
        ATTR_CODE: 0,
        ATTR_FROM: "2012-12-12 00:00:00",
        ATTR_TO: "2012-12-12 01:00:00",
    }
    result = callback(mock_event)
    assert result == {
        LOGBOOK_ENTRY_NAME: "ecoMAX",
        LOGBOOK_ENTRY_MESSAGE: "The alert with code '0' was generated at 2012-12-12 "
        + "00:00:00 and resolved at 2012-12-12 01:00:00",
    }
