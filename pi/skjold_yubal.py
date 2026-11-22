"""yubal: last ned musikk du ikke har, rett inn i Navidrome-biblioteket.

yubal (github.com/guillevc/yubal) laster ned fra YouTube Music med tagger og cover og legger det i musikkmappa
Navidrome leser. yubal har ikke søk – den tar en lenke – så Skjold finner lenken selv (ytmusicapi, uten innlogging)
og viser den aldri som et YouTube Music-treff. Når jobben er ferdig, ber Skjold Navidrome skanne biblioteket.

  GET  /api/yubal/status            {"konfigurert","ok","feil","auto","album"}
  POST /api/yubal/hent {"q"} | {"url"}   start nedlasting → {"id","tittel","artist","bilde","url"}
  GET  /api/yubal/jobber            Skjolds nedlastinger med status og fremdrift (0–100), nyeste først
  GET  /api/yubal/kandidater?q=     de beste låtene for søket, med «sikker» når én passer helt (artist og tittel)
  POST /api/yubal/hent {"vid","album_id","tittel","artist","bilde"}   last ned akkurat den låten (valgt av deg)
yubal-API: POST /api/jobs {"url"} → {"id"}; GET /api/jobs → {"jobs":[{id,status,progress,…}]}; GET /api/health.
Status: pending, fetching_info, downloading, importing, completed, failed, cancelled.
"""
import json
import re
import threading
import unicodedata
import time
import urllib.parse
import urllib.request

FERDIG = ("completed", "failed", "cancelled")


def _http(url, data=None, timeout=10):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"},
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def _thumb(o):
    th = o.get("thumbnails") or []
    return str(th[-1].get("url") or "") if th else ""


def _ord(t):
    """Ord for sammenligning: små bokstaver, uten tegnsetting og «feat.», «remastered» o.l."""
    t = unicodedata.normalize("NFKC", str(t or "")).lower()
    t = re.sub(r"\((?:feat|ft|with|remaster|remastered|live|radio edit)[^)]*\)", " ", t)
    return [w for w in re.split(r"[^\wæøå]+", t) if w and w not in ("feat", "ft", "the", "og", "and", "-")]


def _poeng(q, tittel, artist):
    """Hvor godt en låt passer søket: andel av søkeordene som finnes i tittel+artist, og om både tittel og artist
    står i søket (da er vi sikre). 0–1."""
    qo, to, ao = _ord(q), _ord(tittel), _ord(artist)
    if not qo:
        return 0.0, False
    alle = set(to) | set(ao)
    treff = sum(1 for w in qo if w in alle) / len(qo)
    tittel_i_sok = bool(to) and all(w in qo for w in to)
    artist_i_sok = bool(ao) and any(w in qo for w in ao)
    return treff, treff >= 0.999 and tittel_i_sok and artist_i_sok


class Yubal:
    def __init__(self, settings, subsonic=None, http=None, ytm_client=None):
        self.settings, self.subsonic = settings, subsonic or (lambda: None)
        self.http = http or _http
        self._ytm = ytm_client   # for testene; ellers ytmusicapi.YTMusic() uten innlogging
        self.mine = {}           # jobb-id → {q, tittel, artist, bilde, url, t, skannet}
        self.lock = threading.Lock()

    def base(self):
        u = str(self.settings().get("yubalUrl") or "").strip().rstrip("/")
        if u and not u.startswith(("http://", "https://")):
            u = "http://" + u
        if u and not urllib.parse.urlparse(u).port and u.count(":") < 2:
            u += ":8000"
        return u

    def status(self):
        s, b = self.settings(), self.base()
        out = {"konfigurert": bool(b), "ok": False, "feil": "", "auto": s.get("yubalAuto", True) is not False, "album": bool(s.get("yubalAlbum"))}
        if not b:
            return out
        try:
            self.http(b + "/api/health", timeout=4)
            out["ok"] = True
        except Exception as e:
            out["feil"] = f"yubal svarer ikke på {b} ({e})"
        return out

    def _client(self):
        if self._ytm is None:
            from ytmusicapi import YTMusic   # søket trenger ingen innlogging
            self._ytm = YTMusic()
        return self._ytm

    def finn(self, q):
        """Tekst → YouTube Music-lenke (låten, eller albumet den er på når «Hele albumet» er på)."""
        yt = self._client()
        treff = [x for x in yt.search(q, filter="songs", limit=5) or [] if x.get("videoId")]
        if not treff:
            raise LookupError(f"fant ikke «{q}»")
        t = treff[0]
        artist = ", ".join(a.get("name", "") for a in t.get("artists") or [] if isinstance(a, dict))
        alb = t.get("album") if isinstance(t.get("album"), dict) else {}
        info = {"tittel": str(t.get("title") or q), "artist": artist, "album": str(alb.get("name") or ""), "bilde": _thumb(t)}
        if self.settings().get("yubalAlbum") and alb.get("id"):
            try:
                a = yt.get_album(alb["id"]) or {}
                if a.get("audioPlaylistId"):
                    return {**info, "tittel": str(a.get("title") or info["album"]), "url": "https://music.youtube.com/playlist?list=" + a["audioPlaylistId"]}
            except Exception:
                pass
        return {**info, "url": "https://music.youtube.com/watch?v=" + t["videoId"]}

    def kandidater(self, q):
        """De beste låtene for søket (til å velge fra). «sikker» = én låt der både tittel og artist står i søket."""
        yt = self._client()
        ut = []
        for x in yt.search(q, filter="songs", limit=8) or []:
            if not x.get("videoId"):
                continue
            artist = ", ".join(a.get("name", "") for a in x.get("artists") or [] if isinstance(a, dict))
            alb = x.get("album") if isinstance(x.get("album"), dict) else {}
            p, sikker = _poeng(q, x.get("title"), artist)
            ut.append({"vid": x["videoId"], "tittel": str(x.get("title") or ""), "artist": artist, "album": str(alb.get("name") or ""),
                       "album_id": str(alb.get("id") or ""), "varighet": str(x.get("duration") or ""), "bilde": _thumb(x), "poeng": round(p, 2), "sikker": sikker})
        ut.sort(key=lambda k: (-k["sikker"], -k["poeng"]))
        sikre = [k for k in ut if k["sikker"]]
        # sikker: både tittel og artist står i søket – da er det låten du mente (flere versjoner av samme låt: den øverste)
        return {"kandidater": ut[:6], "sikker": sikre[0] if sikre else None}

    def url_for(self, vid, album_id=""):
        """Lenke til låten, eller albumet den er på når «Hele albumet» er på."""
        if self.settings().get("yubalAlbum") and album_id:
            try:
                a = self._client().get_album(album_id) or {}
                if a.get("audioPlaylistId"):
                    return "https://music.youtube.com/playlist?list=" + a["audioPlaylistId"], str(a.get("title") or "")
            except Exception:
                pass
        return "https://music.youtube.com/watch?v=" + vid, ""

    def hent(self, q="", url="", valgt=None):
        b = self.base()
        if not b:
            raise RuntimeError("yubal er ikke satt opp (Integrasjoner → yubal)")
        if valgt:   # en låt du har valgt fra kandidatene
            u, albumtittel = self.url_for(valgt["vid"], valgt.get("album_id", ""))
            info = {"tittel": albumtittel or valgt.get("tittel", ""), "artist": valgt.get("artist", ""), "album": valgt.get("album", ""),
                    "bilde": valgt.get("bilde", ""), "url": u}
        elif url:
            info = {"tittel": "", "artist": "", "album": "", "bilde": "", "url": url}
        else:
            info = self.finn(q)
        r = self.http(b + "/api/jobs", {"url": info["url"]}, timeout=15)
        jid = str(r.get("id") or "")
        if not jid:
            raise RuntimeError("yubal ga ingen jobb-id")
        with self.lock:
            self.mine[jid] = {**info, "q": q, "t": time.time(), "skannet": False}
            while len(self.mine) > 40:
                self.mine.pop(min(self.mine, key=lambda k: self.mine[k]["t"]))
        return {"id": jid, **info}

    def jobber(self):
        b = self.base()
        if not b or not self.mine:
            return []
        alle = {str(j.get("id")): j for j in (self.http(b + "/api/jobs", timeout=6).get("jobs") or [])}
        ut = []
        with self.lock:
            for jid, m in self.mine.items():
                j = alle.get(jid) or {}
                st = str(j.get("status") or "ukjent")
                p = float(j.get("progress") or 0)
                p = p * 100 if p <= 1 and st not in ("pending",) else p
                ci = j.get("content_info") or {}
                if st == "completed" and not m["skannet"]:   # ferdig: la Navidrome finne de nye filene
                    m["skannet"] = True
                    nd = self.subsonic()
                    if nd:
                        try:
                            nd._call("startScan")
                        except Exception:
                            pass
                ut.append({"id": jid, "status": st, "fremdrift": 100 if st == "completed" else round(min(99, max(0, p))),
                           "tittel": m["tittel"] or ci.get("title") or "", "artist": m["artist"] or ci.get("artist") or "",
                           "bilde": m["bilde"] or ci.get("thumbnail_url") or "", "q": m["q"], "t": m["t"]})
        return sorted(ut, key=lambda x: -x["t"])


def routes(yb):
    import asyncio
    from aiohttp import web

    async def run(fn, *a):
        return await asyncio.get_running_loop().run_in_executor(None, fn, *a)

    async def h_status(_r):
        return web.json_response(await run(yb.status))

    async def h_hent(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        q, url = str(b.get("q") or "").strip()[:200], str(b.get("url") or "").strip()
        vid = str(b.get("vid") or "").strip()
        valgt = None
        if vid:
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                return web.json_response({"error": "ugyldig vid"}, status=400)
            valgt = {"vid": vid, "album_id": str(b.get("album_id") or "")[:64], "tittel": str(b.get("tittel") or "")[:200],
                     "artist": str(b.get("artist") or "")[:200], "album": str(b.get("album") or "")[:200], "bilde": str(b.get("bilde") or "")[:500]}
        if not q and not url and not valgt:
            return web.json_response({"error": "q, url eller vid mangler"}, status=400)
        if url and not url.startswith(("https://music.youtube.com/", "https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
            return web.json_response({"error": "bare YouTube- og YouTube Music-lenker"}, status=400)
        try:
            return web.json_response(await run(yb.hent, q, url, valgt))
        except LookupError as e:
            return web.json_response({"error": str(e)}, status=404)
        except ImportError:
            return web.json_response({"error": "ytmusicapi mangler – kjør pi/update.sh"}, status=503)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)

    async def h_kandidater(r):
        q = (r.query.get("q") or "").strip()[:200]
        if len(q) < 2:
            return web.json_response({"kandidater": [], "sikker": None})
        try:
            return web.json_response(await run(yb.kandidater, q))
        except ImportError:
            return web.json_response({"error": "ytmusicapi mangler – kjør pi/update.sh"}, status=503)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)

    async def h_jobber(_r):
        try:
            return web.json_response({"jobber": await run(yb.jobber)})
        except Exception as e:
            return web.json_response({"jobber": [], "error": str(e)})

    return [web.get("/api/yubal/status", h_status), web.post("/api/yubal/hent", h_hent), web.get("/api/yubal/jobber", h_jobber), web.get("/api/yubal/kandidater", h_kandidater)]
