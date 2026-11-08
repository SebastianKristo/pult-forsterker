"""YouTube Music innebygd i Skjold – uten Music Assistant.

Bibliotek, søk, album og spillelister hentes med ytmusicapi (samme interne API som music.youtube.com), og lyden
finnes med yt-dlp. Lyrion spiller en vanlig HTTP-strøm fra Skjold: /api/ytm/stream/<videoId>.m4a – Skjold slår opp
den egentlige adressen (googlevideo, bundet til Pi-ens IP og gyldig noen timer) og sender lyden videre, med Range,
så spoling virker.

Innlogging: «ytmCookie» i innstillingene (Cookie-headeren fra music.youtube.com i nettleseren, samme felt som før).
Uten den virker søk, album og offentlige spillelister; biblioteket ditt (spillelister, album, likte låter) krever den.
«ytmUser» kan være et tall (x-goog-authuser, f.eks. 1 for konto nr. 2 i nettleseren).

API (registreres av ki_amp_daemon.py):
  GET  /api/ytm/status                → {available, signed_in, error, missing}
  GET  /api/ytm/home                  → {newest, other, frequent, playlists} – samlinger {id, name, artist, cover, count, playlist}
  GET  /api/ytm/tracks?id=<samling>   → {tracks: [{id, title, artist, album, dur, cover, stream}]}
  GET  /api/ytm/search?q=…            → {tracks: [...], albums: [...], playlists: [...]}
  POST /api/ytm/play {id, index?} | {video} → spiller samlingen (fra index) eller én låt via Lyrion-køen
  GET  /api/ytm/stream/<videoId>.m4a  → lyden (til Lyrion)
Samlings-id: «pl:<playlistId>» (spilleliste, LM = likte låter) eller «al:<browseId>» (album)."""
import json
import os
import re
import tempfile
import threading
import time

VID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _thumb(o):
    th = o.get("thumbnails") or (o.get("thumbnail") or {}).get("thumbnails") if isinstance(o, dict) else None
    if not th:
        return ""
    u = str(th[-1].get("url") or "")
    # større bilde: googleusercontent-adresser tar størrelsen i adressen (=w120-h120…)
    return re.sub(r"=w\d+-h\d+", "=w544-h544", u)


def _artists(o):
    a = o.get("artists") or []
    if isinstance(a, list) and a:
        return ", ".join(str(x.get("name") or "") for x in a if isinstance(x, dict) and x.get("name"))
    if isinstance(o.get("artist"), str):
        return o["artist"]
    au = o.get("author")
    if isinstance(au, dict):
        return str(au.get("name") or "")
    if isinstance(au, list) and au:
        return ", ".join(str(x.get("name") or "") for x in au if isinstance(x, dict))
    return str(au or "")


def _dur(o):
    if o.get("duration_seconds"):
        return int(o["duration_seconds"])
    d = str(o.get("duration") or o.get("length") or "")
    if re.match(r"^\d+(:\d+)+$", d):
        s = 0
        for p in d.split(":"):
            s = s * 60 + int(p)
        return s
    return 0


def track(o, album="", cover=""):
    """ytmusicapi-låt → Skjold-låt (uten stream; den legges på i daemonen med Pi-ens adresse)."""
    vid = o.get("videoId") or ""
    alb = o.get("album")
    return {"id": vid, "title": str(o.get("title") or ""), "artist": _artists(o),
            "album": str((alb or {}).get("name") if isinstance(alb, dict) else (alb or album) or album),
            "dur": _dur(o), "cover": _thumb(o) or cover}


def coll_album(o):
    bid = o.get("browseId") or o.get("audioPlaylistId")
    if not bid:
        return None
    return {"id": "al:" + bid, "name": str(o.get("title") or ""), "artist": _artists(o) or str(o.get("year") or ""),
            "cover": _thumb(o), "count": int(o.get("trackCount") or 0) if str(o.get("trackCount") or "").isdigit() else 0,
            "playlist": False}


def coll_playlist(o):
    pid = o.get("playlistId") or (o.get("browseId") or "").removeprefix("VL")
    if not pid:
        return None
    cnt = o.get("count") or o.get("itemCount") or 0
    try:
        cnt = int(str(cnt).split()[0].replace(",", "").replace(" ", ""))
    except ValueError:
        cnt = 0
    return {"id": "pl:" + pid, "name": str(o.get("title") or ""), "artist": _artists(o) or str(o.get("description") or "")[:40],
            "cover": _thumb(o), "count": cnt, "playlist": True}


def _has_login(cookie):
    """Innlogget cookie fra music.youtube.com har SAPISID / __Secure-3PAPISID (brukes til SAPISIDHASH)."""
    return "SAPISID=" in cookie or "__Secure-3PAPISID=" in cookie


def cookie_jar(cookie, path):
    """Cookie-headeren → Netscape-cookiefil til yt-dlp (både .youtube.com og music.youtube.com)."""
    exp = int(time.time()) + 365 * 86400
    lines = ["# Netscape HTTP Cookie File"]
    for part in str(cookie or "").split(";"):
        if "=" not in part:
            continue
        k, v = part.strip().split("=", 1)
        if k:
            lines.append(f".youtube.com\tTRUE\t/\tTRUE\t{exp}\t{k}\t{v}")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


class Ytm:
    def __init__(self, get_settings, cache_dir=None, make_client=None, extract=None):
        self._get = get_settings
        self._lock = threading.Lock()
        self._client, self._key = None, None
        self._urls = {}            # videoId → (url, utløper, headers)
        self._home = (0.0, None)   # (tid, svar)
        self._dir = cache_dir or os.path.join(tempfile.gettempdir(), "skjold-ytm")
        self._make_client = make_client
        self._extract = extract
        self.error = ""

    # ---------- innlogging ----------
    def _cfg(self):
        s = self._get() or {}
        return str(s.get("ytmCookie") or "").strip(), str(s.get("ytmUser") or "").strip()

    def signed_in(self):
        return _has_login(self._cfg()[0])

    def missing(self):
        out = []
        try:
            import ytmusicapi  # noqa: F401
        except Exception:
            out.append("ytmusicapi")
        if self._extract is None:
            try:
                import yt_dlp  # noqa: F401
            except Exception:
                out.append("yt-dlp")
        return out

    def client(self):
        c, u = self._cfg()
        key = (c, u)
        with self._lock:
            if self._client is not None and self._key == key:
                return self._client
            if self._make_client:
                self._client = self._make_client(c, u)
            else:
                from ytmusicapi import YTMusic
                if _has_login(c):
                    from ytmusicapi.helpers import initialize_headers
                    h = dict(initialize_headers())
                    h.update({"cookie": c, "authorization": "SAPISIDHASH 0", "origin": "https://music.youtube.com",
                              "x-goog-authuser": u if u.isdigit() else "0"})
                    self._client = YTMusic(auth=json.dumps(h), language="en", location="NO")
                else:
                    self._client = YTMusic(language="en", location="NO")
            self._key = key
            self._home = (0.0, None)
            return self._client

    def status(self):
        miss = self.missing()
        return {"available": not miss, "signed_in": self.signed_in(), "missing": miss, "error": self.error}

    # ---------- bibliotek ----------
    def home(self, max_age=300):
        t, cached = self._home
        if cached is not None and time.time() - t < max_age:
            return cached
        yt = self.client()
        out = {"newest": [], "other": [], "frequent": [], "playlists": []}
        seen = set()

        def add(lst, c):
            if c and c["id"] not in seen:
                seen.add(c["id"]); lst.append(c)
        if self.signed_in():
            try:
                add(out["playlists"], {"id": "pl:LM", "name": "Likte låter", "artist": "YouTube Music", "cover": "", "count": 0, "playlist": True})
                for p in yt.get_library_playlists(limit=50) or []:
                    if (p.get("playlistId") or "") != "LM":
                        add(out["playlists"], coll_playlist(p))
                for a in yt.get_library_albums(limit=50, order="recently_added") or []:
                    add(out["newest"], coll_album(a))
            except Exception as e:
                self.error = f"bibliotek: {e}"
        try:   # «Til deg»: mikser, anbefalte album og spillelister fra forsiden
            for sec in yt.get_home(limit=6) or []:
                for it in sec.get("contents") or []:
                    if not isinstance(it, dict):
                        continue
                    if it.get("browseId", "").startswith("MPRE") or it.get("type") in ("Album", "Single", "EP"):
                        add(out["other"], coll_album(it))
                    elif it.get("playlistId"):
                        add(out["frequent"], coll_playlist(it))
        except Exception as e:
            if not out["playlists"]:
                self.error = f"forside: {e}"
        if any(out.values()):
            self.error = "" if not self.error.startswith("bibliotek") else self.error
        self._home = (time.time(), out)
        return out

    def tracks(self, cid, limit=200):
        yt = self.client()
        kind, _, rid = str(cid).partition(":")
        if kind == "al":
            a = yt.get_album(rid)
            cover = _thumb(a)
            return [track(x, a.get("title", ""), cover) for x in a.get("tracks") or [] if x.get("videoId")]
        if kind == "pl":
            p = yt.get_liked_songs(limit=limit) if rid == "LM" else yt.get_playlist(rid, limit=limit)
            return [track(x) for x in p.get("tracks") or [] if x.get("videoId")]
        raise ValueError("ukjent samling: " + str(cid))

    def search(self, q, limit=20):
        yt = self.client()
        songs = [track(x) for x in yt.search(q, filter="songs", limit=limit) or [] if x.get("videoId")]
        albums = [c for c in (coll_album(x) for x in yt.search(q, filter="albums", limit=10) or []) if c]
        pls = [c for c in (coll_playlist(x) for x in yt.search(q, filter="playlists", limit=10) or []) if c]
        return {"tracks": songs, "albums": albums, "playlists": pls}

    def find_album(self, artist, album):
        """Album-kassetter: beste album-treff → {"kilde":"ytmusic","ytm_id":"al:…",…} eller None."""
        from skjold_nfc import best_album
        res = self.client().search(f"{artist} {album}".strip(), filter="albums", limit=10) or []
        cand = [{"id": c["id"], "name": c["name"], "artist": c["artist"], "image": c["cover"]} for c in (coll_album(x) for x in res) if c]
        hit = best_album(cand, artist, album)
        if not hit:
            return None
        return {"kilde": "ytmusic", "ytm_id": hit["id"], "navn": hit["name"], "artist": hit["artist"] or artist, "image": hit["image"]}

    # ---------- lyd ----------
    def stream_url(self, vid):
        """videoId → (lyd-URL, headers). Caches til like før adressen utløper."""
        if not VID_RE.match(vid or ""):
            raise ValueError("ugyldig videoId")
        hit = self._urls.get(vid)
        if hit and hit[1] > time.time():
            return hit[0], hit[2]
        info = self._extract(vid) if self._extract else self._ydl(vid)
        url = info["url"]
        m = re.search(r"[?&]expire=(\d+)", url)
        exp = (int(m.group(1)) - 600) if m else time.time() + 3600
        hdr = {k: v for k, v in (info.get("http_headers") or {}).items() if k.lower() in ("user-agent", "referer", "origin")}
        self._urls[vid] = (url, exp, hdr)
        while len(self._urls) > 300:
            self._urls.pop(next(iter(self._urls)))
        return url, hdr

    def _ydl(self, vid):
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
                # m4a (AAC) først: Lyrion spiller det uten ekstra dekodere; opus/webm bare som reserve
                "format": "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio/best"}
        # YouTube krever en JavaScript-motor for signaturene: deno (installeres av update.sh), ellers node ≥ 22 / quickjs
        opts["js_runtimes"] = {"deno": {}, "node": {}, "quickjs": {}}
        c, _u = self._cfg()
        if _has_login(c):   # Premium-konto: høyere kvalitet og ingen aldersgrense
            os.makedirs(self._dir, exist_ok=True)
            opts["cookiefile"] = cookie_jar(c, os.path.join(self._dir, "cookies.txt"))
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(f"https://music.youtube.com/watch?v={vid}", download=False)
        if not info.get("url") and info.get("requested_formats"):
            info = {**info, "url": info["requested_formats"][0]["url"]}
        return info


def routes(ytm, ctx):
    """aiohttp-ruter. ctx: stream_base() → «http://<pi>:<port>», play(tracks, index) spiller via Lyrion-køen."""
    import asyncio
    from aiohttp import web, ClientSession, ClientTimeout

    def with_stream(ts):
        base = ctx["stream_base"]()
        return [{**t, "stream": f"{base}/api/ytm/stream/{t['id']}.m4a"} for t in ts]

    async def run(fn, *a):
        return await asyncio.get_running_loop().run_in_executor(None, fn, *a)

    def fail(e, code=502):
        ytm.error = str(e)
        return web.json_response({"error": str(e)}, status=code)

    async def h_status(_r):
        return web.json_response(ytm.status())

    async def h_home(r):
        if ytm.missing():
            return fail("mangler " + ", ".join(ytm.missing()) + " (kjør pi/update.sh)", 503)
        try:
            return web.json_response(await run(ytm.home, 0 if r.query.get("fresh") else 300))
        except Exception as e:
            return fail(e)

    async def h_tracks(r):
        try:
            return web.json_response({"tracks": with_stream(await run(ytm.tracks, r.query.get("id", "")))})
        except ValueError as e:
            return fail(e, 400)
        except Exception as e:
            return fail(e)

    async def h_search(r):
        q = (r.query.get("q") or "").strip()
        if not q:
            return web.json_response({"tracks": [], "albums": [], "playlists": []})
        try:
            res = await run(ytm.search, q)
            return web.json_response({**res, "tracks": with_stream(res["tracks"])})
        except Exception as e:
            return fail(e)

    async def h_play(r):
        b = await r.json()
        try:
            if b.get("video"):
                ts = [{"id": str(b["video"]), "title": str(b.get("title") or ""), "artist": str(b.get("artist") or ""),
                       "album": "", "dur": 0, "cover": str(b.get("cover") or "")}]
            else:
                ts = await run(ytm.tracks, str(b.get("id") or ""))
            if not ts:
                return fail("tom samling", 404)
            await run(ctx["play"], with_stream(ts), int(b.get("index") or 0))
            return web.json_response({"ok": True, "count": len(ts)})
        except ValueError as e:
            return fail(e, 400)
        except Exception as e:
            return fail(e)

    async def h_stream(r):
        vid = r.match_info["vid"].split(".")[0]
        try:
            url, hdr = await run(ytm.stream_url, vid)
        except ValueError:
            return web.Response(status=400)
        except Exception as e:
            print("YouTube Music: fant ikke lyden til", vid, repr(e), flush=True)
            return web.Response(status=502)
        hdr = dict(hdr)
        if r.headers.get("Range"):
            hdr["Range"] = r.headers["Range"]
        sess = ClientSession(timeout=ClientTimeout(total=None, sock_connect=8, sock_read=60))
        try:
            up = await sess.get(url, headers=hdr)
            if up.status == 403:   # adressen er utløpt eller avvist: slå opp på nytt én gang
                up.release(); ytm._urls.pop(vid, None)
                url, hdr2 = await run(ytm.stream_url, vid)
                up = await sess.get(url, headers={**hdr2, **({"Range": hdr["Range"]} if "Range" in hdr else {})})
        except Exception as e:
            print("YouTube Music: strømmen feilet", vid, repr(e), flush=True)
            await sess.close()
            return web.Response(status=502)
        out = web.StreamResponse(status=up.status, headers={k: v for k, v in up.headers.items()
                                                            if k in ("Content-Length", "Content-Range", "Accept-Ranges")})
        out.content_type = "audio/mp4" if "mp4" in up.headers.get("Content-Type", "audio/mp4") else up.headers.get("Content-Type", "audio/mp4")
        try:
            await out.prepare(r)
            async for chunk in up.content.iter_chunked(65536):
                await out.write(chunk)
            await out.write_eof()
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            up.release(); await sess.close()
        return out

    return [web.get("/api/ytm/status", h_status), web.get("/api/ytm/home", h_home), web.get("/api/ytm/tracks", h_tracks),
            web.get("/api/ytm/search", h_search), web.post("/api/ytm/play", h_play),
            web.get("/api/ytm/stream/{vid}", h_stream)]
