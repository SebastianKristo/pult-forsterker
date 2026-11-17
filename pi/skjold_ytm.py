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
        self._busy = {}            # videoId → Lock: én yt-dlp-oppslag per låt om gangen (forhåndshenting + strøm + test)
        self._home = (0.0, None)   # (tid, svar)
        self._dir = cache_dir or os.path.join(tempfile.gettempdir(), "skjold-ytm")
        self._tracks = {}          # samlings-id → (tid, låter)
        self._refreshing = False
        self._load_home()
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
            self._home = (0.0, None); self._tracks = {}
            self._load_home()   # forsiden fra disk hvis den hører til samme innlogging
            return self._client

    def status(self):
        miss = self.missing()
        return {"available": not miss, "signed_in": self.signed_in(), "missing": miss, "error": self.error}

    # ---------- bibliotek ----------
    # Forsiden lagres på disk og vises straks (også etter omstart); er den eldre enn max_age, hentes den på nytt i
    # bakgrunnen. Bibliotek-spillelister, album og «Til deg» hentes samtidig (før: etter hverandre, 5–15 s på en Pi).
    def _home_file(self):
        return os.path.join(self._dir, "home.json")

    def _load_home(self):
        try:
            with open(self._home_file()) as f:
                d = json.load(f)
            if d.get("key") == self._key_hash():
                self._home = (float(d.get("t", 0)), d.get("home"))
        except Exception:
            pass

    def _key_hash(self):
        import hashlib
        c, u = self._cfg()
        return hashlib.sha256((c + "|" + u).encode()).hexdigest()[:16]

    def _save_home(self, t, out):
        try:
            os.makedirs(self._dir, exist_ok=True)
            tmp = self._home_file() + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"t": t, "key": self._key_hash(), "home": out}, f)
            os.replace(tmp, self._home_file())
        except Exception:
            pass

    def home(self, max_age=300):
        t, cached = self._home
        age = time.time() - t
        if cached is not None and age < max_age:
            return cached
        if cached is not None and max_age > 0 and age < 7 * 86400:
            self.refresh_home_bg()   # gammel, men vis den straks – ny kommer i bakgrunnen
            return cached
        return self._fetch_home()

    def refresh_home_bg(self):
        if self._refreshing:
            return
        self._refreshing = True

        def job():
            try:
                self._fetch_home()
            except Exception as e:
                self.error = f"forside: {e}"
            finally:
                self._refreshing = False
        threading.Thread(target=job, daemon=True).start()

    def _fetch_home(self):
        from concurrent.futures import ThreadPoolExecutor
        yt = self.client()
        out = {"newest": [], "other": [], "frequent": [], "playlists": []}
        seen = set()

        def add(lst, c):
            if c and c["id"] not in seen:
                seen.add(c["id"]); lst.append(c)

        def safe(fn, *a, **k):
            try:
                return fn(*a, **k) or [], None
            except Exception as e:
                return [], e
        signed = self.signed_in()
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_pl = ex.submit(safe, yt.get_library_playlists, limit=50) if signed else None
            f_al = ex.submit(safe, yt.get_library_albums, limit=50, order="recently_added") if signed else None
            f_home = ex.submit(safe, yt.get_home, limit=6)
            pls, e_pl = f_pl.result() if f_pl else ([], None)
            als, e_al = f_al.result() if f_al else ([], None)
            secs, e_home = f_home.result()
        if signed:
            add(out["playlists"], {"id": "pl:LM", "name": "Likte låter", "artist": "YouTube Music", "cover": "", "count": 0, "playlist": True})
            for p in pls:
                if (p.get("playlistId") or "") != "LM":
                    add(out["playlists"], coll_playlist(p))
            for a in als:
                add(out["newest"], coll_album(a))
            if e_pl or e_al:
                self.error = f"bibliotek: {e_pl or e_al}"
        for sec in secs:   # «Til deg»: mikser, anbefalte album og spillelister fra forsiden
            for it in sec.get("contents") or []:
                if not isinstance(it, dict):
                    continue
                if it.get("browseId", "").startswith("MPRE") or it.get("type") in ("Album", "Single", "EP"):
                    add(out["other"], coll_album(it))
                elif it.get("playlistId"):
                    add(out["frequent"], coll_playlist(it))
        if e_home and not out["playlists"]:
            self.error = f"forside: {e_home}"
        if any(out.values()):
            self.error = "" if not self.error.startswith("bibliotek") else self.error
            t = time.time()
            self._home = (t, out)
            self._save_home(t, out)
        return out

    def tracks(self, cid, limit=200):
        hit = self._tracks.get(cid)
        if hit and time.time() - hit[0] < 600:   # samme album/spilleliste åpnet igjen: fra minnet
            return hit[1]
        out = self._tracks_fetch(cid, limit)
        self._tracks[cid] = (time.time(), out)
        while len(self._tracks) > 60:
            self._tracks.pop(next(iter(self._tracks)))
        return out

    def prefetch(self, vids):
        """Slå opp lyd-adressene i bakgrunnen (yt-dlp tar noen sekunder per låt), så avspillingen starter med en gang."""
        def job():
            for v in vids:
                try:
                    self.stream_url(v)
                except Exception:
                    pass
        if vids:
            threading.Thread(target=job, daemon=True).start()

    def _tracks_fetch(self, cid, limit=200):
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
        # Pi-en har ikke kraft til flere yt-dlp samtidig for samme låt: vent på den som allerede slår opp
        with self._lock:
            lk = self._busy.setdefault(vid, threading.Lock())
        with lk:
            hit = self._urls.get(vid)
            if hit and hit[1] > time.time():
                return hit[0], hit[2]
            return self._resolve(vid)

    def _resolve(self, vid):
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

    import shutil

    def with_stream(ts):
        # .aac (ADTS, pakket om av ffmpeg uten omkoding) når ffmpeg finnes: YouTubes m4a er fragmentert (DASH), og
        # Lyrion/squeezelite spiller da ofte bare de første sekundene før låten stopper. ADTS er en ren lydstrøm.
        base, ext = ctx["stream_base"](), ("aac" if shutil.which("ffmpeg") else "m4a")
        return [{**t, "stream": f"{base}/api/ytm/stream/{t['id']}.{ext}"} for t in ts]

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
            ts = await run(ytm.tracks, r.query.get("id", ""))
            ytm.prefetch([t["id"] for t in ts[:2]])   # de første låtene er klare når du trykker spill
            return web.json_response({"tracks": with_stream(ts)})
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
            i = int(b.get("index") or 0)
            # Slå opp den første låten FØR Lyrion får beskjed: ellers venter Lyrion på yt-dlp og gir opp (tidsavbrudd)
            if 0 <= i < len(ts):
                try:
                    await run(ytm.stream_url, ts[i]["id"])
                except Exception as e:
                    print("YouTube Music: fant ikke lyden til", ts[i]["id"], repr(e), flush=True)
            ytm.prefetch([t["id"] for t in ts[i + 1:i + 3]])   # de neste to – neste låt starter uten pause
            await run(ctx["play"], with_stream(ts), i)
            return web.json_response({"ok": True, "count": len(ts)})
        except ValueError as e:
            return fail(e, 400)
        except Exception as e:
            return fail(e)

    CHUNK = 1 << 20   # 1 MB per forespørsel: YouTube struper eller kutter lange enkeltforespørsler (som yt-dlp, http_chunk_size)

    def parse_range(v):
        m = re.match(r"bytes=(\d*)-(\d*)", v or "")
        if not m or not m.group(1):
            return 0, None
        return int(m.group(1)), (int(m.group(2)) if m.group(2) else None)

    async def h_stream_adts(r, vid):
        """AAC fra YouTubes fragmenterte m4a, pakket om til ADTS (-c copy: ingen omkoding, lite CPU)."""
        try:
            await run(ytm.stream_url, vid)    # slå opp først, så ffmpeg ikke venter på yt-dlp
        except ValueError:
            return web.Response(status=400)
        except Exception as e:
            print("YouTube Music: fant ikke lyden til", vid, repr(e), flush=True)
            return web.Response(status=502)
        src = f"{ctx['stream_base']()}/api/ytm/stream/{vid}.m4a"
        p = await asyncio.create_subprocess_exec(
            "ffmpeg", "-nostdin", "-loglevel", "error", "-reconnect", "1", "-reconnect_streamed", "1",
            "-i", src, "-vn", "-c:a", "copy", "-f", "adts", "pipe:1",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out = web.StreamResponse(status=200, headers={"Content-Type": "audio/aac", "Cache-Control": "no-cache"})
        n = 0
        try:
            await out.prepare(r)
            while True:
                b = await p.stdout.read(65536)
                if not b:
                    break
                await out.write(b); n += len(b)
            await out.write_eof()
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            if p.returncode is None:
                try:
                    p.kill()
                except ProcessLookupError:
                    pass
            err = (await p.stderr.read()).decode(errors="replace").strip()
            await p.wait()
            if err and n == 0:
                print("YouTube Music: ffmpeg", vid, err[-300:], flush=True)
        return out

    async def h_stream(r):
        name = r.match_info["vid"]
        vid = name.split(".")[0]
        if name.endswith(".aac") and VID_RE.match(vid) and shutil.which("ffmpeg"):
            return await h_stream_adts(r, vid)
        try:
            url, hdr = await run(ytm.stream_url, vid)
        except ValueError:
            return web.Response(status=400)
        except Exception as e:
            print("YouTube Music: fant ikke lyden til", vid, repr(e), flush=True)
            return web.Response(status=502)
        want = r.headers.get("Range")
        start, end = parse_range(want)
        sess = ClientSession(timeout=ClientTimeout(total=None, sock_connect=8, sock_read=30))
        state = {"url": url, "hdr": dict(hdr)}

        async def piece(a, b):
            """Hent bytes a..b (med nytt oppslag én gang hvis adressen er utløpt/avvist)."""
            for attempt in range(3):
                up = await sess.get(state["url"], headers={**state["hdr"], "Range": f"bytes={a}-{b}"})
                if up.status in (200, 206):
                    return up
                up.release()
                if up.status in (403, 410) and attempt == 0:
                    ytm._urls.pop(vid, None)
                    state["url"], h2 = await run(ytm.stream_url, vid); state["hdr"] = dict(h2)
                    continue
                if up.status == 416:
                    return None
                await asyncio.sleep(0.5)
            raise RuntimeError(f"YouTube svarte {up.status}")

        try:
            first = await piece(start, start + CHUNK - 1 if end is None else min(end, start + CHUNK - 1))
            if first is None:
                await sess.close(); return web.Response(status=416)
            cr = first.headers.get("Content-Range", "")
            m = re.search(r"/(\d+)$", cr)
            total = int(m.group(1)) if m else (start + int(first.headers.get("Content-Length") or 0))
        except Exception as e:
            print("YouTube Music: strømmen feilet", vid, repr(e), flush=True)
            await sess.close()
            return web.Response(status=502)
        last = total - 1 if end is None else min(end, total - 1)
        heads = {"Accept-Ranges": "bytes", "Content-Length": str(last - start + 1)}
        if want:
            heads["Content-Range"] = f"bytes {start}-{last}/{total}"
        out = web.StreamResponse(status=206 if want else 200, headers=heads)
        out.content_type = "audio/mp4" if "mp4" in first.headers.get("Content-Type", "audio/mp4") else first.headers.get("Content-Type", "audio/mp4")
        pos, up = start, first
        try:
            await out.prepare(r)
            while True:
                async for chunk in up.content.iter_chunked(65536):
                    await out.write(chunk); pos += len(chunk)
                up.release()
                if pos > last:
                    break
                up = await piece(pos, min(last, pos + CHUNK - 1))
                if up is None:
                    break
            await out.write_eof()
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        except Exception as e:
            print("YouTube Music: strømmen stoppet ved", pos, "av", total, vid, repr(e), flush=True)
        finally:
            try:
                up.release()
            except Exception:
                pass
            await sess.close()
        return out

    return [web.get("/api/ytm/status", h_status), web.get("/api/ytm/home", h_home), web.get("/api/ytm/tracks", h_tracks),
            web.get("/api/ytm/search", h_search), web.post("/api/ytm/play", h_play),
            web.get("/api/ytm/stream/{vid}", h_stream)]
