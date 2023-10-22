"""Platform for number integration."""
from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
import logging
from typing import Any, Literal

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
from .const import ALL, CALORIFIC_KWH_KG, DOMAIN, MODULE_A
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True, slots=True)
class EcomaxNumberEntityDescription(NumberEntityDescription):
    """Describes ecoMAX number entity."""

    product_types: set[ProductType]
    filter_fn: Callable[[Any], Any] = on_change
    mode: NumberMode = NumberMode.AUTO
    module: str = MODULE_A


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        translation_key="target_heating_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        translation_key="min_heating_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        translation_key="max_heating_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        translation_key="grate_mode_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        translation_key="fuzzy_logic_min_power",
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        translation_key="fuzzy_logic_max_power",
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxNumberEntityDescription(
        key="fuel_calorific_value_kwh_kg",
        translation_key="fuel_calorific_value",
        mode=NumberMode.BOX,
        native_step=0.1,
        native_unit_of_measurement=CALORIFIC_KWH_KG,
        product_types={ProductType.ECOMAX_P},
    ),
)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Represents ecoMAX number platform."""

    _attr_mode: NumberMode = NumberMode.AUTO
    _attr_native_max_value: float | None
    _attr_native_min_value: float | None
    _attr_native_value: float | None
    _connection: EcomaxConnection
    entity_description: EntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxNumberEntityDescription
    ):
        self._attr_available = False
        self._attr_mode = description.mode
        self._attr_native_max_value = None
        self._attr_native_min_value = None
        self._attr_native_value = None
        self._connection = connection
        self.entity_description = description

    async def async_set_native_value(self, value: float) -> None:
        """Update current value."""
        self.device.set_nowait(self.entity_description.key, value)
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_update(self, value: Parameter) -> None:
        """Update entity state."""
        self._attr_native_value = value.value
        self._attr_native_min_value = value.min_value
        self._attr_native_max_value = value.max_value
        self.async_write_ha_state()


@dataclass(slots=True)
class EcomaxMixerNumberEntityDescription(EcomaxNumberEntityDescription):
    """Describes ecoMAX mixer entity."""

    indexes: set[int] | Literal["all"] = ALL


MIXER_NUMBER_TYPES: tuple[EcomaxMixerNumberEntityDescription, ...] = (
    EcomaxMixerNumberEntityDescription(
        key="mixer_target_temp",
        translation_key="target_mixer_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxMixerNumberEntityDescription(
        key="min_target_temp",
        translation_key="min_mixer_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxMixerNumberEntityDescription(
        key="max_target_temp",
        translation_key="max_mixer_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxMixerNumberEntityDescription(
        key="mixer_target_temp",
        translation_key="target_circuit_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
    ),
    EcomaxMixerNumberEntityDescription(
        key="min_target_temp",
        translation_key="min_circuit_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        indexes={2, 3},
    ),
    EcomaxMixerNumberEntityDescription(
        key="max_target_temp",
        translation_key="max_circuit_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        indexes={2, 3},
    ),
    EcomaxMixerNumberEntityDescription(
        key="day_target_temp",
        translation_key="day_target_circuit_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        indexes={2, 3},
    ),
    EcomaxMixerNumberEntityDescription(
        key="night_target_temp",
        translation_key="night_target_circuit_temp",
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        indexes={2, 3},
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


def get_by_index(
    index, descriptions: Iterable[EcomaxMixerNumberEntityDescription]
) -> Generator[EcomaxMixerNumberEntityDescription, None, None]:
    """Filter mixer/circuit descriptions by indexes."""
    index += 1
    for description in descriptions:
        if description.indexes == ALL or index in description.indexes:
            yield description


def async_setup_ecomax_numbers(connection: EcomaxConnection) -> list[EcomaxNumber]:
    """Setup ecoMAX numbers."""
    return [
        EcomaxNumber(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, NUMBER_TYPES),
        )
    ]


def async_setup_mixer_numbers(connection: EcomaxConnection) -> list[MixerNumber]:
    """Setup mixer numbers."""
    entities: list[MixerNumber] = []

    for index in connection.device.mixers.keys():
        entities.extend(
            MixerNumber(connection, description, index)
            for description in get_by_index(
                index,
                get_by_modules(
                    connection.device.modules,
                    get_by_product_type(connection.product_type, MIXER_NUMBER_TYPES),
                ),
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the number platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of number platform...")

    entities: list[EcomaxNumber] = []

    # Add ecoMAX numbers.
    entities.extend(async_setup_ecomax_numbers(connection))

    # Add mixer/circuit numbers.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities.extend(async_setup_mixer_numbers(connection))

    return async_add_entities(entities)
