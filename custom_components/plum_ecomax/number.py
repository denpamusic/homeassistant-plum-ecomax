"""Platform for number integration."""
from __future__ import annotations

from collections.abc import Callable
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
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductType

from .connection import EcomaxConnection
from .const import ATTR_MIXERS, CALORIFIC_KWH_KG, DOMAIN
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxNumberEntityAdditionalKeys:
    """Additional keys for ecoMAX number entity description."""

    value_get_fn: Callable[[Any], Any]
    value_set_fn: Callable[[Any], Any]


@dataclass
class EcomaxNumberEntityDescription(
    NumberEntityDescription, EcomaxNumberEntityAdditionalKeys
):
    """Describes ecoMAX number entity."""

    filter_fn: Callable[[Any], Any] = on_change
    mode: NumberMode = NumberMode.AUTO
    min_value_key: Optional[str] = None
    max_value_key: Optional[str] = None


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = ()

ECOMAX_P_NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        name="Heating Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        name="Minimum Heating Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        name="Maximum Heating Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate Mode Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        name="Fuzzy Logic Minimum Power",
        native_unit_of_measurement=PERCENTAGE,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        name="Fuzzy Logic Maximum Power",
        native_unit_of_measurement=PERCENTAGE,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="fuel_calorific_value_kwh_kg",
        name="Fuel Calorific Value",
        native_unit_of_measurement=CALORIFIC_KWH_KG,
        native_step=0.1,
        value_get_fn=lambda x: x / 10,
        value_set_fn=lambda x: x * 10,
        mode=NumberMode.BOX,
    ),
)

ECOMAX_I_NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = ()


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
        self._attr_native_value = None
        self._attr_native_min_value = None
        self._attr_native_max_value = None
        self._attr_mode = description.mode

    async def async_set_min_value(self, value: Parameter) -> None:
        """Update minimum bound for target temperature."""
        self._attr_native_min_value = self.entity_description.value_get_fn(value.value)
        self.async_write_ha_state()

    async def async_set_max_value(self, value: Parameter) -> None:
        """Update maximum bound for target temperature."""
        self._attr_native_max_value = self.entity_description.value_get_fn(value.value)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update current value."""
        await self.device.set_value(
            self.entity_description.key,
            self.entity_description.value_set_fn(value),
            await_confirmation=False,
        )
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
        self._attr_native_value = self.entity_description.value_get_fn(value.value)
        self._attr_native_min_value = self.entity_description.value_get_fn(
            value.min_value
        )
        self._attr_native_max_value = self.entity_description.value_get_fn(
            value.max_value
        )
        self.async_write_ha_state()


MIXER_NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="mixer_target_temp",
        name="Mixer Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_mixer_target_temp",
        max_value_key="max_mixer_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_mixer_target_temp",
        name="Minimum Mixer Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_mixer_target_temp",
        name="Maximum Mixer Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
)

ECOMAX_I_MIXER_NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="day_mixer_target_temp",
        name="Day Mixer Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_mixer_target_temp",
        max_value_key="max_mixer_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="night_mixer_target_temp",
        name="Night Mixer Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_mixer_target_temp",
        max_value_key="max_mixer_target_temp",
    ),
)


class MixerNumber(MixerEntity, EcomaxNumber):
    """Represents mixer number platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxNumberEntityDescription,
        mixer_number: int,
    ):
        """Initialize ecoMAX sensor object."""
        self.mixer_number = mixer_number
        super().__init__(connection, description)


def setup_ecomax_p(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Setup number platform for ecoMAX P series controllers."""
    return async_add_entities(
        [
            *entities,
            *[
                EcomaxNumber(connection, description)
                for description in ECOMAX_P_NUMBER_TYPES
            ],
        ],
        False,
    )


def setup_ecomax_i(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Setup number platform for ecoMAX I series controllers."""
    return async_add_entities(
        [
            *entities,
            *get_mixer_entities(connection, ECOMAX_I_MIXER_NUMBER_TYPES),
            *[
                EcomaxNumber(connection, description)
                for description in ECOMAX_I_NUMBER_TYPES
            ],
        ],
        False,
    )


def get_mixer_entities(
    connection: EcomaxConnection,
    number_types: tuple[EcomaxNumberEntityDescription, ...],
) -> list[MixerEntity]:
    """Setup mixers sensor platform."""
    entities: list[MixerEntity] = []
    for mixer in connection.device.data.get(ATTR_MIXERS, []):
        entities.extend(
            MixerNumber(connection, description, mixer.mixer_number)
            for description in number_types
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the number platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[EcomaxEntity] = [
        *[EcomaxNumber(connection, description) for description in NUMBER_TYPES],
        *get_mixer_entities(connection, MIXER_NUMBER_TYPES),
    ]

    if connection.product_type == ProductType.ECOMAX_P:
        return setup_ecomax_p(connection, entities, async_add_entities)

    if connection.product_type == ProductType.ECOMAX_I:
        return setup_ecomax_i(connection, entities, async_add_entities)

    _LOGGER.error(
        "Couldn't setup platform due to unknown controller model '%s'", connection.model
    )
    return False
