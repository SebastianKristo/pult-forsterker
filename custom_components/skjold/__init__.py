"""Pultforsterker – Home Assistant-integrasjon."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KiAmpApi, KiAmpError
from .const import CONF_HOST, CONF_PORT, DOMAIN, SCAN_INTERVAL_S

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT, Platform.EVENT]


class KiAmpCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, api: KiAmpApi, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=SCAN_INTERVAL_S))
        self.api = api
        self.entry = entry
        self.presets: list[dict] = []   # fylte favoritter fra /api/presets: [{n, title, genre, image…}]
        self._presets_sig: object = None

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.status()
        except KiAmpError as err:
            raise UpdateFailed(err) from err
        await self._refresh_presets(data)
        return data

    async def _refresh_presets(self, data: dict) -> None:
        """Hent /api/presets bare når favorittlista i status har endret seg (status har bare n/title)."""
        sig = tuple((p.get("n"), p.get("title")) for p in data.get("presets") or [] if isinstance(p, dict))
        if sig == self._presets_sig:
            return
        try:
            res = await self.api.presets()
            items = res.get("items")
            if not isinstance(items, list):
                items = [p for p in res.get("presets") or [] if p]
            self.presets = [p for p in items if isinstance(p, dict) and p.get("n") and p.get("title")]
        except KiAmpError:
            # eldre daemon uten /api/presets: bruk plassene i status
            self.presets = [p for p in data.get("presets") or [] if isinstance(p, dict) and p.get("title")]
        self._presets_sig = sig

    def async_set_updated_data(self, data: dict) -> None:
        if isinstance(data, dict) and "presets" in data:
            sig = tuple((p.get("n"), p.get("title")) for p in data.get("presets") or [] if isinstance(p, dict))
            if sig != self._presets_sig:   # favoritter endret (lagret) – hentes på nytt ved neste oppdatering
                self.presets = [p for p in data.get("presets") or [] if isinstance(p, dict) and p.get("title")]
                self._presets_sig = None
        super().async_set_updated_data(data)


CARDS_URL = "/skjold_static/skjold-cards.js"


async def _register_cards(hass: HomeAssistant) -> None:
    """Dashbordkortene (skjold-card, skjold-rom-card) lastes automatisk – ingen manuell ressurs i Lovelace."""
    if hass.data.get(DOMAIN + "_cards"):
        return
    hass.data[DOMAIN + "_cards"] = True
    import os
    from homeassistant.components import frontend
    path = os.path.join(os.path.dirname(__file__), "www", "skjold-cards.js")
    try:
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths([StaticPathConfig(CARDS_URL, path, True)])
    except ImportError:   # eldre Home Assistant
        hass.http.register_static_path(CARDS_URL, path, True)
    from .const import VERSION_CARDS
    frontend.add_extra_js_url(hass, f"{CARDS_URL}?v={VERSION_CARDS}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        await _register_cards(hass)
    except Exception as e:  # kortene er pynt – integrasjonen skal virke uansett
        _LOGGER.warning("Skjold-kortene ble ikke registrert: %s", e)
    api = KiAmpApi(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT])
    coordinator = KiAmpCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
