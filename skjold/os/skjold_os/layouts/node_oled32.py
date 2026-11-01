"""Skjold Node, OLED-utgave: 0,91″ SSD1306 128×32, 1-bit. Fra drawScreen() i
skjold/design/node/Skjold Node kasse OLED.html (og «… OLED taktil.html»):

  topplinje   KILDE (+ «II» på pause) ................ 12:34      (designet: bold 7px, y=7)
  midten      tittel stor (bold 11px, y=19) – ruller sidelengs når den er for lang
  bunn        undertittel / artist (7px, y=30)
  volum       «VOL 42» / «LYD AV» (bold 9px, y=20) + ramme 125×5 med fyll (y=24,5) i 1,5 s når potmeteret vris
  oppstart    logo-stolpene + SKJOLD + «N O D E»   omstart: «Starter på nytt» + fremdrift   velkomst: tre linjer

Resten (kildebytte, paring, hold/«Lagret», meny, klokke, ingen kontakt) er ikke i designet og er laget i samme
formspråk på 32 px høyde: én topplinje i pikselfonten (s1_common) og to linjer under. Alt tegnes rett på
pikselrutenettet (MonoCanvas: ingen kantutjevning, terskel i frame()).
"""
import math
from .base import Layout
from .s1_common import MonoCanvas, txt, txt_fit, pix_text, pix_fit, pix_w, check, spinner
from .. import fx, sources
from ..gfx import W, BLACK

SCROLL_PX_S = 22      # rulletekst: piksler per sekund
SCROLL_WAIT = 1.6     # pause i starten av hver runde (s)
SCROLL_GAP = 28       # mellomrom før teksten kommer igjen (px)


def _bars(c, x0, y0, k, a=1.0):
    """Logoen (fem stolper) med høyde k·bh, voksende med a (0–1)."""
    for i, (x, bh) in enumerate(fx.BARS):
        ai = max(0.0, min(1.0, a * 5 - i * 0.45)) if a < 1 else 1.0
        h = int(round(bh * k * ai))
        if h > 0: c.rect(int(round(x0 + x * k)), int(round(y0)), max(2, int(round(4.6 * k))), h, W)


def _bt(c, cx, cy, s=1.0):
    P = lambda a, b: (int(round(cx + a * s)), int(round(cy + b * s)))
    c.d.line([P(-3, -3), P(3, 3), P(0, 6), P(0, -6), P(3, -3), P(-3, 3)], fill=W, width=1)


def _dots_ring(c, x, y, r, p):
    """Prikket ring + hel bue for fremdriften p (0–1)."""
    for k in range(0, 360, 15):
        a = math.radians(k); c.d.point((int(round(x + math.cos(a) * r)), int(round(y + math.sin(a) * r))), fill=W)
    if p > 0: c.arc(x, y, r + 1, -math.pi / 2, -math.pi / 2 + p * 2 * math.pi, W, 2)


class NodeOled32Layout(Layout):
    W, H, SS, MONO, name = 128, 32, 1, True, "node-oled32"
    OUT_W, OUT_H = 128, 32

    def canvas(self): return MonoCanvas(self.W, self.H)

    def render(self, vm):
        c = self.canvas()
        getattr(self, "draw_" + vm["screen"], self.draw_off)(c, vm)
        return c.frame()

    # ---------- felles ----------
    def top(self, c, left, right=""):
        """Topplinje i pikselfonten (grunnlinje y=6)."""
        rw = pix_w(right) if right else 0
        pix_text(c, 1, 6, pix_fit(left, 126 - rw - (6 if right else 0)), W)
        if right: pix_text(c, 127, 6, right, W, "r")

    def scroll_text(self, c, vm, s, weight, px, y, x=1, maxw=126):
        """Tekst som ruller når den er bredere enn maxw. Setter vm['anim'] så app.Ui tegner raskt."""
        mpx = max(8, px)
        w = c.text_w(s, weight, mpx)
        if w <= maxw:
            txt(c, x, y, s, W, weight, px); return
        vm["anim"] = True
        period = w + SCROLL_GAP; t = vm["now_ms"] / 1000.0
        cyc = SCROLL_WAIT + period / SCROLL_PX_S
        u = (t - vm.get("scroll_t0", 0.0)) % cyc
        off = 0 if u < SCROLL_WAIT else int((u - SCROLL_WAIT) * SCROLL_PX_S)
        # klipp til [x, x+maxw]: tegn på et eget lerret og lim inn
        sub = MonoCanvas(int(maxw), self.H)
        txt(sub, -off, y, s, W, weight, px)
        if off > period - maxw: txt(sub, -off + period, y, s, W, weight, px)
        c.img.paste(sub.img, (int(x), 0), sub.img.convert("L").point(lambda v: 255 if v > 64 else 0))

    def vol(self, c, vm):
        """Volum-overlegget fra designet: tekst + ramme med fyll."""
        v, m = vm["volume"], vm["mute"]
        c.rect(0, 8, 128, 24, BLACK)
        txt(c, 1, 20, "LYD AV" if (m or v == 0) else "VOL %d" % v, W, "bold", 9)
        c.d.rectangle([1, 24, 126, 29], outline=W)
        n = 0 if m else int(round(122 * v / 100))
        if n > 0: c.rect(3, 26, n, 2, W)

    # ---------- spiller nå ----------
    def draw_play(self, c, vm):
        kick = vm["kicker"] or sources.src(vm["input"])["k"]
        if vm.get("paused"): kick = kick + "  II"
        elif vm["mute"]: kick = kick + "  MUTE"
        self.top(c, kick, vm["clock"])
        if vm.get("vol_overlay"): return self.vol(c, vm)
        self.scroll_text(c, vm, vm["title"] or "", "bold", 11, 19)
        sub = vm.get("sub") or vm.get("bottom") or ""
        if vm["input"] == "radio" and vm.get("preset_idx", -1) >= 0:
            n = len(vm.get("presets") or []) or 6; pos = "%d/%d" % (vm["preset_idx"] + 1, n)
            txt(c, 1, 30, txt_fit(c, sub, "regular", 8, 124 - pix_w(pos) - 4), W, "regular", 8)
            pix_text(c, 127, 30, pos, W, "r")
        elif vm.get("duration"):
            p = max(0.0, min(1.0, vm["position"] / vm["duration"]))
            txt(c, 1, 29, txt_fit(c, sub, "regular", 8, 126), W, "regular", 8)
            for i in range(1, 127, 2): c.d.point((i, 31), fill=W)
            if p > 0: c.rect(1, 31, max(1, int(round(126 * p))), 1, W)
        else:
            txt(c, 1, 30, txt_fit(c, sub, "regular", 8, 126), W, "regular", 8)

    def draw_volume(self, c, vm): self.vol(c, vm)

    # ---------- animasjoner ----------
    def draw_boot(self, c, vm):
        """Designet: stolpene (k=24/42) ved x=30, SKJOLD (bold 12) ved x=58, «N O D E» under."""
        t = vm["t_ms"] / fx.BOOT; c.clear(); k = 24 / 42
        _bars(c, 30, 4, k, min(1.0, t * 1.0) if t < 1 else 1.0)
        if t < 0.45: return
        c.text(58, 17, "SKJOLD", W, "bold", 12, "ls")
        pix_text(c, 59, 26, "N O D E" if vm.get("model", "NODE") == "NODE" else vm.get("model", ""), W)

    def draw_reboot(self, c, vm):
        t = vm["t_ms"]; c.clear()
        if t < 380:   # CRT-kollaps
            u = t / 380; h = max(1, int(round(14 * (1 - u * u)))); w = 124 * (1 if u < 0.7 else 1 - (u - 0.7) / 0.3)
            c.rect(int(64 - w / 2), 16 - h // 2, max(1, int(w)), h, W); return
        txt(c, 64, 14, "Starter på nytt", W, "bold", 9, "ms")
        p = ((t - 380) / 1800.0) % 1
        for i in range(34, 94, 2): c.d.point((i, 23), fill=W)
        c.rect(34, 22, max(1, int(60 * p)), 2, W)

    def draw_switch(self, c, vm):
        """Kildebytte: navnet glir inn fra siden der den nye kilden ligger i ringen, prikker for posisjonen."""
        t, ring, frm, to = vm["t_ms"], vm["ring"], vm["sw_from"], vm["sw_to"]
        u = min(1.0, t / 230); e = 1 - (1 - u) ** 3; d = 1 if to >= frm else -1
        c.clear(); pix_text(c, 1, 6, "KILDE", W)
        x = 127
        for i in reversed(range(len(ring))):
            on = i == to
            if on: c.rect(x - 5, 2, 5, 3, W); x -= 8
            else: c.rect(x - 1, 3, 2, 1, W); x -= 5
        s_new, s_old = sources.src(ring[to]), sources.src(ring[frm])
        off = int(round((1 - e) * 60 * d))
        if e < 1 and frm != to: txt(c, 1 - int(round(e * 60 * d)), 20, s_old["n"], W, "bold", 11)
        txt(c, 1 + off, 20, s_new["n"], W, "bold", 11)
        if t > 150: txt(c, 1, 30, txt_fit(c, vm.get("sw_sub") or s_new["sub"], "regular", 8, 126), W, "regular", 8)
        if vm.get("vol_overlay"): self.vol(c, vm)

    def draw_welcome(self, c, vm):
        """Velkomst: konfetti, tittel i pikselfont, navnet stort, blinkende hint etter 3 s.
        Uten hilsen (førstegangs-oppsett) – designets tre linjer."""
        w = vm.get("welcome") or {}; t = vm["t_ms"] / 1000; c.clear()
        if not w.get("navn") and not w.get("tittel"):
            txt(c, 1, 9, "Velkommen", W, "bold", 9)
            txt(c, 1, 20, txt_fit(c, w.get("hint") or "Åpne Skjold-appen", "regular", 8, 126), W, "regular", 8)
            txt(c, 1, 30, "for oppsett", W, "regular", 8); return
        for i in range(10):
            sp = 0.35 + fx._rnd(i, 1) * 0.5; x = int(fx._rnd(i, 2) * 128 + math.sin(t * 1.6 + i) * 4)
            y = int(((fx._rnd(i, 3) * 1.2 + t * sp) % 1.2 - 0.1) * 32)
            c.d.point((x, y), fill=W)
        title = pix_fit(w.get("tittel") or "Gratulerer med dagen", 124); tw = pix_w(title)
        c.rect(64 - tw // 2 - 2, 0, tw + 4, 8, BLACK); pix_text(c, 64, 6, title, W, "m")
        if t > 0.5:
            name = w.get("navn") or ""; px = 14 if c.text_w(name, "bold", 14) <= 124 else 11
            nw = c.text_w(name, "bold", px); c.rect(64 - nw / 2 - 2, 9, nw + 4, 15, BLACK)
            txt(c, 64, 22, txt_fit(c, name, "bold", px, 124), W, "bold", px, "ms")
        if t > 3 and int((t - 3) * 1.5) % 2 == 0:
            hint = "TRYKK EN KNAPP"; hw = pix_w(hint); c.rect(64 - hw // 2 - 2, 25, hw + 4, 7, BLACK); pix_text(c, 64, 31, hint, W, "m")

    # ---------- Blåtann-paring ----------
    def draw_pair(self, c, vm):
        t, p = vm["pair_t"], max(0.0, min(1.0, vm["pair_p"]))
        c.clear(); pix_text(c, 1, 6, "BLÅTANN", W)
        for i in range(70, 127, 2): c.d.point((i, 4), fill=W)
        c.rect(70, 3, max(1, int(57 * p)), 3, W)
        cx, cy = 8, 21
        r = int(((t * 1.2) % 1) * 7) + 5
        if r < 11: c.circle(cx, cy, r, outline=W, width=1)
        _bt(c, cx, cy, 1.0)
        txt(c, 20, 19, "Paring" + "..."[:1 + int(t * 2) % 3], W, "bold", 9)
        txt(c, 20, 30, txt_fit(c, "Synlig som «%s»" % vm["name"], "regular", 8, 106), W, "regular", 8)

    # ---------- hold-fremdrift / «Lagret» ----------
    def draw_hold(self, c, vm):
        c.clear(); cx, cy = 14, 16
        if vm.get("hold_saved") is not None:
            st = vm.get("saved_t", 1.0); k = min(1.0, st / 0.22)
            r = int(round(11 * k))
            if r > 0: c.circle(cx, cy, r, W)
            if st > 0.12: check(c, [(cx - 5, cy), (cx - 1, cy + 4), (cx + 5, cy - 4)], BLACK)
        else:
            p = max(0.0, min(1.0, vm.get("hold_p", 1.0)))
            _dots_ring(c, cx, cy, 11, p)
            if p >= 1: check(c, [(cx - 5, cy), (cx - 1, cy + 4), (cx + 5, cy - 4)], W)
        txt(c, 31, 15, txt_fit(c, vm.get("hold_title") or ("Lagret" if vm.get("hold_saved") is not None else ""), "bold", 10, 96), W, "bold", 10)
        txt(c, 31, 28, txt_fit(c, vm.get("hold_sub") or "", "regular", 8, 96), W, "regular", 8)

    # ---------- meny (2 rader) ----------
    def draw_menu(self, c, vm):
        rows, idx, head = vm["menu_rows"], vm["menu_idx"], vm.get("menu_head") or "INNSTILLINGER"
        c.clear(); n = len(rows)
        self.top(c, head, "%d/%d" % (idx + 1, n) if n > 1 else "")
        first = max(0, min(n - 2, idx)) if n > 1 else 0
        for r in range(2):
            i = first + r
            if i >= n: break
            it = rows[i]; y = 8 + r * 12; on = i == idx
            if on: c.rect(0, y, 128, 12, W)
            fg = BLACK if on else W
            name = it.get("n", "")
            if head == "RADIO" and it.get("icon"): name = "%s  %s" % (it["icon"], name)
            v = str(it.get("v", "")); vw = c.text_w(v, "regular", 8) if v else 0
            txt(c, 3, y + 9, txt_fit(c, name, "bold" if on else "regular", 8, 122 - vw - (6 if v else 0)), fg, "bold" if on else "regular", 8)
            if v: txt(c, 125, y + 9, v, fg, "regular", 8, "rs")

    # ---------- standby-klokke ----------
    def draw_clock(self, c, vm):
        d = vm["now"]; hm = "%02d:%02d" % (d.hour, d.minute)
        if vm.get("clock_style", 0) % 6 == 1:   # «Stor»: bare klokka
            txt(c, 64, 29, hm, W, "bold", 30, "ms"); return
        txt(c, 64, 22, hm, W, "bold", 22, "ms")
        pix_text(c, 64, 31, pix_fit(fx.date_long(d), 126), W, "m")

    # ---------- ingen kontakt ----------
    def draw_offline(self, c, vm):
        c.clear()
        c.d.line([(8, 3), (15, 16), (1, 16), (8, 3)], fill=W, width=1); c.rect(8, 7, 1, 5, W); c.rect(8, 14, 1, 1, W)
        txt(c, 21, 13, "Ingen kontakt", W, "bold", 9)
        txt(c, 1, 27, "Lydtjenesten svarer ikke", W, "regular", 8)
        spinner(c, 122, 8, 3, 0.6, vm["now_ms"])
        if vm.get("offline_s", 0) >= 1: pix_text(c, 127, 31, "%d S" % vm["offline_s"], W, "r")
