"""Lyd-beskrivelse av musikkbiblioteket (Navidrome): energi, tempo, stemning, akustisk/elektronisk og instrumental/vokal.

Bakgrunnsjobb med lav prioritet (nice 19, ionice idle for ffmpeg) som går gjennom hele biblioteket via Subsonic-API-et,
dekoder et 30-s utdrag per låt (ffmpeg) og regner ut enkle lydtrekk med numpy – ingen ML-modeller. Resultatet lagres i
SQLite (data_dir/libtags.db) med fremdrift, så jobben fortsetter der den slapp etter omstart. På Pi 3 pauser jobben mens
noe spilles. Taggene brukes av søket (/api/library/search), smart radio, Oppdag-listen og «Spill noe til …».

Daemonen kaller routes(ctx). ctx: subsonic() -> Subsonic|None, lyr_info() -> dict, data_dir, settings().
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import subprocess
import threading
import time

try:
    import numpy as np
except Exception:   # pragma: no cover
    np = None

SR = 22050
MOODS = ("glad", "rolig", "trist", "energisk", "mørk", "drømmende")


# ---------- lydtrekk ----------
def _frames(x, n, hop):
    if x.size < n:
        x = np.pad(x, (0, n - x.size))
    k = 1 + (x.size - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(k)[:, None]
    return x[idx]


def _bpm(x, sr):
    try:
        from skjold_smartradio import bpm_of   # samme tempo-algoritme som smart radio
        return float(bpm_of(x, sr))
    except Exception:
        n, hop = 1024, 512
        f = _frames(x, n, hop)
        env = np.sqrt((f ** 2).mean(axis=1))
        onset = np.maximum(0, np.diff(env))
        if onset.size < 8 or onset.std() == 0:
            return 0.0
        onset = onset - onset.mean()
        ac = np.correlate(onset, onset, "full")[onset.size - 1:]
        fps = sr / hop
        lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)
        if hi >= ac.size:
            return 0.0
        lag = lo + int(np.argmax(ac[lo:hi]))
        return round(60 * fps / lag, 1)


def _chroma_major(spec, freqs):
    """True hvis toneart-profilen ligner mer på dur enn moll (Krumhansl-profiler)."""
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    m = (freqs > 60) & (freqs < 2000)
    pc = (np.round(12 * np.log2(freqs[m] / 440.0)) + 9) % 12
    chroma = np.zeros(12)
    np.add.at(chroma, pc.astype(int), spec[:, m].sum(axis=0))
    if chroma.sum() <= 0:
        return True, 0.0
    chroma = chroma / chroma.sum()
    best_maj = max(float(np.corrcoef(chroma, np.roll(maj, k))[0, 1]) for k in range(12))
    best_min = max(float(np.corrcoef(chroma, np.roll(mnr, k))[0, 1]) for k in range(12))
    return best_maj >= best_min, round(best_maj - best_min, 3)


def describe(x, sr=SR):
    """Lydtrekk og tagger for et mono-signal (float −1..1).

    Returnerer {bpm, energy 0–1, brightness 0–1, dynamics 0–1, flatness 0–1, perc 0–1, vocal 0–1, major, valence 0–1,
    arousal 0–1, acoustic bool, instrumental bool, mood}."""
    x = np.asarray(x, dtype=np.float64)
    if x.size < sr:
        x = np.pad(x, (0, sr - x.size))
    n, hop = 2048, 1024
    f = _frames(x, n, hop) * np.hanning(n)
    spec = np.abs(np.fft.rfft(f, axis=1)) ** 2 + 1e-12
    freqs = np.fft.rfftfreq(n, 1 / sr)
    rms = np.sqrt((f ** 2).mean(axis=1))
    energy = float(min(1.0, np.sqrt(np.mean(x ** 2)) / 0.25))
    centroid = float(np.mean((spec * freqs).sum(axis=1) / spec.sum(axis=1)))
    brightness = float(min(1.0, centroid / 4000.0))
    db = 20 * np.log10(rms + 1e-9)
    dynamics = float(min(1.0, max(0.0, (np.percentile(db, 95) - np.percentile(db, 10)) / 30.0)))
    flat = np.exp(np.mean(np.log(spec), axis=1)) / np.mean(spec, axis=1)
    flatness = float(np.clip(np.mean(flat) * 4, 0, 1))
    # harmonisk/perkussiv: perkussivt = bredbåndet energi som endrer seg raskt mellom rammer (spektral fluks)
    flux = np.sqrt((np.diff(np.log(spec), axis=0) ** 2).mean(axis=1))
    perc = float(np.clip((np.mean(flux) - 0.6) / 1.4, 0, 1))
    # vokal: andel energi i 300–3400 Hz som varierer over tid (stemmer svinger mer enn jevne instrumenter)
    vb = (freqs >= 300) & (freqs <= 3400)
    vshare = spec[:, vb].sum(axis=1) / spec.sum(axis=1)
    vocal = float(np.clip((np.mean(vshare) - 0.5) * 0.6 + np.std(vshare) * 6.0, 0, 1))   # jevne toner gir lite
    major, mscore = _chroma_major(spec, freqs)
    bpm = _bpm(x, sr)
    tempo = min(1.0, max(0.0, (bpm - 60) / 110.0)) if bpm else 0.4
    arousal = float(np.clip(0.45 * energy + 0.3 * tempo + 0.25 * perc, 0, 1))
    valence = float(np.clip(0.5 + (0.25 if major else -0.25) + 0.25 * (brightness - 0.4), 0, 1))
    acoustic = bool(flatness < 0.35 and perc < 0.55 and brightness < 0.6)
    instrumental = bool(vocal < 0.45)
    return {"bpm": round(bpm, 1), "energy": round(energy, 3), "brightness": round(brightness, 3), "dynamics": round(dynamics, 3),
            "flatness": round(flatness, 3), "perc": round(perc, 3), "vocal": round(vocal, 3), "major": bool(major),
            "valence": round(valence, 3), "arousal": round(arousal, 3), "acoustic": acoustic, "instrumental": instrumental,
            "mood": mood_of(valence, arousal, brightness)}


def mood_of(valence, arousal, brightness=0.5):
    if arousal >= 0.62:
        return "energisk" if valence >= 0.45 else "mørk"
    if arousal <= 0.38:
        if valence >= 0.6:
            return "rolig"
        return "trist" if brightness < 0.45 else "drømmende"
    return "glad" if valence >= 0.55 else ("drømmende" if brightness >= 0.45 else "trist")


def decode(url, start=30, dur=30, sr=SR, timeout=90):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", url,
           "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    if os.path.exists("/usr/bin/ionice"):
        cmd = ["ionice", "-c3", "nice", "-n", "19"] + cmd
    out = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError("kunne ikke dekode: " + (out.stderr.decode(errors="replace")[-200:] or "tomt"))
    return np.frombuffer(out.stdout, dtype=np.int16).astype(np.float64) / 32768.0


# ---------- lagring ----------
COLS = ("bpm", "energy", "brightness", "dynamics", "flatness", "perc", "vocal", "valence", "arousal")


class Store:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS tags (id TEXT PRIMARY KEY, title TEXT, artist TEXT, album TEXT, genre TEXT,
                         year INTEGER, duration INTEGER, cover TEXT, bpm REAL, energy REAL, brightness REAL, dynamics REAL,
                         flatness REAL, perc REAL, vocal REAL, major INTEGER, valence REAL, arousal REAL, acoustic INTEGER,
                         instrumental INTEGER, mood TEXT, error TEXT, t REAL)""")
            c.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")

    def _db(self):
        return sqlite3.connect(self.path, timeout=10)

    def has(self, sid):
        with self._lock, self._db() as c:
            return c.execute("SELECT 1 FROM tags WHERE id=?", (sid,)).fetchone() is not None

    def put(self, song, feat=None, error=None):
        f = feat or {}
        row = (song["id"], song.get("title", ""), song.get("artist", ""), song.get("album", ""), song.get("genre", ""),
               int(song.get("year") or 0), int(song.get("duration") or 0), song.get("cover", ""),
               *[f.get(k) for k in COLS], int(bool(f.get("major"))) if f else None, int(bool(f.get("acoustic"))) if f else None,
               int(bool(f.get("instrumental"))) if f else None, f.get("mood"), error, time.time())
        with self._lock, self._db() as c:
            c.execute("INSERT OR REPLACE INTO tags VALUES (" + ",".join("?" * 23) + ")", row)

    def get(self, sid):
        with self._lock, self._db() as c:
            c.row_factory = sqlite3.Row
            r = c.execute("SELECT * FROM tags WHERE id=?", (sid,)).fetchone()
            return dict(r) if r else None

    def meta(self, k, v=None):
        with self._lock, self._db() as c:
            if v is None:
                r = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
                return json.loads(r[0]) if r else None
            c.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, json.dumps(v)))

    def count(self):
        with self._lock, self._db() as c:
            done = c.execute("SELECT COUNT(*) FROM tags WHERE error IS NULL").fetchone()[0]
            err = c.execute("SELECT COUNT(*) FROM tags WHERE error IS NOT NULL").fetchone()[0]
            return done, err

    def search(self, mood=None, energy=None, acoustic=None, instrumental=None, bpm=None, genre=None, decade=None,
               limit=50, order="random"):
        """energy: «lav»/«middels»/«høy» eller tall 0–1; bpm: «90-120» eller tall (±10)."""
        q, a = ["error IS NULL"], []
        if mood:
            moods = [m.strip() for m in str(mood).split(",") if m.strip()]
            q.append("mood IN (" + ",".join("?" * len(moods)) + ")"); a += moods
        if energy not in (None, ""):
            rng = {"lav": (0, 0.35), "middels": (0.3, 0.65), "høy": (0.6, 1.01)}.get(str(energy))
            if rng is None:
                v = float(energy); rng = (v - 0.15, v + 0.15)
            q.append("energy BETWEEN ? AND ?"); a += list(rng)
        if acoustic not in (None, ""):
            q.append("acoustic=?"); a.append(1 if str(acoustic).lower() in ("1", "true", "ja", "akustisk") else 0)
        if instrumental not in (None, ""):
            q.append("instrumental=?"); a.append(1 if str(instrumental).lower() in ("1", "true", "ja", "instrumental") else 0)
        if bpm not in (None, ""):
            s = str(bpm)
            lo, hi = (float(s.split("-")[0]), float(s.split("-")[1])) if "-" in s else (float(s) - 10, float(s) + 10)
            q.append("bpm BETWEEN ? AND ?"); a += [lo, hi]
        if genre:
            gs = [g.strip().lower() for g in str(genre).split(",") if g.strip()]
            q.append("(" + " OR ".join("LOWER(genre) LIKE ?" for _ in gs) + ")"); a += ["%" + g + "%" for g in gs]
        if decade:
            d = int(str(decade).rstrip("s")[:4])
            q.append("year BETWEEN ? AND ?"); a += [d, d + 9]
        sql = "SELECT * FROM tags WHERE " + " AND ".join(q) + (" ORDER BY RANDOM()" if order == "random" else " ORDER BY artist, album")
        with self._lock, self._db() as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute(sql + " LIMIT ?", (*a, int(limit))).fetchall()]


# ---------- bakgrunnsjobb ----------
def _is_pi3():
    try:
        with open("/proc/device-tree/model") as fh:
            return "Raspberry Pi 3" in fh.read()
    except OSError:
        return False


def iter_library(nd, page=200):
    """Alle låter i Navidrome (album for album, alfabetisk)."""
    off = 0
    while True:
        r = nd._call("getAlbumList2", type="alphabeticalByName", size=page, offset=off)
        albums = ((r or {}).get("albumList2") or {}).get("album") or []
        if not albums:
            return
        for al in albums:
            try:
                songs = ((nd._call("getAlbum", id=al["id"]) or {}).get("album") or {}).get("song") or []
            except Exception:
                songs = []
            for s in songs:
                yield {"id": s["id"], "title": s.get("title", ""), "artist": s.get("artist", ""), "album": s.get("album", ""),
                       "genre": s.get("genre", ""), "year": s.get("year", 0), "duration": s.get("duration", 0),
                       "cover": s.get("coverArt", ""), "path": s.get("path", "")}
        off += page


class LibTagger:
    def __init__(self, ctx, store=None):
        self.ctx = ctx
        self.store = store or Store(os.path.join(ctx.get("data_dir", "/var/lib/ki-amp"), "libtags.db"))
        self.running = False
        self.paused = bool(self.store.meta("paused"))
        self.total = int(self.store.meta("total") or 0)
        self.current = ""
        self.last_error = ""
        self._thread = None

    def _music_root(self):
        try:
            return (self.ctx.get("settings", lambda: {})() or {}).get("ndMusicDir", "")
        except Exception:
            return ""

    def _source(self, nd, song):
        root = self._music_root()
        if root and song.get("path"):
            p = os.path.join(root, song["path"])
            if os.path.exists(p):
                return p
        from skjold_smartradio import nd_stream_url
        return nd_stream_url(nd, song["id"])

    def _busy(self):
        if not _is_pi3():
            return False
        try:
            return (self.ctx.get("lyr_info", lambda: {})() or {}).get("mode") == "play"
        except Exception:
            return False

    def status(self):
        done, err = self.store.count()
        return {"running": self.running, "paused": self.paused, "done": done, "errors": err, "total": self.total,
                "progress": round(done / self.total, 3) if self.total else 0.0, "current": self.current,
                "error": self.last_error or None, "moods": list(MOODS)}

    def start(self):
        self.paused = False; self.store.meta("paused", False)
        if not self.running:
            self._thread = threading.Thread(target=self._run, daemon=True); self._thread.start()
        return self.status()

    def pause(self):
        self.paused = True; self.store.meta("paused", True)
        return self.status()

    def _run(self):
        self.running = True
        try:
            os.nice(19)
        except Exception:
            pass
        try:
            nd = self.ctx["subsonic"]()
            if nd is None:
                self.last_error = "Navidrome er ikke satt opp"; return
            songs = list(iter_library(nd))
            self.total = len(songs); self.store.meta("total", self.total)
            for s in songs:
                if self.paused:
                    return
                if self.store.has(s["id"]):
                    continue
                while self._busy() and not self.paused:
                    time.sleep(20)
                self.current = f"{s['artist']} – {s['title']}"
                try:
                    self.store.put(s, describe(decode(self._source(nd, s), start=min(30, max(0, (s.get('duration') or 60) // 3)))))
                except Exception as e:
                    self.store.put(s, None, str(e)[:200])
                time.sleep(0.2)
            self.current = ""
        except Exception as e:
            self.last_error = str(e)[:200]
            print("Biblioteksmerking:", e, flush=True)
        finally:
            self.running = False


def routes(ctx):
    from aiohttp import web
    import asyncio
    lt = LibTagger(ctx)
    ctx["libtag"] = lt
    if not lt.paused and (ctx.get("settings", lambda: {})() or {}).get("libtagAuto", True):
        threading.Timer(120, lambda: lt.start() if ctx["subsonic"]() else None).start()   # start etter oppstart, når alt er roet seg

    async def h_tags(r):
        if r.method == "POST":
            try:
                b = await r.json()
            except Exception:
                b = {}
            a = b.get("action")
            if a == "start":
                return web.json_response(lt.start())
            if a == "pause":
                return web.json_response(lt.pause())
            sid = b.get("id")
            if sid:
                return web.json_response(lt.store.get(sid) or {})
        return web.json_response(lt.status())

    async def h_search(r):
        q = r.query
        try:
            res = await asyncio.get_running_loop().run_in_executor(None, lambda: lt.store.search(
                mood=q.get("mood"), energy=q.get("energy"), acoustic=q.get("acoustic"), instrumental=q.get("instrumental"),
                bpm=q.get("bpm"), genre=q.get("genre"), decade=q.get("decade"), limit=int(q.get("limit") or 50)))
        except (ValueError, TypeError) as e:
            return web.json_response({"error": f"ugyldig filter: {e}"}, status=400)
        return web.json_response({"items": res, "count": len(res)})

    return [web.get("/api/library/tags", h_tags), web.post("/api/library/tags", h_tags), web.get("/api/library/search", h_search)]
