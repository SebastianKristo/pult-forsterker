"""Én media_player som samler strøm, kilde, volum, mute og «spiller nå»."""
from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity

SOURCES = {"airplay": "AirPlay", "bt": "Bluetooth", "aux": "AUX", "usb": "USB"}
SOURCES_REV = {v: k for k, v in SOURCES.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([KiAmpMediaPlayer(hass.data[DOMAIN][entry.entry_id])])


class KiAmpMediaPlayer(KiAmpEntity, MediaPlayerEntity):
    _attr_translation_key = "amp"
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE | MediaPlayerEntityFeature.SELECT_SOURCE
    )
    _attr_source_list = list(SOURCES.values())

    def __init__(self, c) -> None:
        super().__init__(c, "amp")

    @property
    def d(self) -> dict:
        return self.coordinator.data

    @property
    def state(self) -> MediaPlayerState:
        if not self.d.get("power"):
            return MediaPlayerState.OFF
        if self.d.get("input") in ("airplay", "bt"):
            return MediaPlayerState.PLAYING if self.d.get("playing") else MediaPlayerState.IDLE
        return MediaPlayerState.ON

    @property
    def source(self) -> str:
        return SOURCES.get(self.d.get("input"), "AirPlay")

    @property
    def volume_level(self) -> float:
        return int(self.d.get("volume", 0)) / 100

    @property
    def is_volume_muted(self) -> bool:
        return bool(self.d.get("mute"))

    @property
    def media_title(self) -> str | None:
        return self.d.get("title") or None

    @property
    def media_artist(self) -> str | None:
        return self.d.get("artist") or None

    @property
    def media_duration(self) -> int | None:
        return int(self.d.get("duration") or 0) or None

    @property
    def media_position(self) -> int | None:
        return int(self.d.get("position") or 0) if self.d.get("playing") else None

    @property
    def extra_state_attributes(self) -> dict:
        return {"bt_device": self.d.get("bt_device", ""), "bt_pairing": bool(self.d.get("bt_pairing"))}

    async def async_turn_on(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_power(True))

    async def async_turn_off(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_power(False))

    async def async_select_source(self, source: str) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_input(SOURCES_REV[source]))

    async def async_set_volume_level(self, volume: float) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_volume(round(volume * 100)))

    async def async_volume_up(self) -> None:
        await self.async_set_volume_level(min(1.0, self.volume_level + 0.05))

    async def async_volume_down(self) -> None:
        await self.async_set_volume_level(max(0.0, self.volume_level - 0.05))

    async def async_mute_volume(self, mute: bool) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_mute(mute))
