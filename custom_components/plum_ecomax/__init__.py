"""The Plum ecoMAX integration."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import asdict, dataclass
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_CODE,
    ATTR_DEVICE_ID,
    ATTR_NAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from pyplumio.filters import custom, delta
from pyplumio.structures.alerts import ATTR_ALERTS, Alert

from .connection import (
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
)
from .const import (
    ATTR_FROM,
    ATTR_MODULES,
    ATTR_PRODUCT,
    ATTR_TO,
    CONF_CAPABILITIES,
    CONF_CONNECTION_TYPE,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    DEFAULT_CONNECTION_TYPE,
    DOMAIN,
    EVENT_PLUM_ECOMAX_ALERT,
    DeviceType,
)
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WATER_HEATER,
]

DATE_STR_FORMAT: Final = "%Y-%m-%d %H:%M:%S"

_LOGGER = logging.getLogger(__name__)

type PlumEcomaxConfigEntry = ConfigEntry["PlumEcomaxData"]


@dataclass
class PlumEcomaxData:
    """Represents and Plum ecoMAX config data."""

    connection: EcomaxConnection


async def async_setup_entry(hass: HomeAssistant, entry: PlumEcomaxConfigEntry) -> bool:
    """Set up the Plum ecoMAX from a config entry."""
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE)
    handler = await async_get_connection_handler(connection_type, hass, entry.data)
    connection = EcomaxConnection(hass, entry, connection=handler)

    try:
        await connection.async_setup()
    except TimeoutError as e:
        await connection.async_close()
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="connection_timeout",
            translation_placeholders={"connection": connection.name},
        ) from e

    entry.runtime_data = PlumEcomaxData(connection)
    async_setup_services(hass, connection)
    async_setup_events(hass, connection)

    async def _async_close_connection(event: Event | None = None) -> None:
        """Close the ecoMAX connection on HA Stop."""
        await connection.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_close_connection)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def async_setup_events(hass: HomeAssistant, connection: EcomaxConnection) -> bool:
    """Set up the ecoMAX events."""

    device_registry = dr.async_get(hass)

    async def _async_dispatch_alert_events(alerts: list[Alert]) -> None:
        """Handle ecoMAX alert events."""
        if (
            device := device_registry.async_get_device({(DOMAIN, connection.uid)})
        ) is None:
            _LOGGER.error("Device not found. uid: %s", connection.uid)
            return

        for alert in alerts:
            event_data = {
                ATTR_NAME: connection.name,
                ATTR_DEVICE_ID: device.id,
                ATTR_CODE: alert.code,
                ATTR_FROM: alert.from_dt.strftime(DATE_STR_FORMAT),
            }
            if alert.to_dt is not None:
                event_data[ATTR_TO] = alert.to_dt.strftime(DATE_STR_FORMAT)

            hass.bus.async_fire(EVENT_PLUM_ECOMAX_ALERT, event_data)

    connection.device.subscribe(
        ATTR_ALERTS, custom(delta(_async_dispatch_alert_events), bool)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PlumEcomaxConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.connection.close()

    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant, entry: PlumEcomaxConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    connection_type = entry.data.get(CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE)
    handler = await async_get_connection_handler(connection_type, hass, entry.data)
    connection = EcomaxConnection(hass, entry, connection=handler)
    await connection.connect()
    data = dict(entry.data)

    try:
        device = await connection.get(DeviceType.ECOMAX, timeout=DEFAULT_TIMEOUT)

        if entry.version < 3:
            # Product type was added in version 3.
            product = await device.get(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_PRODUCT_TYPE] = product.type

        if entry.version < 5:
            # Capabilities got removed to sub_devices in version 5.
            with suppress(KeyError):
                del data[CONF_CAPABILITIES]

            data[CONF_SUB_DEVICES] = await async_get_sub_devices(device)

        if entry.version < 7:
            # Product id were added in version 7.
            product = await device.get(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_PRODUCT_ID] = product.id

        if entry.version < 8:
            # Software versions were added in version 8.
            modules = await device.get(ATTR_MODULES, timeout=DEFAULT_TIMEOUT)
            data[CONF_SOFTWARE] = asdict(modules)

        hass.config_entries.async_update_entry(entry, data=data, version=8)
        await connection.close()
        _LOGGER.info("Migration to version %s successful", entry.version)
    except TimeoutError:
        _LOGGER.error("Migration failed, device has failed to respond in time")
        return False

    return True
