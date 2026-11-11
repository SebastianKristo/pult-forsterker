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

DEFAULTS = {"tiles": [], "scenes": [], "lock_entity": "", "weather_entity": "", "light_entity": ""}
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
        if isinstance(DEFAULTS[k], list):
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


def service_for(eid: str, action: str, target=None, lo=5.0, hi=30.0) -> tuple:
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
        return {**self.cfg, "ha": bool(url and tok)}

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
        url, tok = self.ha()
        if not (url and tok):
            return {"ok": False, "hub": "Home Assistant", "tiles": [], "scenes": [],
                    "error": "Koble til Home Assistant i appen: Innstillinger → Dørklokke → adresse og token."}
        now = time.time()
        if not fresh and self._cache["data"] and now - self._cache["t"] < 3:
            return self._cache["data"]
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

    def press(self, eid: str, action: str) -> dict:
        allowed = set(self.cfg["tiles"] or self._auto["tiles"]) | set(self.cfg["scenes"] or self._auto["scenes"])
        if eid not in allowed:
            raise ValueError("ukjent flis")
        tgt = lo = hi = None
        if action in ("up", "down"):
            a = (self._state(eid) or {}).get("attributes") or {}
            tgt, lo, hi = a.get("temperature"), float(a.get("min_temp", 5)), float(a.get("max_temp", 30))
        self._call(*service_for(eid, action, tgt, lo or 5.0, hi or 30.0))
        time.sleep(0.25)          # gi HA et øyeblikk, så svaret viser den nye tilstanden
        return self.smart(fresh=True)

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
                return web.json_response(await bg(touch.press, str(b.get("id") or ""), str(b.get("action") or "toggle")))
            except ValueError as e:
                return fail(e)
            except Exception as e:
                return fail("Home Assistant svarte ikke: " + str(e)[:120], 502)
        return web.json_response(await bg(touch.smart))

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
            ("POST", "/api/touch/smart", h_smart), ("POST", "/api/touch/unlock", h_unlock), ("GET", "/api/touch/morning", h_morning),
            ("GET", "/api/alarm", h_alarm), ("POST", "/api/alarm", h_alarm), ("GET", "/api/touch/voice", h_voice),
            ("POST", "/api/touch/voice", h_voice), ("POST", "/api/touch/cmd", h_cmd), ("POST", "/api/touch/backlight", h_backlight)]
