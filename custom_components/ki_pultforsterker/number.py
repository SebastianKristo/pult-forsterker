"""Loudness-styrke 0–10."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, status_inputs
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([KiAmpLoudnessLevel(c)] + [KiAmpSourceLevel(c, src) for src in level_sources(c.data)])


LEVEL_SOURCES = ("airplay", "bt", "usb", "radio", "aux", "aux2", "spotify")


def level_sources(data: dict) -> list[str]:
    """Nivåregulatorer for kildene kortet har (og som daemonen rapporterer nivå for)."""
    levels = data.get("levels")
    inputs = status_inputs(data)
    return [s for s in inputs if s in LEVEL_SOURCES and (not isinstance(levels, dict) or s in levels)]


class KiAmpSourceLevel(KiAmpEntity, NumberEntity):
    """Nivå per kilde (0–100) – brukes når kildene mikses (hovedkortet)."""
    _attr_icon = "mdi:volume-source"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, src: str) -> None:
        super().__init__(coordinator, f"level_{src}")
        self._src = src
        self._attr_translation_key = f"level_{src}"

    @property
    def available(self) -> bool:
        return super().available and isinstance(self.coordinator.data.get("levels"), dict)

    @property
    def native_value(self) -> float | None:
        v = (self.coordinator.data.get("levels") or {}).get(self._src)
        return None if v is None else float(v)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_level(self._src, int(value)))


class KiAmpLoudnessLevel(KiAmpEntity, NumberEntity):
    _attr_translation_key = "loudness_level"
    _attr_icon = "mdi:tune-vertical"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "dB"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "loudness_level")

    @property
    def native_value(self) -> float | None:
        v = self.coordinator.data.get("loudness_level")
        return None if v is None else float(v)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_loudness(level=int(value)))
