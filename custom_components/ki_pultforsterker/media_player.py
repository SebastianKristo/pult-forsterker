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
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import KiAmpEntity

SOURCES = {"radio": "Radio", "airplay": "AirPlay", "bt": "Bluetooth", "aux": "AUX 1", "aux2": "AUX 2", "usb": "USB"}
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
    _TRANSPORT = (
        MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK | MediaPlayerEntityFeature.PREVIOUS_TRACK
    )
    _attr_source_list = list(SOURCES.values())

    def __init__(self, c) -> None:
        super().__init__(c, "amp")
        self._fetched_at = dt_util.utcnow()

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        # avspillingskontroll bare for AirPlay og Bluetooth (AUX/USB styres fra kilden)
        if self.d.get("input") in ("airplay", "bt", "radio"):
            return self._attr_supported_features | self._TRANSPORT | MediaPlayerEntityFeature.PLAY_MEDIA
        return self._attr_supported_features

    @property
    def d(self) -> dict:
        return self.coordinator.data

    @property
    def state(self) -> MediaPlayerState:
        if not self.d.get("power"):
            return MediaPlayerState.OFF
        if self.d.get("input") in ("airplay", "bt", "radio"):
            if self.d.get("playing"):
                return MediaPlayerState.PLAYING
            return MediaPlayerState.PAUSED if self.d.get("paused") else MediaPlayerState.IDLE
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
    def media_album_name(self) -> str | None:
        return self.d.get("album") or None

    @property
    def media_duration(self) -> int | None:
        return int(self.d.get("duration") or 0) or None

    @property
    def media_position(self) -> int | None:
        if self.d.get("playing") or self.d.get("paused"):
            return int(self.d.get("position") or 0)
        return None

    @property
    def media_position_updated_at(self):
        # posisjonen i status er beregnet på Pi-en i det øyeblikket den ble hentet
        return self._fetched_at

    @property
    def media_image_url(self) -> str | None:
        cover = self.d.get("cover")
        return f"{self.coordinator.api.base}/cover?{cover}" if cover else None

    @property
    def media_image_remotely_accessible(self) -> bool:
        return False   # HA henter bildet fra Pi-en og viser det via sin egen proxy

    @property
    def media_image_hash(self) -> str | None:
        return self.d.get("cover") or None

    def _handle_coordinator_update(self) -> None:
        self._fetched_at = dt_util.utcnow()
        super()._handle_coordinator_update()

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

    async def _transport(self, action: str) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.transport(action))

    async def async_media_play(self) -> None:
        await self._transport("play")

    async def async_media_pause(self) -> None:
        await self._transport("pause")

    async def async_media_play_pause(self) -> None:
        await self._transport("playpause")

    async def async_media_stop(self) -> None:
        await self._transport("stop")

    async def async_media_next_track(self) -> None:
        await self._transport("next")

    async def async_media_previous_track(self) -> None:
        await self._transport("previous")

    @property
    def media_channel(self) -> str | None:
        return self.d.get("station") or None if self.d.get("input") == "radio" else None

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        """media_player.play_media med media_content_type «preset» (eller «channel») og id 1–6."""
        n = int(str(media_id).strip())
        self.coordinator.async_set_updated_data(await self.coordinator.api.play_preset(n))
