"""Platform for number integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, cast

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    PERCENTAGE,
    Platform,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType, UnitOfMeasurement
from pyplumio.parameters import NumberDescription, Parameter
from pyplumio.parameters.ecomax import EXTENDED_PARAMETER_TYPES

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .const import ATTR_CONTROL_MODE, ATTR_PRODUCT, FLOW_KG_H, DeviceType
from .entity import (
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    SubdeviceEntityDescription,
    ThermostatEntity,
    async_get_by_extended_parameters,
    async_get_by_index,
    async_get_by_modules,
    async_get_by_product_type,
    async_get_custom_entities,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxNumberEntityDescription(EcomaxEntityDescription, NumberEntityDescription):
    """Describes an ecoMAX number."""


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="target_heating_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_heating_temp",
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_heating_temp",
    ),
    EcomaxNumberEntityDescription(
        key="grate_heating_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="grate_mode_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuzzy_logic_min_power",
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuzzy_logic_max_power",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_calorific_value",
        mode=NumberMode.BOX,
        native_step=0.1,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_calorific_value",
    ),
    EcomaxNumberEntityDescription(
        key="heating_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="h1_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="h1_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="h2_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="h2_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="heating_pump_enable_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_pump_enable_temp",
    ),
    EcomaxNumberEntityDescription(
        key="water_heater_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="water_heater_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="airflow_power_100",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="airflow_power_100",
    ),
    EcomaxNumberEntityDescription(
        key="airflow_power_50",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="airflow_power_50",
    ),
    EcomaxNumberEntityDescription(
        key="airflow_power_30",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="airflow_power_30",
    ),
    EcomaxNumberEntityDescription(
        key="boiler_power_100",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        translation_key="boiler_power_100",
    ),
    EcomaxNumberEntityDescription(
        key="boiler_power_50",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        translation_key="boiler_power_50",
    ),
    EcomaxNumberEntityDescription(
        key="boiler_power_30",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        translation_key="boiler_power_30",
    ),
    EcomaxNumberEntityDescription(
        key="max_fan_boiler_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_fan_boiler_power",
    ),
    EcomaxNumberEntityDescription(
        key="min_fan_boiler_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_fan_boiler_power",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_feeding_work_100",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_feeding_work_100",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_feeding_work_50",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_feeding_work_50",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_feeding_work_30",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_feeding_work_30",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_feeding_pause_100",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_feeding_pause_100",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_feeding_pause_50",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_feeding_pause_50",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_feeding_pause_30",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_feeding_pause_30",
    ),
    EcomaxNumberEntityDescription(
        key="cycle_duration",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="cycle_duration",
    ),
    EcomaxNumberEntityDescription(
        key="min_boiler_power",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_boiler_power",
    ),
    EcomaxNumberEntityDescription(
        key="max_boiler_power",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_boiler_power",
    ),
    EcomaxNumberEntityDescription(
        key="min_fan_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_fan_power",
    ),
    EcomaxNumberEntityDescription(
        key="max_fan_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_fan_power",
    ),
    EcomaxNumberEntityDescription(
        key="reduction_airflow_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="reduction_airflow_temp",
    ),
    EcomaxNumberEntityDescription(
        key="fan_power_gain",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="fan_power_gain",
    ),
    EcomaxNumberEntityDescription(
        key="fuzzy_logic_fuel_flow_correction",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuzzy_logic_fuel_flow_correction",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_flow_correction",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_flow_correction",
    ),
    EcomaxNumberEntityDescription(
        key="airflow_correction_100",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="airflow_correction_100",
    ),
    EcomaxNumberEntityDescription(
        key="feeder_correction_100",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="feeder_correction_100",
    ),
    EcomaxNumberEntityDescription(
        key="airflow_correction_50",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="airflow_correction_50",
    ),
    EcomaxNumberEntityDescription(
        key="feeder_correction_50",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="feeder_correction_50",
    ),
    EcomaxNumberEntityDescription(
        key="airflow_correction_30",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="airflow_correction_30",
    ),
    EcomaxNumberEntityDescription(
        key="feeder_correction_30",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="feeder_correction_30",
    ),
    EcomaxNumberEntityDescription(
        key="grate_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="grate_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="grate_heating_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="grate_heating_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="grate_fan_work",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="grate_fan_work",
    ),
    EcomaxNumberEntityDescription(
        key="grate_fan_pause",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="grate_fan_pause",
    ),
    EcomaxNumberEntityDescription(
        key="grate_fuel_detection_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="grate_fuel_detection_time",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_low_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_low_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_airflow_delay",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_airflow_delay",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_test_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_test_time",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_feeder_work",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_feeder_work",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_feeder_dose",
        device_class=NumberDeviceClass.WEIGHT,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_feeder_dose",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_time",
    ),
    EcomaxNumberEntityDescription(
        key="warming_up_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="warming_up_time",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_finish_exhaust_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_finish_exhaust_temp",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_finish_threshold_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_finish_threshold_temp",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_fumes_delta_temp",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_fumes_delta_temp",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_delta_temp",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_delta_temp",
    ),
    EcomaxNumberEntityDescription(
        key="kindling_min_power_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="kindling_min_power_time",
    ),
    EcomaxNumberEntityDescription(
        key="stabilization_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="stabilization_time",
    ),
    EcomaxNumberEntityDescription(
        key="stabilization_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="stabilization_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_time",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_feeder_work",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_feeder_work",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_feeder_dose",
        device_class=NumberDeviceClass.WEIGHT,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_feeder_dose",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_feeder_pause",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_feeder_pause",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_cycle_duration",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_cycle_duration",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_fan_pause",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_fan_pause",
    ),
    EcomaxNumberEntityDescription(
        key="supervision_fan_work",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        product_types={ProductType.ECOMAX_P},
        translation_key="supervision_fan_work",
    ),
    EcomaxNumberEntityDescription(
        key="increase_fan_support_mode",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="increase_fan_support_mode",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_max_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_max_time",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_min_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_min_time",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_time",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_time",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_fan_work",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_fan_work",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_fan_pause",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_fan_pause",
    ),
    EcomaxNumberEntityDescription(
        key="start_burning_off",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="start_burning_off",
    ),
    EcomaxNumberEntityDescription(
        key="stop_burning_off",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="stop_burning_off",
    ),
    EcomaxNumberEntityDescription(
        key="cleaning_begin_time",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="cleaning_begin_time",
    ),
    EcomaxNumberEntityDescription(
        key="burning_off_cleaning_time",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="burning_off_cleaning_time",
    ),
    EcomaxNumberEntityDescription(
        key="cleaning_airflow_power",
        entity_category=EntityCategory.CONFIG,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        translation_key="cleaning_airflow_power",
    ),
    EcomaxNumberEntityDescription(
        key="warming_up_pause_time",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="warming_up_pause_time",
    ),
    EcomaxNumberEntityDescription(
        key="warming_up_cycle_time",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="warming_up_cycle_time",
    ),
    EcomaxNumberEntityDescription(
        key="remind_time",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="remind_time",
    ),
    EcomaxNumberEntityDescription(
        key="lambda_correction_range",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="lambda_correction_range",
    ),
    EcomaxNumberEntityDescription(
        key="oxygen_100",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="oxygen_100",
    ),
    EcomaxNumberEntityDescription(
        key="oxygen_50",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="oxygen_50",
    ),
    EcomaxNumberEntityDescription(
        key="oxygen_30",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="oxygen_30",
    ),
    EcomaxNumberEntityDescription(
        key="fuzzy_logic_oxygen_correction",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuzzy_logic_oxygen_correction",
    ),
    EcomaxNumberEntityDescription(
        key="max_fuel_flow",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=0.2,
        native_unit_of_measurement=FLOW_KG_H,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_fuel_flow",
    ),
    EcomaxNumberEntityDescription(
        key="feeder_calibration",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feeder_calibration",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_detection_time",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_detection_time",
    ),
    EcomaxNumberEntityDescription(
        key="fuel_detection_exhaust_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="fuel_detection_exhaust_temp",
    ),
    EcomaxNumberEntityDescription(
        key="feed2_h1",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feed2_h1",
    ),
    EcomaxNumberEntityDescription(
        key="feed2_h2",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feed2_h2",
    ),
    EcomaxNumberEntityDescription(
        key="feed2_h3",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feed2_h3",
    ),
    EcomaxNumberEntityDescription(
        key="feed2_h4",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feed2_h4",
    ),
    EcomaxNumberEntityDescription(
        key="feed2_work",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feed2_work",
    ),
    EcomaxNumberEntityDescription(
        key="feed2_pause",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="feed2_pause",
    ),
    EcomaxNumberEntityDescription(
        key="pause_heating_for_water_heater",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="pause_heating_for_water_heater",
    ),
    EcomaxNumberEntityDescription(
        key="thermostat_pause",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="thermostat_pause",
    ),
    EcomaxNumberEntityDescription(
        key="thermostat_work",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="thermostat_work",
    ),
    EcomaxNumberEntityDescription(
        key="increase_heating_temp_for_water_heater",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="increase_heating_temp_for_water_heater",
    ),
    EcomaxNumberEntityDescription(
        key="heating_curve",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=0.1,
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_curve",
    ),
    EcomaxNumberEntityDescription(
        key="heating_curve_shift",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_curve_shift",
    ),
    EcomaxNumberEntityDescription(
        key="weather_factor",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="weather_factor",
    ),
    EcomaxNumberEntityDescription(
        key="thermostat_operation",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="thermostat_operation",
    ),
    EcomaxNumberEntityDescription(
        key="thermostat_decrease_target_temp",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="thermostat_decrease_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="boiler_alert_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="boiler_alert_temp",
    ),
    EcomaxNumberEntityDescription(
        key="max_feeder_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_feeder_temp",
    ),
    EcomaxNumberEntityDescription(
        key="external_boiler_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="external_boiler_temp",
    ),
    EcomaxNumberEntityDescription(
        key="alert_notify",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="alert_notify",
    ),
    EcomaxNumberEntityDescription(
        key="pump_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="pump_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="min_water_heater_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_water_heater_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="max_water_heater_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_water_heater_target_temp",
    ),
    EcomaxNumberEntityDescription(
        key="summer_mode_enable_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="summer_mode_enable_temp",
    ),
    EcomaxNumberEntityDescription(
        key="summer_mode_disable_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="summer_mode_disable_temp",
    ),
    EcomaxNumberEntityDescription(
        key="water_heater_work_extension",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="water_heater_work_extension",
    ),
    EcomaxNumberEntityDescription(
        key="circulation_pause",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="circulation_pause",
    ),
    EcomaxNumberEntityDescription(
        key="circulation_work",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        product_types={ProductType.ECOMAX_P},
        translation_key="circulation_work",
    ),
    EcomaxNumberEntityDescription(
        key="circulation_start_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="circulation_start_temp",
    ),
    EcomaxNumberEntityDescription(
        key="max_buffer_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_buffer_temp",
    ),
    EcomaxNumberEntityDescription(
        key="min_buffer_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_buffer_temp",
    ),
    EcomaxNumberEntityDescription(
        key="buffer_hysteresis",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="buffer_hysteresis",
    ),
    EcomaxNumberEntityDescription(
        key="buffer_load_start",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="buffer_load_start",
    ),
    EcomaxNumberEntityDescription(
        key="buffer_load_stop",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="buffer_load_stop",
    ),
)

# Device classes of the extended parameters by unit of measurement.
EXTENDED_NUMBER_DEVICE_CLASSES: dict[
    UnitOfMeasurement | str | None, NumberDeviceClass
] = {
    UnitOfMeasurement.CELSIUS: NumberDeviceClass.TEMPERATURE,
    UnitOfMeasurement.KILO_WATT: NumberDeviceClass.POWER,
    UnitOfMeasurement.KILOGRAMS: NumberDeviceClass.WEIGHT,
    UnitOfMeasurement.MINUTES: NumberDeviceClass.DURATION,
    UnitOfMeasurement.PASCAL: NumberDeviceClass.PRESSURE,
    UnitOfMeasurement.SECONDS: NumberDeviceClass.DURATION,
}

EXTENDED_TEMPERATURE_DELTAS: set[str] = {
    "burning_off_detection_delta_temp",
    "kindling_temp_delta",
    "thermostat_decrease_boiler_temp",
}


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Represents an ecoMAX number."""

    entity_description: EcomaxNumberEntityDescription

    async def async_set_native_value(self, value: float) -> None:
        """Update current value."""
        self.device.set_nowait(self.entity_description.key, value)
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_update(self, value: Parameter) -> None:
        """Update entity state."""
        self._attr_native_value = cast(float, value.value)
        self._attr_native_min_value = cast(float, value.min_value)
        self._attr_native_max_value = cast(float, value.max_value)
        self.async_write_ha_state()


@callback
def async_setup_ecomax_numbers(connection: EcomaxConnection) -> list[EcomaxNumber]:
    """Set up the ecoMAX numbers."""
    return [
        EcomaxNumber(connection, description)
        for description in async_get_by_extended_parameters(
            connection.device.data,
            async_get_by_modules(
                connection.device.modules,
                async_get_by_product_type(connection.product_type, NUMBER_TYPES),
            ),
        )
    ]


@callback
def async_make_extended_number_description(
    description: NumberDescription,
) -> EcomaxNumberEntityDescription:
    """Make number description from the extended parameter description."""
    unit = description.unit_of_measurement
    device_class = EXTENDED_NUMBER_DEVICE_CLASSES.get(unit)
    if description.name in EXTENDED_TEMPERATURE_DELTAS:
        device_class = NumberDeviceClass.TEMPERATURE_DELTA

    return EcomaxNumberEntityDescription(
        key=description.name,
        device_class=device_class,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=description.step,
        native_unit_of_measurement=(
            unit.value if isinstance(unit, UnitOfMeasurement) else unit
        ),
        translation_key=description.name,
    )


@callback
def async_setup_extended_numbers(connection: EcomaxConnection) -> list[EcomaxNumber]:
    """Set up the ecoMAX extended numbers."""
    device = connection.device
    product = device.data[ATTR_PRODUCT]
    parameter_types = EXTENDED_PARAMETER_TYPES[(product.id, product.model)]
    return [
        EcomaxNumber(connection, async_make_extended_number_description(description))
        for description in parameter_types.values()
        if description.name != ATTR_CONTROL_MODE and description.name in device.data
    ]


@callback
def async_setup_custom_ecomax_numbers(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[EcomaxNumber]:
    """Set up the custom ecoMAX sensors."""
    return [
        EcomaxNumber(connection, description)
        for description in async_get_custom_entities(
            platform=Platform.NUMBER,
            source_device=DeviceType.ECOMAX,
            config_entry=config_entry,
            description_factory=EcomaxNumberEntityDescription,
        )
    ]


@dataclass(frozen=True, kw_only=True)
class MixerNumberEntityDescription(
    EcomaxNumberEntityDescription, SubdeviceEntityDescription
):
    """Describes a mixer number."""


MIXER_NUMBER_TYPES: tuple[MixerNumberEntityDescription, ...] = (
    MixerNumberEntityDescription(
        key="mixer_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="target_mixer_temp",
    ),
    MixerNumberEntityDescription(
        key="min_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="min_mixer_temp",
    ),
    MixerNumberEntityDescription(
        key="max_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="max_mixer_temp",
    ),
    MixerNumberEntityDescription(
        key="circuit_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        translation_key="target_circuit_temp",
    ),
    MixerNumberEntityDescription(
        key="min_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        indexes={2, 3},
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        translation_key="min_circuit_temp",
    ),
    MixerNumberEntityDescription(
        key="max_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        indexes={2, 3},
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        translation_key="max_circuit_temp",
    ),
    MixerNumberEntityDescription(
        key="day_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        indexes={2, 3},
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        translation_key="day_target_circuit_temp",
    ),
    MixerNumberEntityDescription(
        key="night_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        indexes={2, 3},
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        translation_key="night_target_circuit_temp",
    ),
    MixerNumberEntityDescription(
        key="thermostat_decrease_target_temp",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="thermostat_decrease_target_temp",
    ),
    MixerNumberEntityDescription(
        key="heating_curve",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=0.1,
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_curve",
    ),
    MixerNumberEntityDescription(
        key="heating_curve_shift",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_curve_shift",
    ),
    MixerNumberEntityDescription(
        key="weather_factor",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="weather_factor",
    ),
    MixerNumberEntityDescription(
        key="mixer_input_dead_zone",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        translation_key="mixer_input_dead_zone",
    ),
    MixerNumberEntityDescription(
        key="thermostat_mode",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_step=1,
        product_types={ProductType.ECOMAX_P},
        translation_key="thermostat_mode",
    ),
)


class MixerNumber(MixerEntity, EcomaxNumber):
    """Represents a mixer number."""

    entity_description: MixerNumberEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: MixerNumberEntityDescription,
        index: int,
    ):
        """Initialize a new mixer number."""
        self.index = index
        super().__init__(connection, description)


@callback
def async_setup_mixer_numbers(connection: EcomaxConnection) -> list[MixerNumber]:
    """Set up the mixer numbers."""
    return [
        MixerNumber(connection, description, index)
        for index in cast(dict[int, Any], connection.device.mixers)
        for description in async_get_by_index(
            index,
            async_get_by_modules(
                connection.device.modules,
                async_get_by_product_type(connection.product_type, MIXER_NUMBER_TYPES),
            ),
        )
    ]


@callback
def async_setup_custom_mixer_numbers(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[MixerNumber]:
    """Set up the custom mixer numbers."""
    return [
        MixerNumber(connection, description, index)
        for description, index in async_get_custom_entities(
            platform=Platform.NUMBER,
            source_device=DeviceType.MIXER,
            config_entry=config_entry,
            description_factory=MixerNumberEntityDescription,
        )
    ]


@dataclass(frozen=True, kw_only=True)
class ThermostatNumberEntityDescription(
    EcomaxNumberEntityDescription, SubdeviceEntityDescription
):
    """Describes a thermostat number."""


class ThermostatNumber(ThermostatEntity, EcomaxNumber):
    """Represents a thermostat number."""

    entity_description: ThermostatNumberEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: ThermostatNumberEntityDescription,
        index: int,
    ):
        """Initialize a new thermostat number."""
        self.index = index
        super().__init__(connection, description)


@callback
def async_setup_custom_thermostat_numbers(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[ThermostatNumber]:
    """Set up the custom thermostat numbers."""
    return [
        ThermostatNumber(connection, description, index)
        for description, index in async_get_custom_entities(
            platform=Platform.NUMBER,
            source_device=DeviceType.THERMOSTAT,
            config_entry=config_entry,
            description_factory=ThermostatNumberEntityDescription,
        )
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the number platform."""
    _LOGGER.debug("Starting setup of number platform...")

    connection = entry.runtime_data.connection
    extended_parameters = await connection.async_setup_extended_parameters()
    entities = async_setup_ecomax_numbers(connection)

    # Add ecoMAX extended numbers.
    if extended_parameters:
        entities += async_setup_extended_numbers(connection)

    # Add custom ecoMAX numbers.
    entities += async_setup_custom_ecomax_numbers(connection, entry)

    # Add mixer/circuit numbers.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities += async_setup_mixer_numbers(connection)
        entities += async_setup_custom_mixer_numbers(connection, entry)

    # Add thermostat numbers.
    if connection.has_thermostats and await connection.async_setup_thermostats():
        entities += async_setup_custom_thermostat_numbers(connection, entry)

    async_add_entities(entities)
    return True
