"""Velg radiokanal (Lyrion-favoritt 1–6)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BRIGHT_OPTIONS, DOMAIN, is_node
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    ents = [KiAmpPresetSelect(c), KiAmpVoiceProfileSelect(c)]
    if is_node(c.data):
        ents.append(KiAmpBrightSelect(c))   # skjermen (ST7735) på Skjold Node
    else:
        ents.append(KiAmpUsbPcSelect(c))    # USB-delingsswitch finnes bare på Pultforsterker
    add(ents)


class KiAmpPresetSelect(KiAmpEntity, SelectEntity):
    _attr_translation_key = "preset"
    _attr_icon = "mdi:radio"

    def __init__(self, c) -> None:
        super().__init__(c, "preset")

    def _labels(self) -> list[tuple[int, str]]:
        return [(p["n"], f"{p['n']}. {p['title']}") for p in self.coordinator.data.get("presets") or [] if p.get("title")]

    @property
    def options(self) -> list[str]:
        return [label for _, label in self._labels()] or ["Ingen kanaler"]

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data.get("input") != "radio":
            return None
        act = self.coordinator.data.get("preset")
        return next((label for n, label in self._labels() if n == act), None)

    async def async_select_option(self, option: str) -> None:
        n = next((n for n, label in self._labels() if label == option), None)
        if n:
            self.coordinator.async_set_updated_data(await self.coordinator.api.play_preset(n))


class KiAmpUsbPcSelect(KiAmpEntity, SelectEntity):
    """Hvilken PC USB-delingsswitchen (tastatur, mus, disk og USB-lyd) er koblet til."""
    _attr_translation_key = "usb_pc"
    _attr_icon = "mdi:usb-port"

    def __init__(self, c) -> None:
        super().__init__(c, "usb_pc")

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data.get("usbsw"))

    @property
    def options(self) -> list[str]:
        return list(self.coordinator.data.get("usb_pc_names") or ["PC 1", "PC 2"])

    @property
    def current_option(self) -> str | None:
        names, pc = self.options, self.coordinator.data.get("usb_pc", 1)
        return names[pc - 1] if 1 <= pc <= len(names) else None

    async def async_select_option(self, option: str) -> None:
        if option in self.options:
            self.coordinator.async_set_updated_data(await self.coordinator.api.set_usb_pc(self.options.index(option) + 1))


class KiAmpVoiceProfileSelect(KiAmpEntity, SelectEntity):
    """Stemmeprofil for talemeldingene (engelsk AI-stemme, norsk, trøndersk)."""
    _attr_translation_key = "voice_profile"
    _attr_icon = "mdi:account-voice"
    _DEFAULT = {"en": "English (AI)", "no": "Norsk", "trondersk": "Trøndersk"}

    def __init__(self, c) -> None:
        super().__init__(c, "voice_profile")

    def _profiles(self) -> dict[str, str]:
        return self.coordinator.data.get("voice_profiles") or self._DEFAULT

    @property
    def options(self) -> list[str]:
        return list(self._profiles().values())

    @property
    def current_option(self) -> str | None:
        return self._profiles().get(self.coordinator.data.get("voice_profile", "en"))

    async def async_select_option(self, option: str) -> None:
        key = next((k for k, v in self._profiles().items() if v == option), None)
        if key:
            self.coordinator.async_set_updated_data(await self.coordinator.api.set_voice_profile(key))


class KiAmpBrightSelect(KiAmpEntity, SelectEntity):
    """Lysstyrke på skjermen (settings["bright"]: 0 = auto, 1 = høy, 2 = middels, 3 = lav)."""
    _attr_translation_key = "bright"
    _attr_icon = "mdi:brightness-6"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = BRIGHT_OPTIONS

    def __init__(self, c) -> None:
        super().__init__(c, "bright")

    @property
    def current_option(self) -> str | None:
        # status["settings"] har bare endrede nøkler – standard er 0 (auto)
        v = (self.coordinator.data.get("settings") or {}).get("bright", 0)
        return BRIGHT_OPTIONS[v] if isinstance(v, int) and 0 <= v < len(BRIGHT_OPTIONS) else None

    async def async_select_option(self, option: str) -> None:
        if option in BRIGHT_OPTIONS:
            res = await self.coordinator.api.set_settings({"bright": BRIGHT_OPTIONS.index(option)})
            if isinstance(res.get("settings"), dict):
                self.coordinator.async_set_updated_data({**self.coordinator.data, "settings": res["settings"]})
            await self.coordinator.async_request_refresh()
