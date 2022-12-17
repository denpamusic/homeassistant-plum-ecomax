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
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.product_info import ProductType

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


BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
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
        value_fn=lambda x: len(x) > 0,
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


MIXER_BINARY_SENSOR_TYPES: tuple[EcomaxBinarySensorEntityDescription, ...] = (
    EcomaxBinarySensorEntityDescription(
        key="mixer_pump",
        name="Mixer pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda x: x,
    ),
)


class MixerBinarySensor(MixerEntity, EcomaxBinarySensor):
    """Represents mixer binary sensor platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxBinarySensorEntityDescription,
        mixer_number: int,
    ):
        """Initialize ecoMAX sensor object."""
        self.mixer_number = mixer_number
        super().__init__(connection, description)


def setup_ecomax_p(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
):
    """Setup binary sensor platform for ecoMAX P series controllers."""
    return async_add_entities(
        [
            *entities,
            *[
                EcomaxBinarySensor(connection, description)
                for description in ECOMAX_P_BINARY_SENSOR_TYPES
            ],
        ],
        False,
    )


def setup_ecomax_i(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
):
    """Setup binary sensor platform for ecoMAX I series controllers."""
    return async_add_entities(
        [
            *entities,
            *[
                EcomaxBinarySensor(connection, description)
                for description in ECOMAX_I_BINARY_SENSOR_TYPES
            ],
        ],
        False,
    )


def get_mixer_entities(
    connection: EcomaxConnection,
    binary_sensor_types: tuple[EcomaxBinarySensorEntityDescription, ...],
) -> list[MixerEntity]:
    """Setup mixers binary sensor platform."""
    entities: list[MixerEntity] = []
    for mixer in connection.device.data.get(ATTR_MIXERS, []):
        entities.extend(
            [
                MixerBinarySensor(connection, description, mixer.mixer_number)
                for description in binary_sensor_types
            ]
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[EcomaxEntity] = [
        *[
            EcomaxBinarySensor(connection, description)
            for description in BINARY_SENSOR_TYPES
        ],
        *get_mixer_entities(connection, MIXER_BINARY_SENSOR_TYPES),
    ]

    if connection.product_type == ProductType.ECOMAX_P:
        return setup_ecomax_p(connection, entities, async_add_entities)

    if connection.product_type == ProductType.ECOMAX_I:
        return setup_ecomax_i(connection, entities, async_add_entities)

    _LOGGER.error(
        "Couldn't setup platform due to unknown controller model '%s'", connection.model
    )
    return False
