"""Skjold Mini – små ESP32-S3-høyttalere (squeezelite-esp32) som rom i Skjold.

En Mini er en vanlig Squeezebox-spiller i Lyrion. Daemonen finner dem i Lyrions spillerliste og lar deg
koble dem til dette rommet (Lyrion-synk = sample-nøyaktig avspilling), styre volum og slå av/på.
Ingen egen protokoll – alt går gjennom Lyrions JSON-RPC som daemonen allerede bruker.

API:  GET /api/mini → {lyrion, minis:[{id, name, ip, connected, power, playing, volume, synced, model}]}
      POST /api/mini {id, action: sync|unsync|volume|power, value}
      POST /api/mini {id, action: "presets", value: [n1, n2, n3, n4]}   legg Skjolds radiofavoritter n1–n4 på
           Mini-ens knapper 1–4 (Lyrion-presets via «jivefavorites set_preset»; knappene sender BCTRLS_PS1–4)
"""
BUTTONS = 4   # favorittknapper på fronten

MODEL_HINTS = ("squeezeesp32", "esp32", "squeezelite-esp32")


def is_mini(p):
    """Er denne Lyrion-spilleren en Skjold Mini? Navnet «Skjold Mini …» eller squeezelite-esp32-modell."""
    name = str(p.get("name") or "").lower()
    model = (str(p.get("modelname") or "") + " " + str(p.get("model") or "")).lower()
    return name.startswith("skjold mini") or any(h in model for h in MODEL_HINTS)


def parse_players(res, own_id="", sync_ids=()):
    """Lyrion «players 0 100»-svar → liste over Mini-er (eget rom utelatt)."""
    out = []
    own = (own_id or "").lower()
    synced = {s.lower() for s in sync_ids}
    for p in (res or {}).get("players_loop") or []:
        pid = str(p.get("playerid") or "").lower()
        if not pid or pid == own or not is_mini(p):
            continue
        out.append({"id": pid, "name": p.get("name") or "Skjold Mini", "ip": str(p.get("ip") or "").split(":")[0],
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
    """Skjolds radiofavoritter (state["presets"], 1-basert «n») → Lyrion-kommandoer for Mini-ens knapper 1–4.
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
        return own_id, ["sync", "{id}"]          # Mini-en blir med i dette rommets synkgruppe
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
