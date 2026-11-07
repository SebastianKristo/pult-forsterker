"""Sanglek: Skjold spiller 10 sekunder av en tilfeldig låt, spillerne gjetter artist og tittel.

Låtene hentes fra Navidrome (tilfeldige, en spilleliste eller et tiår). Spillerne svarer fra mobilen
(web-appen, #sanglek – QR-kode vises på Touch/web), eller man bruker bare «Vis svar» og teller poeng selv.

POST /api/quiz {action: "start", kilde: "tilfeldig"|"spilleliste"|"tiår", id?, tiår?, runder?: 10, sekunder?: 10}
POST /api/quiz {action: "spill"}        spill neste klipp (eller samme på nytt med {igjen: true})
POST /api/quiz {action: "vis"}          vis svaret (cover, artist, tittel) og del ut poeng
POST /api/quiz {action: "bli_med", navn} → {spiller}
POST /api/quiz {action: "svar", spiller, svar}
POST /api/quiz {action: "slutt"}
GET  /api/quiz → {aktiv, runde, runder, fase, spillere: [{navn, poeng, svart}], svar?: {artist, tittel, album, cover}}

Poeng: 1 for riktig artist, 1 for riktig tittel (tåler små skrivefeil, «feat.», parenteser og store/små bokstaver).
"""
import difflib
import random
import re
import threading
import time
import unicodedata


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = re.sub(r"\b(feat|ft|featuring)\b.*", " ", s)
    s = s.replace("&", " and ").replace("λ", " ")
    s = re.sub(r"\b(the|a|an)\b", " ", s)
    return re.sub(r"[^a-z0-9æøå]+", " ", s).strip()


def treff(gjett: str, fasit: str) -> bool:
    g, f = norm(gjett), norm(fasit)
    if not g or not f:
        return False
    if g == f or (len(g) >= 4 and (g in f or f in g)):
        return True
    return difflib.SequenceMatcher(None, g, f).ratio() >= 0.8


def poeng(svar: str, artist: str, tittel: str) -> int:
    """Ett svar kan inneholde både artist og tittel, f.eks. «Linkin Park – Numb» eller «numb linkin park»."""
    s = str(svar or "")
    p = 0
    deler = [x for x in re.split(r"\s+[-–—/|]\s+|,", s) if x.strip()] or [s]
    if treff(s, artist) or any(treff(d, artist) for d in deler) or (norm(artist) and norm(artist) in norm(s)):
        p += 1
    if treff(s, tittel) or any(treff(d, tittel) for d in deler) or (len(norm(tittel)) >= 3 and norm(tittel) in norm(s)):
        p += 1
    return p


class Quiz:
    def __init__(self, ctx, rng=None):
        """ctx: songs(kilde, id, tiår, n) → [{title, artist, album, cover, url, duration}], play(url, title, cover, start_s),
        pause()."""
        self.ctx = ctx
        self.rng = rng or random.Random()
        self.lock = threading.Lock()
        self._timer = None
        self.reset()

    def reset(self):
        self.aktiv, self.runde, self.fase = False, 0, "klar"
        self.songs, self.spillere, self.svar = [], {}, {}
        self.sekunder, self.kilde = 10, "tilfeldig"

    def state(self):
        cur = self.songs[self.runde - 1] if 0 < self.runde <= len(self.songs) else None
        out = {"aktiv": self.aktiv, "runde": self.runde, "runder": len(self.songs), "fase": self.fase,
               "sekunder": self.sekunder, "kilde": self.kilde,
               "spillere": sorted(({"navn": n, "poeng": v["poeng"], "svart": n in self.svar} for n, v in self.spillere.items()),
                                  key=lambda x: -x["poeng"])}
        if cur and self.fase == "vist":
            out["svar"] = {k: cur.get(k, "") for k in ("artist", "title", "album", "cover")}
            out["svar"]["tittel"] = cur.get("title", "")
            out["fasit"] = {n: s for n, s in self.svar.items()}
        return out

    def handle(self, b):
        a = b.get("action")
        with self.lock:
            if a == "start":
                n = max(1, min(50, int(b.get("runder") or 10)))
                songs = [s for s in self.ctx["songs"](b.get("kilde") or "tilfeldig", b.get("id"), b.get("tiår"), n * 2) if s.get("url")]
                if not songs:
                    raise ValueError("fant ingen låter – sjekk at Navidrome er satt opp")
                self.rng.shuffle(songs)
                keep = self.spillere
                self.reset()
                self.spillere = {k: {"poeng": 0} for k in keep}
                self.aktiv, self.songs = True, songs[:n]
                self.sekunder = max(5, min(30, int(b.get("sekunder") or 10)))
                self.kilde = b.get("kilde") or "tilfeldig"
                return self.state()
            if not self.aktiv and a not in ("bli_med",):
                raise ValueError("ingen sanglek i gang")
            if a == "spill":
                if not b.get("igjen") or self.runde == 0:
                    if self.runde >= len(self.songs):
                        self.fase = "ferdig"
                        return self.state()
                    self.runde += 1
                    self.svar = {}
                s = self.songs[self.runde - 1]
                dur = float(s.get("duration") or 0)
                start = round(min(max(20.0, dur * 0.3), max(0.0, dur - self.sekunder - 5)), 1) if dur > self.sekunder + 25 else 0.0
                self.ctx["play"](s["url"], "Sanglek – runde %d" % self.runde, "", start)
                self.fase = "spiller"
                if self._timer:
                    self._timer.cancel()
                self._timer = threading.Timer(self.sekunder, self._stopp_klipp)
                self._timer.daemon = True
                self._timer.start()
                return self.state()
            if a == "vis":
                s = self.songs[self.runde - 1] if self.runde else None
                if s and self.fase != "vist":
                    for navn, svar in self.svar.items():
                        self.spillere.setdefault(navn, {"poeng": 0})["poeng"] += poeng(svar, s.get("artist", ""), s.get("title", ""))
                self.fase = "vist"
                return self.state()
            if a == "bli_med":
                navn = re.sub(r"\s+", " ", str(b.get("navn") or "")).strip()[:24]
                if not navn:
                    raise ValueError("skriv et navn")
                self.spillere.setdefault(navn, {"poeng": 0})
                return {"spiller": navn, **self.state()}
            if a == "svar":
                navn = str(b.get("spiller") or "")
                if navn not in self.spillere:
                    raise ValueError("bli med først")
                if self.fase == "vist":
                    raise ValueError("svaret er allerede vist")
                self.svar[navn] = str(b.get("svar") or "")[:120]
                return self.state()
            if a == "slutt":
                if self._timer:
                    self._timer.cancel()
                self.aktiv, self.fase = False, "ferdig"
                return self.state()
        raise ValueError("ukjent handling")

    def _stopp_klipp(self):
        try:
            self.ctx["pause"]()
        except Exception:
            pass
        with self.lock:
            if self.fase == "spiller":
                self.fase = "gjett"


def subsonic_songs(call, stream_url, cover_url, kilde="tilfeldig", ident=None, tiar=None, n=20):
    """Hent låter fra Navidrome. call(metode, **param) → Subsonic-svar (dict), stream_url(id), cover_url(coverArt-id)."""
    if kilde == "spilleliste" and ident:
        r = call("getPlaylist", id=ident).get("playlist", {}).get("entry", [])
    elif kilde == "tiår" and tiar:
        y = int(tiar)
        r = call("getRandomSongs", size=n, fromYear=y, toYear=y + 9).get("randomSongs", {}).get("song", [])
    else:
        r = call("getRandomSongs", size=n).get("randomSongs", {}).get("song", [])
    return [{"title": s.get("title", ""), "artist": s.get("artist", ""), "album": s.get("album", ""),
             "cover": cover_url(s["coverArt"]) if s.get("coverArt") else "", "duration": s.get("duration", 0),
             "url": stream_url(s["id"])} for s in r if s.get("id")]


del time
