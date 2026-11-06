"""«Hva er dette?» – låtgjenkjenning av det som spiller, og ønskeliste (lokalt og i Navidrome).

Opptak (10–12 s): fra radiostrømmen med ffmpeg når URL-en er kjent, ellers fra ALSA-opptaksenheten (loopback).
Oppslag: AcoustID (Chromaprint via fpcalc + gratis API-nøkkel) med MusicBrainz-metadata, eller AudD (API-token),
som også kjenner radio/live-opptak. Omslag fra Cover Art Archive.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Skjold/1.0 (https://github.com/SebastianKristo/pult-forsterker)"}


def _get_json(url: str, timeout: float = 10.0, data: bytes | None = None, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------- opptak ----------
def record_cmd(out: str, seconds: int = 12, url: str = "", device: str = "") -> list[str]:
    if url:
        return ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-t", str(seconds), "-i", url, "-ac", "1", "-ar", "44100", out]
    return ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "alsa", "-t", str(seconds), "-i", device or "default",
            "-ac", "1", "-ar", "44100", out]


def record(seconds: int = 12, url: str = "", device: str = "") -> str:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg mangler (kjør pi/update.sh)")
    fd, out = tempfile.mkstemp(prefix="skjold-hva-", suffix=".wav"); os.close(fd)
    r = subprocess.run(record_cmd(out, seconds, url, device), capture_output=True, text=True, timeout=seconds + 20)
    if r.returncode != 0 or os.path.getsize(out) < 10000:
        raise RuntimeError("fikk ikke tatt opp lyd: " + (r.stderr.strip()[:200] or "ingen data"))
    return out


# ---------- AcoustID ----------
def fingerprint(path: str) -> tuple[int, str]:
    if not shutil.which("fpcalc"):
        raise RuntimeError("fpcalc mangler (pakken libchromaprint-tools, kjør pi/update.sh)")
    r = subprocess.run(["fpcalc", "-json", path], capture_output=True, text=True, timeout=30)
    d = json.loads(r.stdout or "{}")
    if not d.get("fingerprint"):
        raise RuntimeError("fikk ikke laget fingeravtrykk")
    return int(round(float(d.get("duration") or 0))), d["fingerprint"]


def parse_acoustid(d: dict) -> dict | None:
    """Beste treff fra et AcoustID-svar (meta=recordings+releasegroups) → {title, artist, album, mbid, rgid, score}."""
    best = None
    for res in d.get("results") or []:
        for rec in res.get("recordings") or []:
            if not rec.get("title"):
                continue
            arts = ", ".join(a.get("name", "") for a in rec.get("artists") or [] if a.get("name"))
            rg = (rec.get("releasegroups") or [{}])[0]
            cand = {"title": rec["title"], "artist": arts, "album": rg.get("title", ""), "mbid": rec.get("id", ""),
                    "rgid": rg.get("id", ""), "score": float(res.get("score") or 0), "via": "AcoustID"}
            if best is None or cand["score"] > best["score"]:
                best = cand
    return best


def acoustid_lookup(key: str, duration: int, fp: str) -> dict | None:
    q = urllib.parse.urlencode({"client": key, "meta": "recordings releasegroups compress", "duration": duration, "fingerprint": fp})
    d = _get_json("https://api.acoustid.org/v2/lookup", data=q.encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    if d.get("status") != "ok":
        raise RuntimeError("AcoustID: " + str((d.get("error") or {}).get("message") or d.get("status")))
    return parse_acoustid(d)


# ---------- AudD ----------
def parse_audd(d: dict) -> dict | None:
    if d.get("status") != "success":
        raise RuntimeError("AudD: " + str((d.get("error") or {}).get("error_message") or d.get("status")))
    r = d.get("result")
    if not r:
        return None
    mb = (r.get("musicbrainz") or [{}])
    mb0 = mb[0] if isinstance(mb, list) and mb else {}
    rgs = (mb0.get("releases") or [{}])
    art = ""
    if isinstance(r.get("spotify"), dict):
        imgs = ((r["spotify"].get("album") or {}).get("images") or [])
        art = imgs[0].get("url", "") if imgs else ""
    return {"title": r.get("title", ""), "artist": r.get("artist", ""), "album": r.get("album", ""), "mbid": mb0.get("id", ""),
            "rgid": ((rgs[0] or {}).get("release-group") or {}).get("id", "") if rgs else "", "score": 1.0, "via": "AudD", "art": art}


def audd_lookup(token: str, path: str) -> dict | None:
    boundary = "skjold" + secrets.token_hex(8)
    with open(path, "rb") as fh:
        audio = fh.read()
    parts = []
    for k, v in (("api_token", token), ("return", "musicbrainz,spotify")):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"klipp.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode() + audio + b"\r\n")
    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    d = _get_json("https://api.audd.io/", data=body, timeout=30, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return parse_audd(d)


def cover_url(hit: dict) -> str:
    if hit.get("art"):
        return hit["art"]
    if hit.get("rgid"):
        return f"https://coverartarchive.org/release-group/{hit['rgid']}/front-250"
    return ""


def recognize(cfg: dict, url: str = "", device: str = "", rec=record) -> dict:
    """cfg: {acoustid_key, audd_token, seconds}. Prøver AcoustID først (presist for innspilt musikk), så AudD."""
    if not cfg.get("acoustid_key") and not cfg.get("audd_token"):
        raise ValueError("legg inn en AcoustID-nøkkel eller et AudD-token under Plugins → Låtgjenkjenning")
    path = rec(int(cfg.get("seconds") or 12), url, device)
    try:
        hit, errs = None, []
        if cfg.get("acoustid_key"):
            try:
                dur, fp = fingerprint(path)
                hit = acoustid_lookup(cfg["acoustid_key"], dur, fp)
            except Exception as e:
                errs.append(str(e))
        if not hit and cfg.get("audd_token"):
            try:
                hit = audd_lookup(cfg["audd_token"], path)
            except Exception as e:
                errs.append(str(e))
        if not hit:
            return {"found": False, "error": "; ".join(errs) or "fant ingen treff", "t": time.time()}
        hit["cover"] = cover_url(hit)
        return {"found": True, **hit, "t": time.time()}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------- ønskeliste ----------
class Subsonic:
    """Liten Subsonic-klient for Navidrome: søk, stjerne og spillelisten «Ønskeliste»."""

    def __init__(self, url: str, user: str, password: str, opener=None):
        self.url, self.user, self.pw = url.rstrip("/"), user, password
        self.open = opener or (lambda u: _get_json(u))

    def _call(self, method: str, **params) -> dict:
        salt = secrets.token_hex(6)
        q = {"u": self.user, "t": hashlib.md5((self.pw + salt).encode()).hexdigest(), "s": salt, "v": "1.16.1", "c": "skjold", "f": "json"}
        q.update(params)
        d = self.open(f"{self.url}/rest/{method}.view?" + urllib.parse.urlencode(q, doseq=True))
        r = d.get("subsonic-response") or {}
        if r.get("status") != "ok":
            raise RuntimeError("Navidrome: " + str((r.get("error") or {}).get("message") or "feil"))
        return r

    def find_song(self, artist: str, title: str) -> str | None:
        r = self._call("search3", query=f"{artist} {title}".strip(), songCount=10, albumCount=0, artistCount=0)
        tl, al = title.lower(), artist.lower()
        for s in (r.get("searchResult3") or {}).get("song") or []:
            if s.get("title", "").lower() == tl and (not al or al.split(",")[0].strip() in s.get("artist", "").lower()):
                return s.get("id")
        return None

    def add_to_wishlist(self, song_id: str, name: str = "Ønskeliste") -> str:
        self._call("star", id=song_id)
        pls = (self._call("getPlaylists").get("playlists") or {}).get("playlist") or []
        pl = next((p for p in pls if p.get("name") == name), None)
        if pl:
            self._call("updatePlaylist", playlistId=pl["id"], songIdToAdd=song_id)
        else:
            self._call("createPlaylist", name=name, songId=song_id)
        return name


class Wishlist:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> list[dict]:
        try:
            with open(self.path) as fh:
                return json.load(fh)
        except Exception:
            return []

    def add(self, hit: dict, nd: Subsonic | None = None) -> dict:
        items = self.load()
        key = (hit.get("artist", "").lower(), hit.get("title", "").lower())
        if any((i.get("artist", "").lower(), i.get("title", "").lower()) == key for i in items):
            return {"added": False, "reason": "finnes allerede", "items": items}
        item = {k: hit.get(k, "") for k in ("title", "artist", "album", "cover", "mbid")}
        item["t"] = time.time(); item["navidrome"] = False
        note = ""
        if nd:
            try:
                sid = nd.find_song(item["artist"], item["title"])
                if sid:
                    nd.add_to_wishlist(sid)
                    item["navidrome"] = True
                else:
                    note = "finnes ikke i Navidrome-biblioteket – lagret bare i listen"
            except Exception as e:
                note = str(e)
        items.insert(0, item)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path + ".tmp", "w") as fh:
            json.dump(items[:500], fh, ensure_ascii=False)
        os.replace(self.path + ".tmp", self.path)
        return {"added": True, "note": note, "item": item, "items": items}

    def remove(self, idx: int) -> list[dict]:
        items = self.load()
        if 0 <= idx < len(items):
            items.pop(idx)
            with open(self.path, "w") as fh:
                json.dump(items, fh, ensure_ascii=False)
        return items


# ---------- vinyl- og kassettmodus (AUX/USB uten metadata) ----------
class TrackDetector:
    """Finner spor-skifte i en løpende lydstrøm: stille gap > gap_s, eller et kraftig og varig skift i energinivå.

    Mates med RMS per blokk (block_s sekunder). `feed()` returnerer «gap» når et stille gap avsluttes (nytt spor starter),
    «shift» ved energiskift, ellers None. Nivåene er relative (dBFS) så det tåler ulike innspillingsnivåer.
    """

    def __init__(self, block_s: float = 0.05, gap_s: float = 1.5, silence_db: float = -45.0, shift_db: float = 12.0):
        self.block_s, self.gap_s, self.silence_db, self.shift_db = block_s, gap_s, silence_db, shift_db
        self.quiet = 0.0
        self.long: float | None = None    # langsom middel (dB)
        self.short: float | None = None   # rask middel (dB)
        self.since = 0.0                  # tid siden siste hendelse
        self.playing = False

    @staticmethod
    def db(rms: float) -> float:
        import math
        return 20.0 * math.log10(max(rms, 1e-6))

    def feed(self, rms: float) -> str | None:
        d = self.db(rms)
        self.since += self.block_s
        if d < self.silence_db:
            self.quiet += self.block_s
            return None
        ev = None
        if self.quiet >= self.gap_s and self.playing:
            ev = "gap"
        elif self.quiet >= self.gap_s:
            ev = "start"
        self.quiet = 0.0
        self.playing = True
        a_s, a_l = 0.25, 0.01
        self.short = d if self.short is None else self.short + a_s * (d - self.short)
        self.long = d if self.long is None else self.long + a_l * (d - self.long)
        if ev is None and self.since > 20 and abs(self.short - self.long) > self.shift_db:
            ev = "shift"
            self.long = self.short
        if ev:
            self.since = 0.0
        return ev


def mb_release_tracks(mbid: str, opener=None) -> dict | None:
    """Album og sporliste for en MusicBrainz-innspilling (første offisielle utgivelse) → {album, artist, rid, tracks:[{n,title,ms}], pos}."""
    get = opener or (lambda u: _get_json(u, timeout=10))
    if not mbid:
        return None
    d = get(f"https://musicbrainz.org/ws/2/release?recording={mbid}&inc=recordings+artist-credits&fmt=json&limit=10")
    rels = d.get("releases") or []
    rels.sort(key=lambda r: (r.get("status") != "Official", (r.get("release-group") or {}).get("primary-type") != "Album"))
    for r in rels:
        tracks, pos = [], None
        for m in r.get("media") or []:
            for t in m.get("tracks") or []:
                tracks.append({"n": len(tracks) + 1, "title": t.get("title", ""), "ms": int(t.get("length") or 0),
                               "side": m.get("position", 1)})
                if (t.get("recording") or {}).get("id") == mbid:
                    pos = len(tracks)
        if tracks:
            art = ", ".join(a.get("name", "") for a in r.get("artist-credit") or [] if isinstance(a, dict))
            return {"album": r.get("title", ""), "artist": art, "rid": r.get("id", ""), "tracks": tracks, "pos": pos,
                    "cover": f"https://coverartarchive.org/release/{r.get('id')}/front-250" if r.get("id") else ""}
    return None


class VinylWatcher:
    """Lytter på AUX/USB-inngangen og gjenkjenner sporene automatisk.

    ctx: active_input() -> str, enabled_for(inp) -> bool, cfg() -> dict (acoustid_key/audd_token),
         device(inp) -> ALSA-enhet, set_meta(dict|None), log_track(dict).
    """
    RATE = 11025
    BLOCK = int(RATE * 0.05)

    def __init__(self, ctx: dict, lookup=None, release=mb_release_tracks):
        self.ctx, self.lookup, self.release = ctx, lookup, release
        self.meta: dict | None = None
        self.stop = False
        self.buf = bytearray()
        self.manual = False

    def _fingerprint_buf(self, pcm: bytes) -> dict | None:
        import wave as _w
        fd, path = tempfile.mkstemp(prefix="skjold-vinyl-", suffix=".wav"); os.close(fd)
        try:
            with _w.open(path, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(self.RATE); w.writeframes(pcm)
            cfg = self.ctx["cfg"]()
            return (self.lookup or (lambda c, p: recognize(c, rec=lambda *_a: p)))(cfg, path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def identify(self, pcm: bytes) -> dict | None:
        hit = self._fingerprint_buf(pcm)
        if not hit or not hit.get("found"):
            return None
        alb = None
        try:
            alb = self.release(hit.get("mbid", ""))
        except Exception:
            alb = None
        meta = {"title": hit.get("title", ""), "artist": hit.get("artist", ""), "album": (alb or {}).get("album") or hit.get("album", ""),
                "art": (alb or {}).get("cover") or hit.get("cover", ""), "tracks": (alb or {}).get("tracks") or [],
                "pos": (alb or {}).get("pos"), "via": hit.get("via", ""), "t": time.time()}
        return meta

    def run(self) -> None:
        """Hovedløkke (egen tråd): les PCM fra ALSA med ffmpeg mens AUX/USB er aktiv og modusen er på."""
        import math
        import struct
        while not self.stop:
            inp = self.ctx["active_input"]()
            if inp not in ("aux", "aux2", "usb") or not self.ctx["enabled_for"](inp):
                self.meta = None; self.ctx["set_meta"](None); time.sleep(3); continue
            cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "alsa", "-i", self.ctx["device"](inp),
                   "-ac", "1", "-ar", str(self.RATE), "-f", "s16le", "-"]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            except Exception:
                time.sleep(10); continue
            det, ring, next_try = TrackDetector(), bytearray(), time.time() + 12
            auto = not self.ctx["cfg"]().get("vinyl_manual")
            try:
                while not self.stop and self.ctx["active_input"]() == inp:
                    blk = proc.stdout.read(self.BLOCK * 2)
                    if not blk:
                        break
                    ring += blk
                    del ring[:-self.RATE * 2 * 15]   # siste 15 s
                    n = len(blk) // 2
                    s = struct.unpack(f"<{n}h", blk[:n * 2])
                    rms = math.sqrt(sum(x * x for x in s) / max(1, n)) / 32768.0
                    ev = det.feed(rms)
                    if ev in ("gap", "shift", "start"):
                        self.meta = None; self.ctx["set_meta"](None)
                        next_try = time.time() + 12   # gjenkjenn 12 s inn i det nye sporet
                    want = self.manual or (auto and time.time() >= next_try and det.playing and det.quiet == 0)
                    if want and len(ring) >= self.RATE * 2 * 10:
                        self.manual = False
                        meta = self.identify(bytes(ring[-self.RATE * 2 * 12:]))
                        if meta and (not self.meta or (meta["title"], meta["artist"]) != (self.meta["title"], self.meta["artist"])):
                            self.meta = meta; self.ctx["set_meta"](meta)
                            self.ctx["log_track"]({"title": meta["title"], "artist": meta["artist"], "album": meta["album"], "source": "Vinyl/AUX"})
                        next_try = time.time() + (10**9 if meta else 30)   # treff: vent på neste spor; ellers prøv igjen om 30 s
            finally:
                proc.kill()
