"""Populært: låter og album folk hører på akkurat nå, og de største fra hvert tiår – til Navidrome-forsiden.

Kilder (åpne, uten nøkkel):
  akkurat nå   Apple Musics «mest spilt»-lister for landet (rss.marketingtools.apple.com), Deezer-listene som reserve
  tiår         Deezers redaksjonelle hitlister («80s Hits» o.l.), YouTube Music-spillelister som reserve

  GET /api/populaert?periode=na|60|70|80|90|00|10   {"periode","kilde","sanger":[…],"album":[…]}
Låtene har tittel, artist, album, bilde og år. Appen sjekker selv hva som finnes i Navidrome og tilbyr yubal for resten.
"""
import json
import threading
import time
import urllib.parse
import urllib.request

PERIODER = {"na": "Akkurat nå", "10": "2010-tallet", "00": "2000-tallet", "90": "90-tallet", "80": "80-tallet", "70": "70-tallet", "60": "60-tallet"}
SOK = {"10": ["2010s Hits", "Best of 2010s"], "00": ["2000s Hits", "Best of 2000s"], "90": ["90s Hits", "Best of 90s"],
       "80": ["80s Hits", "Best of 80s"], "70": ["70s Hits", "Best of 70s"], "60": ["60s Hits", "Best of 60s"]}
TTL = 6 * 3600


def _hent(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Skjold/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def _apple_bilde(u, px=400):
    return str(u or "").replace("100x100bb", f"{px}x{px}bb")


def _unik(liste, nokkel):
    sett, ut = set(), []
    for x in liste:
        k = nokkel(x)
        if k and k not in sett:
            sett.add(k)
            ut.append(x)
    return ut


class Populaert:
    def __init__(self, settings=None, http=None, ytm_client=None):
        self.settings = settings or (lambda: {})
        self.http = http or _hent
        self._ytm = ytm_client
        self.cache = {}
        self.lock = threading.Lock()

    def land(self):
        cc = str(self.settings().get("country") or self.settings().get("land") or "no").lower()
        return cc if len(cc) == 2 and cc.isalpha() else "no"

    # ---- akkurat nå ----
    def _apple(self):
        cc = self.land()
        base = f"https://rss.marketingtools.apple.com/api/v2/{cc}/music/most-played"
        s = self.http(base + "/50/songs.json").get("feed", {}).get("results") or []
        a = self.http(base + "/25/albums.json").get("feed", {}).get("results") or []
        sanger = [{"tittel": str(x.get("name") or ""), "artist": str(x.get("artistName") or ""), "album": "",
                   "bilde": _apple_bilde(x.get("artworkUrl100")), "aar": str(x.get("releaseDate") or "")[:4]} for x in s]
        album = [{"tittel": str(x.get("name") or ""), "artist": str(x.get("artistName") or ""),
                  "bilde": _apple_bilde(x.get("artworkUrl100")), "aar": str(x.get("releaseDate") or "")[:4]} for x in a]
        return sanger, album, "Apple Music"

    def _deezer_chart(self):
        s = self.http("https://api.deezer.com/chart/0/tracks?limit=50").get("data") or []
        a = self.http("https://api.deezer.com/chart/0/albums?limit=25").get("data") or []
        return [self._dz_spor(x) for x in s], [{"tittel": str(x.get("title") or ""), "artist": str((x.get("artist") or {}).get("name") or ""),
                                                "bilde": str(x.get("cover_xl") or x.get("cover_big") or ""), "aar": ""} for x in a], "Deezer"

    @staticmethod
    def _dz_spor(x):
        al = x.get("album") or {}
        return {"tittel": str(x.get("title_short") or x.get("title") or ""), "artist": str((x.get("artist") or {}).get("name") or ""),
                "album": str(al.get("title") or ""), "bilde": str(al.get("cover_xl") or al.get("cover_big") or ""), "aar": "",
                "_album_id": al.get("id")}

    # ---- tiår ----
    def _deezer_tiar(self, p):
        for q in SOK[p]:
            pls = self.http("https://api.deezer.com/search/playlist?limit=10&q=" + urllib.parse.quote(q)).get("data") or []
            pls = [x for x in pls if int(x.get("nb_tracks") or 0) >= 20]
            if not pls:
                continue
            red = [x for x in pls if str((x.get("user") or {}).get("name") or "").lower().startswith("deezer")]
            pl = (red or pls)[0]
            spor = self.http(f"https://api.deezer.com/playlist/{int(pl['id'])}/tracks?limit=80").get("data") or []
            sanger = [self._dz_spor(x) for x in spor if x.get("title")]
            if sanger:
                return sanger, "Deezer · " + str(pl.get("title") or q)
        raise LookupError("fant ingen hitliste")

    def _ytm_tiar(self, p):
        if self._ytm is None:
            from ytmusicapi import YTMusic
            self._ytm = YTMusic()
        yt = self._ytm
        for q in SOK[p]:
            for pl in yt.search(q, filter="playlists", limit=5) or []:
                pid = str(pl.get("browseId") or "").removeprefix("VL")
                if not pid:
                    continue
                d = yt.get_playlist(pid, limit=80) or {}
                sanger = []
                for x in d.get("tracks") or []:
                    alb = x.get("album") if isinstance(x.get("album"), dict) else {}
                    th = x.get("thumbnails") or []
                    sanger.append({"tittel": str(x.get("title") or ""), "artist": ", ".join(a.get("name", "") for a in x.get("artists") or [] if isinstance(a, dict)),
                                   "album": str(alb.get("name") or ""), "bilde": str(th[-1].get("url") or "") if th else "", "aar": "", "_album_id": alb.get("id")})
                if len(sanger) >= 20:
                    return sanger, "YouTube Music · " + str(pl.get("title") or q)
        raise LookupError("fant ingen hitliste")

    @staticmethod
    def _album_fra(sanger):
        """Albumene som går igjen i hitlista (flest låter først), uten singler med samme navn som låten."""
        tell = {}
        for i, x in enumerate(sanger):
            if not x.get("album") or x["album"].casefold() == x["tittel"].casefold():
                continue
            k = (x["album"].casefold(), x["artist"].casefold())
            t = tell.setdefault(k, {"tittel": x["album"], "artist": x["artist"], "bilde": x["bilde"], "aar": x.get("aar", ""), "n": 0, "forst": i})
            t["n"] += 1
        return [{k: v for k, v in a.items() if k not in ("n", "forst")} for a in sorted(tell.values(), key=lambda a: (-a["n"], a["forst"]))][:25]

    def hent(self, periode="na"):
        if periode not in PERIODER:
            raise ValueError("ukjent periode")
        with self.lock:
            hit = self.cache.get(periode)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
        feil = []
        sanger, album, kilde = [], [], ""
        if periode == "na":
            for f in (self._apple, self._deezer_chart):
                try:
                    sanger, album, kilde = f()
                    if sanger:
                        break
                except Exception as e:
                    feil.append(repr(e))
        else:
            for f in (self._deezer_tiar, self._ytm_tiar):
                try:
                    sanger, kilde = f(periode)
                    album = self._album_fra(sanger)
                    if sanger:
                        break
                except Exception as e:
                    feil.append(repr(e))
        if not sanger:
            if hit:
                return hit[1]
            raise RuntimeError("fant ingen lister (" + "; ".join(feil) + ")")
        sanger = _unik([{k: v for k, v in x.items() if not k.startswith("_")} for x in sanger],
                       lambda x: (x["tittel"].casefold(), x["artist"].casefold()))[:50]
        album = _unik(album, lambda x: (x["tittel"].casefold(), x["artist"].casefold()))[:25]
        out = {"periode": periode, "navn": PERIODER[periode], "kilde": kilde, "sanger": sanger, "album": album}
        with self.lock:
            self.cache[periode] = (time.time(), out)
        return out


def routes(pop):
    import asyncio
    from aiohttp import web

    async def h(r):
        p = (r.query.get("periode") or "na").strip()
        try:
            return web.json_response(await asyncio.get_running_loop().run_in_executor(None, pop.hent, p))
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)

    async def h_perioder(_r):
        return web.json_response({"perioder": [{"id": k, "navn": v} for k, v in PERIODER.items()]})

    return [web.get("/api/populaert", h), web.get("/api/populaert/perioder", h_perioder)]
