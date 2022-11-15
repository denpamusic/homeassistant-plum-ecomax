"""Platform for binary sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.helpers.filters import on_change

from .connection import EcomaxConnection
from .const import DOMAIN, ECOMAX_I, ECOMAX_P
from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ecoMAX binary sensor entity."""

    filter_fn: Callable[[Any], Any] = on_change


BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="heating_pump",
        name="Heating Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    EcomaxBinarySensorEntityDescription(
        key="water_heater_pump",
        name="Water Heater Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    EcomaxBinarySensorEntityDescription(
        key="ciculation_pump",
        name="Circulation Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)

ECOMAX_P_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="fan",
        name="Fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    EcomaxBinarySensorEntityDescription(
        key="feeder",
        name="Feeder",
        icon="mdi:screw-lag",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    EcomaxBinarySensorEntityDescription(
        key="lighter",
        name="Lighter",
        icon="mdi:fire",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)

ECOMAX_I_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="solar_pump",
        name="Solar Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fireplace_pump",
        name="Fireplace Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Representation of ecoMAX binary sensor."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxBinarySensorEntityDescription,
    ):
        self._connection = connection
        self.entity_description = description
        self._attr_is_on = None

    async def async_update(self, value) -> None:
        """Retrieve latest state."""
        self._attr_is_on = value
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]

    if ECOMAX_P.search(connection.model):
        return async_add_entities(
            [
                *[
                    EcomaxBinarySensor(connection, description)
                    for description in BINARY_SENSOR_TYPES
                ],
                *[
                    EcomaxBinarySensor(connection, description)
                    for description in ECOMAX_P_BINARY_SENSOR_TYPES
                ],
            ],
            False,
        )

    if ECOMAX_I.search(connection.model):
        return async_add_entities(
            [
                *[
                    EcomaxBinarySensor(connection, description)
                    for description in BINARY_SENSOR_TYPES
                ],
                *[
                    EcomaxBinarySensor(connection, description)
                    for description in ECOMAX_I_BINARY_SENSOR_TYPES
                ],
            ],
            False,
        )

    _LOGGER.error(
        "Couldn't setup platform due to unknown controller model '%s'", connection.model
    )
    return False
