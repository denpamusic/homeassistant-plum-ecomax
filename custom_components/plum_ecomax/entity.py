"""Contains base entity classes."""

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal, cast, final, override

from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, Platform
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from pyplumio.const import ProductType
from pyplumio.devices import Device
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import Filter, on_change, throttle
from pyplumio.structures.modules import ConnectedModules

from custom_components.plum_ecomax import PlumEcomaxConfigEntry

from .connection import EcomaxConnection
from .const import (
    ALL,
    ATTR_MIXERS,
    ATTR_THERMOSTATS,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_SOURCE_DEVICE,
    CONF_STEP,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_TCP,
    DOMAIN,
    MANUFACTURER,
    DeviceType,
    ModuleType,
)


@dataclass(frozen=True, kw_only=True)
class EcomaxEntityDescription(EntityDescription):
    """Describes an ecoMAX entity."""

    always_available: bool = False
    entity_registry_enabled_default: bool = False
    filter_fn: Callable[[Any], Filter] = on_change
    module: ModuleType = ModuleType.A
    product_types: set[ProductType] | Literal["all"] = ALL


@callback
def async_get_by_product_type[DescriptorT: EcomaxEntityDescription](
    product_type: ProductType, descriptions: Iterable[DescriptorT]
) -> Generator[DescriptorT]:
    """Filter descriptions by the product type."""
    for description in descriptions:
        product_types = description.product_types
        if product_types == ALL or product_type in product_types:
            yield description


@callback
def async_get_by_modules[DescriptorT: EcomaxEntityDescription](
    connected_modules: ConnectedModules, descriptions: Iterable[DescriptorT]
) -> Generator[DescriptorT]:
    """Filter descriptions by connected modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


@callback
def async_make_description_for_custom_entity[DescriptorT: EcomaxEntityDescription](
    description_factory: Callable[..., DescriptorT], entity: dict[str, Any]
) -> DescriptorT:
    """Make description from partial and entity data."""

    @callback
    def filter_wrapper(update_interval: int) -> Callable[..., Any]:
        """Return a filter function based on the update interval."""

        def filter_fn[CallableT: Callable[..., Any]](
            x: CallableT,
        ) -> Filter | CallableT:
            """Return a filter function."""
            return throttle(x, seconds=update_interval) if update_interval > 0 else x

        return filter_fn

    data = {**entity}

    if step := data.get(CONF_STEP, None):
        data["native_step"] = step
        del data[CONF_STEP]

    if unit_of_measurement := data.get(CONF_UNIT_OF_MEASUREMENT, None):
        data["native_unit_of_measurement"] = unit_of_measurement
        del data[CONF_UNIT_OF_MEASUREMENT]

    if update_interval := data.get(CONF_UPDATE_INTERVAL, None):
        data["filter_fn"] = filter_wrapper(update_interval)
        del data[CONF_UPDATE_INTERVAL]

    del data[CONF_SOURCE_DEVICE]
    return description_factory(**data)


@callback
def async_get_custom_entities[DescriptorT: EcomaxEntityDescription](
    platform: Platform,
    config_entry: PlumEcomaxConfigEntry,
    source_device: DeviceType | Literal["regdata"],
    description_factory: Callable[..., DescriptorT],
) -> Generator[DescriptorT]:
    """Return list of custom sensors."""
    entities: dict[str, Any] = config_entry.options.get("entities", {})
    if not entities:
        return

    for entity in entities[str(platform)].values():
        if entity[CONF_SOURCE_DEVICE] == source_device:
            yield async_make_description_for_custom_entity(description_factory, entity)


class EcomaxEntity(Entity):
    """Represents an ecoMAX entity."""

    _always_available = False
    _attr_available = False
    _attr_has_entity_name = True
    _attr_should_poll = False
    connection: EcomaxConnection
    entity_description: EcomaxEntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxEntityDescription
    ) -> None:
        """Initialize a new ecoMAX entity."""
        self.connection = connection
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Subscribe to events."""
        description = self.entity_description
        handler = description.filter_fn(self.async_update)

        async def _async_set_available(value: Any = None) -> None:
            """Mark entity as available."""
            self._attr_available = True

        if description.key in self.device.data:
            value = self.device.get_nowait(description.key, None)
            await _async_set_available(value)
            await handler(value)
        else:
            self.device.subscribe_once(description.key, _async_set_available)

        self.device.subscribe(description.key, handler)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from events."""
        self.device.unsubscribe(self.entity_description.key, self.async_update)

    @property
    @override
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.entity_description.always_available:
            return True

        return self.connection.connected.is_set() and self._attr_available

    @property
    @override
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        if self.entity_description.entity_registry_enabled_default:
            return True

        return self.entity_description.key in self.device.data

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.connection.uid}-{self.entity_description.key}"

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            configuration_url=(
                f"http://{self.connection.entry.data[CONF_HOST]}"
                if self.connection.entry.data[CONF_CONNECTION_TYPE]
                == CONNECTION_TYPE_TCP
                else None
            ),
            identifiers={(DOMAIN, self.connection.uid)},
            manufacturer=MANUFACTURER,
            model=self.connection.model,
            name=self.connection.name,
            serial_number=self.connection.uid,
            sw_version=self.connection.software[ModuleType.A],
        )

    @cached_property
    def device(self) -> Device:
        """Return the device handler."""
        return self.connection.device

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class SubdeviceEntityDescription(EcomaxEntityDescription):
    """Describes an ecoMAX entity."""

    indexes: set[int] | Literal["all"] = ALL


@callback
def async_get_by_index[SubDescriptorT: SubdeviceEntityDescription](
    index: int, descriptions: Iterable[SubDescriptorT]
) -> Generator[SubDescriptorT]:
    """Filter mixer/circuit descriptions by the index."""
    index += 1
    for description in descriptions:
        if description.indexes == ALL or index in description.indexes:
            yield description


class ThermostatEntity(EcomaxEntity):
    """Represents a thermostat entity."""

    index: int

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return the unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.THERMOSTAT}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            translation_key="thermostat",
            translation_placeholders={
                "device_name": self.connection.name,
                "thermostat_number": str(self.index + 1),
            },
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.THERMOSTAT}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            sw_version=self.connection.software[ModuleType.ECOSTER],
            via_device=(DOMAIN, self.connection.uid),
        )

    @cached_property
    @final
    @override
    def device(self) -> Thermostat:
        """Return the mixer handler."""
        device = self.connection.device
        return cast(Thermostat, device.data[ATTR_THERMOSTATS][self.index])


class MixerEntity(EcomaxEntity):
    """Represents a mixer entity."""

    index: int

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return a unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.MIXER}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            translation_key=(
                "circuit"
                if self.connection.product_type == ProductType.ECOMAX_I
                else "mixer"
            ),
            translation_placeholders={
                "device_name": self.connection.name,
                "mixer_number": str(self.index + 1),
            },
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.MIXER}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, self.connection.uid),
        )

    @cached_property
    @final
    @override
    def device(self) -> Mixer:
        """Return the mixer handler."""
        device = self.connection.device
        return cast(Mixer, device.data[ATTR_MIXERS][self.index])
