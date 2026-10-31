"""Skjold S1 med 2,8″ SPI-TFT (ILI9341/ST7789V via fbtft), 320×240 farge. drawTFT0 i
skjold/design/s1/pultforsterker_revb_metall.js. Overleggene er OLED-ens overlay() tegnet 2,5× fra y=40
(nøyaktig som designet), med kantutjevning og designets gråtoner."""
import colorsys, math
from PIL import Image
from .base import Layout
from .s1_common import draw_reboot, draw_pair, draw_hold, draw_menu, draw_switch, draw_offline, splash
from .s1_oled import TAB, tabs_for
from .. import fx
from ..gfx import Canvas, BLACK, hexc

TW, TDM, ACC = hexc("#f4f1ea"), hexc("#9a968c"), hexc("#d9a441")
PILL, SEG = hexc("#55524c"), hexc("#2c2b29")
HUES = {"AIR": (18, 52), "AUX": (205, 260), "RADIO": (150, 95), "USB": (280, 330)}


def hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s); return (int(r * 255), int(g * 255), int(b * 255))


def fmt(sec): sec = max(0, int(sec)); return "%d:%02d" % (sec // 60, sec % 60)


class S1TftLayout(Layout):
    W, H, SS, MONO, name = 320, 240, 2, False, "s1-tft"
    OUT_W, OUT_H = 320, 240
    OVERLAY = ("reboot", "pair", "hold", "menu", "switch", "offline")

    def render(self, vm):
        scr = vm["screen"]
        if scr in self.OVERLAY:   # overlay(g) i 128×64, skalert 2,5× fra y=40
            c = Canvas(128, 64, ss=5)
            getattr(self, "ov_" + scr)(c, vm)
            out = Image.new("RGB", (320, 240), BLACK)
            out.paste(c.img.resize((320, 160), Image.LANCZOS), (0, 40))
            if scr == "switch" and vm.get("vol_overlay"):
                c2 = self.canvas(); c2.img.paste(out.resize(c2.img.size), (0, 0)); self.vol_row(c2, vm); return c2.frame()
            return out
        c = self.canvas()
        getattr(self, "draw_" + scr, self.draw_off)(c, vm)
        return c.frame()

    # ---------- overlegg ----------
    def ov_reboot(self, c, vm): draw_reboot(c, vm["t_ms"], vm["now_ms"])
    def ov_pair(self, c, vm): draw_pair(c, vm["pair_t"], vm["pair_p"], vm["name"])
    def ov_hold(self, c, vm): draw_hold(c, vm)
    def ov_menu(self, c, vm): draw_menu(c, vm)
    def ov_switch(self, c, vm): draw_switch(c, vm["t_ms"], vm["ring"], vm["sw_from"], vm["sw_to"], vm.get("sw_sub", ""))
    def ov_offline(self, c, vm): draw_offline(c, vm["now_ms"], vm.get("offline_s", 0), vm["clock"])

    # ---------- fullskjerm ----------
    def draw_boot(self, c, vm): splash(c, vm["t_ms"], vm.get("model", "S1"))
    def draw_welcome(self, c, vm):
        w = vm.get("welcome") or {}
        fx.welcome(c, vm["t_ms"], w.get("tittel") or "Gratulerer med dagen", w.get("navn") or "Pappa",
                   w.get("hint") or "Trykk en knapp for å starte")
    def draw_clock(self, c, vm): fx.draw_clock(c, vm.get("clock_style", 0) % 6, vm["now"], still=False)   # drawClock(g,320,240,…)

    # ---------- spiller nå (drawTFT0) ----------
    def vol_row(self, c, vm):
        v, m = vm["volume"], vm["mute"]
        c.rect(0, 208, 320, 32, BLACK)
        c.text(12, 222, "MUTE" if m else "VOL", TDM, "bold", 10, "lm")
        on = 0 if m else round(v / 100 * 32)
        for i in range(32): c.rect(44 + i * 6.875, 216, 5.4, 12, TW if i < on else SEG)
        c.text(308, 222, "—" if m else str(v), TW, "bold", 16, "rm")

    def draw_play(self, c, vm):
        cur = TAB.get(vm["input"], vm["input"].upper()[:5]); x = 12
        for t in tabs_for(vm):
            w = c.text_w(t, "bold", 11) + 16
            if t == cur: c.rrect(x, 8, w, 18, 9, TW); c.text(x + 8, 17.5, t, BLACK, "bold", 11, "lm")
            else: c.rrect(x, 8, w, 18, 9, None, PILL, 1); c.text(x + 8, 17.5, t, TDM, "bold", 11, "lm")
            x += w + 6
        if vm.get("mute"): c.text(308, 17.5, "MUTE", TDM, "bold", 10, "rm")
        if vm.get("cover") is not None:
            c.image(vm["cover"], 12, 36, 128, 128, 6)
        else:
            h0, h1 = HUES.get(cur, (18, 52)); c.gradient_tile(12, 36, 128, 128, 6, hsl(h0, 0.7, 0.55), hsl(h1, 0.6, 0.2))
            if vm["input"] == "radio" and vm.get("preset_idx", -1) >= 0:
                c.text(22, 154, str(vm["preset_idx"] + 1), (240, 240, 236), "bold", 34, "ls")
        tx, tw = 154, 320 - 12 - 154
        c.text(tx, 54, c.ellipsize(vm["title"], "bold", 18, tw), TW, "bold", 18, "lm")
        c.text(tx, 76, c.ellipsize(vm["sub"] or vm.get("bottom") or "", "regular", 13, tw), TDM, "regular", 13, "lm")
        c.text(tx, 98, c.ellipsize(vm["kicker"], "bold", 10, tw, 0.5), ACC, "bold", 10, "lm", 0.5)
        now = vm["now_ms"] / 1000; still = vm.get("paused") or vm.get("bottom")
        for i in range(26):
            v = 0.35 + 0.65 * abs(math.sin(now * 3.1 + i * 0.7) * math.sin(now * 1.7 + i * 0.31))
            h = 2 if (vm["mute"] or still) else 4 + v * 44
            c.rect(154 + i * 6, 164 - h, 4, h, ACC)
        if vm.get("duration"):
            p = max(0, min(1, vm["position"] / vm["duration"]))
            c.rect(12, 180, 296, 2, SEG); c.rect(12, 180, 296 * p, 2, TW)
            c.text(12, 194, fmt(vm["position"]), TDM, "regular", 10, "lm")
            c.text(308, 194, "−" + fmt(vm["duration"] - vm["position"]), TDM, "regular", 10, "rm")
        elif vm["input"] == "radio":
            n = len(vm.get("presets") or []) or 6; x = 12
            for i in range(n):
                on = i == vm.get("preset_idx"); w = 20 if on else 6
                c.rrect(x, 186, w, 6, 3, ACC if on else SEG); x += w + 6
        if cur in ("AIR", "AUX") or vm.get("vol_overlay"):   # volVis(): AIR/AUX alltid, ellers 2,2 s etter endring
            self.vol_row(c, vm)
