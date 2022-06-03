"""Platform for binary sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .entity import EcomaxEntity


@dataclass
class EcomaxBinarySensorEntityAdditionalKeys:
    """Additional keys for ecoMAX binary sensor entity description."""

    value_fn: Callable[[Any], Optional[bool]]


@dataclass
class EcomaxBinarySensorEntityDescription(
    BinarySensorEntityDescription, EcomaxBinarySensorEntityAdditionalKeys
):
    """Describes ecoMAX binary sensor entity."""


BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="heating_pump",
        name="Heating Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="water_heater_pump",
        name="Water Heater Pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan",
        name="Fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="lighter",
        name="Lighter",
        icon="mdi:fire",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
)


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Representation of ecoMAX binary sensor."""

    def __init__(self, connection, description: EcomaxBinarySensorEntityDescription):
        self._connection = connection
        self.entity_description = description
        self._attr_is_on = None

    async def async_update(self) -> None:
        """Retrieve latest state."""
        value = getattr(self._connection.ecomax, self.entity_description.key, None)
        self._attr_is_on = (
            self.entity_description.value_fn(value) if value is not None else value
        )
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform.

    Keyword arguments:
        hass -- instance of Home Assistant core
        config_entry -- instance of config entry
        async_add_entities -- callback to add entities to hass
    """
    connection = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            EcomaxBinarySensor(connection, description)
            for description in BINARY_SENSOR_TYPES
        ],
        False,
    )
