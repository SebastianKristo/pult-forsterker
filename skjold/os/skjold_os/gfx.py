"""Tegnemotoren: et Pillow-lerret i logiske piksler (CSS-px fra designet) med supersampling.

Alt tegnes på et bilde som er SS ganger større og skaleres ned med LANCZOS – det gir
kantutjevning som i nettleser-canvasen designet er laget i. Alfa løses ved å blande mot
bakgrunnen (skjermen er svart nesten overalt), så vi slipper RGBA-komposittering.
"""
import math, os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

# ---- design-tokens (skjold/design/README.md + Node OS.dc.html) ----
W = (242, 242, 238)        # tekst lys på enheten (#f2f2ee)
DIM = (139, 139, 134)      # #8b8b86
DIM2 = (180, 180, 174)     # #b4b4ae (undertittel)
TRACK = (42, 42, 40)       # #2a2a28 (spor/linjer)
OFFDOT = (58, 58, 56)      # #3a3a38
BLACK = (0, 0, 0)
KHAKI = (216, 207, 180)    # #d8cfb4

def hexc(s):
    s = s.lstrip("#"); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

def mix(c, a, bg=BLACK):
    a = max(0.0, min(1.0, a)); return tuple(int(round(bg[i] + (c[i] - bg[i]) * a)) for i in range(3))

# ---- fonter: Helvetica Neue i designet, DejaVu Sans (fonts-dejavu-core) på Pi-en ----
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF"]
FONT_FILES = {
    "regular": ["HelveticaNeue.ttf", "Arial.ttf", "DejaVuSans.ttf"],
    "light": ["HelveticaNeue-Light.ttf", "DejaVuSans-ExtraLight.ttf", "DejaVuSans.ttf"],
    "bold": ["HelveticaNeue-Bold.ttf", "Arial-Bold.ttf", "DejaVuSans-Bold.ttf"],
    "mono": ["IBMPlexMono-Medium.ttf", "DejaVuSansMono.ttf"],
}
# DejaVu er bredere enn Helvetica; krymp litt så linjebrytning/plass stemmer med designet.
FONT_SCALE = float(os.environ.get("SKJOLD_FONT_SCALE", "0.9"))

def _find(names):
    extra = os.environ.get("SKJOLD_FONT_DIR")
    for n in names:
        for d in ([extra] if extra else []) + FONT_DIRS:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None

@lru_cache(maxsize=256)
def font(weight, px):
    p = _find(FONT_FILES.get(weight, FONT_FILES["regular"]))
    try:
        return ImageFont.truetype(p, max(1, int(round(px)))) if p else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


class Canvas:
    """Lerret i logiske piksler. c.img (full oppløsning) hentes med c.frame()."""
    def __init__(self, w, h, ss=3, bg=BLACK):
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new("RGB", (w * ss, h * ss), bg)
        self.d = ImageDraw.Draw(self.img)

    def _p(self, v): return v * self.ss
    def _box(self, x, y, w, h):
        s = self.ss; x0, y0 = x * s, y * s
        return [x0, y0, max(x0, (x + w) * s - 1), max(y0, (y + h) * s - 1)]

    def clear(self, col=BLACK): self.d.rectangle([0, 0, self.img.width, self.img.height], fill=col)

    def rect(self, x, y, w, h, col):
        if w > 0 and h > 0: self.d.rectangle(self._box(x, y, w, h), fill=col)

    def rrect(self, x, y, w, h, r, col=None, outline=None, width=1):
        if w * self.ss < 1 or h * self.ss < 1: return
        r = max(0, min(r, w / 2, h / 2))
        self.d.rounded_rectangle(self._box(x, y, w, h), radius=int(r * self.ss), fill=col, outline=outline,
                                 width=max(1, int(width * self.ss)))

    def circle(self, cx, cy, r, col=None, outline=None, width=1):
        s = self.ss
        self.d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=col, outline=outline,
                       width=max(1, int(width * s)))

    def line(self, pts, col, width=1.0, joint="curve"):
        s = self.ss; self.d.line([(x * s, y * s) for x, y in pts], fill=col, width=max(1, int(round(width * s))), joint=joint)
        r = width * s / 2   # runde ender (lineCap round)
        for x, y in (pts[0], pts[-1]):
            self.d.ellipse([x * s - r, y * s - r, x * s + r, y * s + r], fill=col)

    def poly(self, pts, col): s = self.ss; self.d.polygon([(x * s, y * s) for x, y in pts], fill=col)

    def arc(self, cx, cy, r, a0, a1, col, width=1.0):
        """a0/a1 i radianer, canvas-konvensjon (0 = høyre, med klokka)."""
        s = self.ss
        self.d.arc([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], math.degrees(a0), math.degrees(a1),
                   fill=col, width=max(1, int(round(width * s))))

    def pie(self, cx, cy, r, a0, a1, col):
        s = self.ss
        self.d.pieslice([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], math.degrees(a0), math.degrees(a1), fill=col)

    # ---- tekst ----
    def font(self, weight, px): return font(weight, px * self.ss * FONT_SCALE)

    def text_w(self, s, weight, px, ls=0.0):
        f = self.font(weight, px)
        if not ls: return f.getlength(s) / self.ss
        return sum(f.getlength(ch) for ch in s) / self.ss + ls * max(0, len(s) - 1)

    def text(self, x, y, s, col, weight="regular", px=10, anchor="ls", ls=0.0):
        """anchor: x-del l/m/r, y-del s (grunnlinje), m (midt), t (topp) – som Pillow."""
        if not s: return 0
        f = self.font(weight, px); w = self.text_w(s, weight, px, ls)
        ax = anchor[0]; x0 = x - (w / 2 if ax == "m" else w if ax == "r" else 0)
        va = anchor[1]; pa = "l" + ("s" if va == "s" else "m" if va == "m" else "a")
        if not ls:
            self.d.text((x0 * self.ss, y * self.ss), s, fill=col, font=f, anchor=pa)
        else:
            cx = x0 * self.ss
            for ch in s:
                self.d.text((cx, y * self.ss), ch, fill=col, font=f, anchor=pa)
                cx += f.getlength(ch) + ls * self.ss
        return w

    def ellipsize(self, s, weight, px, maxw, ls=0.0):
        if self.text_w(s, weight, px, ls) <= maxw: return s
        while s and self.text_w(s + "…", weight, px, ls) > maxw: s = s[:-1]
        return s.rstrip() + "…"

    def wrap(self, s, weight, px, maxw, lines=2):
        words, out, cur = (s or "").split(), [], ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if self.text_w(t, weight, px) <= maxw or not cur: cur = t
            else:
                out.append(cur); cur = wd
        if cur: out.append(cur)
        if len(out) > lines:
            out = out[:lines]; out[-1] = self.ellipsize(out[-1] + " …", weight, px, maxw)
        return [self.ellipsize(l, weight, px, maxw) for l in out]

    # ---- bilder ----
    def gradient_tile(self, x, y, w, h, r, c0, c1):
        """linear-gradient(135deg, c0, c1) med avrundede hjørner."""
        s = self.ss; W_, H_ = int(w * s), int(h * s)
        v = Image.linear_gradient("L"); g = Image.blend(v, v.transpose(Image.TRANSPOSE), 0.5).resize((W_, H_))
        tile = Image.composite(Image.new("RGB", (W_, H_), c1), Image.new("RGB", (W_, H_), c0), g)
        self.paste_rounded(tile, x, y, r)

    def paste_rounded(self, im, x, y, r):
        s = self.ss; m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=int(r * s), fill=255)
        self.img.paste(im, (int(x * s), int(y * s)), m)

    def image(self, im, x, y, w, h, r=0):
        im = im.convert("RGB").resize((int(w * self.ss), int(h * self.ss)), Image.LANCZOS)
        if r: self.paste_rounded(im, x, y, r)
        else: self.img.paste(im, (int(x * self.ss), int(y * self.ss)))

    def dim(self, a):
        """Ton hele lerretet mot svart (globalAlpha på en ferdig ramme)."""
        if a < 1: self.img = Image.blend(Image.new("RGB", self.img.size, BLACK), self.img, max(0.0, a)); self.d = ImageDraw.Draw(self.img)

    def frame(self):
        return self.img if self.ss == 1 else self.img.resize((self.w, self.h), Image.LANCZOS)
