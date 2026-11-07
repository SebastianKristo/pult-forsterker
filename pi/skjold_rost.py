"""Skjold Røst – små ESP32-S3-høyttalere (squeezelite-esp32) som rom i Skjold.

En Røst er en vanlig Squeezebox-spiller i Lyrion. Daemonen finner dem i Lyrions spillerliste og lar deg
koble dem til dette rommet (Lyrion-synk = sample-nøyaktig avspilling), styre volum og slå av/på.
Ingen egen protokoll – alt går gjennom Lyrions JSON-RPC som daemonen allerede bruker.

API:  GET /api/rost (gammelt navn /api/mini virker også) → {lyrion, minis:[{id, name, ip, connected, power, playing, volume, synced, model}]}
      POST /api/mini {id, action: sync|unsync|volume|power, value}
      POST /api/mini {id, action: "presets", value: [n1, n2, n3, n4]}   legg Skjolds radiofavoritter n1–n4 på
           høyttalerens knapper 1–4 (Lyrion-presets via «jivefavorites set_preset»; knappene sender BCTRLS_PS1–4)
      GET/POST /api/rost/dusj {på, favoritt, minutter}   dusj-modus: langt trykk på ⏻ (BCTRLS_PS5) spiller favoritten
           og slår høyttaleren av etter «minutter» (myk nedtoning de siste 30 s)
"""
import json
import os
import time

BUTTONS = 4   # favorittknapper på fronten

MODEL_HINTS = ("squeezeesp32", "esp32", "squeezelite-esp32")


def is_mini(p):
    """Er denne Lyrion-spilleren en Skjold Røst? Navnet «Skjold Røst …» (også ASCII «Skjold Rost …»/«Skjold-Rost» fra fastvaren og gamle «Skjold Mini …») eller squeezelite-esp32-modell."""
    name = str(p.get("name") or "").lower()
    model = (str(p.get("modelname") or "") + " " + str(p.get("model") or "")).lower()
    return name.replace("-", " ").replace("_", " ").startswith(("skjold røst", "skjold rost", "skjold mini")) or any(h in model for h in MODEL_HINTS)


def parse_players(res, own_id="", sync_ids=()):
    """Lyrion «players 0 100»-svar → liste over Røst-høyttalere (eget rom utelatt)."""
    out = []
    own = (own_id or "").lower()
    synced = {s.lower() for s in sync_ids}
    for p in (res or {}).get("players_loop") or []:
        pid = str(p.get("playerid") or "").lower()
        if not pid or pid == own or not is_mini(p):
            continue
        out.append({"id": pid, "name": p.get("name") or "Skjold Røst", "ip": str(p.get("ip") or "").split(":")[0],
                    "connected": bool(int(p.get("connected") or 0)), "power": bool(int(p.get("power") or 0)),
                    "playing": bool(int(p.get("isplaying") or 0)), "model": p.get("modelname") or p.get("model") or "",
                    "volume": None, "synced": pid in synced})
    out.sort(key=lambda m: m["name"].lower())
    return out


def parse_sync(res):
    """«sync ?»-svar → liste over spiller-ID-er i samme synkgruppe."""
    v = (res or {}).get("_sync") or ""
    return [] if v in ("", "-") else [s.strip() for s in str(v).split(",") if s.strip()]


def preset_commands(presets, picks):
    """Skjolds radiofavoritter (state["presets"], 1-basert «n») → Lyrion-kommandoer for høyttalerens knapper 1–4.
    picks: liste med favorittnumre i knapperekkefølge (0/None = tom knapp)."""
    cmds = []
    for key, n in enumerate(list(picks or [])[:BUTTONS], 1):
        try:
            p = presets[int(n) - 1] if n else None
        except (ValueError, TypeError, IndexError):
            p = None
        if p and p.get("url"):
            cmds.append(["jivefavorites", "set_preset", f"key:{key}", f"favorites_url:{p['url']}",
                         f"favorites_title:{p.get('title') or 'Radio'}", "favorites_type:audio"])
    return cmds


def command(action, own_id, value=None):
    """→ (spiller, Lyrion-kommando) for en handling. own_id er dette rommets spiller."""
    if action == "sync":
        return own_id, ["sync", "{id}"]          # høyttaleren blir med i dette rommets synkgruppe
    if action == "unsync":
        return "{id}", ["sync", "-"]
    if action == "volume":
        v = max(0, min(100, int(value if value is not None else 30)))
        return "{id}", ["mixer", "volume", str(v)]
    if action == "power":
        return "{id}", ["power", "1" if value else "0"]
    raise ValueError("ukjent handling")


class Minis:
    def __init__(self, rpc, own_id, presets=lambda: []):
        """rpc(player_id, cmd) → resultat; own_id() → dette rommets Lyrion-spiller; presets() → Skjolds radiofavoritter."""
        self.rpc, self.own_id, self.presets = rpc, own_id, presets

    def list(self):
        own = self.own_id() or ""
        try:
            res = self.rpc("", ["players", "0", "100"])
        except Exception as e:
            return {"lyrion": False, "minis": [], "error": str(e)}
        try:
            sync = parse_sync(self.rpc(own, ["sync", "?"])) if own else []
        except Exception:
            sync = []
        minis = parse_players(res, own, sync)
        for m in minis:
            if m["connected"]:
                try:
                    m["volume"] = int(float(self.rpc(m["id"], ["mixer", "volume", "?"]).get("_volume", 0)))
                except Exception:
                    pass
        return {"lyrion": True, "minis": minis}

    def act(self, b):
        mid = str(b.get("id") or "").lower()
        if not mid:
            raise ValueError("mangler id")
        if b.get("action") == "presets":
            cmds = preset_commands(self.presets(), b.get("value") or [1, 2, 3, 4])
            if not cmds:
                raise ValueError("ingen radiofavoritter å legge på knappene")
            for c in cmds:
                self.rpc(mid, c)
            return self.list()
        player, cmd = command(str(b.get("action") or ""), self.own_id() or "", b.get("value"))
        self.rpc(mid if player == "{id}" else player, [mid if c == "{id}" else c for c in cmd])
        return self.list()


# ---------- dusj-modus: langt trykk på ⏻ ----------
DUSJ_KEY = 5            # fastvaren sender BCTRLS_PS5 ved langt trykk på ⏻ (firmware/rost/lag_firmware.py)
FADE_S = 30


class Dusj:
    """Langt trykk på ⏻ på en Røst → Lyrion spiller preset 5 = dusj-favoritten. Daemonen ser at Røst-en spiller den
    adressen, starter en nedtelling, toner ned de siste 30 sekundene og slår høyttaleren av (volumet settes tilbake,
    så neste avspilling starter som før)."""

    STD = {"på": True, "favoritt": 1, "minutter": 15}

    def __init__(self, minis, path=None, now=time.time):
        self.minis, self.path, self.now = minis, path, now
        self.cfg = dict(self.STD)
        self.aktive = {}      # spiller-id → {"slutt": t, "vol": opprinnelig volum}
        if path and os.path.exists(path):
            try:
                self.cfg.update({k: v for k, v in json.load(open(path)).items() if k in self.STD})
            except Exception:
                pass

    def url(self):
        try:
            p = self.minis.presets()[int(self.cfg["favoritt"]) - 1]
        except (ValueError, TypeError, IndexError):
            return ""
        return (p or {}).get("url") or ""

    def sett(self, b):
        if "på" in b:
            self.cfg["på"] = bool(b["på"])
        if b.get("favoritt") is not None:
            self.cfg["favoritt"] = max(1, int(b["favoritt"]))
        if b.get("minutter") is not None:
            self.cfg["minutter"] = max(1, min(120, int(b["minutter"])))
        if self.path:
            with open(self.path + ".tmp", "w") as f:
                json.dump(self.cfg, f)
            os.replace(self.path + ".tmp", self.path)
        self.legg_paa_preset()
        return self.status()

    def legg_paa_preset(self):
        """Legg dusj-favoritten på preset 5 på alle Røst-ene (kalles ved endring og jevnlig)."""
        if not self.cfg["på"]:
            return 0
        cmds = preset_commands(self.minis.presets(), [self.cfg["favoritt"]])
        if not cmds:
            return 0
        cmd = [c if not str(c).startswith("key:") else f"key:{DUSJ_KEY}" for c in cmds[0]]
        n = 0
        for m in self.minis.list().get("minis", []):
            if m.get("connected"):
                try:
                    self.minis.rpc(m["id"], cmd)
                    n += 1
                except Exception:
                    pass
        return n

    def status(self):
        t = self.now()
        return {**self.cfg, "aktive": {k: max(0, int(v["slutt"] - t)) for k, v in self.aktive.items()}}

    def tick(self):
        """Kalles hvert 5. sekund av daemonen."""
        if not self.cfg["på"]:
            self.aktive.clear()
            return
        url, t = self.url(), self.now()
        for m in self.minis.list().get("minis", []):
            pid = m["id"]
            a = self.aktive.get(pid)
            if a is None:
                if not (m.get("playing") and url):
                    continue
                try:
                    path = str(self.minis.rpc(pid, ["path", "?"]).get("_path") or "")
                except Exception:
                    continue
                if path == url:
                    self.aktive[pid] = {"slutt": t + self.cfg["minutter"] * 60, "vol": m.get("volume") or 30}
                continue
            if not m.get("power") or not m.get("playing"):
                self.aktive.pop(pid, None)          # slått av eller stoppet manuelt
                continue
            igjen = a["slutt"] - t
            if igjen <= 0:
                try:
                    self.minis.rpc(pid, ["power", "0"])
                    self.minis.rpc(pid, ["mixer", "volume", str(a["vol"])])
                except Exception:
                    pass
                self.aktive.pop(pid, None)
            elif igjen < FADE_S:
                try:
                    self.minis.rpc(pid, ["mixer", "volume", str(int(a["vol"] * igjen / FADE_S))])
                except Exception:
                    pass
