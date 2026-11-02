"""Loudness-styrke 0–10."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.const import EntityCategory

from .const import DOMAIN, has_leds, product, setting, status_inputs
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    ents = [KiAmpLoudnessLevel(c)] + [KiAmpSourceLevel(c, src) for src in level_sources(c.data)]
    if has_leds(c.data):   # LED-ringene på Skjold Node
        ents.append(KiAmpLedLevel(c))
    add(ents)
    if product(c.data) != "s1":   # eldre oppsett: nivå-entitetene ble lagt til som aktive på Node/Core – skru dem av én gang
        from homeassistant.helpers import entity_registry as er
        reg = er.async_get(hass)
        for e in er.async_entries_for_config_entry(reg, entry.entry_id):
            if e.domain == "number" and "_level_" in e.unique_id and not e.unique_id.endswith("_led_level") \
                    and not e.unique_id.endswith("_loudness_level") and e.disabled_by is None and not e.options.get(DOMAIN, {}).get("seen"):
                reg.async_update_entity(e.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
                reg.async_update_entity_options(e.entity_id, DOMAIN, {"seen": True})


LEVEL_SOURCES = ("airplay", "bt", "usb", "radio", "aux", "aux2", "spotify", "plex")


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
        # Bare Skjold S1 har nivåstyring per kilde i lydkjeden; på Node/Core gjør de ingenting → deaktivert som standard
        self._attr_entity_registry_enabled_default = product(coordinator.data) == "s1"
        self._attr_entity_category = None if product(coordinator.data) == "s1" else EntityCategory.CONFIG

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


class KiAmpLedLevel(KiAmpEntity, NumberEntity):
    """Lysstyrke på LED-ringene (settings["ledLevel"], 0–100 %)."""
    _attr_translation_key = "led_level"
    _attr_icon = "mdi:led-variant-on"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "led_level")

    @property
    def native_value(self) -> float | None:
        v = setting(self.coordinator.data, "ledLevel", 100)
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        res = await self.coordinator.api.set_settings({"ledLevel": int(round(value))})
        if isinstance(res.get("settings"), dict):
            self.coordinator.async_set_updated_data({**self.coordinator.data, "settings": res["settings"]})
        await self.coordinator.async_request_refresh()
