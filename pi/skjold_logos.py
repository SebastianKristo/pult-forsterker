"""Kanallogoer servert av Skjold selv: GET /api/logo?k=<nøkkel>.

Hvorfor: logo-adressene som kom fra Lyrion var ofte relative («imageproxy/…», «/plugins/…») eller ble gjort absolutte
mot Lyrion-verten (http://127.0.0.1:9000/… når Lyrion kjører på samme Pi – uoppnåelig fra telefonen), og
http-bilder blokkeres som blandet innhold over https (fjernstyring/Skjold-hjem) og av iOS ATS / Android cleartext.
Her hentes bildet av daemonen, caches på disk og serveres fra samme opphav som API-et, så det virker overalt.
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

CACHE_DIR = os.environ.get("KI_AMP_LOGO_DIR", "/var/lib/ki-amp/logos")
NRK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos", "nrk")
for _cand in (NRK_DIR, "/usr/local/share/ki-amp/logos/nrk"):
    if os.path.isdir(_cand):
        NRK_DIR = _cand
        break
MAX_AGE = 30 * 86400
NEG_AGE = 86400          # «fant ingen logo» huskes et døgn
UA = {"User-Agent": "Skjold/1.0 (+https://skjold.smarthjemexperten.no)"}

_reg = {}                # nøkkel -> {"src": url|"", "name": kanalnavn}
_lock = threading.Lock()
lyrion_base = None       # settes av daemonen: lambda -> "http://host:9000" eller None


def _norm(name):
    return re.sub(r"[^a-z0-9+]", "", (name or "").lower().replace("æ", "ae").replace("ø", "o").replace("å", "a"))


NRK = {"nrkp1": "nrk-p1", "nrkp1+": "nrk-p1plus", "nrkp1pluss": "nrk-p1plus", "nrkp1plus": "nrk-p1plus", "nrkp2": "nrk-p2",
       "nrkp3": "nrk-p3", "nrkmp3": "nrk-mp3", "nrkjazz": "nrk-jazz", "nrkklassisk": "nrk-klassisk",
       "nrkfolkemusikk": "nrk-folkemusikk", "nrksport": "nrk-sport", "p1": "nrk-p1", "p2": "nrk-p2", "p3": "nrk-p3", "mp3": "nrk-mp3"}


def nrk_file(name):
    f = NRK.get(_norm(name))
    if not f:
        n = _norm(name)
        for k, v in NRK.items():   # «NRK P1 Oslo og Akershus» o.l.
            if k.startswith("nrk") and n.startswith(k) and len(k) > 4:
                f = v
        if not f:
            return None
    p = os.path.join(NRK_DIR, f + ".svg")
    return p if os.path.isfile(p) else None


def absolute(src):
    """Gjør Lyrions relative bildestier absolutte mot Lyrion-serveren (sett fra Skjold, ikke fra telefonen)."""
    src = (src or "").strip()
    if not src or src.startswith("data:"):
        return src
    if src.startswith("//"):
        return "https:" + src
    if re.match(r"^https?://", src, re.I):
        return src
    base = lyrion_base() if callable(lyrion_base) else None
    return (base.rstrip("/") + "/" + src.lstrip("/")) if base else ""


def key_for(src, name):
    raw = (src or "").strip() or ("name:" + _norm(name))
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def path_for(src="", name=""):
    """Relativ /api/logo-adresse for en kanal, eller "" når vi verken har kilde eller navn."""
    if not (src or name):
        return ""
    if not src and not nrk_file(name) and not name.strip():
        return ""
    k = key_for(src, name)
    with _lock:
        _reg[k] = {"src": src or "", "name": name or ""}
    return "/api/logo?k=" + k


def _sniff(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    if b[:4] in (b"\x00\x00\x01\x00",):
        return "image/x-icon"
    head = b[:512].lstrip().lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in b[:2048].lower()):
        return "image/svg+xml"
    return ""


def _fetch(url, timeout=6, maxb=2_000_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(maxb)


def radio_browser_logo(name, fetch=_fetch):
    """Beste favicon fra Radio Browser for kanalnavnet (nøyaktig navn først, så flest stemmer)."""
    if not name:
        return ""
    q = urllib.parse.quote(name)
    for host in ("de1.api.radio-browser.info", "nl1.api.radio-browser.info", "at1.api.radio-browser.info"):
        try:
            data = json.loads(fetch(f"https://{host}/json/stations/byname/{q}?limit=20&hidebroken=true&order=votes&reverse=true"))
        except Exception:
            continue
        best = None
        for s in data if isinstance(data, list) else []:
            fav = (s.get("favicon") or "").strip()
            if not fav:
                continue
            score = (2 if _norm(s.get("name")) == _norm(name) else 0) + (1 if (s.get("countrycode") or "") == "NO" else 0)
            if best is None or score > best[0]:
                best = (score, fav)
        if best:
            return best[1]
        return ""
    return ""


def _cache_paths(k):
    return os.path.join(CACHE_DIR, k + ".bin"), os.path.join(CACHE_DIR, k + ".json")


def get(k, fetch=_fetch, now=None):
    """(bytes, content_type) for nøkkelen, eller None. Bruker cache, kilde, NRK-innebygd og Radio Browser i den rekkefølgen."""
    now = now or time.time()
    if not re.fullmatch(r"[0-9a-f]{16}", k or ""):
        return None
    binp, metap = _cache_paths(k)
    try:
        meta = json.load(open(metap))
        age = now - meta.get("t", 0)
        if meta.get("none") and age < NEG_AGE:
            return None
        if not meta.get("none") and age < MAX_AGE and os.path.isfile(binp):
            return open(binp, "rb").read(), meta.get("ct", "image/png")
    except Exception:
        meta = None
    with _lock:
        info = dict(_reg.get(k) or {})
    if not info and meta:
        info = {"src": meta.get("src", ""), "name": meta.get("name", "")}
    if not info:
        return None
    body = ct = None
    src = absolute(info.get("src", ""))
    if src.startswith("data:"):
        import base64
        try:
            hdr, b64 = src.split(",", 1)
            body = base64.b64decode(b64) if ";base64" in hdr else urllib.parse.unquote_to_bytes(b64)
            ct = _sniff(body)
        except Exception:
            body = None
    elif src:
        try:
            body = fetch(src)
            ct = _sniff(body)
        except Exception:
            body = None
    if not (body and ct):
        f = nrk_file(info.get("name", ""))
        if f:
            body, ct = open(f, "rb").read(), "image/svg+xml"
    if not (body and ct) and info.get("name"):
        rb = radio_browser_logo(info["name"], fetch)
        if rb:
            try:
                body = fetch(rb)
                ct = _sniff(body)
            except Exception:
                body = None
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        if body and ct:
            with open(binp + ".tmp", "wb") as fh:
                fh.write(body)
            os.replace(binp + ".tmp", binp)
            json.dump({"t": now, "ct": ct, "src": info.get("src", ""), "name": info.get("name", "")}, open(metap, "w"))
        else:
            json.dump({"t": now, "none": True, "src": info.get("src", ""), "name": info.get("name", "")}, open(metap, "w"))
    except OSError:
        pass
    return (body, ct) if body and ct else None
