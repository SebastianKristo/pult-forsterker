"""Platesamling: live-gjengivelse av vinyl til FLAC, oppdelt i spor.

Flyt: «Start side A» → ffmpeg tar opp fra AUX (UCA202) mens vi måler nivå hvert 50. ms → «Side ferdig» →
sporene finnes ved stillhet (RMS-terskel + minste pause/sporlengde) → første spor gjenkjennes (AcoustID/AudD via
skjold_recognize) → MusicBrainz gir sporliste og varigheter som retter opp oppdelingen → «Snu platen» (side B) →
«Lagre» skriver Artist/Album/NN Tittel.flac med tagger og omslag (Cover Art Archive) til SMB-delingen.

Rene funksjoner (testes i pi/tests/test_vinyl.py) + en tynn Session-klasse rundt ffmpeg.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import struct
import subprocess
import threading
import time
import urllib.request
import uuid

HOP = 0.05            # sekunder per nivåmåling
SR = 44100
DEFAULTS = {"thresh_db": -45.0, "min_gap": 1.2, "min_track": 30.0, "device": ""}


# ---------------------------------------------------------------- nivå og oppdeling
def rms_db(pcm: bytes, step: int = 4) -> float:
    """RMS i dBFS for s16le-PCM (hver «step»-te sample holder for nivåmåling)."""
    n = len(pcm) // 2
    if n == 0:
        return -120.0
    s = struct.unpack(f"<{n}h", pcm[:n * 2])[::step]
    v = math.sqrt(sum(x * x for x in s) / max(1, len(s))) / 32768.0
    return 20 * math.log10(v) if v > 1e-6 else -120.0


def split_segments(levels: list[float], hop: float = HOP, thresh_db: float = -45.0,
                   min_gap: float = 1.2, min_track: float = 30.0) -> list[tuple[float, float]]:
    """Nivåer (dB per hop) → [(start, slutt)] i sekunder. Stillhet ≥ min_gap deler; korte biter slås sammen."""
    loud = [lv > thresh_db for lv in levels]
    segs, start, quiet = [], None, 0
    gap_n = max(1, int(round(min_gap / hop)))
    for i, on in enumerate(loud):
        if on:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet == gap_n:
                segs.append([start, i - gap_n + 1])
                start = None
    if start is not None:
        end = len(loud) - quiet
        segs.append([start, end])
    # slå sammen for korte spor med naboen (stille passasjer inne i en låt)
    out: list[list[int]] = []
    for s in segs:
        if out and (s[1] - s[0]) * hop < min_track:
            out[-1][1] = s[1]
        elif out and (out[-1][1] - out[-1][0]) * hop < min_track:
            out[-1][1] = s[1]
        else:
            out.append(list(s))
    return [(round(a * hop, 2), round(b * hop, 2)) for a, b in out]


def fit_tracklist(segs: list[tuple[float, float]], durations: list[float], levels: list[float] | None = None,
                  hop: float = HOP) -> list[tuple[float, float]]:
    """Juster oppdelingen så antallet stemmer med sporlisten fra MusicBrainz.

    For mange biter: slå sammen grensen der summen avviker mest fra forventet varighet (minste pause først).
    For få biter: del den lengste biten ved det stilleste punktet nærmest forventet sporlengde.
    """
    segs = [tuple(s) for s in segs]
    want = len(durations)
    if not want or not segs:
        return segs
    while len(segs) > want:
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        i = min(range(len(gaps)), key=lambda k: gaps[k])
        segs[i:i + 2] = [(segs[i][0], segs[i + 1][1])]
    guard = 0
    while len(segs) < want and guard < 50:
        guard += 1
        # finn biten som er mest for lang i forhold til forventet
        best, over = None, 0.0
        for j, (a, b) in enumerate(segs):
            exp = durations[min(j, want - 1)]
            if (b - a) - exp > over:
                best, over = j, (b - a) - exp
        if best is None:
            break
        a, b = segs[best]
        cut = a + durations[min(best, want - 1)]
        if levels:
            lo, hi = int((cut - 10) / hop), int((cut + 10) / hop)
            lo, hi = max(int(a / hop) + 1, lo), min(int(b / hop) - 1, hi)
            if hi > lo:
                cut = min(range(lo, hi), key=lambda x: levels[x]) * hop
        if not (a + 5 < cut < b - 5):
            break
        segs[best:best + 1] = [(a, round(cut, 2)), (round(cut, 2), b)]
    return segs


# ---------------------------------------------------------------- navn og tagger
def safe(s: str, maxlen: int = 80) -> str:
    bad = '/\\:*?"<>|'
    t = "".join(" " if c in bad or ord(c) < 32 else c for c in str(s or "")).strip()
    t = " ".join(t.split()).rstrip(". ")[:maxlen].strip()
    return t or "Ukjent"


def track_relpath(artist: str, album: str, n: int, title: str) -> str:
    return os.path.join(safe(artist), safe(album), f"{n:02d} {safe(title)}.flac")


def plan_tracks(album: dict, sides: list[dict]) -> list[dict]:
    """Samle sidene til én nummerert sporliste med titler fra MusicBrainz der de finnes."""
    names = album.get("tracks") or []
    out, n = [], 0
    for si, side in enumerate(sides):
        for (a, b) in side.get("segs") or []:
            n += 1
            mb = names[n - 1] if n - 1 < len(names) else {}
            out.append({"n": n, "side": side.get("name") or "AB"[si % 2], "start": a, "end": b,
                        "title": mb.get("title") or f"Spor {n}", "raw": side.get("raw", "")})
    return out


def ffmpeg_cut_cmd(src: str, dst: str, start: float, end: float, tags: dict, cover: str = "") -> list[str]:
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", src]
    if cover:
        cmd += ["-i", cover, "-map", "0:a", "-map", "1:v", "-c:v", "copy", "-disposition:v", "attached_pic"]
    cmd += ["-af", "afade=t=in:d=0.05", "-c:a", "flac"]
    for k, v in tags.items():
        if v not in (None, ""):
            cmd += ["-metadata", f"{k}={v}"]
    return cmd + [dst]


def tag_flac(path: str, tags: dict, cover: str = "") -> bool:
    """Skriv/oppdater tagger med mutagen når den finnes (brukes ved redigering). False = mutagen mangler."""
    try:
        from mutagen.flac import FLAC, Picture
    except ImportError:
        return False
    f = FLAC(path)
    for k, v in tags.items():
        if v not in (None, ""):
            f[k] = str(v)
    if cover and os.path.exists(cover) and not f.pictures:
        p = Picture(); p.type = 3; p.mime = "image/jpeg"
        with open(cover, "rb") as fh:
            p.data = fh.read()
        f.add_picture(p)
    f.save()
    return True


# ---------------------------------------------------------------- arkiv
class Archive:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> list[dict]:
        try:
            with open(self.path) as fh:
                return json.load(fh)
        except Exception:
            return []

    def save(self, items: list[dict]) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path + ".tmp", "w") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=1)
        os.replace(self.path + ".tmp", self.path)

    def add(self, rec: dict) -> dict:
        items = [r for r in self.load() if r.get("id") != rec.get("id")]
        self.save([rec] + items)
        return rec

    def get(self, rid: str) -> dict:
        for r in self.load():
            if r.get("id") == rid:
                return r
        raise KeyError("fant ikke platen")

    def delete(self, rid: str) -> list[dict]:
        items = [r for r in self.load() if r.get("id") != rid]
        self.save(items)
        return items

    def edit(self, rid: str, change: dict, root: str = "") -> dict:
        """Endre artist/album/år/spor-titler. Filene får nye navn og tagger når de ligger under root."""
        items = self.load()
        rec = next((r for r in items if r.get("id") == rid), None)
        if not rec:
            raise KeyError("fant ikke platen")
        for k in ("artist", "album", "year"):
            if k in change:
                rec[k] = str(change[k]).strip()
        titles = {int(t["n"]): str(t.get("title", "")).strip() for t in change.get("tracks") or [] if "n" in t}
        for t in rec.get("tracks") or []:
            if titles.get(t["n"]):
                t["title"] = titles[t["n"]]
            new = track_relpath(rec["artist"], rec["album"], t["n"], t["title"])
            if root and t.get("file") and t["file"] != new:
                src, dst = os.path.join(root, t["file"]), os.path.join(root, new)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    os.replace(src, dst)
                    tag_flac(dst, {"ARTIST": rec["artist"], "ALBUMARTIST": rec["artist"], "ALBUM": rec["album"],
                                   "TITLE": t["title"], "TRACKNUMBER": t["n"], "DATE": rec.get("year", "")})
                t["file"] = new
        self.save(items)
        return rec


# ---------------------------------------------------------------- opptaksøkt
class Session:
    """Én plate. ctx: device() -> ALSA, root() -> (mappe, 'smb'|'lokalt'), identify(wav) -> treff|None,
    release(mbid) -> album|None, tmp -> arbeidsmappe, cfg() -> innstillinger, on_change()."""

    def __init__(self, ctx: dict, archive: Archive):
        self.ctx, self.archive = ctx, archive
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.id = uuid.uuid4().hex[:10]
        self.state = "idle"        # idle | recording | review | saving
        self.sides: list[dict] = []
        self.levels: list[float] = []
        self.proc = None
        self.t0 = 0.0
        self.album: dict = {}
        self.msg = ""
        self.progress = 0.0

    # --- status
    def status(self) -> dict:
        cur = {"side": self.sides[-1]["name"], "secs": round(time.time() - self.t0, 1),
               "level": round(self.levels[-1], 1) if self.levels else -120.0} if self.state == "recording" else None
        return {"state": self.state, "id": self.id, "msg": self.msg, "progress": round(self.progress, 2), "now": cur,
                "album": {k: self.album.get(k, "") for k in ("artist", "album", "year", "cover")},
                "tracks": plan_tracks(self.album, self.sides) if self.sides else [],
                "sides": [{"name": s["name"], "secs": s.get("secs", 0), "spor": len(s.get("segs") or [])} for s in self.sides]}

    # --- opptak
    def start_side(self, name: str = "") -> dict:
        with self.lock:
            if self.state == "recording":
                raise RuntimeError("tar allerede opp")
            if self.state == "saving":
                raise RuntimeError("lagrer forrige plate")
            if not shutil.which("ffmpeg"):
                raise RuntimeError("ffmpeg mangler (kjør pi/update.sh)")
            os.makedirs(self.ctx["tmp"], exist_ok=True)
            if not name:
                name = "AB"[len(self.sides)] if len(self.sides) < 2 else f"Side {len(self.sides) + 1}"
            raw = os.path.join(self.ctx["tmp"], f"{self.id}-{len(self.sides) + 1}.wav")
            self.sides.append({"name": name, "raw": raw, "segs": [], "levels": []})
            self.levels = self.sides[-1]["levels"]
            cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "alsa", "-ac", "2", "-ar", str(SR),
                   "-i", self.ctx["device"](), "-f", "s16le", "-ac", "2", "-ar", str(SR), "-"]
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.t0 = time.time()
            self.state, self.msg = "recording", f"Tar opp side {name}"
            threading.Thread(target=self._pump, args=(self.proc, raw, self.levels), daemon=True).start()
        self.ctx["on_change"]()
        return self.status()

    def _pump(self, proc, raw, levels):
        import wave
        blk = int(SR * HOP) * 4
        with wave.open(raw, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            while True:
                b = proc.stdout.read(blk)
                if not b:
                    break
                w.writeframes(b)
                levels.append(rms_db(b, step=8))

    def stop_side(self) -> dict:
        with self.lock:
            if self.state != "recording":
                raise RuntimeError("tar ikke opp nå")
            p, self.proc = self.proc, None
            p.terminate()
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
            time.sleep(0.3)
            side = self.sides[-1]
            side["secs"] = round(len(side["levels"]) * HOP, 1)
            c = {**DEFAULTS, **(self.ctx["cfg"]() or {})}
            side["segs"] = split_segments(side["levels"], HOP, float(c["thresh_db"]), float(c["min_gap"]), float(c["min_track"]))
            self.state, self.msg = "review", f"Side {side['name']}: {len(side['segs'])} spor funnet"
        if not self.album.get("album") and side["segs"]:
            threading.Thread(target=self._identify, args=(side,), daemon=True).start()
        else:
            self._fit()
        self.ctx["on_change"]()
        return self.status()

    def _identify(self, side):
        """Gjenkjenn første spor (20 s ut i det) og hent album fra MusicBrainz."""
        self.msg = "Gjenkjenner platen …"; self.ctx["on_change"]()
        a, b = side["segs"][0]
        clip = os.path.join(self.ctx["tmp"], f"{self.id}-clip.wav")
        try:
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", str(a + min(20, (b - a) / 3)), "-t", "15",
                            "-i", side["raw"], "-ac", "1", clip], timeout=60, check=False)
            hit = self.ctx["identify"](clip) if os.path.exists(clip) else None
            alb = self.ctx["release"](hit.get("mbid", "")) if hit and hit.get("found") and hit.get("mbid") else None
            if hit and hit.get("found"):
                self.album = {"artist": (alb or {}).get("artist") or hit.get("artist", ""),
                              "album": (alb or {}).get("album") or hit.get("album", ""),
                              "cover": (alb or {}).get("cover") or hit.get("cover", ""),
                              "rid": (alb or {}).get("rid", ""), "year": "", "tracks": (alb or {}).get("tracks") or []}
                self.msg = f"Gjenkjent: {self.album['artist']} – {self.album['album']}"
            else:
                self.msg = "Fant ikke platen – skriv inn artist og album selv"
        except Exception as e:
            self.msg = f"Gjenkjenning feilet: {e}"
        finally:
            try:
                os.unlink(clip)
            except OSError:
                pass
        self._fit()
        self.ctx["on_change"]()

    def _fit(self):
        """Bruk MusicBrainz-varighetene til å rette opp oppdelingen side for side."""
        tr = self.album.get("tracks") or []
        if not tr:
            return
        off = 0
        for s in self.sides:
            if not s.get("segs"):
                continue
            n = len(s["segs"])
            # anta at side A har de første sporene; finn hvor mange som passer i sidens lengde
            dur, k, acc = [], off, 0.0
            while k < len(tr) and (tr[k]["ms"] or 0) / 1000 + acc <= s["secs"] + 30:
                acc += (tr[k]["ms"] or 0) / 1000; dur.append((tr[k]["ms"] or 0) / 1000); k += 1
            if dur and all(dur) and abs(len(dur) - n) <= 3:
                s["segs"] = fit_tracklist(s["segs"], dur, s["levels"])
            off += len(s["segs"])

    def edit(self, change: dict) -> dict:
        for k in ("artist", "album", "year", "cover"):
            if k in change:
                self.album[k] = str(change[k]).strip()
        titles = {int(t["n"]): t for t in change.get("tracks") or [] if "n" in t}
        if titles:
            tl = self.album.setdefault("tracks", [])
            for n, t in titles.items():
                while len(tl) < n:
                    tl.append({"n": len(tl) + 1, "title": "", "ms": 0})
                if t.get("title"):
                    tl[n - 1]["title"] = str(t["title"]).strip()
        if "segs" in change and self.sides:   # manuell justering: {"segs": {"A": [[a,b],…]}}
            for s in self.sides:
                if s["name"] in change["segs"]:
                    s["segs"] = [tuple(map(float, x)) for x in change["segs"][s["name"]]]
        self.ctx["on_change"]()
        return self.status()

    # --- lagre
    def finish(self) -> dict:
        with self.lock:
            if self.state != "review":
                raise RuntimeError("ingen plate å lagre (stopp opptaket først)")
            self.state, self.progress = "saving", 0.0
        threading.Thread(target=self._save, daemon=True).start()
        return self.status()

    def _save(self):
        try:
            root, where = self.ctx["root"]()
            artist, album = self.album.get("artist") or "Ukjent artist", self.album.get("album") or time.strftime("Vinyl %Y-%m-%d")
            tracks = plan_tracks(self.album, self.sides)
            folder = os.path.join(root, safe(artist), safe(album))
            os.makedirs(folder, exist_ok=True)
            cover = ""
            if self.album.get("cover"):
                cover = os.path.join(folder, "cover.jpg")
                try:
                    url = self.album["cover"].replace("front-250", "front-500")
                    req = urllib.request.Request(url, headers={"User-Agent": "Skjold/1.0"})
                    with urllib.request.urlopen(req, timeout=15) as r, open(cover, "wb") as fh:
                        fh.write(r.read())
                except Exception:
                    cover = ""
            for i, t in enumerate(tracks):
                rel = track_relpath(artist, album, t["n"], t["title"])
                tags = {"ARTIST": artist, "ALBUMARTIST": artist, "ALBUM": album, "TITLE": t["title"],
                        "TRACKNUMBER": t["n"], "TRACKTOTAL": len(tracks), "DATE": self.album.get("year", ""),
                        "COMMENT": f"Vinyl, side {t['side']} – tatt opp med Skjold", "MUSICBRAINZ_ALBUMID": self.album.get("rid", "")}
                r = subprocess.run(ffmpeg_cut_cmd(t["raw"], os.path.join(root, rel), t["start"], t["end"], tags, cover),
                                   capture_output=True, text=True, timeout=600)
                if r.returncode != 0:
                    raise RuntimeError(r.stderr.strip()[:200] or "ffmpeg feilet")
                t["file"] = rel
                self.progress = (i + 1) / len(tracks)
                self.ctx["on_change"]()
            rec = {"id": self.id, "artist": artist, "album": album, "year": self.album.get("year", ""),
                   "cover": self.album.get("cover", ""), "where": where, "t": int(time.time()),
                   "tracks": [{k: t[k] for k in ("n", "side", "title", "start", "end", "file")} for t in tracks],
                   "secs": round(sum(t["end"] - t["start"] for t in tracks))}
            self.archive.add(rec)
            for s in self.sides:
                try:
                    os.unlink(s["raw"])
                except OSError:
                    pass
            self.reset()
            self.msg = f"Lagret {artist} – {album} ({len(tracks)} spor, {where})"
        except Exception as e:
            self.state, self.msg = "review", f"Lagring feilet: {e}"
        self.ctx["on_change"]()

    def cancel(self) -> dict:
        if self.proc:
            self.proc.kill()
        for s in self.sides:
            try:
                os.unlink(s["raw"])
            except OSError:
                pass
        self.reset()
        self.msg = "Avbrutt"
        self.ctx["on_change"]()
        return self.status()
