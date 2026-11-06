"""Skjold Mini – små ESP32-S3-høyttalere (squeezelite-esp32) som rom i Skjold.

En Mini er en vanlig Squeezebox-spiller i Lyrion. Daemonen finner dem i Lyrions spillerliste og lar deg
koble dem til dette rommet (Lyrion-synk = sample-nøyaktig avspilling), styre volum og slå av/på.
Ingen egen protokoll – alt går gjennom Lyrions JSON-RPC som daemonen allerede bruker.

API:  GET /api/mini → {lyrion, minis:[{id, name, ip, connected, power, playing, volume, synced, model}]}
      POST /api/mini {id, action: sync|unsync|volume|power, value}
"""

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
    def __init__(self, rpc, own_id):
        """rpc(player_id, cmd) → resultat; own_id() → dette rommets Lyrion-spiller."""
        self.rpc, self.own_id = rpc, own_id

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
        player, cmd = command(str(b.get("action") or ""), self.own_id() or "", b.get("value"))
        self.rpc(mid if player == "{id}" else player, [mid if c == "{id}" else c for c in cmd])
        return self.list()
