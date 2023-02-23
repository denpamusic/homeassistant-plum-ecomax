"""Platform for binary sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Generator, Iterable

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
from pyplumio.filters import on_change

from .connection import EcomaxConnection
from .const import DOMAIN, MODULE_A
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxBinarySensorEntityAdditionalKeys:
    """Additional keys for ecoMAX binary sensor entity description."""

    product_types: set[ProductType]
    value_fn: Callable[[Any], Any]


@dataclass
class EcomaxBinarySensorEntityDescription(
    BinarySensorEntityDescription, EcomaxBinarySensorEntityAdditionalKeys
):
    """Describes ecoMAX binary sensor entity."""

    always_available: bool = False
    filter_fn: Callable[[Any], Any] = on_change
    module: str = MODULE_A


BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="heating_pump",
        name="Heating pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="water_heater_pump",
        name="Water heater pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="circulation_pump",
        name="Circulation pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="pending_alerts",
        name="Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x > 0,
    ),
    EcomaxBinarySensorEntityDescription(
        key="connected",
        name="Connection status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        always_available=True,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan",
        name="Fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan2_exhaust",
        name="Exhaust fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="feeder",
        name="Feeder",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:screw-lag",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="lighter",
        name="Lighter",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fire",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="solar_pump",
        name="Solar pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fireplace_pump",
        name="Fireplace pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_I},
        value_fn=lambda x: x,
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
        self._attr_available = False
        self._attr_is_on = None

    async def async_update(self, value) -> None:
        """Update entity state."""
        self._attr_is_on = self.entity_description.value_fn(value)
        self.async_write_ha_state()


@dataclass
class MixerBinarySensorEntityDescription(EcomaxBinarySensorEntityDescription):
    """Describes ecoMAX mixer binary sensor entity."""


MIXER_BINARY_SENSOR_TYPES: tuple[MixerBinarySensorEntityDescription, ...] = (
    MixerBinarySensorEntityDescription(
        key="pump",
        name="Mixer pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    MixerBinarySensorEntityDescription(
        key="pump",
        name="Circuit pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        product_types={ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
)


class MixerBinarySensor(MixerEntity, EcomaxBinarySensor):
    """Represents mixer binary sensor platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: MixerBinarySensorEntityDescription,
        index: int,
    ):
        """Initialize mixer binary sensor object."""
        self.index = index
        super().__init__(connection, description)


def get_by_product_type(
    product_type: ProductType,
    descriptions: Iterable[EcomaxBinarySensorEntityDescription],
) -> Generator[EcomaxBinarySensorEntityDescription, None, None]:
    """Filter descriptions by product type."""
    for description in descriptions:
        if product_type in description.product_types:
            yield description


def get_by_modules(
    connected_modules, descriptions: Iterable[EcomaxBinarySensorEntityDescription]
) -> Generator[EcomaxBinarySensorEntityDescription, None, None]:
    """Filter descriptions by modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def async_setup_ecomax_binary_sensors(
    connection: EcomaxConnection,
) -> list[EcomaxBinarySensor]:
    """Setup ecoMAX binary sensors."""
    return [
        EcomaxBinarySensor(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, BINARY_SENSOR_TYPES),
        )
    ]


def async_setup_mixer_binary_sensors(
    connection: EcomaxConnection,
) -> list[MixerBinarySensor]:
    """Setup mixer binary sensors."""
    entities: list[MixerBinarySensor] = []

    for index in connection.device.mixers.keys():
        entities.extend(
            MixerBinarySensor(connection, description, index)
            for description in get_by_modules(
                connection.device.modules,
                get_by_product_type(connection.product_type, MIXER_BINARY_SENSOR_TYPES),
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the binary sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of binary sensor platform...")

    entities: list[EcomaxEntity] = []

    # Add ecoMAX binary sensors.
    entities.extend(async_setup_ecomax_binary_sensors(connection))

    # Add mixer/circuit binary sensors.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities.extend(async_setup_mixer_binary_sensors(connection))

    return async_add_entities(entities)
