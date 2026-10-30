"""Små hjelpere for DXF-filer til lasermerking: tekst som fylte konturer, enkle former og en DXF-skriver.

Fonter: Helvetiker Bold/Regular (three.js typeface.json, samme som designpakkens merkefiler) fra node_modules/three,
eller woff-fonter fra @fontsource (Sora, IBM Plex Mono). Kjør `npm install` i denne mappen først.
Alle mål i mm. Polygoner er lister av (x, y); «even-odd» gir hull i bokstaver.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
NM = os.path.join(HERE, "node_modules")
HELV_BOLD = os.path.join(NM, "three", "examples", "fonts", "helvetiker_bold.typeface.json")
HELV_REG = os.path.join(NM, "three", "examples", "fonts", "helvetiker_regular.typeface.json")
SORA6 = os.path.join(NM, "@fontsource", "sora", "files", "sora-latin-600-normal.woff")
SORA4 = os.path.join(NM, "@fontsource", "sora", "files", "sora-latin-400-normal.woff")
PLEX = os.path.join(NM, "@fontsource", "ibm-plex-mono", "files", "ibm-plex-mono-latin-400-normal.woff")


def _quad(p0, c, p1, n=8):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in (k / n for k in range(1, n + 1))]


def _cubic(p0, c1, c2, p1, n=10):
    return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t * t * c2[0] + t ** 3 * p1[0],
             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t * t * c2[1] + t ** 3 * p1[1]) for t in (k / n for k in range(1, n + 1))]


class TypefaceFont:
    """three.js typeface.json (Helvetiker). Konturkommandoer: m x y · l x y · q cx cy x y · b c1x c1y c2x c2y x y · z."""
    def __init__(self, path):
        self.f = json.load(open(path)); self.res = self.f["resolution"]; self.g = self.f["glyphs"]
        self.cap = next((self._bbox(ch)[3] for ch in "HI" if ch in self.g), 0.72 * self.res)

    def _polys(self, ch):
        g = self.g.get(ch) or self.g.get("?"); toks = g.get("o", "").split(); i = 0; polys = []; cur = []; last = None
        while i < len(toks):
            c = toks[i]
            if c == "m":
                if len(cur) > 2: polys.append(cur)
                last = (float(toks[i + 1]), float(toks[i + 2])); cur = [last]; i += 3
            elif c == "l":
                last = (float(toks[i + 1]), float(toks[i + 2])); cur.append(last); i += 3
            elif c == "q":
                p1 = (float(toks[i + 1]), float(toks[i + 2])); cc = (float(toks[i + 3]), float(toks[i + 4]))
                cur += _quad(last, cc, p1); last = p1; i += 5
            elif c == "b":
                p1 = (float(toks[i + 1]), float(toks[i + 2])); c1 = (float(toks[i + 3]), float(toks[i + 4])); c2 = (float(toks[i + 5]), float(toks[i + 6]))
                cur += _cubic(last, c1, c2, p1); last = p1; i += 7
            elif c == "z":
                if len(cur) > 2: polys.append(cur)
                cur = []; i += 1
            else:
                i += 1
        if len(cur) > 2: polys.append(cur)
        return polys, g["ha"]

    def _bbox(self, ch):
        pts = [p for poly in self._polys(ch)[0] for p in poly]
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

    def text(self, s, cap_mm, x, y, tracking=0.0, align="c"):
        """Polygoner for teksten (versalhøyde cap_mm, (x, y) = senter av tekstlinjen). Returnerer (polygoner, bredde)."""
        k = cap_mm / self.cap
        items = [self._polys(ch) for ch in s]
        adv = [ha * k + tracking for _, ha in items]
        w = sum(adv) - tracking
        x0 = x - w / 2 if align == "c" else x
        out = []
        for (polys, _), a in zip(items, adv):
            for poly in polys:
                out.append([(x0 + px * k, y - cap_mm / 2 + py * k) for px, py in poly])
            x0 += a
        return out, w


class WoffFont:
    """woff/ttf via fontTools (Sora, IBM Plex Mono)."""
    def __init__(self, path):
        from fontTools.ttLib import TTFont
        self.f = TTFont(path); self.upm = self.f["head"].unitsPerEm; self.gs = self.f.getGlyphSet(); self.cmap = self.f.getBestCmap()
        self.cap = self.f["OS/2"].sCapHeight or 0.7 * self.upm

    def text(self, s, cap_mm, x, y, tracking=0.0, align="c"):
        from fontTools.pens.basePen import BasePen

        class FlatPen(BasePen):
            def __init__(self, gs): super().__init__(gs); self.polys = []; self.cur = []
            def _moveTo(self, p): self.cur = [p]
            def _lineTo(self, p): self.cur.append(p)
            def _curveToOne(self, c1, c2, p1): self.cur += _cubic(self.cur[-1], c1, c2, p1)
            def _qCurveToOne(self, c, p1): self.cur += _quad(self.cur[-1], c, p1)
            def _closePath(self):
                if len(self.cur) > 2: self.polys.append(self.cur)
                self.cur = []
            _endPath = _closePath

        k = cap_mm / self.cap
        glyphs = [self.cmap.get(ord(ch), self.cmap.get(ord("?"))) for ch in s]
        adv = [self.gs[g].width * k + tracking for g in glyphs]
        w = sum(adv) - tracking
        x0 = x - w / 2 if align == "c" else x
        out = []
        for g, a in zip(glyphs, adv):
            pen = FlatPen(self.gs); self.gs[g].draw(pen)
            for poly in pen.polys:
                out.append([(x0 + px * k, y - cap_mm / 2 + py * k) for px, py in poly])
            x0 += a
        return out, w


def rrect(cx, cy, w, h, r, n=8):
    pts = []
    for sx, sy, a0 in ((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)):
        for j in range(n + 1):
            a = math.radians(a0 + 90 * j / n)
            pts.append((cx + sx * (w / 2 - r) + r * math.cos(a), cy + sy * (h / 2 - r) + r * math.sin(a)))
    return pts


def circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def ring(cx, cy, r_out, r_in):
    """Lukket polygon for en ring (ytre + indre kontur motsatt vei) – fungerer med even-odd."""
    return circle(cx, cy, r_out) + circle(cx, cy, r_in)[::-1]


def hp_icon(cx, cy, s=0.9):
    """Hodetelefon-ikon: bøyle (halvring) + to øreklokker."""
    outer = [(cx + 2 * s * math.cos(a), cy + 2 * s * math.sin(a)) for a in (math.pi * i / 16 for i in range(17))]
    inner = [(cx + 1.4 * s * math.cos(a), cy + 1.4 * s * math.sin(a)) for a in (math.pi * (16 - i) / 16 for i in range(17))]
    return [outer + inner] + [rrect(cx + sx * 1.7 * s, cy - 0.6 * s, 1.1 * s, 1.9 * s, 0.3 * s) for sx in (-1, 1)]


def dxf(layers):
    """layers = [(navn, [polygon, …]), …] -> DXF-tekst med lukkede LWPOLYLINE-er (mm)."""
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


def read_dxf_polys(path):
    """Leser lukkede LWPOLYLINE-er: [(lag, [(x, y), …]), …]."""
    import re
    s = open(path).read(); out = []
    for e in re.findall(r"\n0\nLWPOLYLINE\n(.*?)(?=\n0\n)", s, flags=re.S):
        e = "\n" + e
        lay = re.search(r"\n8\n([^\n]+)", e).group(1)
        xs = [float(v) for v in re.findall(r"\n10\n([-\d.eE+]+)", e)]; ys = [float(v) for v in re.findall(r"\n20\n([-\d.eE+]+)", e)]
        out.append((lay, list(zip(xs, ys))))
    return out


def preview(path_png, size_wh, layers, scale=16, bg=(26, 26, 28)):
    """PNG: lag med navn ENGRAVE/MARKING fylles lyst (even-odd), resten tegnes som tynne linjer."""
    try:
        from PIL import Image, ImageDraw
        import numpy as np
    except ImportError:
        return
    pts = [q for _, polys in layers for p in polys for q in p]
    x0, x1, y0, y1 = min(q[0] for q in pts), max(q[0] for q in pts), min(q[1] for q in pts), max(q[1] for q in pts)
    W, H = x1 - x0, y1 - y0; img = Image.new("RGB", (int(W * scale) + 40, int(H * scale) + 40), bg); d = ImageDraw.Draw(img)
    tr = lambda p: (20 + (p[0] - x0) * scale, 20 + (y1 - p[1]) * scale)
    acc = np.zeros((img.size[1], img.size[0]), dtype=np.int32)
    for name, polys in layers:
        for p in polys:
            if name in ("ENGRAVE", "MARKING"):
                m = Image.new("L", img.size, 0); ImageDraw.Draw(m).polygon([tr(q) for q in p], fill=1); acc += np.array(m, dtype=np.int32)
            else:
                d.line([tr(q) for q in p] + [tr(p[0])], fill=(110, 110, 114), width=2)
    px = np.array(img); px[acc % 2 == 1] = (210, 212, 215); Image.fromarray(px).save(path_png)
