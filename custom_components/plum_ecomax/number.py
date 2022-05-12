"""Platform for number integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


@dataclass
class EcomaxNumberEntityDescription(NumberEntityDescription):
    """Describes ecoMAX number entity."""


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_set_temp",
        name="Heating Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate Mode Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_set_temp",
        name="Minimum Heating Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_set_temp",
        name="Maximum Heating Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        name="Fuzzy Logic Minimum Power",
        unit_of_measurement=PERCENTAGE,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        name="Fuzzy Logic Maximum Power",
        unit_of_measurement=PERCENTAGE,
        step=1,
    ),
)


class EcomaxNumber(NumberEntity):
    """Representation of ecoMAX number."""

    def __init__(self, connection, description: EcomaxNumberEntityDescription):
        self._connection = connection
        self.entity_description = description
        self._attr_name = f"{connection.name} {description.name}"
        self._attr_unique_id = f"{connection.uid}-{description.key}"
        self._attr_should_poll = False
        self._attr_value = None
        self._attr_min_value = None
        self._attr_max_value = None

    async def async_update(self) -> None:
        """Update entity state."""
        parameter = getattr(self._connection.ecomax, self.entity_description.key, None)

        if parameter is None:
            self._attr_value = None
            self._attr_min_value = None
            self._attr_max_value = None
        else:
            self._attr_value = parameter.value
            self._attr_min_value = parameter.min_
            self._attr_max_value = parameter.max_

        self.async_write_ha_state()

    async def async_set_value(self, value: float) -> None:
        """Update the current value.

        Keyword arguments:
            value -- new number value
        """
        setattr(self._connection.ecomax, self.entity_description.key, int(value))
        self.async_write_ha_state()

    @property
    def device_info(self) -> Optional[dict]:
        """Return device info."""
        return self._connection.device_info

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Indicate if the entity should be enabled when first added."""
        return self.entity_description.key in self._connection.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform.

    Keyword arguments:
        hass -- instance of Home Assistant core
        config_entry -- instance of config entry
        async_add_entities -- callback to add entities to hass
    """
    connection = hass.data[DOMAIN][config_entry.entry_id]
    connection.add_entities(
        [EcomaxNumber(connection, description) for description in NUMBER_TYPES],
        async_add_entities,
    )
