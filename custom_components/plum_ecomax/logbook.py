"""Describe Plum ecoMAX logbook events."""
from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.logbook.const import (
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from custom_components.plum_ecomax.const import (
    ATTR_CODE,
    ATTR_FROM,
    ATTR_TO,
    DOMAIN,
    EVENT_PLUM_ECOMAX_ALERT,
)


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe logbook events."""

    @callback
    def async_describe_alert_event(event: Event) -> dict[str, str]:
        """Describe ecomax logbook event."""
        alert_code = event.data[ATTR_CODE]
        start_time = event.data[ATTR_FROM]
        time_string = f"was generated at {start_time}"
        if ATTR_TO in event.data:
            end_time = event.data[ATTR_TO]
            time_string += f" and resolved at {end_time}"

        return {
            LOGBOOK_ENTRY_NAME: "ecoMAX",
            LOGBOOK_ENTRY_MESSAGE: f"The alert with code '{alert_code}' {time_string}",
        }

    async_describe_event(DOMAIN, EVENT_PLUM_ECOMAX_ALERT, async_describe_alert_event)
