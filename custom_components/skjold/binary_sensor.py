"""Spiller / spiller ikke."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, product
from .accessories import entities as accessories
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    ents = [KiAmpPlayingSensor(c), PowerProblemSensor(c)]
    if product(c.data) == "s1":   # hodetelefonjack og NTC finnes bare på Pultforsterker-kortene
        ents += [KiAmpHeadphonesSensor(c), KiAmpOvertempSensor(c)]
    add(ents)
    add(accessories(c, "binary_sensor"))   # Skjold Røst, Kassett og Hjul som egne enheter


class KiAmpPlayingSensor(KiAmpEntity, BinarySensorEntity):
    _attr_translation_key = "playing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, c) -> None:
        super().__init__(c, "playing")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("playing"))


class KiAmpHeadphonesSensor(KiAmpEntity, BinarySensorEntity):
    """Hodetelefoner plugget i front-jacken (hovedkortet rev B)."""
    _attr_translation_key = "headphones"
    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_icon = "mdi:headphones"

    def __init__(self, c) -> None:
        super().__init__(c, "headphones")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("headphones"))


class KiAmpOvertempSensor(KiAmpEntity, BinarySensorEntity):
    """Kjøleribben på TPA3116 er for varm (NTC på hovedkortet) – forsterkeren dempes til den er avkjølt."""
    _attr_translation_key = "overtemp"
    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_icon = "mdi:thermometer-alert"

    def __init__(self, c) -> None:
        super().__init__(c, "overtemp")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("overtemp"))


class PowerProblemSensor(KiAmpEntity, BinarySensorEntity):
    """For lav spenning eller struping på Raspberry Pi (vcgencmd get_throttled). Utilgjengelig utenfor Pi."""
    _attr_translation_key = "power_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:flash-alert"

    def __init__(self, c) -> None:
        super().__init__(c, "power_problem")

    @property
    def available(self) -> bool:
        return super().available and bool((self.coordinator.perf or {}).get("throttle"))

    @property
    def is_on(self) -> bool:
        t = (self.coordinator.perf or {}).get("throttle") or {}
        return bool(t.get("under_voltage") or t.get("throttled") or t.get("freq_capped"))

    @property
    def extra_state_attributes(self):
        return (self.coordinator.perf or {}).get("throttle")
