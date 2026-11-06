"""NRK Radio på forespørsel og podkaster for Skjold, via NRKs åpne psapi (https://psapi.nrk.no).

Søk, serier/podkaster med episoder, avspilling via Lyrion (play_url i daemonen) og «fortsett der du slapp» per
episode: posisjonen lagres mens episoden spiller og brukes som startpunkt neste gang (Lyrion «time»). En episode
regnes som hørt når 95 % er spilt.

psapi-svarene er ikke dokumentert offentlig og varierer mellom serier, programmer og podkaster, så alt leses
tolerant: vi går gjennom svaret og plukker ut det som ser ut som serier/episoder.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request

API = os.environ.get("KI_AMP_NRK_API", "https://psapi.nrk.no")
UA = "Skjold/1.0 (+https://skjold.smarthjemexperten.no)"
HEARD = 0.95


class NRKError(RuntimeError):
    pass


def _get(path: str, fetch=None, timeout=8.0):
    url = path if path.startswith("http") else API + path
    if fetch:
        return fetch(url)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise NRKError(f"NRK svarte {e.code}")
    except Exception as e:
        raise NRKError(f"får ikke kontakt med NRK: {e}")


# ---------- tolerant parsing ----------

def _title(d: dict) -> str:
    t = d.get("titles") if isinstance(d.get("titles"), dict) else {}
    return str(t.get("title") or d.get("title") or d.get("name") or "")


def _subtitle(d: dict) -> str:
    t = d.get("titles") if isinstance(d.get("titles"), dict) else {}
    return str(t.get("subtitle") or d.get("subtitle") or d.get("description") or "")


def _image(d: dict) -> str:
    """Største rimelige bilde (≥300 px) fra image/images/squareImage-lister."""
    cands = []
    for k in ("squareImage", "image", "images", "posterImage", "backdropImage"):
        v = d.get(k)
        if isinstance(v, dict):
            v = v.get("webImages") or v.get("images") or [v]
        if isinstance(v, list):
            for im in v:
                if isinstance(im, dict):
                    u = im.get("uri") or im.get("url") or im.get("imageUrl") or ""
                    w = im.get("width") or im.get("pixelWidth") or 0
                    if u:
                        cands.append((int(w or 0), u))
        elif isinstance(v, str) and v.startswith("http"):
            cands.append((0, v))
        if cands:
            break
    if not cands:
        return ""
    good = [c for c in cands if c[0] >= 300]
    return (min(good) if good else max(cands))[1]


def _duration(d: dict) -> float:
    for k in ("durationInSeconds", "duration"):
        v = d.get(k)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict):
            s = v.get("seconds") or v.get("durationInSeconds")
            if isinstance(s, (int, float)):
                return float(s)
            v = v.get("iso8601") or v.get("displayValue")
        if isinstance(v, str) and v.startswith("PT"):
            return _iso_dur(v)
    return 0.0


def _iso_dur(s: str) -> float:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", s or "")
    if not m:
        return 0.0
    h, mi, se = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)


def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def _ep_id(d: dict) -> str:
    return str(d.get("episodeId") or d.get("prfId") or d.get("programId") or "")


def parse_series(res) -> list[dict]:
    """Søk/sider → [{id, title, subtitle, image, kind: series|podcast}] (unike)."""
    out, seen = [], set()
    for d in _walk(res):
        sid = d.get("seriesId") or (d.get("id") if str(d.get("type", "")).lower() in ("series", "podcast", "serie") else None)
        typ = str(d.get("type") or d.get("seriesType") or "").lower()
        if not sid or _ep_id(d) or not _title(d):
            continue
        if typ and typ not in ("series", "podcast", "serie", "standard", "sequential", "news", "umbrella"):
            continue
        sid = str(sid)
        if sid in seen:
            continue
        seen.add(sid)
        out.append({"id": sid, "title": _title(d), "subtitle": _subtitle(d), "image": _image(d),
                    "kind": "podcast" if "podcast" in typ else "series"})
    return out


def parse_episodes(res, series_title="", series_image="") -> list[dict]:
    """Episodelister → [{id, title, subtitle, date, duration, image, series}] (nyeste først som NRK leverer)."""
    out, seen = [], set()
    for d in _walk(res):
        eid = _ep_id(d)
        if not eid or eid in seen or not _title(d):
            continue
        seen.add(eid)
        ur = d.get("usageRights") if isinstance(d.get("usageRights"), dict) else {}
        frm = ur.get("from") if isinstance(ur.get("from"), dict) else {}
        date = d.get("date") or d.get("publishedAt") or d.get("firstTransmissionDateDisplayValue") or frm.get("date") or ""
        out.append({"id": eid, "title": _title(d), "subtitle": _subtitle(d), "date": str(date or "")[:10],
                    "duration": _duration(d), "image": _image(d) or series_image, "series": series_title,
                    "podcast": bool(d.get("episodeId") and not d.get("prfId"))})
    return out


def parse_manifest(res) -> str:
    """Avspillingsmanifest → beste lyd-URL (MP3/AAC foran HLS, siden Lyrion spiller dem sikrest)."""
    assets = []
    for d in _walk(res):
        u = d.get("url") or d.get("uri")
        if isinstance(u, str) and u.startswith("http") and (d.get("format") or d.get("mimeType") or "playable" in str(d).lower()):
            fmt = str(d.get("format") or d.get("mimeType") or "").lower()
            rank = 0 if ("mp3" in fmt or "mpeg" in fmt or u.endswith(".mp3")) else 1 if ("aac" in fmt or "mp4" in fmt) else 2
            assets.append((rank, u))
    if not assets:
        raise NRKError("NRK ga ingen avspillbar adresse (kan være geoblokkert eller utløpt)")
    return min(assets)[1]


# ---------- fremdrift ----------

class Progress:
    def __init__(self, path: str):
        self.path, self.lock, self.data = path, threading.Lock(), {}
        try:
            with open(path) as fh:
                self.data = json.load(fh)
        except Exception:
            self.data = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path + ".tmp", "w") as fh:
                json.dump(self.data, fh)
            os.replace(self.path + ".tmp", self.path)
        except Exception:
            pass

    def update(self, eid: str, pos: float, dur: float, meta: dict | None = None):
        with self.lock:
            e = self.data.setdefault(eid, {})
            if meta:
                e.update({k: v for k, v in meta.items() if v})
            e["pos"], e["t"] = round(max(0.0, pos), 1), time.time()
            if dur:
                e["dur"] = round(dur, 1)
            if dur and pos >= HEARD * dur:
                e["heard"] = True
            self.save()

    def resume_at(self, eid: str) -> float:
        e = self.data.get(eid) or {}
        if e.get("heard"):
            return 0.0
        pos, dur = float(e.get("pos") or 0), float(e.get("dur") or 0)
        if pos < 15 or (dur and pos > dur - 20):
            return 0.0
        return max(0.0, pos - 5)                       # litt overlapp så du hører hvor du var

    def continue_list(self, n=12) -> list[dict]:
        items = [dict(id=k, **v) for k, v in self.data.items() if not v.get("heard") and float(v.get("pos") or 0) >= 15]
        items.sort(key=lambda x: -float(x.get("t") or 0))
        return items[:n]

    def get(self, eid: str) -> dict:
        return self.data.get(eid) or {}


class NRK:
    def __init__(self, progress_path: str, fetch=None):
        self.fetch = fetch
        self.progress = Progress(progress_path)
        self._series_cache: dict = {}

    def search(self, q: str) -> dict:
        res = _get("/radio/search/search?" + urllib.parse.urlencode({"q": q}), self.fetch)
        series = parse_series(res)
        eps = parse_episodes(res)
        return {"series": series, "episodes": [self._with_progress(e) for e in eps][:30]}

    def popular(self) -> list[dict]:
        for p in ("/radio/pages/podcast", "/radio/pages/discover", "/radio/pages/frontpage"):
            try:
                res = _get(p, self.fetch)
            except NRKError:
                continue
            if res:
                s = parse_series(res)
                if s:
                    return s[:30]
        return []

    def series(self, sid: str, kind: str = "") -> dict:
        info = None
        if kind != "podcast":
            info = _get(f"/radio/catalog/series/{urllib.parse.quote(sid)}", self.fetch)
        if not info:
            info = _get(f"/radio/catalog/podcast/{urllib.parse.quote(sid)}", self.fetch)
            kind = "podcast"
        if not info:
            raise NRKError("fant ikke serien hos NRK")
        meta = info.get("series") if isinstance(info, dict) and isinstance(info.get("series"), dict) else info
        title, image = _title(meta or {}), _image(meta or {})
        eps_res = None
        for p in ([f"/radio/catalog/podcast/{sid}/episodes?pageSize=50"] if kind == "podcast" else []) + \
                 [f"/radio/catalog/series/{sid}/episodes?pageSize=50", f"/radio/catalog/podcast/{sid}/episodes?pageSize=50"]:
            try:
                eps_res = _get(p, self.fetch)
            except NRKError:
                eps_res = None
            if eps_res:
                break
        eps = parse_episodes(eps_res or info, title, image)
        if not eps:                                    # serier med sesonger: hent hver sesong
            for d in _walk(info):
                href = ((d.get("_links") or {}).get("self") or {}).get("href") if isinstance(d.get("_links"), dict) else None
                if href and "/seasons/" in href:
                    try:
                        eps += parse_episodes(_get(href, self.fetch), title, image)
                    except NRKError:
                        pass
        return {"id": sid, "title": title, "subtitle": _subtitle(meta or {}), "image": image, "kind": kind or "series",
                "episodes": [self._with_progress(e) for e in eps]}

    def stream(self, eid: str, podcast: bool | None = None) -> str:
        paths = [f"/playback/manifest/podcast/{eid}", f"/playback/manifest/program/{eid}"]
        if podcast is False:
            paths.reverse()
        last = None
        for p in paths:
            try:
                res = _get(p, self.fetch)
                if res:
                    return parse_manifest(res)
            except NRKError as e:
                last = e
        raise last or NRKError("fant ingen strøm for episoden")

    def _with_progress(self, e: dict) -> dict:
        p = self.progress.get(e["id"])
        if p:
            e = {**e, "pos": p.get("pos", 0), "heard": bool(p.get("heard"))}
        return e


# ---------- aiohttp-ruter og fremdriftsvakt ----------

def routes(ctx):
    """ctx: play_url(url,title,image,genre,meta), lyr_cmd(list), lyr_info() -> dict, data_dir, fetch (tester)."""
    from aiohttp import web
    import asyncio

    nrk = NRK(os.path.join(ctx.get("data_dir", "/var/lib/ki-amp"), "nrk_progress.json"), fetch=ctx.get("fetch"))
    ctx["nrk"] = nrk
    playing: dict = {}                                 # episoden som spilles nå: {id, url, meta}

    async def run(fn, *a):
        try:
            return web.json_response(await asyncio.get_running_loop().run_in_executor(None, lambda: fn(*a)))
        except NRKError as e:
            return web.json_response({"error": str(e)}, status=502)
        except Exception as e:
            return web.json_response({"error": f"NRK: {e}"}, status=502)

    async def h_search(r):
        q = r.query.get("q", "").strip()
        if not q:
            return web.json_response({"series": [], "episodes": []})
        return await run(nrk.search, q)

    async def h_popular(_r):
        return await run(lambda: {"series": nrk.popular()})

    async def h_series(r):
        return await run(nrk.series, r.match_info["sid"], r.query.get("kind", ""))

    async def h_continue(_r):
        return web.json_response({"items": nrk.progress.continue_list()})

    def _play(b):
        eid = str(b.get("id") or "")
        if not eid:
            raise NRKError("id mangler")
        url = nrk.stream(eid, b.get("podcast"))
        meta = {"title": b.get("title", ""), "series": b.get("series", ""), "image": b.get("image", ""),
                "dur": b.get("duration") or 0}
        ctx["play_url"](url, b.get("series") or b.get("title") or "NRK", b.get("image", ""), "NRK",
                        {"track": b.get("title", ""), "artist": "NRK", "album": b.get("series", ""),
                         "duration": float(b.get("duration") or 0), "source": "NRK"})
        playing.clear(); playing.update(id=eid, url=url, meta=meta, t=time.time())
        nrk.progress.update(eid, nrk.progress.get(eid).get("pos", 0) if not b.get("restart") else 0, float(b.get("duration") or 0), meta)
        start = 0.0 if b.get("restart") else nrk.progress.resume_at(eid)
        if start:
            def seek():
                for _ in range(10):                    # vent til Lyrion faktisk spiller strømmen
                    time.sleep(1.5)
                    if (ctx["lyr_info"]() or {}).get("mode") == "play":
                        break
                ctx["lyr_cmd"](["time", round(start)])
            threading.Thread(target=seek, daemon=True).start()
        return {"ok": True, "resume": start}

    async def h_play(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        return await run(_play, b)

    def watch():
        while True:
            time.sleep(10)
            try:
                if not playing:
                    continue
                i = ctx["lyr_info"]() or {}
                if i.get("url") and playing.get("url") and i.get("url") != playing["url"] and time.time() - playing.get("t", 0) > 30:
                    playing.clear(); continue          # noe annet spilles nå
                if i.get("mode") != "play":
                    continue
                pos, dur = float(i.get("time") or 0), float(i.get("duration") or 0) or float(playing["meta"].get("dur") or 0)
                if pos > 0:
                    nrk.progress.update(playing["id"], pos, dur)
            except Exception:
                pass

    threading.Thread(target=watch, daemon=True).start()
    return [web.get("/api/nrk/search", h_search), web.get("/api/nrk/popular", h_popular),
            web.get("/api/nrk/series/{sid}", h_series), web.get("/api/nrk/continue", h_continue),
            web.post("/api/nrk/play", h_play)]
