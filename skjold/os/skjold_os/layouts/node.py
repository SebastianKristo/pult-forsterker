"""Skjold Node, 1,8″ ST7735S liggende 160×128. Mål og farger fra design/node/Skjold Node OS.dc.html
(malen er i CSS-px på et 160×128-lerret, så tallene under er de samme som i malen)."""
import math
from PIL import Image, ImageDraw
from .base import Layout
from .. import fx, sources
from ..gfx import W, DIM, DIM2, TRACK, OFFDOT, BLACK, hexc, mix

BLUE = hexc("#4a8cff")


def _darken(c, box_fn):
    """Legg en svart flate med alfa over et område. box_fn(draw, ss) tegner masken (L, 0–255 = alfa)."""
    m = Image.new("L", c.img.size, 0); box_fn(ImageDraw.Draw(m), c.ss)
    c.img.paste(Image.new("RGB", c.img.size, BLACK), (0, 0), m); c.d = ImageDraw.Draw(c.img)


class NodeLayout(Layout):
    W, H, name = 160, 128, "node"

    # ---------- animasjoner (node_fx.js / skjold_welcome.js) ----------
    def draw_boot(self, c, vm): fx.splash(c, vm["t_ms"], vm.get("model", "NODE"))
    def draw_reboot(self, c, vm): fx.reboot(c, vm["t_ms"], vm["now_ms"])
    def draw_switch(self, c, vm): fx.switch_src(c, vm["t_ms"], vm["ring"], vm["sw_from"], vm["sw_to"], vm.get("sw_sub", ""))
    def draw_welcome(self, c, vm):
        w = vm.get("welcome") or {}
        fx.welcome(c, vm["t_ms"], w.get("tittel") or "Gratulerer med dagen", w.get("navn") or "Pappa",
                   w.get("hint") or "Trykk en knapp for å starte")

    # ---------- spiller nå (scrPlay) ----------
    def draw_play(self, c, vm):
        s = sources.src(vm["input"]); col = s["c"]
        # topplinje: ● KILDE ............ [volum] 12:34
        c.circle(10.5, 11, 2.5, col)
        c.text(16, 11, s["k"], DIM, "bold", 7, "lm", 1)
        x = c.w - 8
        c.text(x, 11, vm["clock"], DIM, "bold", 7, "rm"); x -= c.text_w(vm["clock"], "bold", 7) + 5
        if vm["input"] != "radio":
            c.rrect(x - 22, 9.5, 22, 3, 1.5, TRACK)
            if vm["volume"] > 0: c.rrect(x - 22, 9.5, 22 * vm["volume"] / 100, 3, 1.5, DIM if vm["mute"] else W)
        # albumbilde 58×58
        ax, ay = 8, 23
        if vm.get("cover") is not None:
            c.image(vm["cover"], ax, ay, 58, 58, 6)
        else:
            c0, c1 = s["art"]; c.gradient_tile(ax, ay, 58, 58, 6, hexc(c0), hexc(c1))
            c.text(ax + 5, ay + 58 - 6, vm["art_txt"], (235, 235, 235), "bold", 17, "ls")
        # tekst
        tx, tw = 74, c.w - 8 - 74
        c.text(tx, 29.5, c.ellipsize(vm["kicker"], "bold", 7, tw, 0.5), col, "bold", 7, "ls", 0.5)
        lines = c.wrap(vm["title"], "bold", 13, tw, 2); y = 44
        for ln in lines: c.text(tx, y, ln, W, "bold", 13); y += 14
        c.text(tx, y + 1, c.ellipsize(vm["sub"], "regular", 9, tw), DIM2, "regular", 9)
        # bunn: favoritt-prikker (radio) eller fremdrift
        if vm["input"] == "radio":
            ws = [10 if i == vm["preset_idx"] else 3 for i in range(6)]; x = (c.w - (sum(ws) + 3 * 5)) / 2
            for i, w in enumerate(ws):
                c.rrect(x, 116, w, 4, 2, col if i == vm["preset_idx"] else OFFDOT); x += w + 3
        elif vm.get("duration"):
            p = max(0, min(1, vm["position"] / vm["duration"]))
            c.rrect(8, 106, 144, 3, 1.5, TRACK); c.rrect(8, 106, max(3, 144 * p), 3, 1.5, W) if p > 0 else None
            c.text(8, 118, fx_fmt(vm["position"]), DIM, "regular", 7)
            c.text(152, 118, "−" + fx_fmt(vm["duration"] - vm["position"]), DIM, "regular", 7, "rs")
        elif vm.get("bottom"):
            c.text(80, 118, vm["bottom"], DIM, "regular", 7, "ms")
        if vm.get("paused"):
            _darken(c, lambda d, ss: d.ellipse([22 * ss, 41 * ss, 50 * ss, 69 * ss], fill=153))
            c.rect(32, 51, 2.5, 8, W); c.rect(37.5, 51, 2.5, 8, W)

    # ---------- volum nederst i 1,5 s (showVol) ----------
    def draw_volume(self, c, vm):
        def grad(d, ss):
            y0 = 99
            for y in range(y0 * ss, c.h * ss):
                a = min(1.0, (y - y0 * ss) / (0.3 * (c.h - y0) * ss)); d.line([(0, y), (c.w * ss, y)], fill=int(255 * a))
        _darken(c, grad)
        v = vm["volume"]; off = v == 0 or vm["mute"]; col = DIM if off else W
        c.text(8, 115, "AV" if off else str(v), col, "bold", 9, "lm")
        c.rrect(33, 112.5, 119, 5, 2.5, TRACK)
        if v > 0: c.rrect(33, 112.5, max(5, 119 * v / 100), 5, 2.5, col)

    # ---------- Blåtann-paring (scrPair) ----------
    def draw_pair(self, c, vm):
        pt = vm["pair_t"]; cx, cy = 80, 35
        for i in range(3):
            r = (pt * 0.9 + i / 3) % 1; d = 20 + r * 24
            c.circle(cx, cy, d / 2, outline=mix(BLUE, 1 - r), width=1)
        c.circle(cx, cy, 10, BLUE); fx.ico_bt(c, cx, cy, 0.62, W)
        c.text(80, 76, "Paring" + "..."[:1 + int(pt * 2) % 3], W, "bold", 12, "ms")
        c.text(80, 88, "Synlig som «%s»" % vm["name"], DIM, "regular", 8, "ms")
        c.text(80, 98.5, vm.get("pair_hint", "◀◀ avbryter"), DIM, "regular", 8, "ms")
        c.rrect(25, 106, 110, 2, 1, TRACK); c.rect(25, 106, 110 * min(1, vm["pair_p"]), 2, BLUE)

    # ---------- hold-fremdrift / «Lagret» (scrHold) ----------
    def draw_hold(self, c, vm):
        if vm.get("hold_saved") is not None: return self.draw_saved(c, vm)
        p = vm.get("hold_p", 1.0)
        c.circle(80, 47, 15, TRACK)
        if p > 0: c.pie(80, 47, 15, -math.pi / 2, -math.pi / 2 + p * 2 * math.pi, W)
        c.circle(80, 47, 12.5, BLACK)
        c.text(80, 81, vm.get("hold_title", ""), W, "bold", 12, "ms")
        c.text(80, 91, vm.get("hold_sub", "Fortsett å holde"), DIM, "regular", 8, "ms")

    def draw_saved(self, c, vm):
        """Bekreftelse («Lagret»): fylt sirkel i kildefargen som spretter inn, så tegnes haken."""
        t = max(0.0, vm.get("saved_t", 1.0)); acc = vm.get("accent") or W
        k = min(1.0, t / 0.22); sc = 1 + 0.18 * math.sin(k * math.pi) if k < 1 else 1.0   # 0 → 1,18 → 1
        r = 16 * (k if k < 1 else 1) * (sc if k >= 0.5 else 1)
        if t > 0.22: c.circle(80, 47, 16 + 5 * min(1, (t - 0.22) / 0.35), outline=mix(acc, max(0, 1 - (t - 0.22) / 0.35)), width=1)
        if r > 0.5: c.circle(80, 47, r, acc)
        ink = BLACK if sum(acc[:3]) > 420 else W   # mørk hake på lyse kildefarger (AirPlay/AUX)
        q = min(1.0, max(0.0, (t - 0.12) / 0.25))   # haken tegnes fra venstre
        if q > 0:
            a, b_, e = (72, 47.5), (78, 53.5), (89, 41.5)
            if q < 0.4: pts = [a, (a[0] + (b_[0] - a[0]) * q / 0.4, a[1] + (b_[1] - a[1]) * q / 0.4)]
            else:
                f = (q - 0.4) / 0.6; pts = [a, b_, (b_[0] + (e[0] - b_[0]) * f, b_[1] + (e[1] - b_[1]) * f)]
            c.line(pts, ink, 2.6, joint="curve")
        c.text(80, 81, vm.get("hold_title", "Lagret"), W, "bold", 12, "ms")
        c.text(80, 91, vm.get("hold_sub", ""), DIM, "regular", 8, "ms")

    # ---------- meny (scrSet) – brukes til daemonens radiomeny ----------
    def draw_menu(self, c, vm):
        rows, idx = vm["menu_rows"], vm["menu_idx"]
        c.text(6, 10, vm["menu_head"], DIM, "bold", 7, "lm", 1)
        c.text(154, 10, "%d/%d" % (idx + 1, len(rows)), DIM, "bold", 7, "rm")
        c.rect(6, 14.5, 148, 0.6, TRACK)
        first = max(0, min(len(rows) - 5, idx - 2))
        for j, it in enumerate(rows[first:first + 5]):
            sel = first + j == idx; y = 18 + j * 20
            if sel: c.rrect(6, y, 148, 20, 4, W)
            fg = BLACK if sel else W
            c.text(16, y + 10, it.get("icon", ""), BLACK if sel else DIM, "regular", 9, "mm")
            vw = c.text_w(it.get("v", ""), "regular", 8.5)
            c.text(26, y + 10, c.ellipsize(it["n"], "bold" if sel else "regular", 9.5, 148 - 25 - vw - 8),
                   fg, "bold" if sel else "regular", 9.5, "lm")
            c.text(149, y + 10, it.get("v", ""), (51, 51, 51) if sel else DIM, "regular", 8.5, "rm")

    # ---------- standby-klokke (scrClock + klokkestilene i felles/skjold_settings.js) ----------
    def draw_clock(self, c, vm):
        d, style = vm["now"], vm.get("clock_style", 0)
        if style == 0:   # Node-designet: stor tynn klokke + dato
            c.text(80, 58, "%02d:%02d" % (d.hour, d.minute), W, "light", 46, "mm", -1.5)
            c.text(80, 90, fx.date_long(d).upper(), DIM, "regular", 8, "ms", 1)
        else:
            fx.draw_clock(c, style, d, color=DIM2, still=False)

    # ---------- ingen kontakt med daemonen (ikke i designet; samme formspråk) ----------
    def draw_offline(self, c, vm):
        k = 0.42; bx = 80 - 20.5 * k
        for x, bh in fx.BARS: c.rrect(bx + x * k, 22, 4.6 * k, bh * k, 2.3 * k, mix(W, 0.35))
        c.text(80, 62, "Ingen kontakt", W, "bold", 12, "ms")
        c.text(80, 75, "Lydtjenesten (ki-amp) svarer ikke", DIM, "regular", 8, "ms")
        c.text(80, 85.5, "Prøver igjen …", DIM, "regular", 8, "ms")
        now = vm["now_ms"]
        for kk in range(8):
            an = kk / 8 * math.pi * 2 + now / 140; op = 0.2 + 0.8 * ((kk / 8 + now / 1120) % 1)
            c.circle(80 + math.cos(an) * 4, 102 + math.sin(an) * 4, 0.9, mix(W, op))
        if vm.get("offline_s", 0) >= 1:
            c.text(80, 121, "%s · %d s" % (vm["clock"], vm["offline_s"]), mix(DIM, 0.7), "regular", 7, "ms")


def fx_fmt(sec):
    sec = max(0, int(sec)); return "%d:%02d" % (sec // 60, sec % 60)
