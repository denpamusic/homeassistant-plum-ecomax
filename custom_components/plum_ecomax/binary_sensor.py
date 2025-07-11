"""Platform for binary sensor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .const import DeviceType
from .entity import (
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    RegdataEntity,
    async_get_by_modules,
    async_get_by_product_type,
    async_get_custom_entities,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxBinarySensorEntityDescription(
    EcomaxEntityDescription, BinarySensorEntityDescription
):
    """Describes an ecoMAX binary sensor."""

    value_fn: Callable[[Any], Any]


BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="heating_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="heating_pump",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="water_heater_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="water_heater_pump",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="circulation_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="circulation_pump",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="pending_alerts",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="alert",
        value_fn=lambda x: x > 0,
    ),
    EcomaxBinarySensorEntityDescription(
        key="connected",
        always_available=True,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="connection_status",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_P},
        translation_key="fan",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fan2_exhaust",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_P},
        translation_key="exhaust_fan",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="feeder",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_P},
        translation_key="feeder",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="lighter",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_P},
        translation_key="lighter",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="solar_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_I},
        translation_key="solar_pump",
        value_fn=lambda x: x,
    ),
    EcomaxBinarySensorEntityDescription(
        key="fireplace_pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_I},
        translation_key="fireplace_pump",
        value_fn=lambda x: x,
    ),
)


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Represents an ecoMAX binary sensor."""

    entity_description: EcomaxBinarySensorEntityDescription

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        self._attr_is_on = self.entity_description.value_fn(value)
        self.async_write_ha_state()


@dataclass(frozen=True, kw_only=True)
class MixerBinarySensorEntityDescription(EcomaxBinarySensorEntityDescription):
    """Describes a mixer binary sensor."""


MIXER_BINARY_SENSOR_TYPES: tuple[MixerBinarySensorEntityDescription, ...] = (
    MixerBinarySensorEntityDescription(
        key="pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_P},
        translation_key="mixer_pump",
        value_fn=lambda x: x,
    ),
    MixerBinarySensorEntityDescription(
        key="pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        product_types={ProductType.ECOMAX_I},
        translation_key="circuit_pump",
        value_fn=lambda x: x,
    ),
)


class MixerBinarySensor(MixerEntity, EcomaxBinarySensor):
    """Represents a mixer binary sensor."""

    entity_description: MixerBinarySensorEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: MixerBinarySensorEntityDescription,
        index: int,
    ):
        """Initialize a new mixer binary sensor."""
        self.index = index
        super().__init__(connection, description)


@dataclass(frozen=True, kw_only=True)
class RegdataBinarySensorEntityDescription(EcomaxBinarySensorEntityDescription):
    """Describes a regulator data binary sensor."""


class RegdataBinarySensor(RegdataEntity, EcomaxBinarySensor):
    """Represents a regulator data binary sensor."""

    async def async_update(self, regdata: dict[int, Any]) -> None:
        """Update entity state."""
        self._attr_is_on = self.entity_description.value_fn(
            regdata.get(self._regdata_key, None)
        )
        self.async_write_ha_state()


@callback
def async_setup_ecomax_binary_sensors(
    connection: EcomaxConnection,
) -> list[EcomaxBinarySensor]:
    """Set up the ecoMAX binary sensors."""
    return [
        EcomaxBinarySensor(connection, description)
        for description in async_get_by_modules(
            connection.device.modules,
            async_get_by_product_type(connection.product_type, BINARY_SENSOR_TYPES),
        )
    ]


@callback
def async_setup_custom_ecomax_binary_sensors(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[EcomaxBinarySensor]:
    """Set up the custom ecoMAX binary sensors."""
    description_partial = partial(
        EcomaxBinarySensorEntityDescription, value_fn=lambda x: x
    )
    return [
        EcomaxBinarySensor(connection, description)
        for description in async_get_custom_entities(
            platform=Platform.BINARY_SENSOR,
            source_device=DeviceType.ECOMAX,
            config_entry=config_entry,
            description_factory=description_partial,
        )
    ]


@callback
def async_setup_custom_regdata_binary_sensors(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[RegdataBinarySensor]:
    """Set up the custom regulator data binary sensors."""
    description_partial = partial(
        RegdataBinarySensorEntityDescription, value_fn=lambda x: x
    )
    return [
        RegdataBinarySensor(connection, description)
        for description in async_get_custom_entities(
            platform=Platform.BINARY_SENSOR,
            source_device="regdata",
            config_entry=config_entry,
            description_factory=description_partial,
        )
    ]


@callback
def async_setup_mixer_binary_sensors(
    connection: EcomaxConnection,
) -> list[MixerBinarySensor]:
    """Set up the mixer binary sensors."""
    return [
        MixerBinarySensor(connection, description, index)
        for index in connection.device.mixers
        for description in async_get_by_modules(
            connection.device.modules,
            async_get_by_product_type(
                connection.product_type, MIXER_BINARY_SENSOR_TYPES
            ),
        )
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the binary sensor platform."""
    _LOGGER.debug("Starting setup of binary sensor platform...")

    connection = entry.runtime_data.connection
    entities = async_setup_ecomax_binary_sensors(connection)

    # Add custom ecoMAX binary sensors.
    entities += async_setup_custom_ecomax_binary_sensors(connection, entry)

    # Add custom regulator data binary sensors.
    if (
        regdata_entities := async_setup_custom_regdata_binary_sensors(connection, entry)
    ) and await connection.async_setup_regdata():
        entities += regdata_entities

    # Add mixer/circuit binary sensors.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities += async_setup_mixer_binary_sensors(connection)

    async_add_entities(entities)
    return True
