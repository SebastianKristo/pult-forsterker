"""Skjold S1 med 2,42″ SSD1309 OLED, 128×64 monokrom. drawOLED0 + overlay() i
skjold/design/s1/pultforsterker_revb_metall.js, tegnet rett på pikselrutenettet (1-bit, ingen kantutjevning).

Hierarkiet i designet (W mot Dm-grå) kan ikke vises på 1-bit; det bæres av vekt/størrelse og pikselfonten
for versal-etikettene. Spor (#2a2a28) er prikkede linjer.
"""
import math
from .base import Layout
from .s1_common import (MonoCanvas, DM, cap, cap_fit, txt, txt_fit, pix_text, pix_fit, pix_w, hline, track,
                        draw_reboot, draw_pair, draw_hold, draw_menu, draw_switch, draw_offline, splash)
from .. import fx
from ..gfx import W, BLACK

# faner i designet: INPUTS = AIR (AirPlay · BT), AUX, RADIO, USB
TAB = {"airplay": "AIR", "bt": "AIR", "spotify": "AIR", "aux": "AUX", "aux2": "AUX", "radio": "RADIO", "usb": "USB"}
DEFAULT_TABS = ["AIR", "AUX", "RADIO", "USB"]

SPK_MUTE = ["..#.....", ".##.#.#.", "###..#..", ".##.#.#.", "..#....."]
HEADPH = [".###.", "#...#", "#...#", "##.##", "##.##"]


def bitmap(c, x, y, rows, col=W):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#": c.d.point((x + i, y + j), fill=col)


def tabs_for(vm):
    ins = vm.get("inputs")
    if not ins: return DEFAULT_TABS
    out = []
    for i in ins:
        t = TAB.get(i, (i or "?").upper()[:5])
        if t not in out: out.append(t)
    return [t for t in DEFAULT_TABS if t in out] + [t for t in out if t not in DEFAULT_TABS]


def fmt(sec): sec = max(0, int(sec)); return "%d:%02d" % (sec // 60, sec % 60)


class S1OledLayout(Layout):
    W, H, SS, MONO, name = 128, 64, 1, True, "s1-oled"
    OUT_W, OUT_H = 128, 64

    def canvas(self): return MonoCanvas(self.W, self.H)

    def render(self, vm):
        c = self.canvas()
        getattr(self, "draw_" + vm["screen"], self.draw_off)(c, vm)
        return c.frame()

    # ---------- animasjoner ----------
    def draw_boot(self, c, vm): splash(c, vm["t_ms"], vm.get("model", "S1"))
    def draw_reboot(self, c, vm): draw_reboot(c, vm["t_ms"], vm["now_ms"])
    def draw_switch(self, c, vm):
        draw_switch(c, vm["t_ms"], vm["ring"], vm["sw_from"], vm["sw_to"], vm.get("sw_sub", ""))
        if vm.get("vol_overlay"): self.vol_bar(c, vm)
    def draw_welcome(self, c, vm):
        """skjold_welcome.js i mono-utgave for 128×64: få konfetti-piksler, dansende logo, tittel i pikselfont,
        navnet stort, blinkende hint etter 3 s."""
        w = vm.get("welcome") or {}; t = vm["t_ms"] / 1000; c.clear()
        for i in range(18):
            sp = 0.35 + fx._rnd(i, 1) * 0.5; x = int(fx._rnd(i, 2) * 128 + math.sin(t * 1.6 + i) * 4)
            y = int(((fx._rnd(i, 3) * 1.2 + t * sp) % 1.2 - 0.1) * 64)
            c.rect(x, y, 2 if int(t * 3 + i) % 2 else 1, 1 if int(t * 3 + i) % 2 else 2, W)
        inn = min(1, t / 0.6)
        for i, (x, bh) in enumerate(fx.BARS):
            h = max(1, int(round(bh * 0.24 * (0.65 + 0.35 * abs(math.sin(t * 4.2 + i * 0.9))) * inn)))
            c.rect(57 + i * 3, 2, 2, h, W)
        title = pix_fit(w.get("tittel") or "Gratulerer med dagen", 124); tw = pix_w(title)
        if t > 0.5:
            c.rect(64 - tw // 2 - 2, 20, tw + 4, 9, BLACK); pix_text(c, 64, 27, title, W, "m")
        if t > 0.9:
            name = w.get("navn") or "Pappa"; px = 18 if c.text_w(name, "bold", 18) <= 120 else 13
            nw = c.text_w(name, "bold", px); c.rect(64 - nw / 2 - 2, 33, nw + 4, 17, BLACK)
            txt(c, 64, 48, txt_fit(c, name, "bold", px, 124), W, "bold", px, "ms")
        if t > 3 and int((t - 3) * 1.5) % 2 == 0:
            hint = "TRYKK EN KNAPP"; hw = pix_w(hint); c.rect(64 - hw // 2 - 2, 55, hw + 4, 9, BLACK); pix_text(c, 64, 62, hint, W, "m")

    def draw_pair(self, c, vm): draw_pair(c, vm["pair_t"], vm["pair_p"], vm["name"])
    def draw_hold(self, c, vm): draw_hold(c, vm)
    def draw_menu(self, c, vm): draw_menu(c, vm)
    def draw_offline(self, c, vm): draw_offline(c, vm["now_ms"], vm.get("offline_s", 0), vm["clock"])

    def draw_clock(self, c, vm):   # felles klokkestiler, 128×64 er designets egen størrelse; full lysstyrke på 1-bit
        fx.draw_clock(c, vm.get("clock_style", 0) % 6, vm["now"], color=W, still=False)

    # ---------- topplinje: faner + status ----------
    def top(self, c, vm):
        cur = TAB.get(vm["input"], (vm["input"] or "?").upper()[:5]); x = 2
        for t in tabs_for(vm):
            w = pix_w(t) + 6
            if t == cur:
                c.rect(x, 1, w, 9, W); pix_text(c, x + 3, 8, t, BLACK)
            else:
                pix_text(c, x + 3, 8, t, W)
            x += w + 3
        rx = 127
        if vm.get("mute"): bitmap(c, rx - 8, 3, SPK_MUTE); rx -= 11
        if vm.get("headphones"): bitmap(c, rx - 5, 3, HEADPH)

    def vol_bar(self, c, vm):
        """volBar: VOL + 24 segmenter + tall (y 52–59). Ubrukte segmenter = én prikk i bunnen."""
        c.rect(0, 50, 128, 14, BLACK)
        v, m = vm["volume"], vm["mute"]
        pix_text(c, 2, 59, "MUTE" if m else "VOL", W)
        on = 0 if m else round(v / 100 * 22)
        for i in range(22):
            x = 21 + i * 4
            if i < on: c.rect(x, 52, 3, 7, W)
            else: c.d.point((x + 1, 58), fill=W)
        txt(c, 127, 59, "—" if m else str(v), W, "bold", 8, "rs")

    # ---------- spiller nå (drawOLED0) ----------
    def draw_play(self, c, vm):
        self.top(c, vm); i = vm["input"]; now = vm["now_ms"]
        if i == "radio":
            n = len(vm.get("presets") or []) or 6
            left = vm["kicker"] if vm.get("preset_idx", -1) < 0 else vm["kicker"]
            pix_text(c, 2, 19, pix_fit(left, 100), W)
            if vm.get("preset_idx", -1) >= 0: pix_text(c, 126, 19, "%d/%d" % (vm["preset_idx"] + 1, n), W, "r")
            txt(c, 2, 35, txt_fit(c, vm["title"], "bold", 12, 124), W, "bold", 12)
            txt(c, 2, 46, txt_fit(c, vm["sub"], "regular", 8, 124), W, "regular", 8)
            if vm.get("vol_overlay"): self.vol_bar(c, vm); return
            hline(c, 2, 51, 124)
            if not vm.get("paused") and int(now / 700) % 2 == 0: c.circle(4.5, 58.5, 2, W)
            elif vm.get("paused"): c.rect(3, 56, 1, 5, W); c.rect(5, 56, 1, 5, W)
            else: c.circle(4.5, 58.5, 2, outline=W)
            pix_text(c, 10, 61, "MUTE" if vm["mute"] else ("PAUSE" if vm.get("paused") else "DIREKTE"), W)
            pix_text(c, 126, 61, "LYRION", W, "r")
            return
        if vm.get("bottom"):   # ingen lyd ennå: sigI-grenen («Ingen signal») for AUX/USB, ellers «Klar for …»
            pix_text(c, 2, 19, pix_fit(vm["kicker"], 124), W)
            if i in ("aux", "aux2", "usb"):
                c.rect(2, 30, 20, 1, W); txt(c, 27, 34, "Ingen signal", W, "bold", 11)
                txt(c, 2, 45, txt_fit(c, vm["sub"] or vm["bottom"], "regular", 7, 124), W, "regular", 7)
            else:
                txt(c, 2, 32, txt_fit(c, vm["title"], "bold", 12, 124), W, "bold", 12)
                txt(c, 2, 44, txt_fit(c, vm["sub"] or vm["bottom"], "regular", 7, 124), W, "regular", 7)
            self.vol_bar(c, vm); return
        # kicker + aktivitetsstolper / pause
        pix_text(c, 2, 19, pix_fit(vm["kicker"], 112), W)
        if vm.get("paused"):
            c.rect(120, 14, 2, 5, W); c.rect(124, 14, 2, 5, W)
        else:
            for k in range(3):
                h = 1 if vm["mute"] else int(round(1.5 + 3.5 * abs(math.sin(now / 260 + k * 1.3))))
                c.rect(119 + k * 3, 19 - h, 2, h, W)
        txt(c, 2, 31, txt_fit(c, vm["title"], "bold", 11, 124), W, "bold", 11)
        if vm.get("duration"):
            ts = fmt(vm["position"]) + "/" + fmt(vm["duration"]); tw = pix_w(ts)
            txt(c, 2, 42, txt_fit(c, vm["sub"], "regular", 7, 120 - tw), W, "regular", 7)
            pix_text(c, 126, 42, ts, W, "r")
            track(c, 2, 45, 124, 1, max(0, min(1, vm["position"] / vm["duration"])))
        else:
            txt(c, 2, 42, txt_fit(c, vm["sub"], "regular", 7, 124), W, "regular", 7)
        self.vol_bar(c, vm)
