"""Fotoskjermsparer for Skjold Touch: store bilder som bytter sakte, med fotograf og kilde i hjørnet.

Kilder (velges i Touch → Skjermsparer → Foto):
- «dagens»:   Dagens bilde fra Wikimedia Commons (Wikipedia sin «featured»-strøm, fritt lisensiert) og NASA sitt
              astronomibilde (APOD), de siste 14 dagene. Ingen nøkkel.
- «unsplash»: kuraterte fotografier fra Unsplash (krever en gratis tilgangsnøkkel, «Access Key», fra
              unsplash.com/developers; den skrives inn på Touch og lagres bare på enheten). Bildene vises fra Unsplash
              sine egne adresser, med fotografens navn – slik Unsplash sine retningslinjer krever.

Enheten henter listene (nøkkelen forlater aldri enheten) og mellomlagrer dem: Unsplash i 2 timer (30 bilder per
henting, godt under grensen på 50 forespørsler i timen), dagens bilde i 6 timer.

Parserne er rene funksjoner og testes uten nett (pi/tests/test_foto.py).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import threading
import time
import urllib.parse
import urllib.request

UA = "Skjold/1.0 (skjold-lab.com; fotoskjermsparer)"
BREDDE = 1920


def _tekst(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(html or ""))).strip()


def parse_unsplash(js) -> list:
    """GET /photos/random?count=… → [{url, title, credit, link, source}]."""
    out = []
    for p in js if isinstance(js, list) else []:
        raw = ((p.get("urls") or {}).get("raw") or "")
        if not raw:
            continue
        u = p.get("user") or {}
        sep = "&" if "?" in raw else "?"
        link = ((u.get("links") or {}).get("html") or "https://unsplash.com")
        out.append({"url": f"{raw}{sep}w={BREDDE}&q=80&fm=jpg&fit=max", "title": _tekst(p.get("description") or p.get("alt_description") or ""),
                    "credit": (u.get("name") or "Ukjent") + " · Unsplash", "sted": ((p.get("location") or {}).get("name") or ""),
                    "link": link + "?utm_source=skjold&utm_medium=referral", "source": "unsplash", "farge": p.get("color") or ""})
    return out


def wiki_skalert(src: str, bredde: int = BREDDE) -> str:
    """Wikimedia-miniatyr («…/thumb/a/ab/Fil.jpg/640px-Fil.jpg») → samme bilde i ønsket bredde."""
    return re.sub(r"/(\d+)px-", f"/{bredde}px-", src, count=1) if "/thumb/" in src else src


def parse_wikimedia(js) -> dict | None:
    """Wikipedia featured-strømmen (api.wikimedia.org/feed/v1/wikipedia/en/featured/Å/M/D) → dagens bilde."""
    im = (js or {}).get("image") if isinstance(js, dict) else None
    if not isinstance(im, dict):
        return None
    full = im.get("image") or {}
    thumb = (im.get("thumbnail") or {}).get("source") or ""
    url = wiki_skalert(thumb) if thumb else full.get("source") or ""
    if not url or not re.search(r"\.(jpe?g|png|webp)($|\?)", url, re.I):
        return None
    w, h = int(full.get("width") or 0), int(full.get("height") or 0)
    if w and w < BREDDE and full.get("source"):
        url = full["source"]                       # mindre enn ønsket bredde: bruk originalen
    artist = _tekst((im.get("artist") or {}).get("text") or "") or "Wikimedia Commons"
    lisens = ((im.get("license") or {}).get("type") or "")
    return {"url": url, "title": _tekst((im.get("description") or {}).get("text") or "")[:160],
            "credit": artist[:80] + (" · " + lisens if lisens else "") + " · Wikimedia Commons",
            "link": im.get("file_page") or "https://commons.wikimedia.org", "source": "wikimedia", "liggende": not (w and h) or w >= h}


def parse_apod(js) -> list:
    """NASA APOD (api.nasa.gov/planetary/apod?start_date=…) → bildene (videoer hoppes over)."""
    out = []
    for p in js if isinstance(js, list) else [js] if isinstance(js, dict) else []:
        if p.get("media_type") != "image" or not p.get("url"):
            continue
        out.append({"url": p["url"], "title": _tekst(p.get("title") or "")[:160],
                    "credit": (_tekst(p.get("copyright") or "") or "NASA") + " · NASA APOD", "link": "https://apod.nasa.gov/apod/",
                    "source": "apod"})
    return out


def _hent(url: str, headers: dict | None = None, timeout: float = 12.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


class Foto:
    def __init__(self, cfg, hent=_hent, klokke=time.time):
        """cfg() → {"foto_kilder": "dagens|unsplash|begge", "unsplash_key": "...", "unsplash_tema": "nature"}"""
        self.cfg, self.hent, self.klokke = cfg, hent, klokke
        self.cache = {"unsplash": (0.0, "", []), "dagens": (0.0, "", [])}
        self.feil = {"unsplash": "", "dagens": ""}
        self.lock = threading.Lock()

    def _unsplash(self, key: str, tema: str) -> list:
        q = urllib.parse.urlencode({"count": 30, "orientation": "landscape", "content_filter": "high", **({"query": tema} if tema else {})})
        return parse_unsplash(self.hent("https://api.unsplash.com/photos/random?" + q, {"Authorization": "Client-ID " + key, "Accept-Version": "v1"}))

    def _dagens(self) -> list:
        bilder, idag = [], _dt.date.fromtimestamp(self.klokke())
        for d in range(14):
            dag = idag - _dt.timedelta(days=d)
            try:
                b = parse_wikimedia(self.hent(f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/{dag:%Y/%m/%d}", timeout=8))
                if b and b.get("liggende", True):
                    bilder.append(b)
            except Exception:
                pass
        try:
            start = (idag - _dt.timedelta(days=13)).isoformat()
            bilder += parse_apod(self.hent("https://api.nasa.gov/planetary/apod?" + urllib.parse.urlencode({"api_key": "DEMO_KEY", "start_date": start})))
        except Exception:
            pass
        return bilder

    def bilder(self) -> dict:
        c = self.cfg() or {}
        valg = str(c.get("foto_kilder") or "dagens")
        key, tema = str(c.get("unsplash_key") or "").strip(), str(c.get("unsplash_tema") or "").strip()
        ut, nå = [], self.klokke()
        with self.lock:
            if valg in ("unsplash", "begge"):
                t, sig, l = self.cache["unsplash"]
                if not key:
                    self.feil["unsplash"] = "Mangler Unsplash-nøkkel"
                elif nå - t > 7200 or sig != key + "|" + tema or not l:
                    try:
                        l = self._unsplash(key, tema)
                        self.cache["unsplash"], self.feil["unsplash"] = (nå, key + "|" + tema, l), ""
                    except Exception as e:
                        self.feil["unsplash"] = "Unsplash svarte ikke: " + str(e)[:80]
                        self.cache["unsplash"] = (nå - 7200 + 600, sig, l)   # prøv igjen om 10 min
                ut += l if key else []
            if valg in ("dagens", "begge"):
                t, _, l = self.cache["dagens"]
                if nå - t > 6 * 3600 or not l:
                    l = self._dagens()
                    self.cache["dagens"] = (nå if l else nå - 6 * 3600 + 900, "", l)
                    self.feil["dagens"] = "" if l else "Fikk ikke hentet dagens bilde"
                ut += l
        return {"kilde": valg, "items": ut, "feil": "; ".join(v for k, v in self.feil.items() if v and (valg == "begge" or valg == k))}
