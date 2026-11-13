#!/usr/bin/env python3
"""Kassett-cover på A4: skriv artist og album, så hentes coveret og etikettene legges ferdig på A4 for utskrift.

Bruk (på Mac/PC med nett):
    python3 lag_cover.py album.txt              # én linje per kassett: «Artist - Album»
    python3 lag_cover.py "Linkin Park - Hybrid Theory" "Daft Punk - Discovery"

Linjeformat i album.txt (tomme linjer og linjer som starter med # hoppes over):
    Artist - Album
    Artist - Album | /sti/til/eget-cover.jpg          (bruk ditt eget bilde i stedet for å søke)
    Artist - Album | 2                                (antall kopier)

Resultat i samme mappe som album.txt (eller her): kassett-cover.pdf (A4, 15 per side) og kassett-cover.svg per side.
Coveret er 44 × 49,6 mm med avfasede øvre hjørner, og legges inni kassetten bak etikettvinduet (ingen lim: rammen
og bakplaten holder det). Vanlig A4-papir holder. Skriv ut i 100 % skala
(ikke «tilpass til side»), helst på blankt fotopapir eller klistremerkeark, og klipp langs den tynne grå linjen.

Cover hentes fra iTunes-søket (ingen nøkkel), med MusicBrainz/Cover Art Archive som reserve. Bildene caches i
.cover-cache/. Finnes ingen cover, lages et fargefelt med navnet. PDF lages med Playwright (pip install playwright &&
python3 -m playwright install chromium); uten Playwright skrives bare SVG-filene (åpne i nettleser → Skriv ut → 100 %).
"""
import base64
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

W, H = 210.0, 297.0
# Papiret ligger inni kassetten bak etikettvinduet (ingen lim): 44 × 49,6 mm, øvre hjørner avfaset 7 mm (papW/papH/papC
# i skjold_kassett.scad). Rammen dekker 2,4 mm langs kanten (rimW), så alt viktig står innenfor det synlige vinduet.
LW, LH, C, RIM = 44.0, 49.6, 7.0, 2.4
COLS, ROWS = 3, 5
GX, GY = 8.0, 4.0
MX = (W - COLS * LW - (COLS - 1) * GX) / 2
MY = (H - ROWS * LH - (ROWS - 1) * GY) / 2
UA = {"User-Agent": "SkjoldKassett/1.0 (+https://skjold-lab.com)"}


def _get(url, timeout=12):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def itunes_cover(artist, album, get=_get):
    q = urllib.parse.urlencode({"term": f"{artist} {album}", "entity": "album", "limit": 5, "country": "NO"})
    res = json.loads(get("https://itunes.apple.com/search?" + q)).get("results") or []
    def score(x):
        a, c = (x.get("artistName") or "").lower(), (x.get("collectionName") or "").lower()
        return (artist.lower() in a) * 2 + (album.lower() in c) * 2 + (c.startswith(album.lower()))
    res.sort(key=score, reverse=True)
    for x in res:
        u = x.get("artworkUrl100")
        if u:
            return get(re.sub(r"/\d+x\d+bb\.", "/1000x1000bb.", u))
    return None


def musicbrainz_cover(artist, album, get=_get):
    q = urllib.parse.quote(f'releasegroup:"{album}" AND artist:"{artist}"')
    res = json.loads(get(f"https://musicbrainz.org/ws/2/release-group/?query={q}&fmt=json&limit=3")).get("release-groups") or []
    for rg in res:
        try:
            return get(f"https://coverartarchive.org/release-group/{rg['id']}/front-500")
        except Exception:
            continue
    return None


def mime(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    return None


def cover(artist, album, own=None, cache=".cover-cache", get=_get):
    """Bildebytes for albumet (eget bilde, cache, iTunes, MusicBrainz) eller None."""
    if own:
        return open(os.path.expanduser(own), "rb").read()
    os.makedirs(cache, exist_ok=True)
    f = os.path.join(cache, hashlib.sha1(f"{artist}|{album}".lower().encode()).hexdigest()[:16] + ".img")
    if os.path.isfile(f):
        return open(f, "rb").read()
    for finn in (itunes_cover, musicbrainz_cover):
        try:
            b = finn(artist, album, get)
        except Exception:
            b = None
        if b and mime(b):
            open(f, "wb").write(b)
            return b
    return None


def parse(lines):
    out = []
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        extra = None
        if "|" in s:
            s, extra = [x.strip() for x in s.split("|", 1)]
        if " - " in s:
            artist, album = [x.strip() for x in s.split(" - ", 1)]
        else:
            artist, album = "", s
        n, own = 1, None
        if extra:
            if extra.isdigit():
                n = max(1, min(15, int(extra)))
            else:
                own = extra
        out += [{"artist": artist, "album": album, "own": own}] * n
    return out


def _fit(text, size, maxw, minsize=2.2):
    """Krymp skrifta til teksten får plass (≈ 0,55 em per tegn), men ikke under minsize – da kuttes den med «…»."""
    while size > minsize and len(text) * size * 0.55 > maxw:
        size -= 0.1
    return round(size, 2)


def _cut(text, size, maxw):
    n = max(4, int(maxw / (size * 0.55)))
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _lines(text, size, maxw, maks=3):
    """Del i linjer for fargefeltet."""
    n, out, cur = max(6, int(maxw / (size * 0.55))), [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    if len(out) > maks:
        out = out[:maks]; out[-1] = _cut(out[-1] + " …", size, maxw)
    return [_cut(x, size, maxw) for x in out]


def _hue(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:4], 16) % 360


def omriss(inset=0.0):
    """Papirets form (SVG-sti), y nedover: avfaset 45° i de øvre hjørnene. inset > 0 = vinduet innenfor rammen."""
    c = C - inset * (2 ** 0.5 - 1)   # samme 45°-fas, flyttet innover
    a, b, w, h = inset, inset, LW - inset, LH - inset
    return f"M{a + c:.2f},{b:.2f} L{w - c:.2f},{b:.2f} L{w:.2f},{b + c:.2f} L{w:.2f},{h:.2f} L{a:.2f},{h:.2f} L{a:.2f},{b + c:.2f} Z"


def label(x, y, it, img):
    tx = RIM + 1.0                      # tekst innenfor rammen
    ft, fa = _fit(it["album"], 3.0, LW - 2 * tx), _fit(it["artist"], 2.3, LW - 2 * tx)
    side = LW - 2 * RIM - 2.6           # kvadratisk cover, fylles helt opp mot vinduets avfasede hjørner
    ax, ay = (LW - side) / 2, RIM + 0.6
    cid = f"c{x:.0f}{y:.0f}"
    clip = f'<clipPath id="{cid}"><path d="{omriss(RIM + 0.6)}"/></clipPath>'
    if img:
        art = (clip + f'<image href="data:{mime(img)};base64,{base64.b64encode(img).decode()}" x="{ax}" y="{ay}" width="{side}" height="{side}" '
               f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>')
    else:   # fargefelt med navnet når coveret ikke finnes
        h = _hue(it["artist"] + it["album"])
        fs = 4.2
        ls = _lines(it["album"], fs, side - 6)
        y0 = ay + side / 2 - (len(ls) - 1) * fs * 0.6
        txt = "".join(f'<text x="{LW/2}" y="{y0 + i*fs*1.2:.2f}" font-size="{fs}" fill="hsl({h},40%,88%)" text-anchor="middle" '
                      f'class="t" font-weight="600">{html.escape(l)}</text>' for i, l in enumerate(ls))
        art = clip + f'<rect x="{ax}" y="{ay}" width="{side}" height="{side}" fill="hsl({h},35%,28%)" clip-path="url(#{cid})"/>' + txt
    ty = ay + side + 3.4
    return (f'<g transform="translate({x:.2f},{y:.2f})"><path d="{omriss()}" fill="#f6f3ee"/>{art}'
            f'<text x="{tx}" y="{ty:.2f}" font-size="{ft}" font-weight="600" class="t" fill="#1b1b1c">{html.escape(_cut(it["album"], ft, LW - 2 * tx))}</text>'
            f'<text x="{tx}" y="{ty + 3.0:.2f}" font-size="{fa}" class="t" fill="#6a6a65">{html.escape(_cut(it["artist"], fa, LW - 2 * tx - 8))}</text>'
            f'<text x="{LW - tx}" y="{ty + 3.0:.2f}" font-size="1.7" class="t" fill="#b0aca4" text-anchor="end" letter-spacing=".4">SKJOLD</text>'
            f'<path d="{omriss()}" fill="none" stroke="#c9c5bd" stroke-width=".15"/></g>')


def pages(items, imgs):
    per = COLS * ROWS
    for p in range(0, len(items), per):
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
                 '<style>.t{font-family:Sora,Helvetica,Arial,sans-serif}</style>',
                 f'<text x="{MX}" y="{MY-3}" font-size="2.6" fill="#9b978f" class="t">SKJOLD KASSETT · cover 44 × 49,6 mm · '
                 f'skriv ut i 100 % · klipp langs den grå linjen</text>']
        for i, it in enumerate(items[p:p + per]):
            r, c = divmod(i, COLS)
            parts.append(label(MX + c * (LW + GX), MY + r * (LH + GY), it, imgs[p + i]))
        parts.append('</svg>')
        yield "\n".join(parts)


def pdf(svgs, path):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    body = "".join(f'<div style="page-break-after:always">{s}</div>' for s in svgs)
    doc = ('<html><head><meta charset="utf-8"><style>@page{size:A4;margin:0}body{margin:0}svg{display:block}</style>'
           '<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap" rel="stylesheet"></head>'
           f'<body>{body}</body></html>')
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
        try:
            b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        except Exception:
            return False
        pg = b.new_page()
        pg.set_content(doc, wait_until="networkidle")
        pg.pdf(path=path, width="210mm", height="297mm", print_background=True)
        b.close()
    return True


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    if len(argv) == 1 and not os.path.isfile(argv[0]) and os.path.basename(argv[0]) == "album.txt":
        ex = os.path.join(os.path.dirname(os.path.abspath(argv[0])), "album-eksempel.txt")
        if os.path.isfile(ex):   # første gang: lag din egen album.txt fra eksempelet (album.txt følges ikke av Git)
            import shutil
            shutil.copy(ex, argv[0])
            print(f"Laget {argv[0]} fra album-eksempel.txt – rediger den og kjør igjen om du vil endre lista.")
    if len(argv) == 1 and os.path.isfile(argv[0]):
        src = argv[0]
        out_dir = os.path.dirname(os.path.abspath(src))
        items = parse(open(src, encoding="utf-8"))
    else:
        out_dir = os.getcwd()
        items = parse(argv)
    if not items:
        print("Ingen album funnet – skriv «Artist - Album», én per linje.")
        return 1
    imgs = []
    for it in items:
        b = cover(it["artist"], it["album"], it["own"], cache=os.path.join(out_dir, ".cover-cache"))
        print(("✓ " if b else "· ingen cover, bruker fargefelt: ") + f'{it["artist"]} – {it["album"]}')
        imgs.append(b)
    svgs = list(pages(items, imgs))
    for i, s in enumerate(svgs, 1):
        open(os.path.join(out_dir, f"kassett-cover-{i}.svg"), "w", encoding="utf-8").write(s)
    p = os.path.join(out_dir, "kassett-cover.pdf")
    if pdf(svgs, p):
        print(f"\nFerdig: {p} ({len(svgs)} side{'r' if len(svgs) > 1 else ''}). Skriv ut i 100 % skala.")
    else:
        print(f"\nPlaywright mangler – åpne kassett-cover-1.svg i nettleseren og skriv ut i 100 % skala "
              f"(eller: pip install playwright && python3 -m playwright install chromium).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
