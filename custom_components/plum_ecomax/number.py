"""Platform for number integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.number import (
    EntityDescription,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.parameter import Parameter

from .connection import EcomaxConnection
from .const import CALORIFIC_KWH_KG, DOMAIN
from .entity import EcomaxEntity, MixerEntity


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


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        name="Heating Target Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate Mode Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        name="Minimum Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        name="Maximum Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
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
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
        min_value_key="min_heating_target_temp",
        max_value_key="max_heating_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_mixer_target_temp",
        name="Minimum Mixer Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_mixer_target_temp",
        name="Maximum Mixer Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
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


def get_mixer_entities(connection: EcomaxConnection) -> list[MixerEntity]:
    """Setup mixers sensor platform."""
    entities: list[MixerEntity] = []

    if connection.device is not None and "mixers" in connection.device.data:
        for mixer in connection.device.data["mixers"]:
            for description in MIXER_NUMBER_TYPES:
                entities.append(MixerNumber(connection, description, mixer.index))

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the number platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    return async_add_entities(
        [
            *[EcomaxNumber(connection, description) for description in NUMBER_TYPES],
            *get_mixer_entities(connection),
        ],
        False,
    )
