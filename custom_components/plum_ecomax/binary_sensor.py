"""Platform for binary sensor integration."""
from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
import logging
from typing import Any, Literal

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
from pyplumio.structures.modules import ConnectedModules

from .connection import EcomaxConnection
from .const import ALL, DOMAIN, MODULE_A
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True, slots=True)
class EcomaxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an ecoMAX binary sensor."""

    value_fn: Callable[[Any], Any]
    product_types: set[ProductType] | Literal["all"] = ALL
    always_available: bool = False
    filter_fn: Callable[[Any], Any] = on_change
    icon_off: str | None = None
    module: str = MODULE_A


BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="heating_pump",
        translation_key="heating_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="water_heater_pump",
        translation_key="water_heater_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="circulation_pump",
        translation_key="circulation_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="pending_alerts",
        translation_key="alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x > 0,
    ),
    EcomaxBinarySensorEntityDescription(
        key="connected",
        translation_key="connection_status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x,
        always_available=True,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan",
        translation_key="fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        icon_off="mdi:fan-off",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan2_exhaust",
        translation_key="exhaust_fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        icon_off="mdi:fan-off",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="feeder",
        translation_key="feeder",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:screw-lag",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="lighter",
        translation_key="lighter",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fire",
        icon_off="mdi:fire-off",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="solar_pump",
        translation_key="solar_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        product_types={ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fireplace_pump",
        translation_key="fireplace_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        product_types={ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
)


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Represents an ecoMAX binary sensor."""

    entity_description: EcomaxBinarySensorEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxBinarySensorEntityDescription,
    ):
        """Initialize a new ecoMAX binary sensor."""
        self.connection = connection
        self.entity_description = description

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        self._attr_is_on = self.entity_description.value_fn(value)
        self.async_write_ha_state()

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        return (
            self.entity_description.icon_off
            if self.entity_description.icon_off is not None and not self.is_on
            else self.entity_description.icon
        )


@dataclass(kw_only=True, frozen=True, slots=True)
class MixerBinarySensorEntityDescription(EcomaxBinarySensorEntityDescription):
    """Describes a mixer binary sensor."""


MIXER_BINARY_SENSOR_TYPES: tuple[MixerBinarySensorEntityDescription, ...] = (
    MixerBinarySensorEntityDescription(
        key="pump",
        translation_key="mixer_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        product_types={ProductType.ECOMAX_P},
        value_fn=lambda x: x,
    ),
    MixerBinarySensorEntityDescription(
        key="pump",
        translation_key="circuit_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        icon_off="mdi:pump-off",
        product_types={ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
)


class MixerBinarySensor(MixerEntity, EcomaxBinarySensor):
    """Represents a mixer binary sensor."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: MixerBinarySensorEntityDescription,
        index: int,
    ):
        """Initialize a new mixer binary sensor."""
        self.index = index
        super().__init__(connection, description)


def get_by_product_type(
    product_type: ProductType,
    descriptions: Iterable[EcomaxBinarySensorEntityDescription],
) -> Generator[EcomaxBinarySensorEntityDescription, None, None]:
    """Filter descriptions by the product type."""
    for description in descriptions:
        if (
            description.product_types == ALL
            or product_type in description.product_types
        ):
            yield description


def get_by_modules(
    connected_modules: ConnectedModules,
    descriptions: Iterable[EcomaxBinarySensorEntityDescription],
) -> Generator[EcomaxBinarySensorEntityDescription, None, None]:
    """Filter descriptions by connected modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def async_setup_ecomax_binary_sensors(
    connection: EcomaxConnection,
) -> list[EcomaxBinarySensor]:
    """Set up the ecoMAX binary sensors."""
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
    """Set up the mixer binary sensors."""
    entities: list[MixerBinarySensor] = []

    for index in connection.device.mixers:
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

    entities: list[EcomaxBinarySensor] = []

    # Add ecoMAX binary sensors.
    entities.extend(async_setup_ecomax_binary_sensors(connection))

    # Add mixer/circuit binary sensors.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities.extend(async_setup_mixer_binary_sensors(connection))

    async_add_entities(entities)
    return True
