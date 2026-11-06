"""Skjold – hjem-ekstra: vekking med lys, tilstede-modus («Bortreise») og spillelister fra radio.

Egen modul så daemonen bare trenger små kroker. Rene funksjoner (wake_ramp, plan_presence, fuzzy, m3u) er testbare
uten nettverk; klassene får alt de trenger via ctx-dict fra ki_amp_daemon.py.
"""
import datetime as _dt
import json
import random
import re
import threading
import time
import unicodedata
import urllib.request

from aiohttp import web

# ---------------------------------------------------------------- felles: Home Assistant
def ha_call(url, token, domain, service, data, timeout=6):
    """POST /api/services/<domain>/<service>. Returnerer True ved 2xx."""
    req = urllib.request.Request(url.rstrip("/") + f"/api/services/{domain}/{service}", data=json.dumps(data).encode(),
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return 200 <= r.status < 300


# ---------------------------------------------------------------- vekking med lys
LIGHT_DEFAULTS = {"enabled": False, "entities": [], "minutes": 10, "step": 20, "ha_url": "", "ha_token": ""}


def wake_ramp(minutes=10, step_s=20, b0=1, b1=100, k0=2200, k1=4000):
    """Liste med (sekunder_fra_start, lysstyrke_%, kelvin) fra svakt varmt til fullt kaldere lys."""
    total = max(60, int(minutes * 60))
    step_s = max(15, min(30, int(step_s)))
    n = max(1, total // step_s)
    out = []
    for i in range(n + 1):
        f = i / n
        out.append((i * step_s if i < n else total, int(round(b0 + (b1 - b0) * f)), int(round(k0 + (k1 - k0) * f))))
    return out


def next_alarm_epoch(alarm, now):
    """Neste tidspunkt (epoch) alarmen går, fra og med now. None hvis av/ugyldig."""
    if not alarm.get("on", True) or not re.match(r"^\d\d:\d\d$", str(alarm.get("time") or "")):
        return None
    h, m = map(int, alarm["time"].split(":"))
    base = _dt.datetime.fromtimestamp(now).replace(hour=h, minute=m, second=0, microsecond=0)
    days = alarm.get("days") or []
    for add in range(8):
        d = base + _dt.timedelta(days=add)
        if d.timestamp() >= now - 1 and (not days or d.weekday() in days):
            return d.timestamp()
    return None


class WakeLight:
    """Starter lysrampe X min før alarmen. Stopper når alarmen slås av (strøm av etter alarmtid) eller via API."""

    def __init__(self, ctx, call=ha_call):
        self.ctx, self.call = ctx, call
        self.run = None          # {"alarm": epoch, "stop": Event}
        self.started = set()
        self.last = ""

    def cfg(self):
        a = self.ctx["alarm_cfg"]() or {}
        lc = {**LIGHT_DEFAULTS, **(a.get("light") or {})}
        ha = self.ctx.get("ha_fallback", lambda: {})() or {}
        lc["ha_url"] = lc.get("ha_url") or ha.get("ha_url", "")
        lc["ha_token"] = lc.get("ha_token") or ha.get("ha_token", "")
        return a, lc

    def tick(self, now=None):
        now = now or time.time()
        a, lc = self.cfg()
        if not (a.get("enabled") and lc["enabled"] and lc["entities"] and lc["ha_url"] and lc["ha_token"]):
            return
        lead = max(1, int(lc["minutes"])) * 60
        for al in a.get("alarms") or []:
            t = next_alarm_epoch(al, now)
            if t and t - lead <= now < t and t not in self.started and not self.run:
                self.started.add(t)
                self.start(t, lc)
        if len(self.started) > 50:
            self.started = set(sorted(self.started)[-10:])

    def start(self, alarm_t, lc):
        ev = threading.Event()
        self.run = {"alarm": alarm_t, "stop": ev}
        threading.Thread(target=self._ramp, args=(alarm_t, lc, ev), daemon=True).start()

    def _ramp(self, alarm_t, lc, ev):
        t0 = time.time()
        ramp = wake_ramp(max(1, (alarm_t - t0) / 60), lc.get("step", 20))
        try:
            for sec, b, k in ramp:
                while time.time() < t0 + sec:
                    if ev.wait(1):
                        return
                for ent in lc["entities"]:
                    try:
                        self.call(lc["ha_url"], lc["ha_token"], "light", "turn_on",
                                  {"entity_id": ent, "brightness_pct": b, "color_temp_kelvin": k, "transition": 5})
                    except Exception as e:
                        self.last = f"HA-feil: {e}"
                self.last = f"Lys {b} % · {k} K"
            # hold lyset til alarmen er slått av (strøm av) eller stoppet
            while not ev.wait(5):
                if not self.ctx["power"]():
                    return
        finally:
            self.run = None

    def stop(self):
        if self.run:
            self.run["stop"].set()
            return True
        return False

    def status(self):
        return {"active": bool(self.run), "alarm": self.run and self.run["alarm"], "last": self.last}


# ---------------------------------------------------------------- tilstede-modus
PRESENCE_DEFAULTS = {"source": "favorites", "start": "07:00", "end": "23:00", "min_on": 10, "max_on": 60,
                     "min_off": 15, "max_off": 120, "volume": 15, "rooms": [], "rotate": False, "seed": 0}
TALK_URL = "https://lyd.nrk.no/nrk_radio_p2_aac_h"


def _mins(hm):
    h, m = map(int, str(hm).split(":"))
    return h * 60 + m


def plan_presence(date_str, cfg, seed=None):
    """Dagsplan: liste med {start, end (minutter etter midnatt), room}. Deterministisk for (dato, seed)."""
    c = {**PRESENCE_DEFAULTS, **(cfg or {})}
    rnd = random.Random(f"{date_str}|{c['seed'] if seed is None else seed}")
    t, end = _mins(c["start"]), _mins(c["end"])
    rooms = list(c.get("rooms") or [])
    t += rnd.randint(0, max(0, int(c["min_off"])))
    out = []
    i = 0
    while t < end:
        dur = rnd.randint(int(c["min_on"]), max(int(c["min_on"]), int(c["max_on"])))
        e = min(end, t + dur)
        if e - t >= 5:
            room = (rooms[i % len(rooms)] if c.get("rotate") else rooms[0]) if rooms else ""
            out.append({"start": t, "end": e, "room": room})
            i += 1
        t = e + rnd.randint(int(c["min_off"]), max(int(c["min_off"]), int(c["max_off"])))
    return out


def hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


class Presence:
    def __init__(self, ctx):
        self.ctx = ctx
        self.active = None   # gjeldende økt

    def cfg(self):
        return {**PRESENCE_DEFAULTS, **(self.ctx["plug_cfg"]() or {})}

    def today(self, now=None):
        return plan_presence(time.strftime("%Y-%m-%d", time.localtime(now or time.time())), self.cfg())

    def next_session(self, now=None):
        now = now or time.time()
        lt = time.localtime(now)
        cur = lt.tm_hour * 60 + lt.tm_min
        for s in self.today(now):
            if s["end"] > cur:
                return s
        return None

    def tick(self, now=None):
        now = now or time.time()
        c = self.cfg()
        if not c.get("enabled"):
            if self.active:
                self._end()
            return
        lt = time.localtime(now)
        cur = lt.tm_hour * 60 + lt.tm_min
        s = next((x for x in self.today(now) if x["start"] <= cur < x["end"]), None)
        if s and not self.active:
            self.active = s
            self._begin(c, s)
        elif not s and self.active:
            self._end()

    def _begin(self, c, s):
        try:
            self.ctx["power_set"](True)
            self.ctx["volume_set"](max(0, min(40, int(c.get("volume", 15)))))
            src = c.get("source")
            if src == "p1":
                self.ctx["play_url"](self.ctx["nrk_p1"], "NRK P1")
            elif src == "talk":
                self.ctx["play_url"](TALK_URL, "NRK P2")
            else:
                pres = [i + 1 for i, p in enumerate(self.ctx["presets"]() or []) if p]
                if pres:
                    self.ctx["play_preset"](random.choice(pres))
                else:
                    self.ctx["play_url"](self.ctx["nrk_p1"], "NRK P1")
        except Exception as e:
            print("Tilstede-modus:", e, flush=True)

    def _end(self):
        self.active = None
        try:
            self.ctx["power_set"](False)
        except Exception:
            pass

    def set_enabled(self, on):
        c = self.ctx["plug_cfg"]() or {}
        c["enabled"] = bool(on)
        self.ctx["plug_save"](c)
        if not on and self.active:
            self._end()

    def status(self):
        c = self.cfg()
        if not c.get("enabled"):
            return "Av"
        if self.active:
            return f"Spiller til {hm(self.active['end'])}" + (f" ({self.active['room']})" if self.active["room"] else "")
        n = self.next_session()
        return f"Neste økt {hm(n['start'])}–{hm(n['end'])}" if n else "Ingen flere økter i dag"


# ---------------------------------------------------------------- spillelister fra radio
def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)|\[.*?\]|feat\.?.*$|ft\..*$|- remaster.*$", " ", s)
    return " ".join(re.sub(r"[^a-z0-9æøå ]+", " ", s).split())


def similarity(a, b):
    """Token-basert likhet 0–1 (Jaccard + prefiks-bonus)."""
    ta, tb = set(norm(a).split()), set(norm(b).split())
    if not ta or not tb:
        return 0.0
    j = len(ta & tb) / len(ta | tb)
    return min(1.0, j + (0.15 if norm(a).startswith(norm(b)[:6]) else 0))


def best_match(want, songs, threshold=0.6):
    best, score = None, 0.0
    for s in songs:
        sc = 0.6 * similarity(want.get("title"), s.get("title")) + 0.4 * similarity(want.get("artist"), s.get("artist"))
        if sc > score:
            best, score = s, sc
    return (best, score) if score >= threshold else (None, score)


def m3u(tracks):
    lines = ["#EXTM3U"]
    for t in tracks:
        lines.append(f"#EXTINF:{int(t.get('duration') or -1)},{t.get('artist', '')} - {t.get('title', '')}")
        lines.append(t.get("path") or t.get("url") or f"{t.get('artist', '')} - {t.get('title', '')}")
    return "\n".join(lines) + "\n"


class RadioLists:
    def __init__(self, ctx):
        self.ctx = ctx
        self.last = {}

    def tracks_from(self, source, channel=""):
        """source: 'recordings' (låter gjenkjent i opptak / historikk for kanal) eller 'wishlist'."""
        if source == "wishlist":
            return [{"title": w.get("title"), "artist": w.get("artist")} for w in (self.ctx["wishlist"]() or [])]
        out, seen = [], set()
        for h in self.ctx["history"]() or []:
            where = " ".join(str(h.get(k) or "") for k in ("station", "album", "source", "input")).lower()
            if channel and channel.lower() not in where:
                continue
            t, a = h.get("track") or h.get("title") or "", h.get("artist") or ""
            if t and a and (norm(t), norm(a)) not in seen:
                seen.add((norm(t), norm(a)))
                out.append({"title": t, "artist": a})
        return out

    def build(self, source="recordings", channel="", name=None, scan=True):
        nd = self.ctx["subsonic"]()
        name = name or ("Gjenkjent" if source == "wishlist" else f"Fra radio – {channel or 'alle kanaler'}")
        want = self.tracks_from(source, channel)
        if scan:
            try: nd._call("startScan")
            except Exception: pass
        found, missing = [], []
        for w in want:
            try:
                r = nd._call("search3", query=f"{w['artist']} {w['title']}", songCount=10, artistCount=0, albumCount=0)
                songs = ((r.get("searchResult3") or {}).get("song")) or []
            except Exception:
                songs = []
            s, _sc = best_match(w, songs)
            (found if s else missing).append({**w, **({"id": s["id"], "path": s.get("path"), "duration": s.get("duration")} if s else {})})
        pid = None
        try:
            lists = ((nd._call("getPlaylists").get("playlists") or {}).get("playlist")) or []
            pid = next((p["id"] for p in lists if p.get("name") == name), None)
            if pid:
                nd._call("deletePlaylist", id=pid)
            if found:
                nd._call("createPlaylist", name=name, songId=[f["id"] for f in found])
        except Exception as e:
            print("Spilleliste fra radio:", e, flush=True)
        self.last = {"name": name, "found": found, "missing": missing, "time": time.time()}
        return {"name": name, "found": len(found), "missing": len(missing), "missingList": missing[:50]}


# ---------------------------------------------------------------- ruter
def routes(ctx):
    wl = WakeLight(ctx)
    pr = Presence(ctx)
    rl = RadioLists(ctx)
    ctx["wakelight"], ctx["presence"], ctx["radiolists"] = wl, pr, rl

    def loop():
        while True:
            for f in (wl.tick, pr.tick):
                try: f()
                except Exception as e: print("hjem-ekstra:", e, flush=True)
            time.sleep(20)
    threading.Thread(target=loop, daemon=True).start()

    async def h_wake(r):
        if r.method == "POST":
            b = await r.json()
            if b.get("stop"): wl.stop()
        return web.json_response(wl.status())

    async def h_presence(r):
        if r.method == "POST":
            b = await r.json()
            if "on" in b: pr.set_enabled(bool(b["on"]))
        lt = time.localtime()
        return web.json_response({"enabled": bool(pr.cfg().get("enabled")), "status": pr.status(),
                                  "plan": [{"start": hm(s["start"]), "end": hm(s["end"]), "room": s["room"]} for s in pr.today()],
                                  "now": "%02d:%02d" % (lt.tm_hour, lt.tm_min)})

    async def h_radiolist(r):
        if r.method == "POST":
            b = await r.json()
            import asyncio
            res = await asyncio.get_running_loop().run_in_executor(
                None, lambda: rl.build(b.get("source", "recordings"), b.get("channel", ""), b.get("name")))
            return web.json_response(res)
        if r.query.get("m3u"):
            tr = rl.last.get("found", []) + ([] if r.query.get("m3u") == "found" else rl.last.get("missing", []))
            return web.Response(text=m3u(tr), content_type="audio/x-mpegurl",
                                headers={"Content-Disposition": f'attachment; filename="{rl.last.get("name", "skjold")}.m3u"'})
        last = rl.last
        return web.json_response({"name": last.get("name"), "found": len(last.get("found", [])), "missing": len(last.get("missing", [])),
                                  "missingList": last.get("missing", [])[:50]})

    return [web.get("/api/wakelight", h_wake), web.post("/api/wakelight", h_wake),
            web.get("/api/presence", h_presence), web.post("/api/presence", h_presence),
            web.get("/api/radiolist", h_radiolist), web.post("/api/radiolist", h_radiolist)]
