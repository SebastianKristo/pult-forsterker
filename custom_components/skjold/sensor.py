"""Kilde og «spiller nå»."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation, UnitOfTemperature, UnitOfTime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, all_known_sources
from .accessories import entities as accessories
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([KiAmpSourceSensor(c), KiAmpTitleSensor(c), KiAmpArtistSensor(c)])
    add([PerfSensor(c, *d) for d in PERF])   # ytelse på Pi-en (diagnostikk)
    add(accessories(c, "sensor"))   # Skjold Røst, Kassett og Hjul som egne enheter


class KiAmpSourceSensor(KiAmpEntity, SensorEntity):
    _attr_translation_key = "source"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:audio-input-stereo-minijack"

    def __init__(self, c) -> None:
        super().__init__(c, "source")
        # alle verdier sensoren kan rapportere (supersett, så kildebytte på daemonen aldri gir ugyldig tilstand)
        self._attr_options = all_known_sources(c.data)

    @property
    def native_value(self) -> str:
        v = self.coordinator.data.get("input", "airplay")
        return v if v in self._attr_options else None


class KiAmpTitleSensor(KiAmpEntity, SensorEntity):
    _attr_translation_key = "title"
    _attr_icon = "mdi:music"

    def __init__(self, c) -> None:
        super().__init__(c, "title")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("title") or None


class KiAmpArtistSensor(KiAmpEntity, SensorEntity):
    _attr_translation_key = "artist"
    _attr_icon = "mdi:account-music"

    def __init__(self, c) -> None:
        super().__init__(c, "artist")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("artist") or None


def _get(d, path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


# (nøkkel, sti i /api/health/perf, enhet, device_class, ikon, desimaler)
PERF = [
    ("cpu", ("cpu_pct",), PERCENTAGE, None, "mdi:cpu-64-bit", 1),
    ("cpu_temp", ("temp_c",), UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, None, 1),
    ("load_1", ("load", 0), None, None, "mdi:gauge", 2),
    ("memory", ("memory", "pct"), PERCENTAGE, None, "mdi:memory", 1),
    ("memory_used", ("memory", "used_mb"), UnitOfInformation.MEGABYTES, SensorDeviceClass.DATA_SIZE, "mdi:memory", 0),
    ("disk_free", ("disk", "free_gb"), UnitOfInformation.GIGABYTES, SensorDeviceClass.DATA_SIZE, "mdi:micro-sd", 1),
    ("uptime", ("uptime_s",), UnitOfTime.SECONDS, SensorDeviceClass.DURATION, "mdi:timer-outline", 0),
]


class PerfSensor(KiAmpEntity, SensorEntity):
    """Ytelse på maskinen Skjold kjører på (Raspberry Pi, Proxmox …)."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, c, key, path, unit, dc, icon, prec) -> None:
        super().__init__(c, "perf_" + key)
        self._path = path
        self._attr_translation_key = "perf_" + key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = dc
        self._attr_suggested_display_precision = prec
        if icon:
            self._attr_icon = icon
        if key == "uptime":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        if key in ("memory_used", "disk_free", "uptime", "load_1"):
            self._attr_entity_registry_enabled_default = key != "load_1"

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        p = self.coordinator.perf or {}
        if self._path[0] == "load":
            l = p.get("load") or []
            return l[0] if l else None
        return _get(p, self._path)

    @property
    def extra_state_attributes(self):
        p = self.coordinator.perf or {}
        if self._path == ("cpu_pct",):
            return {"cpus": p.get("cpus"), "load": p.get("load"), "model": p.get("model"),
                    "services": {k: v for k, v in (p.get("services") or {}).items()}}
        return None
