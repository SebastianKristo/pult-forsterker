"""Music Assistant (MA 2.x) som kilde for Skjold.

MA har ett felles bibliotek for TIDAL, Qobuz, Deezer, Spotify, YouTube Music, Plex, Jellyfin, podkaster m.m. Skjold
snakker med MA over WebSocket-API-et (ws://<host>:8095/ws) og ber MA spille på MA-spilleren som er denne Skjold-en –
enten via MA sin Squeezelite/Slimproto-provider (Skjold er en Squeezebox-spiller i Lyrion) eller via DLNA/AirPlay.

API-et i MA er versjonert og feltnavn varierer litt mellom versjoner, så alt her leses tolerant.
Daemonen kobler modulen inn med `routes(ctx)` (se ki_amp_daemon.py). Ingen andre avhengigheter enn websocket-client
(python3-websocket, finnes allerede for CamillaDSP) – den importeres først når den trengs.
"""
from __future__ import annotations

import itertools
import json
import re
import socket
import threading
import time

PORT = 8095
KINDS = {"albums": "album", "artists": "artist", "playlists": "playlist", "tracks": "track",
         "radio": "radio", "podcasts": "podcast", "audiobooks": "audiobook"}
# leverandørens domene i MA → merke i appene
PROVIDERS = {"tidal": "TIDAL", "qobuz": "Qobuz", "deezer": "Deezer", "spotify": "Spotify", "ytmusic": "YouTube Music",
             "youtube_music": "YouTube Music", "plex": "Plex", "jellyfin": "Jellyfin", "subsonic": "Subsonic",
             "opensubsonic": "Navidrome", "filesystem_local": "Lokale filer", "filesystem_smb": "NAS",
             "tunein": "TuneIn", "radiobrowser": "Radio Browser", "soundcloud": "SoundCloud", "apple_music": "Apple Music",
             "podcastfeed": "Podkast", "audible": "Audible", "builtin": "Music Assistant", "library": "Bibliotek"}


class MAError(RuntimeError):
    pass


def base_url(addr: str) -> tuple[str, str]:
    """«192.168.1.5», «ma.local:8095», «http://ma:8095/» → (ws-URL, http-URL)."""
    a = (addr or "").strip().rstrip("/")
    if not a:
        raise MAError("Music Assistant-adresse mangler")
    a = re.sub(r"^wss?://", "http://", a)
    if not re.match(r"^https?://", a):
        a = "http://" + a
    a = re.sub(r"/ws$", "", a)
    host = re.sub(r"^https?://", "", a)
    if ":" not in host.split("/")[0]:
        a += f":{PORT}"
    return re.sub(r"^http", "ws", a) + "/ws", a


class Client:
    """Én kortvarig WebSocket-tilkobling per forespørselsrunde (MA lukker ikke-autentiserte klienter raskt)."""

    def __init__(self, addr: str, token: str = "", timeout: float = 8.0, connect=None):
        self.ws_url, self.http_url = base_url(addr)
        self.token = (token or "").strip()
        self.timeout = timeout
        self._connect = connect          # tester: fn(url, timeout) -> obj med send/recv/close
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self.server_info: dict = {}

    def _open(self):
        if self._connect:
            return self._connect(self.ws_url, self.timeout)
        try:
            import websocket  # python3-websocket / websocket-client
        except Exception as e:  # pragma: no cover
            raise MAError(f"python3-websocket mangler ({e})")
        try:
            return websocket.create_connection(self.ws_url, timeout=self.timeout)
        except Exception as e:
            raise MAError(f"får ikke kontakt med Music Assistant på {self.ws_url}: {e}")

    def call_many(self, calls: list[tuple[str, dict]]) -> list:
        with self._lock:
            ws = self._open()
            try:
                first = _loads(ws.recv())           # server_info sendes først
                if isinstance(first, dict) and "server_version" in first:
                    self.server_info = first
                if self.token:
                    self._roundtrip(ws, "auth", {"token": self.token}, allow_fail=True)
                return [self._roundtrip(ws, cmd, args) for cmd, args in calls]
            finally:
                try:
                    ws.close()
                except Exception:
                    pass

    def call(self, cmd: str, **args):
        return self.call_many([(cmd, args)])[0]

    def _roundtrip(self, ws, cmd, args, allow_fail=False):
        mid = str(next(self._ids))
        ws.send(json.dumps({"message_id": mid, "command": cmd, "args": args}))
        parts: list = []
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            msg = _loads(ws.recv())
            if not isinstance(msg, dict) or str(msg.get("message_id")) != mid:
                continue                            # hendelser og andre svar
            if "error_code" in msg or msg.get("error"):
                if allow_fail:
                    return None
                raise MAError(str(msg.get("details") or msg.get("error") or msg.get("error_code")))
            res = msg.get("result")
            if msg.get("partial"):                  # store lister kommer i biter
                parts.extend(res or [])
                continue
            if parts:
                return parts + (res or [])
            return res
        raise MAError(f"Music Assistant svarte ikke på {cmd}")


def _loads(raw):
    try:
        return json.loads(raw)
    except Exception:
        return None


# ---------- normalisering til ett enkelt format for web og apper ----------

def _img(item: dict, http_url: str) -> str:
    md = item.get("metadata") or {}
    imgs = md.get("images") or item.get("images") or []
    for im in imgs if isinstance(imgs, list) else []:
        if not isinstance(im, dict):
            continue
        if im.get("type", "thumb") in ("thumb", "front", "cover", None):
            p = im.get("path") or im.get("url") or ""
            if not p:
                continue
            if im.get("remotely_accessible") or p.startswith("http"):
                return p
            # bilder som bare MA kan nå, hentes via MA sin imageproxy
            from urllib.parse import quote
            return f"{http_url}/imageproxy?path={quote(p, safe='')}&provider={quote(str(im.get('provider', '')))}&size=300"
    img = item.get("image")
    if isinstance(img, dict):
        return _img({"metadata": {"images": [img]}}, http_url)
    return img if isinstance(img, str) else ""


def _provider(item: dict) -> str:
    for m in item.get("provider_mappings") or []:
        dom = str(m.get("provider_domain") or m.get("provider_instance") or "").split("--")[0]
        if dom and dom not in ("library",):
            return PROVIDERS.get(dom, dom.replace("_", " ").title())
    dom = str(item.get("provider") or "").split("--")[0]
    return PROVIDERS.get(dom, dom.title() if dom else "")


def _artists(item: dict) -> str:
    a = item.get("artists") or []
    names = [x.get("name", "") if isinstance(x, dict) else str(x) for x in a]
    if not names and isinstance(item.get("artist"), dict):
        names = [item["artist"].get("name", "")]
    return ", ".join(n for n in names if n)


def norm(item: dict, http_url: str = "") -> dict:
    if not isinstance(item, dict):
        return {}
    kind = str(item.get("media_type") or item.get("type") or "").lower()
    album = item.get("album") if isinstance(item.get("album"), dict) else {}
    out = {
        "uri": item.get("uri") or "",
        "kind": kind,
        "id": str(item.get("item_id") or item.get("id") or ""),
        "name": item.get("name") or item.get("title") or "",
        "artist": _artists(item) or (item.get("owner") or ""),
        "album": album.get("name", "") if album else "",
        "duration": item.get("duration") or 0,
        "image": _img(item, http_url) or (_img(album, http_url) if album else ""),
        "provider": _provider(item),
        "year": item.get("year") or (album.get("year") if album else None),
    }
    return out


def _items(res) -> list:
    if isinstance(res, dict):
        for k in ("items", "result", "tracks"):
            if isinstance(res.get(k), list):
                return res[k]
        return []
    return res if isinstance(res, list) else []


def norm_search(res, http_url="") -> dict:
    """search-resultat ({tracks:[], albums:[], …}) → {tracks:[…], albums:[…], …} normalisert."""
    out = {k: [] for k in KINDS}
    if not isinstance(res, dict):
        return out
    for k in KINDS:
        out[k] = [norm(x, http_url) for x in (res.get(k) or []) if isinstance(x, dict)]
    return out


def find_player(players: list, name: str, mac: str = "") -> dict | None:
    """MA-spilleren som er denne Skjold-en: MAC (Squeezelite-ID) først, så navnet (Lyrion/AirPlay/DLNA)."""
    mac_n = re.sub(r"[^0-9a-f]", "", (mac or "").lower())
    name_n = (name or "").strip().lower()
    best = None
    for p in players or []:
        if not isinstance(p, dict) or p.get("available") is False:
            continue
        pid = re.sub(r"[^0-9a-f]", "", str(p.get("player_id", "")).lower())
        if mac_n and len(mac_n) >= 12 and mac_n in pid:
            return p
        pn = str(p.get("display_name") or p.get("name") or "").strip().lower()
        if name_n and pn == name_n:
            best = best or p
        elif name_n and best is None and (pn.startswith(name_n) or name_n in pn):
            best = p
    return best


class MA:
    """Høynivå: brukt av daemonen. get_conf() -> (adresse, token)."""

    def __init__(self, get_conf, name_fn, mac_fn, connect=None):
        self.get_conf, self.name_fn, self.mac_fn, self._connect = get_conf, name_fn, mac_fn, connect
        self._player = (0.0, None)

    def client(self) -> Client:
        addr, token = self.get_conf()
        return Client(addr, token, connect=self._connect)

    def status(self) -> dict:
        addr, _ = self.get_conf()
        if not addr:
            return {"configured": False, "ok": False}
        try:
            c = self.client()
            players = c.call("players/all") or []
            p = find_player(players, self.name_fn(), self.mac_fn())
            return {"configured": True, "ok": True, "version": c.server_info.get("server_version", ""),
                    "player": (p or {}).get("display_name") or (p or {}).get("name"),
                    "player_id": (p or {}).get("player_id"),
                    "players": [{"id": x.get("player_id"), "name": x.get("display_name") or x.get("name")} for x in players if isinstance(x, dict)]}
        except Exception as e:
            return {"configured": True, "ok": False, "error": str(e)}

    def search(self, q: str, kinds=None, limit=20) -> dict:
        c = self.client()
        mt = [KINDS[k] for k in (kinds or ["tracks", "albums", "artists", "playlists", "podcasts", "radio"]) if k in KINDS]
        res = c.call("music/search", search_query=q, media_types=mt, limit=limit)
        return norm_search(res, c.http_url)

    def library(self, kind: str, limit=60, offset=0, search: str = "") -> list:
        if kind not in KINDS:
            raise MAError("ukjent type")
        c = self.client()
        args = {"limit": limit, "offset": offset}
        if search:
            args["search"] = search
        return [norm(x, c.http_url) for x in _items(c.call(f"music/{kind}/library_items", **args))]

    def recent(self, limit=20) -> list:
        c = self.client()
        return [norm(x, c.http_url) for x in _items(c.call("music/recently_played_items", limit=limit))]

    def tracks(self, uri: str) -> dict:
        """Album/spilleliste/podkast → {item, tracks} via item_by_uri + album_tracks/playlist_tracks/podcast_episodes."""
        c = self.client()
        item = c.call("music/item_by_uri", uri=uri) or {}
        kind = str(item.get("media_type") or "").lower()
        prov = item.get("provider") or "library"
        iid = item.get("item_id")
        cmd = {"album": "music/albums/album_tracks", "playlist": "music/playlists/playlist_tracks",
               "podcast": "music/podcasts/podcast_episodes", "artist": "music/artists/artist_toptracks"}.get(kind)
        tr = []
        if cmd and iid is not None:
            try:
                tr = _items(c.call(cmd, item_id=str(iid), provider_instance_id_or_domain=prov))
            except MAError:
                # eldre navn
                old = {"album": "music/album_tracks", "playlist": "music/playlist_tracks"}.get(kind)
                tr = _items(c.call(old, item_id=str(iid), provider_instance_id_or_domain=prov)) if old else []
        return {"item": norm(item, c.http_url), "tracks": [norm(x, c.http_url) for x in tr]}

    def player_id(self, c: Client | None = None) -> str:
        t, pid = self._player
        if pid and time.time() - t < 300:
            return pid
        c = c or self.client()
        p = find_player(c.call("players/all") or [], self.name_fn(), self.mac_fn())
        if not p:
            raise MAError(f"fant ikke «{self.name_fn()}» som spiller i Music Assistant – legg til Squeezelite-, "
                          "AirPlay- eller DLNA-provideren i MA, eller sjekk navnet")
        self._player = (time.time(), p["player_id"])
        return p["player_id"]

    def play(self, uri: str, enqueue: str = "play") -> dict:
        """enqueue: play (erstatt og spill), next (spill neste), add (legg sist i køen), replace."""
        if enqueue not in ("play", "next", "add", "replace", "replace_next"):
            enqueue = "play"
        c = self.client()
        pid = self.player_id(c)
        c.call("player_queues/play_media", queue_id=pid, media=[uri] if isinstance(uri, str) else uri, option=enqueue)
        return {"ok": True, "player_id": pid}


def discover(timeout=2.0) -> list[str]:
    """mDNS _mass._tcp → ['host:port'] (zeroconf hvis installert, ellers avahi-browse)."""
    found: list[str] = []
    try:
        from zeroconf import ServiceBrowser, Zeroconf  # type: ignore

        zc = Zeroconf()

        class L:
            def add_service(self, z, t, n):
                info = z.get_service_info(t, n, 1500)
                if info and info.addresses:
                    found.append(f"{socket.inet_ntoa(info.addresses[0])}:{info.port}")

            def update_service(self, *a):
                pass

            def remove_service(self, *a):
                pass

        ServiceBrowser(zc, "_mass._tcp.local.", L())
        time.sleep(timeout)
        zc.close()
        return sorted(set(found))
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.run(["avahi-browse", "-rtp", "_mass._tcp"], capture_output=True, text=True, timeout=timeout + 3).stdout
        for line in out.splitlines():
            f = line.split(";")
            if f and f[0] == "=" and len(f) > 8 and "." in f[7]:
                found.append(f"{f[7]}:{f[8]}")
    except Exception:
        pass
    return sorted(set(found))


# ---------- aiohttp-ruter (daemonen kaller routes(ctx)) ----------

def routes(ctx):
    """ctx: dict med settings(), name(), mac(), connect (valgfri, tester)."""
    from aiohttp import web
    import asyncio

    def conf():
        s = ctx["settings"]()
        return (str(s.get("maUrl") or "").strip(), str(s.get("maToken") or "").strip())

    ma = MA(conf, ctx["name"], ctx["mac"], connect=ctx.get("connect"))
    ctx["ma"] = ma

    async def run(fn, *a):
        try:
            return web.json_response(await asyncio.get_running_loop().run_in_executor(None, lambda: fn(*a)))
        except MAError as e:
            return web.json_response({"error": str(e)}, status=502)
        except Exception as e:
            return web.json_response({"error": f"Music Assistant: {e}"}, status=502)

    async def h_status(_r):
        return await run(ma.status)

    async def h_discover(_r):
        return await run(lambda: {"found": discover()})

    async def h_search(r):
        q = r.query.get("q", "").strip()
        kinds = [k for k in r.query.get("types", "").split(",") if k] or None
        if not q:
            return web.json_response({k: [] for k in KINDS})
        return await run(ma.search, q, kinds, int(r.query.get("limit", 20)))

    async def h_library(r):
        return await run(ma.library, r.match_info["kind"], int(r.query.get("limit", 60)), int(r.query.get("offset", 0)), r.query.get("q", ""))

    async def h_recent(_r):
        return await run(lambda: {"items": ma.recent()})

    async def h_tracks(r):
        uri = r.query.get("uri", "")
        if not uri:
            return web.json_response({"error": "uri mangler"}, status=400)
        return await run(ma.tracks, uri)

    async def h_play(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        uri = b.get("uri") or b.get("uris")
        if not uri:
            return web.json_response({"error": "uri mangler"}, status=400)
        res = await run(ma.play, uri, str(b.get("enqueue") or "play"))
        if res.status == 200 and ctx.get("on_play"):
            ctx["on_play"](b)
        return res

    return [web.get("/api/ma/status", h_status), web.get("/api/ma/discover", h_discover), web.get("/api/ma/search", h_search),
            web.get("/api/ma/library/{kind}", h_library), web.get("/api/ma/recent", h_recent),
            web.get("/api/ma/tracks", h_tracks), web.post("/api/ma/play", h_play)]
