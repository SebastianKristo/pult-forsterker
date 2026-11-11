"""Skjold Touch: det 7″-skjermen trenger utover vanlig avspilling.

- Smarthus-fliser fra Home Assistant (lys, brytere, porter, varme, sensorer, scener) – GET/POST /api/touch/smart
- Vekkeklokke som ringer på skjermen, med slumre og slå av – GET/POST /api/alarm
- Stemmeoverlegg: stemmesatellitten (wyoming-satellite) melder fra om lytter / tenker / svar – POST /api/touch/voice
- Kommandoer til skjermen fra HA, Homey eller appen (standby, vekk, side, omstart) – POST /api/touch/cmd
- Bakgrunnslys – POST /api/touch/backlight
- Volumhjul (EC11) når pinnene er satt i KI_TOUCH_ENC=A,B[,SW]

Home Assistant-adresse og token deles med dørklokka (Innstillinger → Dørklokke i appen). Alt her er rent Python uten
maskinvare, så det kan testes på en vanlig PC.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import threading
import time
import urllib.request

DEFAULTS = {"tiles": [], "scenes": [], "lock_entity": "", "weather_entity": "", "light_entity": "", "calendar_entity": "",
            # Homey som smarthus-kilde i stedet for Home Assistant: adresse (http://homey-xxxx.local eller IP) og API-nøkkel
            "hub": "ha", "homey_url": "", "homey_token": "", "homey_devices": []}
WAKE_WORDS = ("ok_nabu", "hey_jarvis", "hey_mycroft")
PAGES = ("now", "home", "smart", "alarm", "lib", "rooms", "set")
SNOOZE_MIN = 9
RING_MAX_S = 30 * 60          # ringer ingen ut etter en halvtime, gir alarmen seg selv
ON_STATES = {"on", "open", "opening", "unlocked", "playing", "heat", "cool", "heat_cool", "auto", "dry", "fan_only", "home"}
TOGGLE = ("light", "switch", "input_boolean", "fan", "media_player", "humidifier", "siren")
WEATHER_NO = {"sunny": "sol", "clear-night": "klart", "cloudy": "overskyet", "partlycloudy": "delvis skyet", "rainy": "regn",
              "pouring": "kraftig regn", "snowy": "snø", "snowy-rainy": "sludd", "fog": "tåke", "windy": "vind",
              "windy-variant": "vind", "lightning": "torden", "lightning-rainy": "torden og regn", "hail": "hagl",
              "exceptional": "uvanlig vær"}
TAGS = {"light": "LYS", "switch": "BRYTER", "input_boolean": "BRYTER", "fan": "VIFTE", "media_player": "SPILLER", "lock": "LÅS",
        "humidifier": "LUFT", "siren": "SIRENE"}


# ------------------------------------------------------------------ rene hjelpere
def no_num(v, dec=1) -> str:
    """Tall slik vi skriver dem på norsk: 21,5 og 7 (ikke 7,0)."""
    try:
        f = round(float(v), dec)
    except (TypeError, ValueError):
        return str(v)
    s = ("%.*f" % (dec, f)).rstrip("0").rstrip(".") if dec else str(int(round(f)))
    return s.replace(".", ",").replace("-", "−")


def clean(cfg: dict, body: dict) -> dict:
    out = dict(cfg)
    for k, v in (body or {}).items():
        if k not in DEFAULTS:
            continue
        if k == "hub":
            if v not in ("ha", "homey"):
                raise ValueError("hub må være ha eller homey")
        elif k == "homey_token":
            if isinstance(v, str) and v.startswith("••••"):
                continue                       # maskert verdi sendt tilbake uendret
            v = str(v or "").strip()[:400]
        elif k == "homey_url":
            v = str(v or "").strip().rstrip("/")[:200]
            if v and not v.startswith(("http://", "https://")):
                v = "http://" + v
        elif k == "homey_devices":
            if not isinstance(v, list):
                raise ValueError("homey_devices må være en liste")
            v = [str(x).strip()[:80] for x in v if str(x).strip()][:12]
        elif isinstance(DEFAULTS[k], list):
            if not isinstance(v, list):
                raise ValueError(f"{k} må være en liste")
            v = [str(x).strip()[:120] for x in v if "." in str(x)][:12 if k == "tiles" else 4]
        else:
            v = str(v or "").strip()[:120]
            if v and "." not in v:
                raise ValueError(f"{k} må være en entitet, f.eks. lock.inngang")
        out[k] = v
    return out


def tile_of(s: dict) -> dict:
    """Én Home Assistant-tilstand → én flis på Smarthus-siden."""
    eid = str(s.get("entity_id") or "")
    dom = eid.split(".")[0]
    a = s.get("attributes") or {}
    st = str(s.get("state") or "")
    t = {"id": eid, "name": str(a.get("friendly_name") or eid)[:28], "domain": dom, "on": st in ON_STATES,
         "kind": "toggle" if dom in TOGGLE or dom == "cover" else "info", "text": "", "tag": TAGS.get(dom, "")}
    if st in ("unavailable", "unknown", ""):
        t.update(on=False, text="Utilgjengelig", kind="info")
        return t
    if dom == "light":
        b = a.get("brightness")
        t["text"] = ("På · %d %%" % round(float(b) / 255 * 100)) if t["on"] and b else ("På" if t["on"] else "Av")
        modes = a.get("supported_color_modes") or []
        if b is not None or any(m != "onoff" for m in modes):      # kan dimmes: hold på flisa for lysstyrke
            t["pct"] = round(float(b) / 255 * 100) if t["on"] and b else 0
    elif dom in TOGGLE:
        t["text"] = "På" if t["on"] else "Av"
    elif dom == "cover":
        t["text"] = "Åpen" if t["on"] else "Lukket"
        t["tag"] = "TRYKK FOR Å LUKKE" if t["on"] else "TRYKK FOR Å ÅPNE"
    elif dom == "climate":
        cur, tgt = a.get("current_temperature"), a.get("temperature")
        t.update(kind="climate", on=st != "off", text=("Nå " + no_num(cur) + " °C") if cur is not None else ("Av" if st == "off" else "På"),
                 target=float(tgt) if tgt is not None else None, min=float(a.get("min_temp", 5)), max=float(a.get("max_temp", 30)))
    elif dom == "lock":
        t["on"] = st == "unlocked"
        t["text"] = "Ulåst" if t["on"] else "Låst"
    elif dom == "camera":
        t.update(kind="camera", on=False, text="Kamera", tag="VIS KAMERA")
    elif dom == "binary_sensor":
        t["text"] = "På" if st == "on" else "Av"
        t["tag"] = str(a.get("device_class") or "SENSOR").upper()[:18]
    elif dom == "weather":
        tmp = a.get("temperature")
        t["text"] = ((no_num(tmp) + " °C og ") if tmp is not None else "") + WEATHER_NO.get(st, st)
        t["tag"] = "VÆR"
    else:   # sensor og alt annet: vis verdien
        unit = str(a.get("unit_of_measurement") or "")
        t["on"] = False
        t["text"] = (no_num(st, 2) if _is_num(st) else st[:24]) + ((" " + unit) if unit else "")
        t["tag"] = str(a.get("device_class") or "").upper().replace("_", " ")[:18]
    return t


def _is_num(s) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------ Homey (lokalt web-API)
HOMEY_CLASS = {"light": "light", "socket": "switch", "thermostat": "climate", "heater": "climate", "lock": "lock", "sensor": "sensor",
               "garagedoor": "cover", "curtain": "cover", "blinds": "cover", "windowcoverings": "cover", "sunshade": "cover", "fan": "fan"}


def homey_tile(dev: dict) -> dict:
    """Én Homey-enhet → én flis, i samme form som flisene fra Home Assistant."""
    caps = dev.get("capabilitiesObj") or {}
    val = lambda c: (caps.get(c) or {}).get("value")
    dom = HOMEY_CLASS.get(str(dev.get("virtualClass") or dev.get("class") or ""), "switch" if "onoff" in caps else "sensor")
    t = {"id": "homey:" + str(dev.get("id")), "name": str(dev.get("name") or "")[:28], "domain": dom, "on": bool(val("onoff")),
         "kind": "info", "text": "", "tag": TAGS.get(dom, "")}
    if dev.get("available") is False:
        t.update(on=False, text="Utilgjengelig")
        return t
    if dom == "climate" and "target_temperature" in caps:
        cur, tgt = val("measure_temperature"), val("target_temperature")
        t.update(kind="climate", on=True, text=("Nå " + no_num(cur) + " °C") if cur is not None else "",
                 target=float(tgt) if tgt is not None else None,
                 min=float((caps.get("target_temperature") or {}).get("min", 5)), max=float((caps.get("target_temperature") or {}).get("max", 30)))
    elif dom == "lock":
        laast = bool(val("locked"))
        t.update(on=not laast, text="Låst" if laast else "Ulåst")            # låsen åpnes ikke med et trykk på flisa
    elif dom == "cover":
        st = val("windowcoverings_state") or val("garagedoor_closed")
        aapen = (st == "up") if isinstance(st, str) else (st is False)
        t.update(on=bool(aapen), text="Åpen" if aapen else "Lukket", tag="", kind="info")
    elif "onoff" in caps:
        t["kind"] = "toggle"
        dim = val("dim")
        if dom == "light" and dim is not None:
            t["pct"] = round(float(dim) * 100) if t["on"] else 0
            t["text"] = ("På · %d %%" % t["pct"]) if t["on"] else "Av"
        else:
            t["text"] = "På" if t["on"] else "Av"
    else:
        for cap, enhet, merke in (("measure_power", "W", "EFFEKT"), ("measure_temperature", "°C", "TEMPERATUR"), ("measure_humidity", "%", "FUKT"),
                                  ("measure_battery", "%", "BATTERI")):
            if val(cap) is not None:
                t.update(text=no_num(val(cap), 1) + " " + enhet, tag=merke)
                break
        if "alarm_motion" in caps and not t["text"]:
            t.update(text="Bevegelse" if val("alarm_motion") else "Ingen bevegelse", tag="BEVEGELSE")
    return t


def homey_action(dev: dict, action: str, value=None) -> tuple:
    """(kapabilitet, verdi) for et trykk på en Homey-flis."""
    caps = dev.get("capabilitiesObj") or {}
    val = lambda c: (caps.get(c) or {}).get("value")
    if action == "toggle" and "onoff" in caps and "locked" not in caps:
        return "onoff", not bool(val("onoff"))
    if action == "brightness" and "dim" in caps and value is not None:
        pct = max(0, min(100, int(round(float(value)))))
        return ("onoff", False) if pct == 0 else ("dim", pct / 100)
    if action in ("up", "down") and "target_temperature" in caps and val("target_temperature") is not None:
        c = caps["target_temperature"]
        return "target_temperature", max(float(c.get("min", 5)), min(float(c.get("max", 30)), float(val("target_temperature")) + (0.5 if action == "up" else -0.5)))
    raise ValueError("kan ikke styres herfra")


def homey_pick(devices: list) -> list:
    """Ingen enheter valgt: fire lys, én varme og to brytere."""
    def kl(d):
        return HOMEY_CLASS.get(str(d.get("virtualClass") or d.get("class") or ""), "")
    ok = sorted((d for d in devices if d.get("available") is not False), key=lambda d: str(d.get("name") or "").lower())
    ut = [d for d in ok if kl(d) == "light"][:4] + [d for d in ok if kl(d) == "climate" and "target_temperature" in (d.get("capabilitiesObj") or {})][:1] \
        + [d for d in ok if kl(d) == "switch"][:2]
    return [str(d.get("id")) for d in ut][:8]


def auto_pick(states: list) -> tuple:
    """Ingen fliser valgt ennå: ta et fornuftig utvalg så siden ikke står tom. Gir (fliser, scener)."""
    by = {}
    for s in states:
        eid = str(s.get("entity_id") or "")
        if s.get("state") in ("unavailable", "unknown") or (s.get("attributes") or {}).get("hidden"):
            continue
        by.setdefault(eid.split(".")[0], []).append(eid)
    tiles = sorted(by.get("light", []))[:4] + sorted(by.get("climate", []))[:1] + sorted(by.get("cover", []))[:1] + sorted(by.get("switch", []))[:2]
    return tiles[:8], sorted(by.get("scene", []))[:3]


def service_for(eid: str, action: str, target=None, lo=5.0, hi=30.0, value=None) -> tuple:
    """(domene, tjeneste, data) for et trykk på en flis. Låser og alarmer styres aldri herfra med et vanlig trykk."""
    dom = eid.split(".")[0]
    if action == "toggle":
        if dom in TOGGLE:
            return "homeassistant", "toggle", {"entity_id": eid}
        if dom == "cover":
            return "cover", "toggle", {"entity_id": eid}
    if action in ("up", "down") and dom == "climate" and target is not None:
        t = max(lo, min(hi, float(target) + (0.5 if action == "up" else -0.5)))
        return "climate", "set_temperature", {"entity_id": eid, "temperature": t}
    if action == "brightness" and dom == "light" and value is not None:
        pct = max(0, min(100, int(round(float(value)))))
        if pct == 0:
            return "light", "turn_off", {"entity_id": eid}
        return "light", "turn_on", {"entity_id": eid, "brightness_pct": pct}
    if action == "scene" and dom in ("scene", "script"):
        return dom, "turn_on", {"entity_id": eid}
    raise ValueError("kan ikke styres herfra")


def in_night(mode: int, start: int, end: int, hour: int, ext: bool) -> bool:
    """Nattmodus nå? mode: 0 av, 1 tidsplan, 2 styrt av HA/Homey, 3 på."""
    if mode == 3:
        return True
    if mode == 1:
        return (hour >= start or hour < end) if start > end else (start <= hour < end)
    return mode == 2 and bool(ext)


def next_alarm(alarms: list, tm) -> dict | None:
    """Neste alarm som er på: {time, name, in_min}. tm er time.struct_time (lokal). days: 0 = mandag, tom = hver dag."""
    best = None
    now = tm.tm_hour * 60 + tm.tm_min
    for a in alarms or []:
        if not a.get("on", True):
            continue
        try:
            h, m = str(a.get("time")).split(":")
            at = int(h) * 60 + int(m)
        except ValueError:
            continue
        days = a.get("days") or list(range(7))
        for d in range(8):
            if (tm.tm_wday + d) % 7 in days and (d > 0 or at > now):
                mins = d * 1440 + at - now
                if best is None or mins < best["in_min"]:
                    best = {"time": a["time"], "name": str(a.get("name") or "Alarm"), "in_min": mins}
                break
    return best


def morning_text(weather: dict | None, light: dict | None) -> str:
    """Linja under klokka når alarmen ringer: «6 °C og overskyet · lyset på soverommet er på 40 %»."""
    parts = []
    if weather and weather.get("state") not in (None, "unavailable", "unknown"):
        tmp = (weather.get("attributes") or {}).get("temperature")
        parts.append(((no_num(tmp, 0) + " °C og ") if tmp is not None else "") + WEATHER_NO.get(weather["state"], weather["state"]))
    if light and light.get("state") == "on":
        a = light.get("attributes") or {}
        navn = str(a.get("friendly_name") or "lyset").strip()
        b = a.get("brightness")
        parts.append((navn[0].lower() + navn[1:]) + (" er på %d %%" % round(float(b) / 255 * 100) if b else " er på"))
    return " · ".join(parts)


def _local_hm(iso: str, tz=None) -> str:
    """ISO-tid fra Home Assistant (UTC eller med sone) → «HH:MM» i lokal tid."""
    from datetime import datetime
    return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(tz).strftime("%H:%M")


def home_weather(state: dict | None, hourly: list | None = None, tz=None) -> dict | None:
    """Været slik standby-stilene på S1 vil ha det: {t, c, hours: [[«HH», grader] × 4]}."""
    if not state or state.get("state") in (None, "unavailable", "unknown"):
        return None
    a = state.get("attributes") or {}
    if a.get("temperature") is None:
        return None
    tekst = WEATHER_NO.get(state["state"], str(state["state"]))
    sted = str(a.get("friendly_name") or "").strip()
    hours = []
    for f in (hourly or [])[:4]:
        try:
            hours.append([_local_hm(f["datetime"], tz)[:2], round(float(f["temperature"]))])
        except (KeyError, TypeError, ValueError):
            pass
    return {"t": round(float(a["temperature"])), "c": tekst[:1].upper() + tekst[1:] + ((" · " + sted) if sted and sted.lower() not in ("home", "hjem", "forecast home") else ""),
            "hours": hours}


def home_sun(state: dict | None, tz=None) -> list | None:
    """[soloppgang, solnedgang] som «HH:MM» fra sun.sun."""
    a = (state or {}).get("attributes") or {}
    try:
        return [_local_hm(a["next_rising"], tz), _local_hm(a["next_setting"], tz)]
    except (KeyError, TypeError, ValueError):
        return None


def home_calendar(events: list, today, tz=None) -> dict | None:
    """Neste dag med avtaler: {day: «I DAG» | «I MORGEN» | «FREDAG», items: [«09:30 Fotballtrening», …]} (høyst to)."""
    from datetime import date, datetime
    dager = ["MANDAG", "TIRSDAG", "ONSDAG", "TORSDAG", "FREDAG", "LØRDAG", "SØNDAG"]
    rows = []
    for e in events or []:
        st = e.get("start") or {}
        try:
            if st.get("dateTime"):
                dt = datetime.fromisoformat(str(st["dateTime"]).replace("Z", "+00:00")).astimezone(tz)
                rows.append((dt.date(), dt.strftime("%H:%M"), str(e.get("summary") or "").strip()))
            elif st.get("date"):
                rows.append((date.fromisoformat(st["date"]), "", str(e.get("summary") or "").strip()))
        except (TypeError, ValueError):
            pass
    rows = sorted(r for r in rows if r[0] >= today and r[2])
    if not rows:
        return None
    d0 = rows[0][0]
    diff = (d0 - today).days
    return {"day": "I DAG" if diff == 0 else "I MORGEN" if diff == 1 else dager[d0.weekday()],
            "items": [((t + " ") if t else "") + n[:40] for d, t, n in rows if d == d0][:2]}


# ------------------------------------------------------------------ smart vekking (KI Søvn i Home Assistant)
# Integrasjonen ki_sovn lager en «vekkealarm» med én tid og én bryter per ukedag, og kan vite om personen sover.
# Touch finner den via attributtet integrasjon = ki_sovn, og styrer bare entitetene den fant.
WAKE_DAYS = ("mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lordag", "sondag")
WAKE_SWITCHES = ("aktiv", "nattlampe", "vekk_person", "bare_hvis_sover")
WAKE_NUMBERS = ("fade_opp", "av_etter")
WAKE_BUTTONS = ("test", "stopp")
WAKE_SKIP = {"betingelser": "Hoppes over nå: betingelsene i Home Assistant er ikke oppfylt",
             "våken": "Hoppes over hvis du allerede er våken"}


def _hm(v) -> str:
    """«07:00:00» → «07:00». Ugyldig tid gir tom tekst."""
    p = str(v or "").split(":")
    try:
        h, m = int(p[0]), int(p[1])
    except (ValueError, IndexError):
        return ""
    return f"{h:02d}:{m:02d}" if 0 <= h < 24 and 0 <= m < 60 else ""


def wake_find(states: list) -> list:
    """Alle vekkealarmene fra ki_sovn i en liste med HA-tilstander, klare for skjermen."""
    by = {s.get("entity_id", ""): s for s in states if isinstance(s, dict)}

    def st(eid):
        s = by.get(eid)
        return s if s and s.get("state") not in (None, "unavailable", "unknown") else None

    out = []
    for eid, s in sorted(by.items()):
        a = s.get("attributes") or {}
        if not eid.startswith("sensor.") or a.get("integrasjon") != "ki_sovn" or a.get("type") != "vekking":
            continue
        base = eid.split(".", 1)[1]
        base = base[:-len("_neste_alarm")] if base.endswith("_neste_alarm") else str(a.get("prefix") or base)
        ent = {}
        for k in WAKE_SWITCHES:
            ent[k] = f"switch.{base}_{k}"
        for d in WAKE_DAYS:
            ent[d] = f"time.{base}_{d}"
            ent[d + "_aktiv"] = f"switch.{base}_{d}_aktiv"
        for k in WAKE_NUMBERS:
            ent[k] = f"number.{base}_{k}"
        for k in WAKE_BUTTONS:
            ent[k] = f"button.{base}_{k}"
        ent = {k: v for k, v in ent.items() if v in by}
        on = lambda k: (st(ent.get(k, "")) or {}).get("state") == "on"       # noqa: E731

        def num(k, dflt):
            x = st(ent.get(k, ""))
            if not x:
                return None
            xa = x.get("attributes") or {}
            try:
                return {"value": int(float(x["state"])), "min": int(float(xa.get("min", 1))), "max": int(float(xa.get("max", dflt))),
                        "step": max(1, int(float(xa.get("step", 1))))}
            except (TypeError, ValueError):
                return None

        days = [{"key": d, "time": _hm((st(ent.get(d, "")) or {}).get("state")) or "07:00", "on": on(d + "_aktiv"),
                 "ok": d in ent and d + "_aktiv" in ent} for d in WAKE_DAYS]
        run = st(f"binary_sensor.{base}_kjorer")
        person = None
        ps = st(str(a.get("person") or ""))
        if ps:
            pa = ps.get("attributes") or {}
            pb = ps["entity_id"].split(".", 1)[1]
            pb = pb[:-len("_sover")] if pb.endswith("_sover") else pb
            try:
                pct = round(float(pa.get("sannsynlighet")))
            except (TypeError, ValueError):
                pct = None
            person = {"name": str(pa.get("navn") or "")[:24], "sleeping": ps["state"] == "on", "pct": pct,
                      "reason": str(pa.get("årsak") or "")[:60],
                      "can_set": f"button.{pb}_sett_sover" in by and f"button.{pb}_sett_vaken" in by, "_base": pb}
        nxt = s.get("state") if _hm(s.get("state")) else ""
        out.append({"id": base, "name": str(a.get("navn") or base)[:24], "on": on("aktiv"), "days": days,
                    "fade": num("fade_opp", 60), "off_after": num("av_etter", 240),
                    "night_light": on("nattlampe") if "nattlampe" in ent else None,
                    "wake_person": on("vekk_person") if "vekk_person" in ent else None,
                    "only_if_asleep": on("bare_hvis_sover") if "bare_hvis_sover" in ent else None,
                    "next": nxt, "next_day": str(a.get("neste_dag") or "") if nxt else "",
                    "skip": WAKE_SKIP.get(str(a.get("hopper_over") or ""), ""),
                    "running": bool(run and run["state"] == "on"), "phase": str(((run or {}).get("attributes") or {}).get("fase") or ""),
                    "lights": len(a.get("lys") or []), "person": person, "can_test": "test" in ent and "stopp" in ent, "_ent": ent})
    return out


def wake_calls(alarm: dict, changes: dict) -> list:
    """Endringer fra skjermen → tjenestekall til HA: [(domene, tjeneste, data)]. Ukjente nøkler og verdier gir ValueError."""
    ent, calls = alarm["_ent"], []
    for k, v in changes.items():
        if k in ("sett_sover", "sett_vaken"):
            p = alarm.get("person")
            if not (p and p.get("can_set")):
                raise ValueError("vekkealarmen har ingen person å sette")
            calls.append(("button", "press", {"entity_id": f"button.{p['_base']}_{k}"}))
            continue
        eid = ent.get(k)
        if not eid:
            raise ValueError(f"ukjent innstilling: {k}"[:60])
        if k in WAKE_BUTTONS:
            calls.append(("button", "press", {"entity_id": eid}))
        elif k in WAKE_DAYS:
            t = _hm(v)
            if not t:
                raise ValueError("tiden må være TT:MM")
            calls.append(("time", "set_value", {"entity_id": eid, "time": t + ":00"}))
        elif k in WAKE_NUMBERS:
            n = alarm["fade" if k == "fade_opp" else "off_after"] or {"min": 1, "max": 240}
            try:
                x = int(v)
            except (TypeError, ValueError):
                raise ValueError("verdien må være et tall") from None
            calls.append(("number", "set_value", {"entity_id": eid, "value": max(n["min"], min(n["max"], x))}))
        else:
            if not isinstance(v, bool):
                raise ValueError("verdien må være true eller false")
            calls.append(("switch", "turn_on" if v else "turn_off", {"entity_id": eid}))
    if not calls:
        raise ValueError("ingen endringer")
    return calls


def wake_public(alarms: list) -> list:
    out = []
    for a in alarms:
        a = {k: v for k, v in a.items() if not k.startswith("_")}
        if a.get("person"):
            a["person"] = {k: v for k, v in a["person"].items() if not k.startswith("_")}
        out.append(a)
    return out


def set_backlight(pct: int, root: str = "/sys/class/backlight") -> bool:
    """Bakgrunnslys 0–100 %. Skjermer uten styrbart lys gir False, og skjermen dimmes da bare i grensesnittet."""
    pct = max(0, min(100, int(pct)))
    ok = False
    for d in glob.glob(os.path.join(root, "*")):
        try:
            with open(os.path.join(d, "max_brightness")) as f:
                mx = int(f.read().strip() or 255)
            with open(os.path.join(d, "brightness"), "w") as f:
                f.write(str(round(mx * pct / 100)))
            ok = True
        except (OSError, ValueError):
            pass
    return ok


class AlarmRing:
    """Alarmen som ringer akkurat nå. Lyden startes av vekkeklokka i daemonen; dette holder rede på skjermen og slumring."""

    def __init__(self, ctx: dict, clock=time.time):
        self.ctx, self.clock = ctx, clock
        self.on, self.snoozed, self.snooze_until, self.t = False, False, 0.0, 0.0
        self.alarm: dict = {}

    def start(self, alarm: dict, snoozed: bool = False):
        self.on, self.snoozed, self.snooze_until, self.t = True, snoozed, 0.0, self.clock()
        self.alarm = dict(alarm or {})
        self.ctx["changed"]()

    def snooze(self, minutes: int = SNOOZE_MIN):
        if not self.on:
            return
        self.on, self.snoozed, self.snooze_until = False, True, self.clock() + max(1, int(minutes)) * 60
        self._quiet()

    def stop(self):
        was = self.on or self.snooze_until
        self.on, self.snoozed, self.snooze_until = False, False, 0.0
        if was:
            self._quiet()

    def _quiet(self):
        try:
            if not self.alarm.get("test"):     # en test har ikke startet noe lyd, så la musikken være
                self.ctx["pause"]()
        except Exception as e:   # ingen lyd å stoppe er helt greit
            print("alarm: fikk ikke stoppet lyden:", e, flush=True)
        self.ctx["changed"]()

    def tick(self):
        now = self.clock()
        if self.snooze_until and now >= self.snooze_until:
            self.snooze_until = 0.0
            if not self.alarm.get("test"):
                self.ctx["fire"]({**self.alarm, "fade": 0})   # starter lyden igjen, uten myk oppstart
            self.start(self.alarm, snoozed=True)
        elif self.on and now - self.t > RING_MAX_S:
            self.on, self.snoozed = False, False
            self.ctx["changed"]()

    def status(self) -> dict:
        return {"ringing": self.on, "snoozed": self.snoozed, "name": str(self.alarm.get("name") or "") if (self.on or self.snooze_until) else "",
                "time": self.alarm.get("time", "") if (self.on or self.snooze_until) else "", "t": self.t,
                "snooze_until": self.snooze_until}


class Touch:
    def __init__(self, ctx: dict, path: str):
        self.ctx, self.path = ctx, path
        self.cfg = dict(DEFAULTS)
        try:
            with open(path) as f:
                self.cfg = clean(self.cfg, json.load(f))
        except (OSError, ValueError):
            pass
        self.ring = AlarmRing(ctx)
        self.cmd = {"cmd": "", "arg": "", "seq": 0}
        self.voice = {"state": "idle", "text": "", "reply": "", "t": 0.0}
        self._auto = {"t": 0.0, "tiles": [], "scenes": []}
        self._cache = {"t": 0.0, "data": None}
        self._wake = {"t": 0.0, "data": None}

    # --- oppsett
    def save(self, body: dict) -> dict:
        self.cfg = clean(self.cfg, body)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)
        self._cache["t"] = self._auto["t"] = 0.0
        return self.public()

    def ha(self) -> tuple:
        c = self.ctx["ha"]() or {}
        return str(c.get("ha_url") or "").rstrip("/"), str(c.get("ha_token") or "")

    def public(self) -> dict:
        url, tok = self.ha()
        c = dict(self.cfg)
        if c.get("homey_token"):
            c["homey_token"] = "••••••"
        return {**c, "ha": bool(url and tok), "homey": bool(self.cfg["homey_url"] and self.cfg["homey_token"])}

    # --- Homey
    def _homey(self, path: str, method: str = "GET", body=None, timeout: float = 6.0):
        url, tok = self.cfg["homey_url"], self.cfg["homey_token"]
        if not (url and tok):
            raise RuntimeError("Homey er ikke koblet til")
        req = urllib.request.Request(url + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    def _homey_devices(self) -> dict:
        d = self._homey("/api/manager/devices/device/")
        return d if isinstance(d, dict) else {str(x.get("id")): x for x in (d or [])}

    def _homey_smart(self) -> dict:
        if not (self.cfg["homey_url"] and self.cfg["homey_token"]):
            return {"ok": False, "hub": "Homey", "tiles": [], "scenes": [],
                    "error": "Koble til Homey: legg inn adressen og en API-nøkkel (Homey → Innstillinger → API-nøkler) med POST /api/touch."}
        try:
            alle = self._homey_devices()
            ids = list(self.cfg["homey_devices"]) or homey_pick(list(alle.values()))
            self._auto = {"t": time.time(), "tiles": ["homey:" + i for i in ids], "scenes": []}
            return {"ok": True, "hub": "Homey", "scenes": [], "auto": not self.cfg["homey_devices"], "lock": False,
                    "tiles": [homey_tile(alle[i]) for i in ids if i in alle]}
        except Exception as e:
            return {"ok": False, "hub": "Homey", "tiles": [], "scenes": [], "error": "Får ikke kontakt med Homey: " + str(e)[:120]}

    def _homey_press(self, tid: str, action: str, value=None) -> dict:
        did = tid.split(":", 1)[1]
        if tid not in set(self._auto["tiles"]) | {"homey:" + i for i in self.cfg["homey_devices"]}:
            raise ValueError("ukjent flis")
        dev = self._homey_devices().get(did)
        if not dev:
            raise ValueError("ukjent flis")
        cap, val = homey_action(dev, action, value)
        self._homey(f"/api/manager/devices/device/{did}/capability/{cap}", "PUT", {"value": val})
        if cap == "dim":                    # dimming slår ikke alltid på lyset av seg selv
            if not ((dev.get("capabilitiesObj") or {}).get("onoff") or {}).get("value"):
                self._homey(f"/api/manager/devices/device/{did}/capability/onoff", "PUT", {"value": True})
        time.sleep(0.25)
        return self.smart(fresh=True)

    # --- Home Assistant
    def _get(self, path: str, timeout: float = 5.0):
        url, tok = self.ha()
        if not (url and tok):
            raise RuntimeError("Home Assistant er ikke koblet til")
        req = urllib.request.Request(url + path, headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def _call(self, domain: str, service: str, data: dict):
        url, tok = self.ha()
        if not (url and tok):
            raise RuntimeError("Home Assistant er ikke koblet til")
        req = urllib.request.Request(url + f"/api/services/{domain}/{service}", data=json.dumps(data).encode(), method="POST",
                                     headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as r:
            r.read()

    def _state(self, eid: str) -> dict | None:
        try:
            return self._get("/api/states/" + eid, 4)
        except Exception:
            return None

    def smart(self, fresh: bool = False) -> dict:
        """Flisene og scenene til Smarthus-siden. Svaret hurtiglagres i 3 s, så skjermen kan spørre ofte."""
        now = time.time()
        if not fresh and self._cache["data"] and now - self._cache["t"] < 3:
            return self._cache["data"]
        if self.cfg["hub"] == "homey":
            out = self._homey_smart()
            self._cache = {"t": now, "data": out}
            return out
        url, tok = self.ha()
        if not (url and tok):
            return {"ok": False, "hub": "Home Assistant", "tiles": [], "scenes": [],
                    "error": "Koble til Home Assistant i appen: Innstillinger → Dørklokke → adresse og token."}
        try:
            want, scenes = list(self.cfg["tiles"]), list(self.cfg["scenes"])
            if not want:
                if now - self._auto["t"] > 600 or not self._auto["tiles"]:
                    t, sc = auto_pick(self._get("/api/states", 10))
                    self._auto = {"t": now, "tiles": t, "scenes": sc}
                want, scenes = self._auto["tiles"], scenes or self._auto["scenes"]
            tiles = [tile_of(s) for s in (self._state(e) for e in want) if s]
            sc = [{"id": e, "name": str(((self._state(e) or {}).get("attributes") or {}).get("friendly_name") or e.split(".", 1)[1])[:18]} for e in scenes]
            out = {"ok": True, "hub": "Home Assistant", "tiles": tiles, "scenes": sc, "auto": not self.cfg["tiles"],
                   "lock": bool(self.cfg["lock_entity"])}
        except Exception as e:
            out = {"ok": False, "hub": "Home Assistant", "tiles": [], "scenes": [], "error": "Får ikke kontakt med Home Assistant: " + str(e)[:120]}
        self._cache = {"t": now, "data": out}
        return out

    def press(self, eid: str, action: str, value=None) -> dict:
        if eid.startswith("homey:"):
            return self._homey_press(eid, action, value)
        allowed = set(self.cfg["tiles"] or self._auto["tiles"]) | set(self.cfg["scenes"] or self._auto["scenes"])
        if eid not in allowed:
            raise ValueError("ukjent flis")
        tgt = lo = hi = None
        if action in ("up", "down"):
            a = (self._state(eid) or {}).get("attributes") or {}
            tgt, lo, hi = a.get("temperature"), float(a.get("min_temp", 5)), float(a.get("max_temp", 30))
        self._call(*service_for(eid, action, tgt, lo or 5.0, hi or 30.0, value))
        time.sleep(0.25)          # gi HA et øyeblikk, så svaret viser den nye tilstanden
        return self.smart(fresh=True)

    # --- smart vekking (KI Søvn)
    def _wake_load(self) -> list:
        return wake_find(self._get("/api/states", 10))

    def wake(self, fresh: bool = False) -> dict:
        """Vekkealarmene fra KI Søvn i Home Assistant. Hurtiglagres i 3 s."""
        now = time.time()
        if not fresh and self._wake["data"] and now - self._wake["t"] < 3:
            return self._wake["data"]
        url, tok = self.ha()
        if not (url and tok):
            out = {"ok": False, "alarms": [], "error": "Koble til Home Assistant i appen: Innstillinger → Dørklokke → adresse og token."}
        else:
            try:
                out = {"ok": True, "alarms": wake_public(self._wake_load())}
            except Exception as e:
                out = {"ok": False, "alarms": [], "error": "Får ikke kontakt med Home Assistant: " + str(e)[:120]}
        self._wake = {"t": now, "data": out}
        return out

    def wake_set(self, wid: str, changes: dict) -> dict:
        al = next((a for a in self._wake_load() if a["id"] == wid), None)
        if not al:
            raise ValueError("ukjent vekkealarm")
        for c in wake_calls(al, changes):
            self._call(*c)
        time.sleep(0.3)
        return self.wake(fresh=True)

    def unlock(self) -> dict:
        eid = self.cfg["lock_entity"]
        if not eid.startswith("lock."):
            raise ValueError("ingen lås er satt opp")
        self._call("lock", "unlock", {"entity_id": eid})
        return {"ok": True}

    def morning(self) -> str:
        w = self._state(self.cfg["weather_entity"]) if self.cfg["weather_entity"] else None
        l = self._state(self.cfg["light_entity"]) if self.cfg["light_entity"] else None
        return morning_text(w, l)

    # --- data til standby-stilene på S1 (vær, sol, kalender, neste alarm)
    def home(self) -> dict:
        """Siste kjente data. Hentes på nytt i bakgrunnen hvert 5. minutt, så status aldri venter på Home Assistant."""
        h = self.__dict__.setdefault("_home", {"t": 0.0, "data": {}, "busy": False})
        if not h["busy"] and time.time() - h["t"] > 300 and all(self.ha()):
            h["busy"] = True
            threading.Thread(target=self._home_refresh, daemon=True).start()
        d = dict(h["data"])
        nxt = next_alarm(self.ctx["alarms"](), time.localtime())
        if nxt:
            d["alarm"] = nxt["time"]
        return d

    def _home_refresh(self):
        from datetime import date, datetime, timedelta, timezone
        h = self._home
        out = {}
        try:
            w, c = self.cfg["weather_entity"], self.cfg["calendar_entity"]
            if not (w and c):      # ikke valgt: bruk det første været og den første kalenderen i Home Assistant
                ids = [str(x.get("entity_id") or "") for x in self._get("/api/states", 10)]
                w = w or next((i for i in sorted(ids) if i.startswith("weather.")), "")
                c = c or next((i for i in sorted(ids) if i.startswith("calendar.")), "")
            if w:
                hourly = []
                try:
                    url, tok = self.ha()
                    req = urllib.request.Request(url + "/api/services/weather/get_forecasts?return_response", method="POST",
                                                 data=json.dumps({"entity_id": w, "type": "hourly"}).encode(),
                                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        hourly = ((json.loads(r.read()).get("service_response") or {}).get(w) or {}).get("forecast") or []
                except Exception:
                    pass          # eldre Home Assistant eller vær uten timevarsel: vis uten timene
                v = home_weather(self._state(w), hourly)
                if v:
                    out["weather"] = v
            s = home_sun(self._state("sun.sun"))
            if s:
                out["sun"] = s
            if c:
                now = datetime.now(timezone.utc)
                q = "?start=" + now.strftime("%Y-%m-%dT%H:%M:%SZ") + "&end=" + (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
                k = home_calendar(self._get("/api/calendars/" + c + q, 8), date.today())
                if k:
                    out["cal"] = k
        except Exception as e:
            print("Touch/S1: fikk ikke hentet vær og kalender:", str(e)[:120], flush=True)
        h.update(t=time.time(), data=out or h["data"], busy=False)
        self.ctx["changed"]()

    # --- skjerm og stemme
    def command(self, cmd: str, arg: str = "") -> dict:
        if cmd not in ("standby", "wake", "boot", "page"):
            raise ValueError("ukjent kommando")
        if cmd == "page" and arg not in PAGES:
            raise ValueError("ukjent side")
        self.cmd = {"cmd": cmd, "arg": arg, "seq": self.cmd["seq"] + 1}
        self.ctx["changed"]()
        return self.cmd

    def set_voice(self, state: str, text: str = "", reply: str = "") -> dict:
        if state not in ("idle", "listen", "think", "reply", "error"):
            raise ValueError("ukjent tilstand")
        v = self.voice
        self.voice = {"state": state, "text": (text or (v["text"] if state in ("think", "reply") else ""))[:300],
                      "reply": (reply or (v["reply"] if state == "reply" else ""))[:500], "t": time.time()}
        self.ctx["changed"]()
        return self.voice

    def status(self) -> dict:
        v = self.voice
        if v["state"] != "idle" and time.time() - v["t"] > 25:      # satellitten sa aldri fra at den var ferdig
            v = self.voice = {"state": "idle", "text": "", "reply": "", "t": 0.0}
        return {"alarm": {**self.ring.status(), "next": next_alarm(self.ctx["alarms"](), time.localtime())},
                "touch": {"cmd": self.cmd, "voice": v}}


def _systemctl(*a) -> bool:
    try:
        return subprocess.run(["systemctl", *a], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def voice_service(mic=None, wake=None, env="/etc/skjold-voice.env") -> dict:
    """Stemmesatellitten (skjold-voice.service): demp mikrofonen helt, eller bytt vekkeord."""
    if wake is not None:
        if wake not in WAKE_WORDS:
            raise ValueError("ukjent vekkeord")
        with open(env + ".tmp", "w") as f:
            f.write("WAKE_WORD=" + wake + "\n")
        os.replace(env + ".tmp", env)
        _systemctl("restart", "skjold-wakeword.service")
        _systemctl("try-restart", "skjold-voice.service")
    if mic is not None:
        _systemctl("start" if mic else "stop", "skjold-voice.service")
    return {"installed": os.path.exists("/etc/systemd/system/skjold-voice.service"), "running": _systemctl("is-active", "--quiet", "skjold-voice.service")}


def start_encoder(ctx: dict, spec: str):
    """Volumhjul (EC11). spec = «A,B» eller «A,B,SW» (BCM-pinner) fra KI_TOUCH_ENC. Uten spec skjer ingenting."""
    pins = [int(p) for p in spec.replace(" ", "").split(",") if p.isdigit()]
    if len(pins) < 2:
        return None
    from gpiozero import Button, RotaryEncoder
    enc = RotaryEncoder(pins[0], pins[1], max_steps=0)
    enc.when_rotated_clockwise = lambda: ctx["volume_step"](2)
    enc.when_rotated_counter_clockwise = lambda: ctx["volume_step"](-2)
    btn = None
    if len(pins) > 2:
        btn = Button(pins[2], pull_up=True, bounce_time=0.05)
        btn.when_pressed = lambda: ctx["playpause"]()
    return enc, btn


def mqtt_discovery(base: str, hid: str, dev: dict) -> list:
    """(topic, payload)-par for Home Assistant MQTT discovery: alarmen som ringer, Slå av, Slumre og skjerm av/på."""
    av = {"availability_topic": base + "/online", "device": dev}
    knapp = lambda key, navn, felt, verdi, ikon: (f"homeassistant/button/{hid}/{key}/config",
                                                  {"name": navn, "unique_id": f"{hid}_{key}", "command_topic": f"{base}/set/{felt}",
                                                   "payload_press": verdi, "icon": ikon, **av})
    return [
        (f"homeassistant/binary_sensor/{hid}/alarm/config",
         {"name": "Alarm ringer", "unique_id": f"{hid}_alarm", "state_topic": base + "/alarm", "payload_on": "ON", "payload_off": "OFF",
          "icon": "mdi:alarm", **av}),
        knapp("alarm_stop", "Slå av alarm", "alarm", "stop", "mdi:alarm-off"),
        knapp("alarm_snooze", "Slumre", "alarm", "snooze", "mdi:alarm-snooze"),
        knapp("screen_wake", "Vekk skjermen", "screen", "on", "mdi:monitor"),
        knapp("screen_standby", "Skjerm i standby", "screen", "off", "mdi:monitor-off"),
    ]


# ------------------------------------------------------------------ ruter
def routes(touch: Touch):
    import asyncio
    from aiohttp import web

    async def body(r) -> dict:
        try:
            b = await r.json()
        except Exception:
            b = {}
        return b if isinstance(b, dict) else {}

    def bg(fn, *a):
        return asyncio.get_running_loop().run_in_executor(None, fn, *a)

    def fail(e, status=400):
        return web.json_response({"error": str(e)}, status=status)

    async def h_touch(r):
        if r.method == "POST":
            try:
                return web.json_response(touch.save(await body(r)))
            except ValueError as e:
                return fail(e)
        return web.json_response(touch.public())

    async def h_smart(r):
        if r.method == "POST":
            b = await body(r)
            try:
                return web.json_response(await bg(touch.press, str(b.get("id") or ""), str(b.get("action") or "toggle"), b.get("value")))
            except (ValueError, TypeError) as e:
                return fail(e)
            except Exception as e:
                return fail("Home Assistant svarte ikke: " + str(e)[:120], 502)
        return web.json_response(await bg(touch.smart))

    async def h_wake(r):
        if r.method == "POST":
            b = await body(r)
            ch = b.get("set")
            try:
                if not isinstance(ch, dict):
                    raise ValueError("set må være et objekt")
                return web.json_response(await bg(touch.wake_set, str(b.get("id") or ""), ch))
            except (ValueError, TypeError) as e:
                return fail(e)
            except Exception as e:
                return fail("Home Assistant svarte ikke: " + str(e)[:120], 502)
        return web.json_response(await bg(touch.wake))

    async def h_unlock(_r):
        try:
            return web.json_response(await bg(touch.unlock))
        except ValueError as e:
            return fail(e, 409)
        except Exception as e:
            return fail("Home Assistant svarte ikke: " + str(e)[:120], 502)

    async def h_morning(_r):
        try:
            return web.json_response({"text": await bg(touch.morning)})
        except Exception:
            return web.json_response({"text": ""})

    async def h_alarm(r):
        if r.method == "POST":
            b = await body(r)
            act = str(b.get("action") or "")
            if act == "snooze":
                await bg(touch.ring.snooze, int(b.get("minutes") or SNOOZE_MIN))
            elif act == "stop":
                await bg(touch.ring.stop)
            elif act == "test":
                touch.ring.start({"name": str(b.get("name") or "Test"), "time": time.strftime("%H:%M"), "test": True})
            else:
                return fail("action må være snooze, stop eller test")
        return web.json_response(touch.status()["alarm"])

    async def h_voice(r):
        b = await body(r)
        try:
            if "mic" in b or "wake" in b:
                return web.json_response(await bg(lambda: voice_service(b.get("mic"), b.get("wake"))))
            if "state" in b:
                return web.json_response(touch.set_voice(str(b["state"]), str(b.get("text") or ""), str(b.get("reply") or "")))
            return web.json_response({**touch.voice, **await bg(voice_service)})
        except (ValueError, OSError) as e:
            return fail(e)

    async def h_cmd(r):
        b = await body(r)
        try:
            return web.json_response(touch.command(str(b.get("cmd") or ""), str(b.get("arg") or "")))
        except ValueError as e:
            return fail(e)

    async def h_backlight(r):
        b = await body(r)
        try:
            lvl = int(b.get("level"))
        except (TypeError, ValueError):
            return fail("level må være 0–100")
        return web.json_response({"ok": await bg(set_backlight, lvl), "level": max(0, min(100, lvl))})

    return [("GET", "/api/touch", h_touch), ("POST", "/api/touch", h_touch), ("GET", "/api/touch/smart", h_smart),
            ("POST", "/api/touch/smart", h_smart), ("GET", "/api/touch/wake", h_wake), ("POST", "/api/touch/wake", h_wake), ("POST", "/api/touch/unlock", h_unlock), ("GET", "/api/touch/morning", h_morning),
            ("GET", "/api/alarm", h_alarm), ("POST", "/api/alarm", h_alarm), ("GET", "/api/touch/voice", h_voice),
            ("POST", "/api/touch/voice", h_voice), ("POST", "/api/touch/cmd", h_cmd), ("POST", "/api/touch/backlight", h_backlight)]
