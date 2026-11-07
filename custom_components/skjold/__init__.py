"""Pultforsterker – Home Assistant-integrasjon."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
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
        self.settings: dict = {}             # /api/settings (EQ-profiler til Skjold-kortet)
        self._settings_n = 0

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.status()
        except KiAmpError as err:
            raise UpdateFailed(err) from err
        await self._refresh_presets(data)
        # innstillingene endres sjelden: hent dem hver 6. oppdatering (~30 s) for EQ-profilen i kortet
        if self._settings_n % 6 == 0:
            try:
                self.settings = (await self.api.settings()).get("settings") or {}
            except KiAmpError:
                pass
        self._settings_n += 1
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
    hass.http.register_view(SkjoldLogoView(hass))


class SkjoldLogoView(HomeAssistantView):
    """Kanallogoer til Skjold-kortet: /api/skjold_logo/<entry_id>?k=<nøkkel> → daemonens /api/logo.

    Går via Home Assistant så bildet har samme opphav som dashbordet (virker over https og utenfra). <img> kan ikke
    sende HA-token, så visningen er åpen – den leverer bare offentlige kanallogoer, og nøkkelen må være 16 hex-tegn."""
    url = "/api/skjold_logo/{entry_id}"
    name = "api:skjold_logo"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request, entry_id: str):
        from aiohttp import web
        from .cardhelpers import valid_key
        k = request.query.get("k", "")
        c = self.hass.data.get(DOMAIN, {}).get(entry_id)
        if c is None or not valid_key(k):
            return web.Response(status=404)
        try:
            body, ct = await c.api.logo(k)
        except KiAmpError:
            return web.Response(status=404)
        if not ct.startswith("image/"):
            return web.Response(status=404)
        return web.Response(body=body, content_type=ct.split(";")[0], headers={"Cache-Control": "public, max-age=86400"})


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

    def _by_entity(call):
        """Koordinatorene for entity_id-ene i kallet (Skjold-mediaspillere), ellers entry_id/alle."""
        from homeassistant.helpers import entity_registry as er
        ids = call.data.get("entity_id") or []
        if isinstance(ids, str):
            ids = [ids]
        if not ids:
            return _targets(call)
        reg = er.async_get(hass)
        out = []
        for eid in ids:
            ent = reg.async_get(eid)
            c = hass.data.get(DOMAIN, {}).get(ent.config_entry_id) if ent else None
            if c is not None and c not in out:
                out.append(c)
        return out

    async def _eq(call) -> None:
        from .cardhelpers import eq_patch, eq_source
        for c in _by_entity(call):
            src = call.data.get("source") or eq_source(c.data or {})
            await c.api.set_settings(eq_patch(call.data["profile"], src))
            c._settings_n = 0
            await c.async_request_refresh()

    async def _ask(call) -> None:
        for c in _by_entity(call):
            await c.api.ask(str(call.data["text"]))
            await c.async_request_refresh()

    hass.services.async_register(DOMAIN, "set_eq_profile", _eq)
    hass.services.async_register(DOMAIN, "ask", _ask)
    hass.services.async_register(DOMAIN, "doorbell", _doorbell)
    hass.services.async_register(DOMAIN, "run_routine", _routine)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
