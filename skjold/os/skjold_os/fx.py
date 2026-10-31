"""Animasjoner og felles tegninger, oversatt fra design/node/node_fx.js, felles/skjold_welcome.js
og drawClock i felles/skjold_settings.js. Alle tar et gfx.Canvas og tid i ms."""
import math, datetime
from .gfx import W, DIM, TRACK, BLACK, KHAKI, hexc, mix
from . import sources

# ---------- ikoner (logiske koordinater rundt (x,y), skala k) ----------
def ico_air(c, x, y, k, col):
    P = lambda px, py: (x + px * k, y + py * k)
    c.line([P(-3, 4), P(-7, 4), P(-8, 3), P(-8, -6), P(-7, -7), P(7, -7), P(8, -6), P(8, 3), P(7, 4), P(3, 4)], col, 1.2 * k)
    c.poly([P(0, 1), P(5, 8), P(-5, 8)], col)

def ico_bt(c, x, y, k, col):
    P = lambda px, py: (x + px * k, y + py * k)
    c.line([P(-4, -4), P(4, 4), P(0, 8), P(0, -8), P(4, -4), P(-4, 4)], col, 1.3 * k)

def ico_radio(c, x, y, k, col):
    c.circle(x, y, 1.8 * k, col)
    for r in (4.5, 7.5):
        c.arc(x, y, r * k, -0.7, 0.7, col, 1.2 * k); c.arc(x, y, r * k, math.pi - 0.7, math.pi + 0.7, col, 1.2 * k)

def ico_spotify(c, x, y, k, col):
    c.circle(x, y, 8 * k, outline=col, width=1.2 * k)
    for i, (r, dy) in enumerate(((6, -1.5), (4.6, 1.2), (3.4, 3.6))):
        c.arc(x, y + dy * k + r * k, r * k, math.pi * 1.25, math.pi * 1.75, col, (1.3 - i * 0.15) * k)

def ico_aux(c, x, y, k, col):
    P = lambda px, py: (x + px * k, y + py * k)
    c.circle(x, y + 3 * k, 4.5 * k, outline=col, width=1.2 * k)
    c.line([P(0, -8), P(0, 3)], col, 1.6 * k); c.rect(x - 1.6 * k, y - 4 * k, 3.2 * k, 1.2 * k, col)

def ico_usb(c, x, y, k, col):
    P = lambda px, py: (x + px * k, y + py * k)
    c.line([P(0, 8), P(0, -6)], col, 1.2 * k); c.poly([P(0, -9), P(2.4, -5.5), P(-2.4, -5.5)], col)
    c.line([P(0, 4), P(-4.5, 0), P(-4.5, -2.5)], col, 1.2 * k); c.circle(x - 4.5 * k, y - 3 * k, 1.3 * k, col)
    c.line([P(0, 2), P(4.5, -1.5), P(4.5, -3)], col, 1.2 * k); c.rect(x + 3.2 * k, y - 5.5 * k, 2.6 * k, 2.6 * k, col)

ICONS = {"air": ico_air, "bt": ico_bt, "radio": ico_radio, "spotify": ico_spotify, "aux": ico_aux, "usb": ico_usb}

def icon(c, key, x, y, k, col): ICONS.get(sources.src(key)["ico"], ico_aux)(c, x, y, k, col)

# ---------- logo (fem stolper 22/33/42/33/22, bredde 4,6) ----------
BARS = [(0, 22), (9, 33), (18.7, 42), (28.4, 33), (36.4, 22)]

# ---------- oppstart ----------
BOOT = 2600
def splash(c, ms, name="NODE"):
    w, h = c.w, c.h; t = ms / BOOT; c.clear()
    tw0 = c.text_w("SKJOLD", "bold", 13, 2)
    unit = 41 * 0.62 + 6 + tw0; sc = min(w * 0.84 / unit, h * 0.5 / (42 * 0.62))
    k = sc * 0.62; mw = 41 * k; tw = c.text_w("SKJOLD", "bold", 13 * sc, 2 * sc); gap = 6 * sc
    x0 = (w - (mw + gap + tw)) / 2; y0 = h / 2 - 21 * k - 4
    for i, (x, bh) in enumerate(BARS):
        a = max(0, min(1, t * 5 - i * 0.45))
        if a > 0: c.rrect(x0 + x * k, y0, 4.6 * k, bh * k * a, 2.3 * k, mix(W, a))
    ta = max(0, min(1, (t - 0.45) * 3))
    c.text(x0 + mw + gap, h / 2 - 4 - 2 * sc, "SKJOLD", mix(W, ta), "bold", 13 * sc, "lm", 2 * sc)
    c.text(x0 + mw + gap + 1, h / 2 - 4 + 10.5 * sc, name, mix(DIM, ta), "mono", 4.6 * sc, "lm", 1.6 * sc)
    p = max(0, min(1, (t - 0.6) / 0.4))
    c.rect(40, 104, 80, 2, mix(TRACK, ta)); c.rect(40, 104, 80 * p, 2, mix(W, ta))
    return ms < BOOT

# ---------- omstart ----------
RB = 380 + 3420
REBOOT_STEPS = ["Stopper lydtjenester", "Starter Raspberry Pi", "Kobler til Lyrion"]
def reboot(c, ms, now_ms, steps=REBOOT_STEPS):
    c.clear()
    if ms < 380:   # CRT-kollaps
        u = ms / 380; hh = max(0.6, 40 * (1 - u * u)); ww = 156 * (1 if u < 0.7 else 1 - (u - 0.7) / 0.3)
        c.rect(80 - ww / 2, 64 - hh / 2, ww, hh, mix(W, 0.9)); return True
    if ms >= RB: return False
    T = ms - 380; fade = max(0, min(1, T / 250, (3420 - T) / 300)); A = lambda col: mix(col, fade)
    c.text(8, 14, "OMSTART", A(DIM), "bold", 7, "ls", 1); c.rect(7, 17, 146, 0.6, A(TRACK))
    D = 900; cur = min(3, int(T // D))
    for i, l in enumerate(steps):
        y = 38 + i * 17; done, act, cx = i < cur, i == cur, 11.7
        if done: c.line([(cx - 2.7, y - 3.3), (cx - 0.7, y - 1.3), (cx + 2.8, y - 5.8)], A(W), 1.3)
        elif act:
            for kk in range(8):
                an = kk / 8 * math.pi * 2 + now_ms / 140; op = 0.2 + 0.8 * ((kk / 8 + now_ms / 1120) % 1)
                c.circle(cx + math.cos(an) * 3, y - 3.5 + math.sin(an) * 3, 0.65, A(mix(W, op)))
        else: c.circle(cx, y - 3.5, 1.1, A(hexc("#3a3a37")))
        c.text(22, y, l, A(W if done or act else hexc("#55554f")), "bold" if act else "regular", 10)
    p = min(1, T / (3 * D)); c.rect(7, 112, 146, 2, A(TRACK)); c.rect(7, 112, 146 * (1 - (1 - p) ** 2), 2, A(W))
    return True

# ---------- kildebytte ----------
SW = 950
def switch_src(c, ms, ring, frm, to, sub=""):
    """ring = liste med input-nøkler, frm/to = indekser i ring."""
    if ms >= SW: return False
    u = min(1, ms / 230); e = 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2; fo = min(1, (SW - ms) / 180)
    c.clear(); cc = frm + (to - frm) * e
    for i, key in enumerate(ring):
        v = i - cc; d = 1 - min(1, abs(v)); a = fo * max(0, 0.25 + 0.75 * d - max(0, abs(v) - 1) * 0.6)
        if a <= 0.01 or abs(v) > 2.2: continue
        icon(c, key, 80 + v * 48, 48, 1.8 + 1.0 * d, mix(W if d > 0.5 else DIM, a))
    ta = fo * min(1, max(0, (ms - 120) / 120)); s = sources.src(ring[to])
    c.text(80, 96, s["k"], mix(W, ta), "bold", 14, "ms", 1.5)
    c.text(80, 110, sub or s["sub"], mix(DIM, ta), "regular", 9, "ms")
    return True

# ---------- velkomst (felles/skjold_welcome.js) ----------
COLS = [hexc(x) for x in ("#e8893a", "#4a8cff", "#f2f2ee", "#d8cfb4", "#e85a6a")]
def _rnd(i, k): x = math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - math.floor(x)

def welcome(c, ms, title="Gratulerer med dagen", name="Pappa", hint="Trykk en knapp for å starte", mono=False):
    w, h = c.w, c.h; s = min(w / 160, h / 128 * 1.25); wide = w / h > 1.7; t = ms / 1000; c.clear()
    N = 26 if mono else 46
    for i in range(N):
        sp = 0.35 + _rnd(i, 1) * 0.5; x = _rnd(i, 2) * w + math.sin(t * 1.6 + i) * 6 * s
        y = ((_rnd(i, 3) * 1.2 + t * sp) % 1.2 - 0.1) * h; a = t * 3 + i; sz = (1.4 + _rnd(i, 4) * 1.8) * s
        al = min(1, t * 2) * (0.8 if mono else 0.95); col = mix(W if mono else COLS[i % len(COLS)], al)
        hw, hh = sz / 2, (sz * 0.6 * abs(math.cos(a)) + 0.4) / 2; ca, sa = math.cos(a), math.sin(a)
        c.poly([(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))], col)
    k = (0.32 if wide else 0.42) * s; bx = w / 2 - 20.5 * k; by = h * (0.12 if wide else 0.14); inn = min(1, t / 0.6)
    for i, (x, bh) in enumerate(BARS):
        dance = 0.65 + 0.35 * abs(math.sin(t * 4.2 + i * 0.9))
        if inn > 0: c.rrect(bx + x * k, by, 4.6 * k, bh * k * dance * inn, 2.3 * k, mix(W, inn))
    ta = max(0, min(1, (t - 0.5) / 0.5)); ty = (1 - ta) * 6 * s
    tY = h * (0.62 if wide else 0.58); nY = h * (0.86 if wide else 0.80)
    c.text(w / 2, tY + ty, title, mix(DIM if mono else KHAKI, ta), "bold", (6.5 if wide else 9) * s, "ms", (0.6 if wide else 0.8) * s)
    nb = max(0, min(1, (t - 0.9) / 0.45)); pop = 1 + 0.25 * math.sin(nb * math.pi) if nb < 1 else 1
    if nb > 0: c.text(w / 2, nY, name, mix(W, nb), "bold", (17 if wide else 26) * s * pop, "ms")
    if t > 3:
        p = 0.45 + 0.55 * (0.5 + 0.5 * math.sin((t - 3) * 3))
        c.text(w / 2, h - (1.5 if wide else 4) * s, hint, mix(DIM, p * (0.9 if mono else 1)), "regular", (4.6 if wide else 6.5) * s, "ms")

# ---------- standby-klokker (felles/skjold_settings.js drawClock, 128×64 logisk) ----------
CLOCKS = ["Tynn", "Stor", "Analog", "Ord", "Linje", "Dato"]
HW = ["tolv", "ett", "to", "tre", "fire", "fem", "seks", "sju", "åtte", "ni", "ti", "elleve", "tolv"]
DAYS = ["søndag", "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag"]
MON = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]

def jsday(d): return (d.weekday() + 1) % 7   # JS getDay(): 0 = søndag

def word_time(d):
    m = round(d.minute / 5) * 5 % 60; h0 = d.hour + (1 if d.minute >= 58 else 0); h = h0 % 12
    n = HW[12 if h == 0 else h]; n1 = HW[12 if (h + 1) % 12 == 0 else (h + 1) % 12]
    return [("klokka er", n), ("fem over", n), ("ti over", n), ("kvart over", n), ("ti på halv", n1), ("fem på halv", n1),
            ("halv", n1), ("fem over halv", n1), ("ti over halv", n1), ("kvart på", n1), ("ti på", n1), ("fem på", n1)][m // 5]

def date_long(d): return f"{DAYS[jsday(d)]} {d.day}. {MON[d.month - 1]}"

def draw_clock(c, style, d, color=(90, 90, 85), still=False):
    k = c.w / 128; oy = (c.h - 64 * k) / 2; mi = d.minute
    dx = 0 if still else ((mi % 5) - 2) * 1.5; dy = 0 if still else ((mi % 3) - 1) * 1.5
    X = lambda x: (x + dx) * k; Y = lambda y: oy + (y + dy) * k
    hh, mm = f"{d.hour:02d}", f"{mi:02d}"; C = color
    if style == 0: c.text(X(64), Y(40), hh + ":" + mm, C, "light", 22 * k, "ms")
    elif style == 1: c.text(X(64), Y(47), hh + ":" + mm, C, "bold", 40 * k, "ms")
    elif style == 2:
        cx, cy, r = X(40), Y(32), 24 * k
        c.circle(cx, cy, r, outline=C, width=k)
        for i in range(12):
            a = i / 12 * math.pi * 2; l = (2 if i % 3 else 4) * k; r1 = r - 1.5 * k
            c.line([(cx + math.sin(a) * r1, cy - math.cos(a) * r1), (cx + math.sin(a) * (r1 - l), cy - math.cos(a) * (r1 - l))], C, k)
        ha = ((d.hour % 12) + mi / 60) / 12 * math.pi * 2; ma = mi / 60 * math.pi * 2
        c.line([(cx, cy), (cx + math.sin(ha) * 12 * k, cy - math.cos(ha) * 12 * k)], C, 2.4 * k)
        c.line([(cx, cy), (cx + math.sin(ma) * 19 * k, cy - math.cos(ma) * 19 * k)], C, 1.4 * k)
        c.circle(cx, cy, 1.6 * k, C)
        c.text(X(74), Y(30), DAYS[jsday(d)][:3].capitalize(), C, "bold", 9 * k)
        c.text(X(74), Y(41), f"{d.day}. {MON[d.month - 1][:3]}", C, "regular", 8 * k)
    elif style == 3:
        a, b = word_time(d); c.text(X(64), Y(28), a, C, "light", 11 * k, "ms"); c.text(X(64), Y(45), b, C, "bold", 15 * k, "ms")
    elif style == 4:
        p = (d.hour * 60 + mi) / 1440; c.rect(X(8), Y(40), 112 * k, 0.8 * k, C)
        for i in range(0, 25, 6): c.rect(X(8 + 112 * i / 24 - 0.4), Y(37.5), 0.8 * k, 5 * k, C)
        c.circle(X(8 + 112 * p), Y(40.4), 2.4 * k, C)
        c.text(X(8 + 112 * p), Y(31), hh + ":" + mm, C, "regular", 10 * k, "rs" if p > 0.75 else "ls" if p < 0.25 else "ms")
    else:
        c.text(X(64), Y(34), hh + ":" + mm, C, "light", 26 * k, "ms")
        c.text(X(64), Y(48), date_long(d).capitalize(), C, "regular", 8 * k, "ms")
