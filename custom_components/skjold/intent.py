"""Stemmekommandoer for Home Assistant Assist: «spill …» på en Skjold-enhet.

Intensjonen SkjoldSpill har slottene query (det som skal spilles), kind (radio | musikk, valgfri) og name (rommet eller
enheten, valgfri). Setningene på norsk ligger i sentences/nb/skjold.yaml og kopieres til
<config>/custom_sentences/nb/skjold.yaml første gang integrasjonen settes opp (start Home Assistant på nytt etterpå).

Hvilken Skjold som spiller: den som er nevnt («… på kjøkkenet»), ellers den i samme område som stemmesatellitten du
snakker til (f.eks. Skjold Touch), ellers en Skjold Touch, ellers den første.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, intent

from .api import KiAmpError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
INTENT_SPILL = "SkjoldSpill"


async def async_setup_intents(hass: HomeAssistant) -> None:
    intent.async_register(hass, SkjoldSpill())


def _velg(hass: HomeAssistant, navn: str | None, satellitt: str | None):
    koord = hass.data.get(DOMAIN, {})
    if not koord:
        return None
    devreg, areareg = dr.async_get(hass), ar.async_get(hass)
    enheter = {}
    for eid, c in koord.items():
        dev = next((d for d in devreg.devices.values() if eid in d.config_entries), None)
        enheter[eid] = (c, dev)
    if navn:
        n = navn.strip().lower()
        for eid, (c, dev) in enheter.items():
            område = areareg.async_get_area(dev.area_id).name.lower() if dev and dev.area_id and areareg.async_get_area(dev.area_id) else ""
            if n in {(dev.name_by_user or dev.name or "").lower() if dev else "", område, str((c.data or {}).get("name") or "").lower()}:
                return c
    if satellitt:
        sd = devreg.async_get(satellitt)
        if sd and sd.area_id:
            for c, dev in enheter.values():
                if dev and dev.area_id == sd.area_id:
                    return c
    for c, _ in enheter.values():
        d = c.data or {}
        if d.get("product") == "touch" or d.get("board") == "touch":
            return c
    return next(iter(enheter.values()))[0]


class SkjoldSpill(intent.IntentHandler):
    intent_type = INTENT_SPILL
    description = "Spill en radiokanal, radiofavoritt eller sang på en Skjold-enhet"
    slot_schema = {"query": intent.non_empty_string, "kind": str, "name": str}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        slots = self.async_validate_slots(intent_obj.slots)
        query = slots["query"]["value"]
        kind = (slots.get("kind") or {}).get("value") or ""
        navn = (slots.get("name") or {}).get("value")
        svar = intent_obj.create_response()
        c = _velg(intent_obj.hass, navn, intent_obj.device_id)
        if c is None:
            svar.async_set_speech("Fant ingen Skjold-enhet.")
            return svar
        try:
            r = await c.api.voice_play(query, kind)
            await c.async_request_refresh()
            svar.async_set_speech(("Spiller " + str(r.get("title") or query)) if r.get("ok", True) else str(r.get("error")))
        except KiAmpError as e:
            _LOGGER.info("SkjoldSpill: %s", e)
            svar.async_set_speech(f"Fant ikke {query}.")
        return svar
