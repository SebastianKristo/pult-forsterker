"""Kilde og «spiller nå»."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, all_known_sources
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([KiAmpSourceSensor(c), KiAmpTitleSensor(c), KiAmpArtistSensor(c)])


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
