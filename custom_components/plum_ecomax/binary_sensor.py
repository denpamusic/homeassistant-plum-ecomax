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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.const import ProductType
from pyplumio.devices import Mixer
from pyplumio.helpers.filters import on_change

from .connection import EcomaxConnection
from .const import ATTR_MIXERS, DOMAIN
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxBinarySensorEntityAdditionalKeys:
    """Additional keys for ecoMAX binary sensor entity description."""

    value_fn: Callable[[Any], Any]


@dataclass
class EcomaxBinarySensorEntityDescription(
    BinarySensorEntityDescription, EcomaxBinarySensorEntityAdditionalKeys
):
    """Describes ecoMAX binary sensor entity."""

    filter_fn: Callable[[Any], Any] = on_change


COMMON_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="heating_pump",
        name="Heating pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="water_heater_pump",
        name="Water heater pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="ciculation_pump",
        name="Circulation pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="pending_alerts",
        name="Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x > 0,
    ),
)

ECOMAX_P_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="fan",
        name="Fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan2_exhaust",
        name="Exhaust fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="feeder",
        name="Feeder",
        icon="mdi:screw-lag",
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

ECOMAX_I_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="solar_pump",
        name="Solar pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fireplace_pump",
        name="Fireplace pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
)

BINARY_SENSOR_TYPES: dict[
    ProductType, tuple[EcomaxBinarySensorEntityDescription, ...]
] = {
    ProductType.ECOMAX_P: COMMON_BINARY_SENSOR_TYPES + ECOMAX_P_BINARY_SENSOR_TYPES,
    ProductType.ECOMAX_I: COMMON_BINARY_SENSOR_TYPES + ECOMAX_I_BINARY_SENSOR_TYPES,
}


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Representation of ecoMAX binary sensor."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxBinarySensorEntityDescription,
    ):
        self._connection = connection
        self.entity_description = description
        self._attr_available = False
        self._attr_is_on = None

    async def async_update(self, value) -> None:
        """Retrieve latest state."""
        self._attr_is_on = self.entity_description.value_fn(value)
        self.async_write_ha_state()


ECOMAX_P_MIXER_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="pump",
        name="Mixer pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
)

ECOMAX_I_MIXER_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="pump",
        name="Circuit pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
)


MIXER_BINARY_SENSOR_TYPES: dict[
    ProductType, tuple[EcomaxBinarySensorEntityDescription, ...]
] = {
    ProductType.ECOMAX_P: ECOMAX_P_MIXER_BINARY_SENSOR_TYPES,
    ProductType.ECOMAX_I: ECOMAX_I_MIXER_BINARY_SENSOR_TYPES,
}


class MixerBinarySensor(MixerEntity, EcomaxBinarySensor):
    """Represents mixer binary sensor platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxBinarySensorEntityDescription,
        index: int,
    ):
        """Initialize mixer binary sensor object."""
        self.index = index
        super().__init__(connection, description)


async def async_setup_mixer_entities(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup mixers binary sensor platform."""
    mixers: dict[int, Mixer] = connection.device.data[ATTR_MIXERS]
    for index in mixers.keys():
        entities.extend(
            MixerBinarySensor(connection, description, index)
            for description in MIXER_BINARY_SENSOR_TYPES[connection.product_type]
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the binary sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of binary sensor platform...")

    async def _async_setup_entities(product_type: ProductType) -> list[EcomaxEntity]:
        """Add binary sensor entities."""
        entities: list[EcomaxEntity] = []

        # Add ecoMAX binary sensors.
        entities.extend(
            EcomaxBinarySensor(connection, description)
            for description in BINARY_SENSOR_TYPES[product_type]
        )

        # Add mixer/circuit binary sensors.
        if connection.has_mixers and await connection.setup_mixers():
            await async_setup_mixer_entities(connection, entities)

        return entities

    return async_add_entities(await _async_setup_entities(connection.product_type))
