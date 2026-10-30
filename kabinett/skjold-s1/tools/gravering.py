#!/usr/bin/env python3
"""Lasergravering på undersiden av kassen (bunnplaten): logo, navn og typeskilt.

Lager  ../platemetall/skjold_s1_avrundet/skjold_s1_bunn_gravering.dxf  (lag ENGRAVE = graveres, lag REF = bunnplatens
omriss og hull, bare til plassering) og en forhåndsvisning  ../platemetall/skjold_s1_avrundet/skjold_s1_bunn_gravering.png.

Tegningen er sett fra UNDERSIDEN av kassen med fronten nederst – slik teksten leses når kassen snus. Fonter hentes fra
npm-pakkene @fontsource/sora og @fontsource/ibm-plex-mono (kjør `npm install` i denne mappen først).
Kjør:  python3 gravering.py [serienummer]      (standard SKJ-S1-0001)
"""
import math, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "platemetall", "skjold_s1_avrundet")
FONTS = os.path.join(HERE, "node_modules", "@fontsource")
SORA6 = os.path.join(FONTS, "sora", "files", "sora-latin-600-normal.woff")
SORA4 = os.path.join(FONTS, "sora", "files", "sora-latin-400-normal.woff")
PLEX = os.path.join(FONTS, "ibm-plex-mono", "files", "ibm-plex-mono-latin-400-normal.woff")
SERIAL = sys.argv[1] if len(sys.argv) > 1 else "SKJ-S1-0001"

# bunnplaten (samme tall som cad/generate_sheet_round.js): 172 × 136,4, hull Ø4,2 for PEM ved (±80, −60/0/60), luftespalter y −34…6
PLATE_W, PLATE_H = 172.0, 136.4
PEM = [(-80, -60), (80, -60), (-80, 0), (80, 0), (-80, 60), (80, 60)]
VENTS = [(-55 + 5 * i, -14) for i in range(23)]   # 2,4 × 40


class FlatPen(BasePen):
    """Samler glyfkonturen som polygoner (kurver gjøres om til korte linjer)."""
    def __init__(self, gs):
        super().__init__(gs); self.polys = []; self.cur = []

    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, c1, c2, p1):
        p0 = self.cur[-1]
        for k in range(1, 11):
            t = k / 10
            self.cur.append(((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t * t * c2[0] + t ** 3 * p1[0],
                             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t * t * c2[1] + t ** 3 * p1[1]))
    def _qCurveToOne(self, c, p1):
        p0 = self.cur[-1]
        for k in range(1, 9):
            t = k / 8
            self.cur.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
    def _closePath(self):
        if len(self.cur) > 2: self.polys.append(self.cur)
        self.cur = []
    _endPath = _closePath


class Face:
    def __init__(self, path):
        self.f = TTFont(path); self.upm = self.f["head"].unitsPerEm; self.gs = self.f.getGlyphSet(); self.cmap = self.f.getBestCmap()

    def text(self, s, size_cap, x, y, tracking=0.0, align="c"):
        """Polygoner for teksten; size_cap = høyde på versal (mm). Returnerer (polygoner, bredde)."""
        cap = self.f["OS/2"].sCapHeight or 0.7 * self.upm
        k = size_cap / cap
        glyphs = [self.cmap.get(ord(ch), self.cmap.get(ord("?"))) for ch in s]
        adv = [self.gs[g].width * k + tracking for g in glyphs]
        w = sum(adv) - tracking
        x0 = x - w / 2 if align == "c" else x
        out = []
        for g, a in zip(glyphs, adv):
            pen = FlatPen(self.gs); self.gs[g].draw(pen)
            for poly in pen.polys:
                out.append([(x0 + px * k, y + py * k) for px, py in poly])
            x0 += a
        return out, w


def rrect(cx, cy, w, h, r, n=8):
    pts = []
    for i, (sx, sy, a0) in enumerate(((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180))):
        for j in range(n + 1):
            a = math.radians(a0 + 90 * j / n)
            pts.append((cx + sx * (w / 2 - r) + r * math.cos(a), cy + sy * (h / 2 - r) + r * math.sin(a)))
    return pts


def circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


sora6, sora4, plex = Face(SORA6), Face(SORA4), Face(PLEX)
E = []   # graveringspolygoner (fylte flater)

# ---- typeskilt, sentrert på bakre halvdel av bunnen (y 14 … 56, fri for spalter og PEM-hull) ----
CY = 36.0
# logo: fem streker (skjold_merke.svg, 42 × 46, stolper 4,6 brede, høyder 22/33/42/33/22) skalert til 12 mm høyde + SKJOLD
LOGO_H = 12.0; ks = LOGO_H / 42.0
bars = [(1, 22), (9, 33), (18.7, 42), (28.4, 33), (36.4, 22)]
word, ww = sora6.text("SKJOLD", 9.0, 0, 0, tracking=2.2)
mark_w = 41 * ks; gap = 5.0
total = mark_w + gap + ww
mx = -total / 2; wx = mx + mark_w + gap + ww / 2
top_y = CY + 14.0
for bx, bh in bars:
    E.append(rrect(mx + (bx + 2.3) * ks, top_y, 4.6 * ks, bh * ks, 2.3 * ks))
polys, _ = sora6.text("SKJOLD", 9.0, wx, top_y - 4.5, tracking=2.2); E += polys
polys, _ = plex.text("STREAMING AMPLIFIER", 2.6, wx, top_y - 9.2, tracking=1.1); E += polys
# modell og opphav
polys, _ = sora6.text("Skjold S1", 4.0, 0, CY - 4.0); E += polys
polys, _ = sora4.text("Designet av Sebastian Kristo Jemtland i Norge", 2.6, 0, CY - 9.6); E += polys
polys, _ = plex.text(f"19-24 V   3 A  ·  Modell S1  ·  Serienr. {SERIAL}", 2.3, 0, CY - 14.6, tracking=0.25); E += polys
# likestrømssymbol ⎓ (finnes ikke i fonten): heltrukket strek over tre korte, plassert i mellomrommet etter «19-24 V»
polys, w_line = plex.text(f"19-24 V   3 A  ·  Modell S1  ·  Serienr. {SERIAL}", 2.3, 0, CY - 14.6, tracking=0.25)
_, w7 = plex.text("19-24 V ", 2.3, 0, 0, tracking=0.25); _, wsp = plex.text("  ", 2.3, 0, 0, tracking=0.25)
sx = -w_line / 2 + w7 + wsp / 2 - 1.3 - 1.1; sy = CY - 14.6   # midt i de to mellomrommene
E.append([(sx, sy + 1.6), (sx + 2.6, sy + 1.6), (sx + 2.6, sy + 1.95), (sx, sy + 1.95)])
for i in range(3):
    x = sx + i * 0.95
    E.append([(x, sy + 0.7), (x + 0.7, sy + 0.7), (x + 0.7, sy + 1.05), (x, sy + 1.05)])

# ---- tegningen er sett fra undersiden: teksten leses rett, kassens x-akse er speilet (hull/omriss speiles) ----
REF = [rrect(0, 0, PLATE_W, PLATE_H, 1.0)] + [circle(-x, y, 2.1) for x, y in PEM] + [rrect(-x, y, 2.4, 40, 1.2) for x, y in VENTS]

# ---- DXF ----
def dxf(layers):
    L = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(layers))]
    for i, (name, _) in enumerate(layers):
        L += ["0", "LAYER", "2", name, "70", "0", "62", str(7 if i == 0 else 1 + i), "6", "CONTINUOUS"]
    L += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for name, polys in layers:
        for p in polys:
            L += ["0", "LWPOLYLINE", "8", name, "90", str(len(p)), "70", "1"]
            for x, y in p:
                L += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"


os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "skjold_s1_bunn_gravering.dxf"), "w") as fh:
    fh.write(dxf([("ENGRAVE", E), ("REF", REF)]))

# ---- PNG-forhåndsvisning (sort eloksert kasse, lys gravering) ----
try:
    from PIL import Image, ImageDraw
    S = 6; img = Image.new("RGB", (int(PLATE_W * S) + 40, int(PLATE_H * S) + 40), (26, 26, 28)); d = ImageDraw.Draw(img)
    tr = lambda p: (20 + (p[0] + PLATE_W / 2) * S, 20 + (PLATE_H / 2 - p[1]) * S)
    for p in REF:
        d.line([tr(q) for q in p] + [tr(p[0])], fill=(70, 70, 74), width=1)
    # even-odd: tell hvor mange polygoner hvert punkt ligger i (indre konturer i bokstaver blir mørke igjen)
    import numpy as np
    acc = np.zeros((img.size[1], img.size[0]), dtype=np.int32)
    for p in E:
        m = Image.new("L", img.size, 0); ImageDraw.Draw(m).polygon([tr(q) for q in p], fill=1); acc += np.array(m, dtype=np.int32)
    px = np.array(img); px[acc % 2 == 1] = (210, 212, 215); img = Image.fromarray(px)
    img.save(os.path.join(OUT, "skjold_s1_bunn_gravering.png"))
except ImportError:
    pass
print("skrev skjold_s1_bunn_gravering.dxf/.png –", len(E), "polygoner, serienr.", SERIAL)
