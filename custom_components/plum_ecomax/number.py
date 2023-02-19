"""Platform for number integration."""
from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
import logging
from typing import Any, Optional

from homeassistant.components.number import (
    EntityDescription,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.const import ProductType
from pyplumio.filters import on_change
from pyplumio.helpers.parameter import Parameter

from .connection import EcomaxConnection
from .const import CALORIFIC_KWH_KG, DOMAIN, MODULE_A
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxNumberEntityAdditionalKeys:
    """Additional keys for ecoMAX number entity description."""

    product_types: set[ProductType]


@dataclass
class EcomaxNumberEntityDescription(
    NumberEntityDescription, EcomaxNumberEntityAdditionalKeys
):
    """Describes ecoMAX number entity."""

    filter_fn: Callable[[Any], Any] = on_change
    mode: NumberMode = NumberMode.AUTO
    min_value_key: Optional[str] = None
    max_value_key: Optional[str] = None
    module: str = MODULE_A


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        name="Target heating temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        name="Minimum heating temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        name="Maximum heating temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate mode temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        name="Fuzzy logic minimum power",
        native_unit_of_measurement=PERCENTAGE,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        name="Fuzzy logic maximum power",
        native_unit_of_measurement=PERCENTAGE,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="fuel_calorific_value_kwh_kg",
        name="Fuel calorific value",
        native_unit_of_measurement=CALORIFIC_KWH_KG,
        native_step=0.1,
        mode=NumberMode.BOX,
        product_types={ProductType.ECOMAX_P},
    ),
)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Represents ecoMAX number platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_native_value: float | None
    _attr_native_min_value: float | None
    _attr_native_max_value: float | None
    _attr_mode: NumberMode = NumberMode.AUTO

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxNumberEntityDescription
    ):
        self._connection = connection
        self.entity_description = description
        self._attr_available = False
        self._attr_native_value = None
        self._attr_native_min_value = None
        self._attr_native_max_value = None
        self._attr_mode = description.mode

    async def async_set_min_value(self, value: Parameter) -> None:
        """Update minimum bound for target temperature."""
        self._attr_native_min_value = value.value
        self.async_write_ha_state()

    async def async_set_max_value(self, value: Parameter) -> None:
        """Update maximum bound for target temperature."""
        self._attr_native_max_value = value.value
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update current value."""
        self.device.set_nowait(self.entity_description.key, value)
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Called when an entity has their entity_id assigned."""
        if self.entity_description.min_value_key is not None:
            self.device.subscribe(
                self.entity_description.min_value_key,
                on_change(self.async_set_min_value),
            )

        if self.entity_description.max_value_key is not None:
            self.device.subscribe(
                self.entity_description.max_value_key,
                on_change(self.async_set_max_value),
            )

        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Called when an entity is about to be removed."""
        if self.entity_description.min_value_key is not None:
            self.device.unsubscribe(
                self.entity_description.min_value_key, self.async_set_min_value
            )

        if self.entity_description.max_value_key is not None:
            self.device.unsubscribe(
                self.entity_description.max_value_key, self.async_set_max_value
            )

        await super().async_will_remove_from_hass()

    async def async_update(self, value: Parameter) -> None:
        """Update entity state."""
        self._attr_native_value = value.value
        self._attr_native_min_value = value.min_value
        self._attr_native_max_value = value.max_value
        self.async_write_ha_state()


@dataclass
class EcomaxMixerNumberEntityDescription(EcomaxNumberEntityDescription):
    """Describes ecoMAX mixer entity."""


MIXER_NUMBER_TYPES: tuple[EcomaxMixerNumberEntityDescription, ...] = (
    EcomaxMixerNumberEntityDescription(
        key="mixer_target_temp",
        name="Target mixer temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        min_value_key="min_target_temp",
        max_value_key="max_target_temp",
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxMixerNumberEntityDescription(
        key="min_target_temp",
        name="Minimum mixer temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxMixerNumberEntityDescription(
        key="max_target_temp",
        name="Maximum mixer temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxMixerNumberEntityDescription(
        key="mixer_target_temp",
        name="Target circuit temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        min_value_key="min_target_temp",
        max_value_key="max_target_temp",
        product_types={ProductType.ECOMAX_I},
    ),
    EcomaxMixerNumberEntityDescription(
        key="min_target_temp",
        name="Minimum circuit temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        product_types={ProductType.ECOMAX_I},
    ),
    EcomaxMixerNumberEntityDescription(
        key="max_target_temp",
        name="Maximum circuit temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        product_types={ProductType.ECOMAX_I},
    ),
    EcomaxMixerNumberEntityDescription(
        key="day_target_temp",
        name="Day target circuit temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        min_value_key="min_target_temp",
        max_value_key="max_target_temp",
        product_types={ProductType.ECOMAX_I},
    ),
    EcomaxMixerNumberEntityDescription(
        key="night_target_temp",
        name="Night target circuit temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        min_value_key="min_target_temp",
        max_value_key="max_target_temp",
        product_types={ProductType.ECOMAX_I},
    ),
)


class MixerNumber(MixerEntity, EcomaxNumber):
    """Represents mixer number platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxNumberEntityDescription,
        index: int,
    ):
        """Initialize mixer number object."""
        self.index = index
        super().__init__(connection, description)


def get_by_product_type(
    product_type: ProductType,
    descriptions: Iterable[EcomaxNumberEntityDescription],
) -> Generator[EcomaxNumberEntityDescription, None, None]:
    """Filter descriptions by product type."""
    for description in descriptions:
        if product_type in description.product_types:
            yield description


def get_by_modules(
    connected_modules, descriptions: Iterable[EcomaxNumberEntityDescription]
) -> Generator[EcomaxNumberEntityDescription, None, None]:
    """Filter descriptions by modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def async_setup_ecomax_numbers(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup ecoMAX numbers."""
    entities.extend(
        EcomaxNumber(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, NUMBER_TYPES),
        )
    )


def async_setup_mixer_numbers(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup mixer numbers."""
    for index in connection.device.mixers.keys():
        entities.extend(
            MixerNumber(connection, description, index)
            for description in get_by_modules(
                connection.device.modules,
                get_by_product_type(connection.product_type, MIXER_NUMBER_TYPES),
            )
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the number platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of number platform...")

    entities: list[EcomaxEntity] = []

    # Add ecoMAX numbers.
    async_setup_ecomax_numbers(connection, entities)

    # Add mixer/circuit numbers.
    if connection.has_mixers and await connection.async_setup_mixers():
        async_setup_mixer_numbers(connection, entities)

    return async_add_entities(entities)
