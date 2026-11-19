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
import unicodedata
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
UA = {"User-Agent": "Skjold/1.0 (+https://skjold-lab.com)"}

_reg = {}                # nøkkel -> {"src": url|"", "name": kanalnavn}
_lock = threading.Lock()
lyrion_base = None       # settes av daemonen: lambda -> "http://host:9000" eller None


def _tokens(name):
    """Kanalnavn → ord til sammenligning: små bokstaver, æøå/aksenter brettet, «+» → «pluss», uten nummer foran
    («1-NRK Jazz»), parentes-tillegg («(Oslo, Norway / Pop)») og skilletegn. «NRK P1+», «NRK P1 Pluss», «nrk p1 plus»
    og «NRK P1+ (Pop)» gir alle [nrk, p1, pluss]."""
    s = unicodedata.normalize("NFKD", (name or "").lower().replace("æ", "ae").replace("ø", "o").replace("å", "a"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^\s*\d{1,2}\s*[-:)]\s*|^\s*\d{1,2}\.\s+", "", s)
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s).replace("+", " pluss ")
    s = re.sub(r"\bplus\b", "pluss", s)
    return re.findall(r"[a-z0-9]+", s)


def _norm(name):
    """Normalisert kanalnavn (uten mellomrom og tegn): «NRK P1+» og «NRK P1 Pluss» → «nrkp1pluss»."""
    return "".join(_tokens(name))


# Innebygde NRK-logoer (pi/logos/nrk/<fil>.png): fil -> (visningsnavn, normaliserte navn).
# Navn som begynner med «nrk» godtas også med tillegg bak («NRK P1 Oslo og Akershus», «NRK P3 Musikk»), men bare
# på hele ord – «NRK P13» er ikke P1. Navn uten «NRK» («P1+», «P3») må stemme helt.
NRK_KANALER = {
    "nrk-p1": ("NRK P1", ("nrkp1", "p1")),
    "nrk-p1plus": ("NRK P1+", ("nrkp1pluss", "nrkp1plus", "p1pluss", "p1plus")),
    "nrk-p2": ("NRK P2", ("nrkp2", "p2")),
    "nrk-p3": ("NRK P3", ("nrkp3", "p3")),
    "nrk-mp3": ("NRK mP3", ("nrkmp3", "mp3")),
    "nrk-jazz": ("NRK Jazz", ("nrkjazz",)),
    "nrk-klassisk": ("NRK Klassisk", ("nrkklassisk",)),
    "nrk-folkemusikk": ("NRK Folkemusikk", ("nrkfolkemusikk",)),
    "nrk-sport": ("NRK Sport", ("nrksport",)),
}
NRK = {alias: fil for fil, (_vis, aliaser) in NRK_KANALER.items() for alias in aliaser}


def nrk_key(name):
    """Filnavnet (uten endelse) til den innebygde NRK-logoen for kanalnavnet, eller None."""
    t = _tokens(name)
    if len(t) > 2 and t[0] == "nrk" and t[1] == "radio":     # «NRK Radio P1+»
        t = [t[0]] + t[2:]
    n = "".join(t)
    if n in NRK:
        return NRK[n]
    for m in range(len(t) - 1, 0, -1):    # lengste treff på hele ord først: «NRK P1+ …» før «NRK P1 …»
        k = "".join(t[:m])
        if k.startswith("nrk") and len(k) > 3 and k in NRK:
            return NRK[k]
    return None


def canonical(name):
    """Visningsnavnet NRK bruker («P1 pluss» → «NRK P1+»), eller "" når kanalen ikke er en kjent NRK-kanal."""
    f = nrk_key(name)
    return NRK_KANALER[f][0] if f else ""


def nrk_file(name):
    f = nrk_key(name)
    if not f:
        return None
    for ext in (".png", ".svg"):   # PNG først: iOS og Android viser ikke SVG
        p = os.path.join(NRK_DIR, f + ext)
        if os.path.isfile(p):
            return p
    return None


NRK_URL = (("nrk_p1plus", "NRK P1+"), ("p1pluss", "NRK P1+"), ("p1plus", "NRK P1+"), ("nrkjazz", "NRK Jazz"), ("jazz_", "NRK Jazz"),
           ("klassisk", "NRK Klassisk"), ("folkemusikk", "NRK Folkemusikk"), ("nrk_mp3", "NRK mP3"), ("mp3_", "NRK mP3"),
           ("sport", "NRK Sport"), ("p3_", "NRK P3"), ("nrkp3", "NRK P3"), ("p2_", "NRK P2"), ("nrkp2", "NRK P2"),
           ("p1_", "NRK P1"), ("nrkp1", "NRK P1"))


def logo_name(name, url=""):
    """Navnet logoen skal slås opp på: «1-NRK Jazz» → «NRK Jazz», og NRK-kanalen fra strømadressen når Lyrion viser
    programnavnet («Jazzbrunsj: …») i stedet for kanalnavnet."""
    n = re.sub(r"^\s*\d+\s*[-.:)]\s*", "", name or "").strip()
    if nrk_file(n):
        return n
    u = (url or "").lower()
    if "nrk" in u or "contentdelivery.net" in u:
        for pat, canon in NRK_URL:
            if pat in u:
                return canon
    return n


def to_png(body):
    """SVG → PNG på mørk, kvadratisk flis (appene viser ikke SVG; hvite logoer synes ikke på lys bakgrunn)."""
    try:
        import io
        import cairosvg
        from PIL import Image
        logo = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=body, output_width=420))).convert("RGBA")
        tile = Image.new("RGBA", (512, 512), (18, 18, 20, 255))
        tile.alpha_composite(logo, ((512 - logo.width) // 2, max(0, (512 - logo.height) // 2)))
        out = io.BytesIO()
        tile.convert("RGB").save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception:
        return None


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


def generic(src):
    """Lyrions standardbilde for radio (masten) o.l. er ikke en kanallogo – samme fil for alle kanaler."""
    a = (src or "").lower()
    return "html/images/" in a or a.endswith(("/radio.png", "/radio.svg", "/cover.png")) or ("/plugins/" in a and "icon" in a)


def key_for(src, name):
    # navnet er alltid med: ellers fikk alle kanaler med samme (standard)bilde samme nøkkel og samme logo
    raw = (src or "").strip() + "|name:" + _norm(name)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def path_for(src="", name=""):
    """Relativ /api/logo-adresse for en kanal, eller "" når vi verken har kilde eller navn."""
    if generic(src):
        src = ""
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
    """Beste favicon fra Radio Browser for kanalnavnet; prøver også uten «Radio »-prefiks og «(by, land / sjanger)»."""
    if not name:
        return ""
    tried = []
    base = re.sub(r"\s*\(.*\)\s*$", "", name).strip()
    for cand in (name, base, canonical(name), re.sub(r"\s*\+\s*$|\s+pluss?$", "+", base, flags=re.I),
                 re.sub(r"\s*\+\s*$", " Pluss", base), re.sub(r"^radio\s+", "", name, flags=re.I)):
        cand = (cand or "").strip()
        if cand and cand not in tried:
            tried.append(cand)
            hit = _radio_browser_one(cand, fetch)
            if hit:
                return hit
    return ""


def _radio_browser_one(name, fetch):
    q = urllib.parse.quote(name)
    for host in ("de1.api.radio-browser.info", "nl1.api.radio-browser.info", "at1.api.radio-browser.info"):
        try:
            data = json.loads(fetch(f"https://{host}/json/stations/byname/{q}?limit=20&hidebroken=true&order=votes&reverse=true"))
        except Exception:
            continue
        best = None
        for s in data if isinstance(data, list) else []:
            fav = (s.get("favicon") or "").strip()
            if not fav or not re.match(r"^(https?:)?//", fav, re.I):
                continue
            # samme navn etter normalisering («NRK P1+» = «NRK P1 Pluss»), norsk kanal, og helst ikke et lite .ico
            score = (4 if _norm(s.get("name")) == _norm(name) else 0) + (2 if (s.get("countrycode") or "") == "NO" else 0) \
                - (1 if re.search(r"\.ico(\?|$)", fav, re.I) else 0)
            if best is None or score > best[0]:
                best = (score, fav)
        if best:
            return best[1]
        return ""
    return ""


def _cache_paths(k):
    return os.path.join(CACHE_DIR, k + ".bin"), os.path.join(CACHE_DIR, k + ".json")


def get(k, fetch=_fetch, now=None):
    """(bytes, content_type) for nøkkelen, eller None. Bruker cache, NRK-innebygd, kilde og Radio Browser i den rekkefølgen."""
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
    f = nrk_file(info.get("name", ""))
    if f:
        # Kjent NRK-kanal: bruk logoen i repoet (samme utseende overalt, virker uten nett). Kildens bilde for NRK-kanaler
        # var ofte et lite favicon, en død adresse eller et generisk bilde – da ble NRK P1+ stående uten logo.
        body = open(f, "rb").read()
        ct = "image/png" if f.endswith(".png") else "image/svg+xml"
    elif src.startswith("data:"):
        import base64
        try:
            hdr, b64 = src.split(",", 1)
            body = base64.b64decode(b64) if ";base64" in hdr else urllib.parse.unquote_to_bytes(b64)
            ct = _sniff(body)
        except Exception:
            body = None
    elif src and not generic(src):
        try:
            body = fetch(src)
            ct = _sniff(body)
        except Exception:
            body = None
    if not (body and ct) and info.get("name"):
        rb = radio_browser_logo(info["name"], fetch)
        if rb:
            try:
                body = fetch(rb)
                ct = _sniff(body)
            except Exception:
                body = None
    if body and ct == "image/svg+xml":
        png = to_png(body)
        if png:
            body, ct = png, "image/png"
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
