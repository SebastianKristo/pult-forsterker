"""Smart radio: en endeløs kanal ut fra en låt eller artist, med låter fra Navidrome (Subsonic) eller Music Assistant.

Neste låt velges blant kandidater (lignende låter, topplåter for artisten, tilfeldige i samme sjanger) etter hvor godt den
passer den forrige: tempo (BPM), energi (RMS) og klang (MFCC-snitt), regnet ut med numpy fra et 30-s utdrag (ffmpeg).
Analysen caches per låt. Samme artist høyst 2 ganger på rad, og ingen gjentak blant de siste 50.

Daemonen kaller routes(ctx) og start(ctx). ctx: settings(), subsonic() -> skjold_recognize.Subsonic|None,
play_url(url, title, image, genre, meta), lyr_info() -> dict, data_dir, ma (valgfri, settes av skjold_ma.routes).
"""
from __future__ import annotations

import json
import math
import os
import random
import subprocess
import threading
import time
from collections import deque

try:
    import numpy as np
except Exception:   # pragma: no cover – numpy finnes på Skjold
    np = None

SR = 22050


# ---------- lydanalyse ----------
def _frames(x, n, hop):
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    k = 1 + (len(x) - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(k)[:, None]
    return x[idx]


def bpm_of(x, sr=SR):
    """Tempo fra onset-styrke (positiv spektralfluks) og autokorrelasjon, søkt i 60–180 BPM."""
    n, hop = 1024, 256
    f = _frames(x, n, hop) * np.hanning(n)
    mag = np.abs(np.fft.rfft(f, axis=1))
    flux = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
    flux = flux - flux.mean()
    if not np.any(flux):
        return 0.0
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    fps = sr / hop
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
    hi = min(hi, len(ac) - 1)
    if hi <= lo:
        return 0.0
    lag = lo + int(np.argmax(ac[lo:hi + 1]))
    # parabolsk interpolasjon for finere tempo
    if lo < lag < hi:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        d = (a - c) / (2 * (a - 2 * b + c)) if (a - 2 * b + c) else 0.0
        lag = lag + d
    return round(60.0 * fps / lag, 1)


def _mel(n_fft, sr, n_mels=26):
    def hz2m(h): return 2595 * math.log10(1 + h / 700)
    def m2hz(m): return 700 * (10 ** (m / 2595) - 1)
    pts = [m2hz(m) for m in np.linspace(hz2m(30), hz2m(sr / 2), n_mels + 2)]
    bins = np.floor((n_fft + 1) * np.array(pts) / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(1, n_mels + 1):
        l, c, r = bins[i - 1], bins[i], bins[i + 1]
        for k in range(l, c):
            fb[i - 1, k] = (k - l) / max(1, c - l)
        for k in range(c, r):
            fb[i - 1, k] = (r - k) / max(1, r - c)
    return fb


def features(x, sr=SR):
    """{bpm, rms, centroid, mfcc[13]} for et mono-signal (float, −1..1)."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return {"bpm": 0.0, "rms": 0.0, "centroid": 0.0, "mfcc": [0.0] * 13}
    n, hop = 2048, 512
    f = _frames(x, n, hop) * np.hanning(n)
    spec = np.abs(np.fft.rfft(f, axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / sr)
    tot = spec.sum(axis=1) + 1e-12
    centroid = float(np.mean((spec * freqs).sum(axis=1) / tot))
    mel = np.log(spec @ _mel(n, sr).T + 1e-10)
    k = np.arange(mel.shape[1])
    dct = np.cos(np.pi / mel.shape[1] * (k[None, :] + 0.5) * np.arange(13)[:, None])
    mfcc = (mel @ dct.T).mean(axis=0)
    return {"bpm": bpm_of(x, sr), "rms": float(np.sqrt(np.mean(x ** 2))), "centroid": round(centroid, 1),
            "mfcc": [round(float(v), 3) for v in mfcc]}


def decode(url, start=30, dur=30, sr=SR, timeout=60):
    out = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", url,
                          "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True, timeout=timeout)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError("kunne ikke dekode: " + (out.stderr.decode(errors="replace")[-200:] or "tomt"))
    return np.frombuffer(out.stdout, dtype=np.int16).astype(np.float64) / 32768.0


def _tempo_ratio(a, b):
    if not a or not b:
        return 1.0
    r = max(a, b) / min(a, b)
    # halv/dobbel tid regnes som samme puls
    return min(r, abs(r - 2) + 1, abs(r - 0.5) + 1)


def distance(a, b):
    """Lavere = likere. Tempo (±8 % er gratis), klang (MFCC), energi og lyshet (sentroide)."""
    t = max(0.0, _tempo_ratio(a.get("bpm", 0), b.get("bpm", 0)) - 1.08) * 10
    ma, mb = np.array(a.get("mfcc") or [0] * 13), np.array(b.get("mfcc") or [0] * 13)
    timbre = float(np.linalg.norm(ma[1:] - mb[1:])) / (1 + float(np.linalg.norm(ma[1:])))
    ea, eb = a.get("rms", 0) or 1e-6, b.get("rms", 0) or 1e-6
    energy = abs(math.log(ea / eb))
    ca, cb = a.get("centroid", 0) or 1, b.get("centroid", 0) or 1
    bright = abs(math.log(ca / cb))
    return 1.5 * t + 2.0 * timbre + 1.0 * energy + 0.8 * bright


def choose_next(cur, candidates, recent_ids=(), recent_artists=(), rnd=None):
    """cur: features for låta som spiller. candidates: [{id, artist, feat?}]. Gir beste kandidat (dict) eller None."""
    rnd = rnd or random.Random()
    recent_ids = set(recent_ids)
    last = list(recent_artists)[-2:]
    pool = [c for c in candidates if c.get("id") not in recent_ids]
    if len(last) == 2 and last[0] and last[0] == last[1]:
        pool = [c for c in pool if (c.get("artist") or "").lower() != last[-1].lower()] or pool
    if not pool:
        return None
    scored = []
    for c in pool:
        d = distance(cur, c["feat"]) if cur and c.get("feat") else 3.0
        scored.append((d + rnd.random() * 0.15, c))
    scored.sort(key=lambda t: t[0])
    return scored[0][1]


# ---------- kilder ----------
def _songs(r, *path):
    for p in path:
        r = (r or {}).get(p) or {}
    if isinstance(r, list):
        return r
    return r.get("song") or [] if isinstance(r, dict) else []


def nd_candidates(nd, seed):
    out, seen = [], set()

    def add(lst):
        for s in lst or []:
            if s.get("id") and s["id"] not in seen:
                seen.add(s["id"])
                out.append({"id": s["id"], "title": s.get("title", ""), "artist": s.get("artist", ""), "album": s.get("album", ""),
                            "genre": s.get("genre", ""), "duration": s.get("duration", 0), "cover": s.get("coverArt", ""), "src": "navidrome"})
    try:
        if seed.get("id"):
            add(_songs(nd._call("getSimilarSongs2", id=seed["id"], count=40), "similarSongs2"))
    except Exception:
        pass
    try:
        if seed.get("artist"):
            add(_songs(nd._call("getTopSongs", artist=seed["artist"], count=20), "topSongs"))
    except Exception:
        pass
    try:
        if seed.get("genre"):
            add(_songs(nd._call("getRandomSongs", size=30, genre=seed["genre"]), "randomSongs"))
        if len(out) < 10:
            add(_songs(nd._call("getRandomSongs", size=30), "randomSongs"))
    except Exception:
        pass
    return out


def nd_stream_url(nd, song_id):
    import hashlib
    import secrets
    import urllib.parse
    salt = secrets.token_hex(6)
    q = {"id": song_id, "u": nd.user, "t": hashlib.md5((nd.pw + salt).encode()).hexdigest(), "s": salt,
         "v": "1.16.1", "c": "skjold", "format": "mp3", "maxBitRate": "320"}
    return f"{nd.url}/rest/stream.view?" + urllib.parse.urlencode(q)


def nd_cover_url(nd, cover_id):
    if not cover_id:
        return ""
    import hashlib
    import secrets
    import urllib.parse
    salt = secrets.token_hex(6)
    q = {"id": cover_id, "u": nd.user, "t": hashlib.md5((nd.pw + salt).encode()).hexdigest(), "s": salt, "v": "1.16.1", "c": "skjold", "size": "600"}
    return f"{nd.url}/rest/getCoverArt.view?" + urllib.parse.urlencode(q)


def ma_candidates(ma, seed):
    """Music Assistant: søk på artist/sjanger (MA har ikke et stabilt «lignende»-kall i alle versjoner)."""
    out = []
    q = seed.get("artist") or seed.get("title") or ""
    if not q or ma is None:
        return out
    try:
        res = ma.search(q, ["tracks"], 40)
        for t in res.get("tracks") or []:
            out.append({"id": t.get("uri") or t.get("id"), "title": t.get("name") or t.get("title", ""), "artist": t.get("artist", ""),
                        "album": t.get("album", ""), "src": "ma", "uri": t.get("uri"), "image": t.get("image", "")})
    except Exception:
        pass
    return out


# ---------- motor ----------
class SmartRadio:
    def __init__(self, ctx):
        self.ctx = ctx
        self.lock = threading.Lock()
        self.cache_path = os.path.join(ctx.get("data_dir") or "/var/lib/ki-amp", "smartradio_features.json")
        self.cache = self._load()
        self.reset()

    def reset(self):
        self.active, self.seed, self.src = False, None, ""
        self.queue, self.current, self.cur_feat = [], None, None
        self.recent_ids, self.recent_artists = deque(maxlen=50), deque(maxlen=5)
        self.pool, self.err = [], ""

    def _load(self):
        try:
            with open(self.cache_path) as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path + ".tmp", "w") as fh:
                json.dump(self.cache, fh)
            os.replace(self.cache_path + ".tmp", self.cache_path)
        except Exception:
            pass

    def feat(self, cand):
        key = cand.get("id")
        if key in self.cache:
            return self.cache[key]
        if cand.get("src") != "navidrome" or np is None:
            return None
        nd = self.ctx["subsonic"]()
        if not nd:
            return None
        try:
            f = features(decode(nd_stream_url(nd, cand["id"])))
        except Exception:
            return None
        self.cache[key] = f
        if len(self.cache) > 5000:
            for k in list(self.cache)[:1000]:
                self.cache.pop(k, None)
        self._save()
        return f

    def status(self):
        return {"active": self.active, "seed": self.seed, "source": self.src, "current": self.current,
                "next": self.queue[:3], "error": self.err or None,
                "label": ("Smart radio fra " + (self.seed.get("title") or self.seed.get("artist") or "")) if self.active and self.seed else ""}

    def start(self, seed):
        nd = self.ctx["subsonic"]()
        ma = self.ctx.get("ma")
        src = seed.get("source") or ("navidrome" if nd else "ma")
        with self.lock:
            self.reset()
            self.seed, self.src, self.active = dict(seed), src, True
        self._refill(first=True)
        if not self.pool and not self.queue:
            self.active, self.err = False, "Fant ingen låter å bygge radioen av"
            raise RuntimeError(self.err)
        self.advance()
        return self.status()

    def stop(self):
        with self.lock:
            self.active = False
        return self.status()

    def _refill(self, first=False):
        nd = self.ctx["subsonic"]()
        seed = dict(self.seed or {})
        if self.current:
            seed.update({"id": self.current.get("id") if self.current.get("src") == "navidrome" else seed.get("id"),
                         "artist": self.current.get("artist") or seed.get("artist"), "genre": self.current.get("genre") or seed.get("genre")})
        cands = nd_candidates(nd, seed) if self.src == "navidrome" and nd else ma_candidates(self.ctx.get("ma"), seed)
        known = {c["id"] for c in self.pool}
        self.pool += [c for c in cands if c["id"] not in known]
        if first and self.seed.get("id") and self.src == "navidrome" and not any(c["id"] == self.seed["id"] for c in self.queue):
            # start med selve låta det ble valgt fra
            s = next((c for c in self.pool if c["id"] == self.seed["id"]), None) or {
                "id": self.seed["id"], "title": self.seed.get("title", ""), "artist": self.seed.get("artist", ""), "src": "navidrome"}
            self.queue.insert(0, s)

    def _pick(self):
        ref = self.queue[-1] if self.queue else self.current
        ref_feat = (ref or {}).get("feat") or (self.feat(ref) if ref else None)
        cands = [c for c in self.pool if c["id"] not in {q["id"] for q in self.queue}]
        rnd = random.Random()
        rnd.shuffle(cands)
        cands = cands[:12]
        for c in cands:
            if "feat" not in c:
                c["feat"] = self.feat(c)
        arts = list(self.recent_artists) + [q.get("artist", "") for q in self.queue]
        return choose_next(ref_feat, cands, list(self.recent_ids) + [q["id"] for q in self.queue], arts, rnd)

    def fill(self):
        if not self.active:
            return
        if len(self.pool) - len(self.recent_ids) < 8:
            self._refill()
        while self.active and len(self.queue) < 3:
            c = self._pick()
            if not c:
                break
            self.queue.append(c)

    def advance(self):
        if not self.active:
            return
        self.fill()
        if not self.queue:
            self.active, self.err = False, "Tom for låter"
            return
        c = self.queue.pop(0)
        self.current = c
        self.recent_ids.append(c["id"])
        self.recent_artists.append(c.get("artist", ""))
        if c.get("src") == "navidrome":
            nd = self.ctx["subsonic"]()
            self.ctx["play_url"](nd_stream_url(nd, c["id"]), c.get("title", ""), nd_cover_url(nd, c.get("cover", "")), c.get("genre", ""),
                                 {"track": c.get("title", ""), "artist": c.get("artist", ""), "album": c.get("album", ""),
                                  "duration": float(c.get("duration") or 0), "source": "Smart radio"})
        elif self.ctx.get("ma") is not None and c.get("uri"):
            self.ctx["ma"].play(c["uri"], "play")
        threading.Thread(target=self.fill, daemon=True).start()

    def tick(self):
        """Kalles hvert 2. s: går videre når låta er slutt (Lyrion stopper, eller tiden er nådd)."""
        if not self.active or not self.current:
            return
        i = self.ctx["lyr_info"]() or {}
        dur, t, mode = float(i.get("duration") or 0), float(i.get("time") or 0), i.get("mode")
        started = time.time() - getattr(self, "_t0", 0) > 8
        if started and (mode == "stop" or (dur > 0 and t >= dur - 1.0)):
            self._t0 = time.time()
            self.advance()


def routes(ctx):
    from aiohttp import web
    import asyncio
    sr = SmartRadio(ctx)
    ctx["smartradio"] = sr

    def loop():
        sr._t0 = 0
        while True:
            time.sleep(2)
            try:
                sr.tick()
            except Exception as e:
                print("Smart radio:", e, flush=True)
    threading.Thread(target=loop, daemon=True).start()

    async def h_get(_r):
        return web.json_response(sr.status())

    async def h_post(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        try:
            if b.get("stop"):
                res = sr.stop()
            elif b.get("skip"):
                await asyncio.get_running_loop().run_in_executor(None, sr.advance)
                res = sr.status()
            else:
                sr._t0 = time.time()
                res = await asyncio.get_running_loop().run_in_executor(None, sr.start, b.get("seed") or b)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=409)
        return web.json_response(res)

    return [web.get("/api/smartradio", h_get), web.post("/api/smartradio", h_post)]


# ---------- Ukentlig «Oppdag»-liste ----------
def _k(artist, title):
    return ((artist or "").strip().lower(), (title or "").strip().lower())


def taste(history, now, weeks=6):
    """Toppartister og -sjangre fra lyttehistorikken de siste `weeks` ukene."""
    t0 = now - weeks * 7 * 86400
    arts, gen = {}, {}
    for e in history:
        if float(e.get("t") or 0) < t0:
            continue
        a = (e.get("artist") or "").strip()
        if a:
            arts[a] = arts.get(a, 0) + 1
        g = (e.get("genre") or "").strip()
        if g:
            gen[g] = gen.get(g, 0) + 1
    top = lambda d, n: [k for k, _ in sorted(d.items(), key=lambda kv: -kv[1])[:n]]
    return {"artists": top(arts, 8), "genres": top(gen, 4)}


def flow_order(items, feat_of):
    """Grådig nærmeste nabo fra roligste låt, så BPM/energi glir i stedet for å hoppe."""
    rest = list(items)
    if not rest:
        return []
    keyf = lambda c: ((feat_of(c) or {}).get("rms", 0), (feat_of(c) or {}).get("bpm", 0))
    rest.sort(key=keyf)
    out = [rest.pop(0)]
    while rest:
        cur = feat_of(out[-1])
        if cur:
            j = min(range(len(rest)), key=lambda i: distance(cur, feat_of(rest[i])) if feat_of(rest[i]) else 9.0)
        else:
            j = 0
        out.append(rest.pop(j))
    return out


def select_discover(cands, history, now, size=35, per_artist=2, played_days=90, rnd=None, feat_of=lambda c: c.get("feat")):
    """Velg Oppdag-lista: ikke spilt siste `played_days`, høyst `per_artist` per artist, flytsortert."""
    rnd = rnd or random.Random()
    t0 = now - played_days * 86400
    played = {_k(e.get("artist"), e.get("title") or e.get("song")) for e in history if float(e.get("t") or 0) >= t0}
    pool, seen = [], set()
    for c in cands:
        k = _k(c.get("artist"), c.get("title"))
        if not k[1] or k in played or k in seen or c.get("id") in seen:
            continue
        seen.add(k)
        seen.add(c.get("id"))
        pool.append(c)
    rnd.shuffle(pool)
    count, out = {}, []
    for c in pool:
        a = (c.get("artist") or "").lower()
        if count.get(a, 0) >= per_artist:
            continue
        count[a] = count.get(a, 0) + 1
        out.append(c)
        if len(out) >= size:
            break
    return flow_order(out, feat_of)


def week_no(now):
    return int(time.strftime("%V", time.localtime(now)))


class Discover:
    DEF = {"enabled": True, "day": 0, "time": "06:00", "size": 35, "weeks": 6, "archive": True, "sources": ["navidrome", "ma"]}

    def __init__(self, ctx, sr):
        self.ctx, self.sr = ctx, sr
        self.path = os.path.join(ctx.get("data_dir") or "/var/lib/ki-amp", "discover.json")
        self.data = self._load()
        self.busy, self.err = False, ""

    def _load(self):
        try:
            with open(self.path) as fh:
                return json.load(fh)
        except Exception:
            return {"cfg": dict(self.DEF), "lists": []}

    def _save(self):
        try:
            with open(self.path + ".tmp", "w") as fh:
                json.dump(self.data, fh)
            os.replace(self.path + ".tmp", self.path)
        except Exception:
            pass

    def cfg(self):
        return {**self.DEF, **(self.data.get("cfg") or {})}

    def set_cfg(self, b):
        c = self.cfg()
        for k in self.DEF:
            if k in b:
                c[k] = b[k]
        self.data["cfg"] = c
        self._save()

    def status(self):
        cur = (self.data.get("lists") or [None])[-1]
        return {"cfg": self.cfg(), "current": cur, "busy": self.busy, "error": self.err or None}

    def build(self, now=None):
        now = now or time.time()
        c = self.cfg()
        nd = self.ctx["subsonic"]()
        hist = self.ctx["history"]() or []
        tst = taste(hist, now, int(c.get("weeks") or 6))
        cands = []
        if nd and "navidrome" in c.get("sources", []):
            for a in tst["artists"][:6]:
                try:
                    info = nd._call("getArtistInfo2", id=self._artist_id(nd, a), count=6) if self._artist_id(nd, a) else {}
                    sims = [s.get("name") for s in ((info.get("artistInfo2") or {}).get("similarArtist") or [])]
                except Exception:
                    sims = []
                for name in [a] + sims[:4]:
                    cands += nd_candidates(nd, {"artist": name})
            for g in tst["genres"]:
                cands += nd_candidates(nd, {"genre": g})
            try:
                for al in ((nd._call("getAlbumList2", type="newest", size=10).get("albumList2") or {}).get("album") or []):
                    for s in ((nd._call("getAlbum", id=al["id"]).get("album") or {}).get("song") or [])[:3]:
                        cands.append({"id": s["id"], "title": s.get("title", ""), "artist": s.get("artist", ""), "album": s.get("album", ""),
                                      "duration": s.get("duration", 0), "cover": s.get("coverArt", ""), "src": "navidrome"})
            except Exception:
                pass
        if self.ctx.get("ma") is not None and "ma" in c.get("sources", []):
            for a in tst["artists"][:4]:
                cands += ma_candidates(self.ctx["ma"], {"artist": a})
        for x in cands:
            if x["id"] in self.sr.cache:
                x["feat"] = self.sr.cache[x["id"]]
        picked = select_discover(cands, hist, now, int(c.get("size") or 35))
        wk = week_no(now)
        name = f"Oppdag uke {wk}"
        entry = {"name": name, "week": wk, "t": now, "tracks": [{k: v for k, v in p.items() if k != "feat"} for p in picked], "navidrome": None}
        if nd:
            try:
                ids = [p["id"] for p in picked if p.get("src") == "navidrome"]
                pls = (nd._call("getPlaylists").get("playlists") or {}).get("playlist") or []
                for p in pls:   # erstatt forrige (eller behold de 4 siste som arkiv)
                    if str(p.get("name", "")).startswith("Oppdag uke"):
                        old = [x for x in pls if str(x.get("name", "")).startswith("Oppdag uke")]
                        if not c.get("archive") or len(old) >= 4 or p.get("name") == name:
                            nd._call("deletePlaylist", id=p["id"])
                if ids:
                    r = nd._call("createPlaylist", name=name, songId=ids)
                    entry["navidrome"] = ((r.get("playlist") or {}).get("id")) or True
            except Exception as e:
                self.err = f"Navidrome: {e}"
        self.data.setdefault("lists", []).append(entry)
        self.data["lists"] = self.data["lists"][-4:]
        self.data["last_run"] = now
        self._save()
        return entry

    def _artist_id(self, nd, name):
        try:
            r = nd._call("search3", query=name, artistCount=1, songCount=0, albumCount=0)
            a = ((r.get("searchResult3") or {}).get("artist") or [])
            return a[0]["id"] if a else None
        except Exception:
            return None

    def run(self):
        if self.busy:
            return self.status()
        self.busy, self.err = True, ""
        try:
            self.build()
        except Exception as e:
            self.err = str(e)
        finally:
            self.busy = False
        return self.status()

    def due(self, now=None):
        now = now or time.time()
        c = self.cfg()
        if not c.get("enabled"):
            return False
        tm = time.localtime(now)
        if tm.tm_wday != int(c.get("day", 0)) or time.strftime("%H:%M", tm) < str(c.get("time", "06:00")):
            return False
        return float(self.data.get("last_run") or 0) < now - 6 * 86400

    def play(self, shuffle=False):
        cur = (self.data.get("lists") or [None])[-1]
        if not cur or not cur.get("tracks"):
            raise RuntimeError("Ingen Oppdag-liste ennå")
        tracks = list(cur["tracks"])
        if shuffle:
            random.shuffle(tracks)
        sr = self.sr
        with sr.lock:
            sr.reset()
            sr.active, sr.src = True, "navidrome"
            sr.seed = {"title": cur["name"]}
            sr.queue = tracks
            sr.pool = list(tracks)
        sr._t0 = time.time()
        sr.advance()
        return sr.status()


def discover_routes(ctx):
    from aiohttp import web
    import asyncio
    dv = Discover(ctx, ctx["smartradio"])
    ctx["discover"] = dv

    def loop():
        while True:
            time.sleep(60)
            try:
                if dv.due():
                    dv.run()
            except Exception as e:
                print("Oppdag-liste:", e, flush=True)
    threading.Thread(target=loop, daemon=True).start()

    async def h(r):
        if r.method == "GET":
            return web.json_response(dv.status())
        try:
            b = await r.json()
        except Exception:
            b = {}
        loop_ = asyncio.get_running_loop()
        try:
            if "cfg" in b:
                dv.set_cfg(b["cfg"])
            if b.get("build"):
                await loop_.run_in_executor(None, dv.run)
            if b.get("play"):
                await loop_.run_in_executor(None, dv.play, bool(b.get("shuffle")))
        except Exception as e:
            return web.json_response({"error": str(e)}, status=409)
        return web.json_response(dv.status())

    return [web.get("/api/discover", h), web.post("/api/discover", h)]
