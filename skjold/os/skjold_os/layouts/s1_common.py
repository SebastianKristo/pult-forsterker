"""Felles for Skjold S1: 1-bit-lerret, pikselfont og overleggene fra overlay() i
skjold/design/s1/pultforsterker_revb_metall.js.

overlay() er tegnet i et 128×64-koordinatsystem. OLED-en bruker det direkte (1-bit), TFT-en tegner det samme
skalert 2,5× inn i 320×160 fra y=40 (som designet: g.translate(0,40); g.scale(2.5,2.5); overlay(g)).
Alle tegnefunksjonene her tar derfor et lerret c i 128×64 logiske px; c.mono sier om det er OLED-en.
"""
import math
from functools import lru_cache
from PIL import ImageFont
from ..gfx import Canvas, W, BLACK, TRACK, hexc, mix, FONT_FILES, _find
from .. import fx, sources

DM = hexc("#8b8b86")           # designets Dm
OFF3 = hexc("#3a3a37")
GREY55 = hexc("#55554f")
MONO_T = 64                    # luminans over dette = tent piksel


# ---------------------------------------------------------------- 1-bit-lerret
class MonoCanvas(Canvas):
    """Lerret for SSD1309: ingen supersampling, tekst uten kantutjevning, terskel til rent svart/hvitt i frame().
    Grått fra designet (Dm, mix(W,a)) blir tent over MONO_T, spor (#2a2a28) blir slukket – spor tegnes derfor
    eksplisitt prikket med dots()."""
    mono = True

    def __init__(self, w=128, h=64):
        super().__init__(w, h, ss=1); self.d.fontmode = "1"

    def font(self, weight, px): return _mono_font(weight, int(round(px)))   # eksakte px, ingen FONT_SCALE

    def text(self, x, y, s, col, weight="regular", px=10, anchor="ls", ls=0.0):
        """Som Canvas.text, men startpunktet rundes til hel piksel (ellers forskyves glyfene ujevnt på 1-bit)."""
        if not s: return 0
        w = self.text_w(s, weight, px, ls); ax = anchor[0]
        x0 = int(round(x - (w / 2 if ax == "m" else w if ax == "r" else 0)))
        return super().text(x0, int(round(y)), s, col, weight, px, "l" + anchor[1], ls)

    def dim(self, a):
        super().dim(a); self.d.fontmode = "1"

    def frame(self):
        return self.img.convert("L").point(lambda v: 255 if v > MONO_T else 0).convert("RGB")


@lru_cache(maxsize=64)
def _mono_font(weight, px):
    """BASIC-layout: hele piksel-fremrykk (Raqm gir brøkdels-posisjoner som ser hakkete ut uten kantutjevning)."""
    p = _find(FONT_FILES.get(weight, FONT_FILES["regular"]))
    try: return ImageFont.truetype(p, max(1, px), layout_engine=ImageFont.Layout.BASIC) if p else ImageFont.load_default()
    except OSError: return ImageFont.load_default()


def is_mono(c): return getattr(c, "mono", False)


# ---------------------------------------------------------------- pikselfont (versaler, 5 px høy)
# Til de små versal-etikettene designet setter i «bold 6px» med 1px sperring (OMSTART, BLÅTANN, VOL, 3/6 …).
# DejaVu under 8 px blir uleselig uten kantutjevning; denne er tegnet for rutenettet.
_G = {
    "A": ".#.|#.#|###|#.#|#.#", "B": "##.|#.#|##.|#.#|##.", "C": ".##|#..|#..|#..|.##", "D": "##.|#.#|#.#|#.#|##.",
    "E": "###|#..|##.|#..|###", "F": "###|#..|##.|#..|#..", "G": ".##|#..|#.#|#.#|.##", "H": "#.#|#.#|###|#.#|#.#",
    "I": "#|#|#|#|#", "J": "..#|..#|..#|#.#|.#.", "K": "#.#|#.#|##.|#.#|#.#", "L": "#..|#..|#..|#..|###",
    "M": "#...#|##.##|#.#.#|#...#|#...#", "N": "#..#|##.#|#.##|#..#|#..#", "O": ".##.|#..#|#..#|#..#|.##.",
    "P": "##.|#.#|##.|#..|#..", "Q": ".##.|#..#|#..#|#.#.|.#.#", "R": "##.|#.#|##.|#.#|#.#", "S": ".##|#..|.#.|..#|##.",
    "T": "###|.#.|.#.|.#.|.#.", "U": "#.#|#.#|#.#|#.#|###", "V": "#.#|#.#|#.#|#.#|.#.", "W": "#...#|#...#|#.#.#|##.##|#...#",
    "X": "#.#|#.#|.#.|#.#|#.#", "Y": "#.#|#.#|.#.|.#.|.#.", "Z": "###|..#|.#.|#..|###",
    "Æ": ".####|#.#..|####.|#.#..|#.###", "Ø": ".###.|#..##|#.#.#|##..#|.###.", "Å": "^.#.|.#.|#.#|###|#.#|#.#",
    "Ü": "^#.#|...|#.#|#.#|#.#|###", "Ö": "^#.#|...|.#.|#.#|#.#|.#.", "Ä": "^#.#|...|.#.|#.#|###|#.#",
    "0": "###|#.#|#.#|#.#|###", "1": ".#|##|.#|.#|.#", "2": "##.|..#|.#.|#..|###", "3": "##.|..#|.#.|..#|##.",
    "4": "#.#|#.#|###|..#|..#", "5": "###|#..|##.|..#|##.", "6": ".##|#..|###|#.#|###", "7": "###|..#|.#.|.#.|.#.",
    "8": "###|#.#|###|#.#|###", "9": "###|#.#|###|..#|##.",
    " ": "..|..|..|..|..", "·": ".|.|#|.|.", ".": ".|.|.|.|#", ",": ".|.|.|#|#", ":": ".|#|.|#|.", "/": "..#|..#|.#.|#..|#..",
    "-": "...|...|###|...|...", "–": "...|...|###|...|...", "—": "....|....|####|....|....", "%": "#.#|..#|.#.|#..|#.#",
    "?": "##.|..#|.#.|...|.#.", "!": "#|#|#|.|#", "+": "...|.#.|###|.#.|...", "'": "#|#|.|.|.", "(": ".#|#.|#.|#.|.#",
    ")": "#.|.#|.#|.#|#.", "›": "#..|.#.|..#|.#.|#..", "‹": "..#|.#.|#..|.#.|..#", "&": ".#..|#.#.|.#.#|#.#.|.#.#",
    "«": ".....|.#.#.|#.#..|.#.#.|.....", "»": ".....|.#.#.|..#.#|.#.#.|.....", "_": "...|...|...|...|###",
    "…": ".....|.....|.....|.....|#.#.#",
}
_GLYPH = {}
for _k, _v in _G.items():
    rows = _v.split("|"); acc = rows[0].startswith("^")
    if acc: rows[0] = rows[0][1:]
    _GLYPH[_k] = ([(x, y - (2 if acc else 0)) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == "#"], len(rows[-1]))


def pix_w(s, sp=1):
    s = s.upper(); return sum(_GLYPH.get(ch, _GLYPH["?"])[1] for ch in s) + sp * max(0, len(s) - 1)


def pix_text(c, x, y, s, col, anchor="l", sp=1):
    """Pikselfont: y = grunnlinje (glyfene står på rad y-5..y-1). anchor l/m/r."""
    s = s.upper(); w = pix_w(s, sp)
    x0 = int(round(x - (w / 2 if anchor == "m" else w if anchor == "r" else 0))); y0 = int(round(y)) - 5
    for ch in s:
        pts, gw = _GLYPH.get(ch, _GLYPH["?"])
        for px, py in pts: c.d.point((x0 + px, y0 + py), fill=col)
        x0 += gw + sp
    return w


def pix_fit(s, maxw):
    s = s.upper()
    if pix_w(s) <= maxw: return s
    while s and pix_w(s + "…") > maxw: s = s[:-1]
    return s.rstrip(" ·") + "…"


def cap(c, x, y, s, col=DM, anchor="l", ls=1.0, px=6):
    """Designets små versaler («bold 6px», letterSpacing 1px). OLED: pikselfont; TFT: DejaVu Bold."""
    if is_mono(c): return pix_text(c, x, y, s, W if col != BLACK else BLACK, anchor)
    return c.text(x, y, s.upper(), col, "bold", px, anchor + "s", ls)


def cap_w(c, s, ls=1.0, px=6): return pix_w(s) if is_mono(c) else c.text_w(s.upper(), "bold", px, ls)


def cap_fit(c, s, maxw, px=6):
    return pix_fit(s, maxw) if is_mono(c) else c.ellipsize(s.upper(), "bold", px, maxw, 1)


def txt(c, x, y, s, col, weight="regular", px=7, anchor="ls"):
    """Brødtekst. OLED: DejaVu uten kantutjevning, minst 8 px (6–7 px i designet er uleselig på 1-bit)."""
    if is_mono(c): px = max(8, px + (1 if px < 9 else 0))
    return c.text(x, y, s, col, weight, px, anchor)


def txt_fit(c, s, weight, px, maxw):
    if is_mono(c): px = max(8, px + (1 if px < 9 else 0))
    return c.ellipsize(s, weight, px, maxw)


def hline(c, x, y, w, col=TRACK):
    """Skillelinje/spor (#2a2a28, 0.6 px). OLED: prikket 1 px (annenhver piksel), ellers som designet."""
    if is_mono(c):
        for i in range(int(x), int(x + w), 2): c.d.point((i, int(y)), fill=W)
    else:
        c.rect(x, y, w, max(0.6, 0.6), col)


def track(c, x, y, w, h, p, col=W, tcol=TRACK):
    """Fremdrift: spor + fyll. OLED: sporet er en prikket underkant, fyllet er hel."""
    if is_mono(c):
        y1 = int(y + h) - 1
        for i in range(int(x), int(x + w), 2): c.d.point((i, y1), fill=W)
        if p > 0: c.rect(int(x), int(y), max(1, int(round(w * p))), max(1, int(round(h))), W)
    else:
        c.rect(x, y, w, h, tcol)
        if p > 0: c.rect(x, y, w * p, h, col)


def spinner(c, cx, cy, r, dot, now_ms, col=W):
    if is_mono(c):   # 8 prikker, tre «lyse» som går rundt
        hd = int(now_ms / 140) % 8
        for k in range(8):
            if (hd - k) % 8 < 3:
                an = k / 8 * math.pi * 2; c.d.point((int(round(cx + math.cos(an) * r)), int(round(cy + math.sin(an) * r))), fill=W)
        return
    for k in range(8):
        an = k / 8 * math.pi * 2 + now_ms / 140; op = 0.2 + 0.8 * ((k / 8 + now_ms / 1120) % 1)
        c.circle(cx + math.cos(an) * r, cy + math.sin(an) * r, dot, mix(col, op))


def check(c, pts, col=W, width=1.4):
    if is_mono(c):
        c.d.line([(int(x), int(y)) for x, y in pts], fill=col, width=2, joint="curve")
    else:
        c.line(pts, col, width)


def spk(c, x, y, k, muted, col=W):
    """Høyttalerikon (spk i designet), ferdig animert."""
    P = lambda px, py: (x + px * k, y + py * k)
    c.poly([P(-6, -2.5), P(-3, -2.5), P(1.5, -6.5), P(1.5, 6.5), P(-3, 2.5), P(-6, 2.5)], col)
    lw = max(1, 1.3 * k)
    if muted:
        c.line([P(4, -3), P(10, 3)], col, lw); c.line([P(10, -3), P(4, 3)], col, lw)
    else:
        for r in (3.5, 6.5, 9.5): c.arc(x + 1.5 * k, y, r * k, -0.75, 0.75, col, lw)


# ---------------------------------------------------------------- overleggene (128×64)
def draw_reboot(c, t, now_ms):
    """S.rebootT: CRT-kollaps 380 ms, så tre steg à 900 ms (fx.RB totalt)."""
    c.clear()
    if t < 380:
        u = t / 380; h = max(1 if is_mono(c) else 0.6, 26 * (1 - u * u)); w = 124 * (1 if u < 0.7 else 1 - (u - 0.7) / 0.3)
        c.rect(64 - w / 2, 32 - h / 2, w, h, mix(W, 0.9)); return
    T = t - 380; fade = max(0, min(1, T / 250, (3420 - T) / 300)); A = lambda col: mix(col, fade)
    cap(c, 4, 8, "OMSTART", A(DM)); hline(c, 4, 11, 120)
    D = 900; cur = min(3, int(T // D))
    for i, l in enumerate(fx.REBOOT_STEPS):
        y = 23 + i * 11; done, act = i < cur, i == cur
        if done: check(c, [(5, y - 3), (7, y - 1), (10.5, y - 5.5)], A(W), 1.2)
        elif act: spinner(c, 7.7, y - 3.3, 2.6, 0.55, now_ms, A(W))
        elif is_mono(c): c.d.point((8, y - 3), fill=W)
        else: c.circle(7.7, y - 3.3, 1, A(OFF3))
        col = W if done or act else (W if is_mono(c) else GREY55)
        txt(c, 15, y, l, A(col), "bold" if act else "regular", 7)
    p = min(1, T / (3 * D)); track(c, 4, 56, 120, 2, 1 - (1 - p) ** 2)


def draw_pair(c, t, p, name):
    """S.pairT: pulserende ringer rundt BT-runen, «Paring…», synlig som, fremdrift."""
    c.clear(); cap(c, 4, 8, "BLÅTANN")
    cx, cy = 22, 34
    for i in range(3):
        r = ((t * 1.2 + i / 3) % 1) * 20
        if is_mono(c):
            if r > 2 and r < 18 and i != 2: c.circle(cx, cy, r, outline=W, width=1)
        else: c.circle(cx, cy, r, outline=mix(W, 1 - r / 20), width=1)
    fx.ico_bt(c, cx, cy, 1.0, W) if not is_mono(c) else \
        c.d.line([(cx - 4, cy - 4), (cx + 4, cy + 4), (cx, cy + 8), (cx, cy - 8), (cx + 4, cy - 4), (cx - 4, cy + 4)], fill=W, width=1)
    txt(c, 44, 28, "Paring" + "..."[:1 + int(t * 2) % 3], W, "bold", 9)
    txt(c, 44, 39 if is_mono(c) else 38, txt_fit(c, "Synlig som «%s»" % name, "regular", 6, 82), DM, "regular", 6)
    txt(c, 44, 48 if is_mono(c) else 47, "Hold igjen = avbryt", DM, "regular", 6)
    track(c, 44, 53, 78, 3 if is_mono(c) else 2.5, min(1, p))


def _gear(c, cx, cy, ang, col):
    for k in range(8):
        a = ang + (k + 1) * math.pi / 4; ca, sa = math.cos(a), math.sin(a)
        pts = [(-1.2, -6.2), (1.2, -6.2), (1.2, -3.6), (-1.2, -3.6)]
        c.poly([(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts], col)
    c.circle(cx, cy, 4.6, col); c.circle(cx, cy, 1.9, BLACK)


def draw_hold(c, vm):
    """S.knobHoldT: ring som fylles + tannhjul, tittel/undertittel. Med hold_saved: «Lagret» (saveT) med hake."""
    c.clear()
    if vm.get("hold_saved") is not None:
        st = vm.get("saved_t", 1.0); u = min(1, st / 0.22); e = 1 - (1 - u) ** 3
        if is_mono(c):
            ox = 0 if e >= 1 else 0
            check(c, [(56 + ox, 24), (62 + ox, 30), (73 + ox, 18)]) if e > 0.4 else c.d.point((62, 30), fill=W)
        else:
            s = 0.6 + 0.4 * e; acc = vm.get("accent") or W
            pts = [(64 + (x - 64) * s, 24 + (y - 24) * s) for x, y in ((56, 24), (62, 30), (73, 18))]
            c.line(pts, mix(acc, e), 1.4)
        txt(c, 64, 45, txt_fit(c, vm.get("hold_title") or "Lagret", "bold", 8, 124), W, "bold", 8, "ms")
        txt(c, 64, 56 if is_mono(c) else 55, txt_fit(c, vm.get("hold_sub") or "", "regular", 6, 124), DM, "regular", 6, "ms")
        return
    p = max(0.0, min(1.0, vm.get("hold_p", 1.0))); cx, cy = 64, 26
    if is_mono(c):
        for k in range(0, 360, 12):   # prikket spor
            a = math.radians(k); c.d.point((int(round(cx + math.cos(a) * 11)), int(round(cy + math.sin(a) * 11))), fill=W)
        if p > 0: c.arc(cx, cy, 12, -math.pi / 2, -math.pi / 2 + p * 2 * math.pi, W, 2)
    else:
        c.circle(cx, cy, 11, outline=TRACK, width=2)
        if p > 0: c.arc(cx, cy, 12, -math.pi / 2, -math.pi / 2 + p * 2 * math.pi, W, 2)
    _gear(c, cx, cy, p * math.pi, W)
    txt(c, 64, 50, txt_fit(c, vm.get("hold_title", ""), "bold", 8, 124), W, "bold", 8, "ms")
    txt(c, 64, 60 if is_mono(c) else 59, txt_fit(c, vm.get("hold_sub", ""), "regular", 6, 124), DM, "regular", 6, "ms")


def draw_menu(c, vm):
    """S.set.open: overskrift + 4 rader à 12,5 px, valgt rad invertert, rullefelt."""
    rows, idx, head = vm["menu_rows"], vm["menu_idx"], vm.get("menu_head") or "INNSTILLINGER"
    if head == "RADIO": return draw_radio_menu(c, vm)
    c.clear(); cap(c, 4, 8, cap_fit(c, head, 90))
    if len(rows) > 1: cap(c, 124, 8, "%d/%d" % (idx + 1, len(rows)), DM, "r")
    hline(c, 4, 11, 120)
    vis = 4; first = max(0, min(len(rows) - vis, idx - 1)); mono = is_mono(c)
    for r in range(vis):
        i = first + r
        if i >= len(rows): break
        it = rows[i]; y = 14 + r * 12.5; on = i == idx
        if mono: y = 13 + r * 13   # hele piksler: 13,26,39,52 (rad = 12 høy)
        if on: c.rrect(2, y, 118 if len(rows) > vis else 122, 12 if mono else 11.5, 2, W)
        fg = BLACK if on else W
        v = str(it.get("v", "")); vx = 116 if len(rows) > vis else 120
        vw = c.text_w(v, "bold" if mono else "bold", 8 if mono else 7) if v else 0
        nm = txt_fit(c, it.get("n", ""), "bold" if on else "regular", 7, vx - 6 - vw - 6)
        by = y + (9 if mono else 8.3)
        txt(c, 6, by, nm, fg, "bold" if on else "regular", 7)
        if v: txt(c, vx, by, v, BLACK if on else (W if mono else DM), "regular" if mono and not on else "bold", 7, "rs")
    if len(rows) > vis:
        sh = 50 * vis / len(rows); y0 = 14 + first * (50 - sh) / (len(rows) - vis)
        if mono:
            for yy in range(14, 64, 2): c.d.point((124, yy), fill=W)
            c.rect(123, int(y0), 3, max(3, int(sh)), W)
        else:
            c.rect(123.5, 14, 1.5, 50, TRACK); c.rect(123.5, y0, 1.5, sh, W)


def draw_radio_menu(c, vm):
    """Radio-knappen (S.input===2 && menuT): valgt favoritt stor i invertert boks, naboer over/under, prikker til høyre."""
    rows, idx = vm["menu_rows"], vm["menu_idx"]; n = len(rows); c.clear()
    cap(c, 4, 8, "RADIO"); cap(c, 118, 8, "FAVORITT %d AV %d" % (idx + 1, n), DM, "r"); hline(c, 4, 11, 114)
    for d_, y in ((-1, 22), (1, 59)):
        p = idx + d_
        if 0 <= p < n:
            txt(c, 6, y, str(p + 1), DM, "regular", 7); txt(c, 16, y, txt_fit(c, rows[p]["n"], "regular", 7, 100), DM, "regular", 7)
    y0 = 26 if is_mono(c) else 27
    c.rrect(2, y0, 116, 23 if is_mono(c) else 22, 2, W)
    it = rows[idx]
    txt(c, 6, y0 + 10, str(idx + 1), BLACK, "bold", 7)
    txt(c, 16, y0 + 11 if is_mono(c) else y0 + 10, txt_fit(c, it["n"], "bold", 10, 100), BLACK, "bold", 10)
    sub = it.get("sub") or ("Spiller nå" if it.get("v") else "")
    if sub:
        if is_mono(c): pix_text(c, 16, y0 + 20, pix_fit(sub, 98), BLACK)
        else: txt(c, 16, y0 + 18, sub, BLACK, "regular", 6)
    for i in range(min(n, 6)):
        on = i == idx
        if is_mono(c): c.rect(122, 15 + i * 8, 2, 6 if on else 2, W) if on else c.rect(122, 17 + i * 8, 2, 2, W)
        else: c.rect(122, 15 + i * 8, 2.4, 6 if on else 3, W if on else OFF3)


def _ring_icon(c, key, x, y, k, col):
    if is_mono(c) and sources.src(key)["ico"] == "bt":
        s = k; P = lambda a, b: (int(round(x + a * s)), int(round(y + b * s)))
        c.d.line([P(-4, -4), P(4, 4), P(0, 8), P(0, -8), P(4, -4), P(-4, 4)], fill=col, width=max(1, int(round(1.3 * k))))
    else:
        fx.icon(c, key, x, y, k, col)


def draw_switch(c, t, ring, frm, to, sub):
    """Kildebytte (S.wlT-animasjonen i overlay(), generalisert til alle kilder): ikonene glir 34 px per steg,
    det aktive er stort og lyst, navn + undertekst nederst."""
    u = min(1, t / 230); e = 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2; fo = min(1, (fx.SW - t) / 180)
    c.clear(); cc = frm + (to - frm) * e; mono = is_mono(c)
    for i, key in enumerate(ring):
        v = i - cc; d = 1 - min(1, abs(v))
        if abs(v) > 2: continue
        a = 1 if mono else fo * (0.25 + 0.75 * d)
        if mono and d <= 0.5 and abs(v) > 1.4: continue
        _ring_icon(c, key, 64 + v * 34, 25, 0.9 + 0.5 * d, mix(W if d > 0.5 else DM, a))
    ta = fo * min(1, max(0, (t - 120) / 120)); s = sources.src(ring[to])
    if ta > (0.3 if mono else 0):
        if mono: txt(c, 64, 50, s["k"], W, "bold", 9, "ms")
        else: c.text(64, 50, s["k"], mix(W, ta), "bold", 9, "ms", 1)
        txt(c, 64, 60 if mono else 59, txt_fit(c, sub or s["sub"], "regular", 6, 124), mix(DM, ta), "regular", 6, "ms")


def draw_offline(c, now_ms, secs, clock):
    """Ingen kontakt med ki-amp (ikke i S1-designet): samme formspråk som feilmeldingene (S.err)."""
    c.clear()
    if is_mono(c):
        c.d.line([(64, 9), (75, 28), (53, 28), (64, 9)], fill=W, width=1)
        c.rect(64, 15, 1, 8, W); c.rect(64, 25, 1, 1, W)
    else:
        c.line([(64, 9), (75, 28), (53, 28), (64, 9)], W, 1.4); c.rect(63.3, 15, 1.4, 7, W); c.rect(63.3, 23.6, 1.4, 1.6, W)
    txt(c, 64, 42, "Ingen kontakt", W, "bold", 9, "ms")
    txt(c, 64, 52, "Lydtjenesten svarer ikke", DM, "regular", 6, "ms")
    if secs >= 1:
        s = "%s · %d s" % (clock, secs)
        if is_mono(c): pix_text(c, 64, 62, s, W, "m")
        else: txt(c, 64, 61, s, mix(DM, 0.7), "regular", 6, "ms")


def splash(c, ms, model="S1"):
    """drawSplash: stolpene vokser inn én etter én, så SKJOLD + STREAMING AMPLIFIER (2,6 s)."""
    w, h = c.w, c.h; t = ms / fx.BOOT; c.clear(); mono = is_mono(c)
    tw0 = c.text_w("SKJOLD", "bold", 13, 2); unit = 41 * 0.62 + 6 + tw0
    sc = min(w * 0.78 / unit, h * 0.5 / (42 * 0.62)); k = sc * 0.62; mw = 41 * k
    tw = c.text_w("SKJOLD", "bold", 13 * sc, 2 * sc); gap = 6 * sc; x0 = (w - (mw + gap + tw)) / 2; y0 = h / 2 - 21 * k
    for i, (x, bh) in enumerate(fx.BARS):
        a = max(0, min(1, t * 5 - i * 0.45))
        if a > 0:
            if mono: c.rect(int(round(x0 + x * k)), int(round(y0)), max(2, int(round(4.6 * k))), max(1, int(round(bh * k * a))), W)
            else: c.rrect(x0 + x * k, y0, 4.6 * k, bh * k * a, 2.3 * k, mix(W, a))
    ta = max(0, min(1, (t - 0.45) * 3))
    if mono and ta < 0.5: return
    c.text(x0 + mw + gap, h / 2 - 2 * sc, "SKJOLD", mix(W, ta), "bold", 13 * sc, "lm", 2 * sc)
    if mono: pix_text(c, x0 + mw + gap + 1, int(h / 2 + 9 * sc + 3.5), "STREAMING AMP", W)
    else: c.text(x0 + mw + gap + 1, h / 2 + 9 * sc, "STREAMING AMPLIFIER", mix(DM, ta), "mono", 3.6 * sc, "lm", 1.1 * sc)
