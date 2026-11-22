"""yubal: last ned musikk du ikke har, rett inn i Navidrome-biblioteket.

yubal (github.com/guillevc/yubal) laster ned fra YouTube Music med tagger og cover og legger det i musikkmappa
Navidrome leser. yubal har ikke søk – den tar en lenke – så Skjold finner lenken selv (ytmusicapi, uten innlogging)
og viser den aldri som et YouTube Music-treff. Når jobben er ferdig, ber Skjold Navidrome skanne biblioteket.

  GET  /api/yubal/status            {"konfigurert","ok","feil","auto","album"}
  POST /api/yubal/hent {"q"} | {"url"}   start nedlasting → {"id","tittel","artist","bilde","url"}
  GET  /api/yubal/jobber            Skjolds nedlastinger med status og fremdrift (0–100), nyeste først
yubal-API: POST /api/jobs {"url"} → {"id"}; GET /api/jobs → {"jobs":[{id,status,progress,…}]}; GET /api/health.
Status: pending, fetching_info, downloading, importing, completed, failed, cancelled.
"""
import json
import threading
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

    def hent(self, q="", url=""):
        b = self.base()
        if not b:
            raise RuntimeError("yubal er ikke satt opp (Integrasjoner → yubal)")
        info = {"tittel": "", "artist": "", "album": "", "bilde": "", "url": url} if url else self.finn(q)
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
        if not q and not url:
            return web.json_response({"error": "q eller url mangler"}, status=400)
        if url and not url.startswith(("https://music.youtube.com/", "https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
            return web.json_response({"error": "bare YouTube- og YouTube Music-lenker"}, status=400)
        try:
            return web.json_response(await run(yb.hent, q, url))
        except LookupError as e:
            return web.json_response({"error": str(e)}, status=404)
        except ImportError:
            return web.json_response({"error": "ytmusicapi mangler – kjør pi/update.sh"}, status=503)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)

    async def h_jobber(_r):
        try:
            return web.json_response({"jobber": await run(yb.jobber)})
        except Exception as e:
            return web.json_response({"jobber": [], "error": str(e)})

    return [web.get("/api/yubal/status", h_status), web.post("/api/yubal/hent", h_hent), web.get("/api/yubal/jobber", h_jobber)]
