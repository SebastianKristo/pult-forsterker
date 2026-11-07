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
        # tilbehør (Skjold Røst, Kassett, Hjul): hentes sjeldnere enn status, og feil (eldre daemon) ignoreres
        self.extras: dict = {"rost": None, "nfc": None, "spoler": None, "hjul": None}
        self._extras_n = 0

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.status()
        except KiAmpError as err:
            raise UpdateFailed(err) from err
        await self._refresh_presets(data)
        if self._extras_n % 6 == 0:   # ca. hvert 30. sekund
            await self.refresh_extras()
        self._extras_n += 1
        return data

    async def refresh_extras(self) -> None:
        for key, fn in (("rost", self.api.rost), ("nfc", self.api.nfc), ("spoler", self.api.spoler), ("hjul", self.api.hjul)):
            try:
                self.extras[key] = await fn()
            except KiAmpError:
                self.extras[key] = None

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
    _register_services(hass)
    return True


def _register_services(hass: HomeAssistant) -> None:
    """skjold.doorbell og skjold.run_routine – går til alle Skjold-enheter (eller bare entry_id hvis oppgitt)."""
    if hass.services.has_service(DOMAIN, "doorbell"):
        return

    def _targets(call):
        want = call.data.get("entry_id")
        return [c for eid, c in hass.data.get(DOMAIN, {}).items() if not want or eid == want]

    async def _doorbell(call) -> None:
        for c in _targets(call):
            await c.api.doorbell()

    async def _routine(call) -> None:
        for c in _targets(call):
            await c.api.run_routine(str(call.data["routine"]))

    hass.services.async_register(DOMAIN, "doorbell", _doorbell)
    hass.services.async_register(DOMAIN, "run_routine", _routine)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
