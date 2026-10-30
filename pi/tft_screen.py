"""Pultforsterker – 2,8" SPI TFT 320 × 240 (ILI9341 / ST7789V via fbtft) med valgfri touch (XPT2046 via ads7846).

Tegner hele skjermbildet i farger med PIL og skriver RGB565 rett til framebufferen. Innholdet er det samme som på
OLED-en: kilde, tittel/artist (ruller), albumbilde, fremdrift, volum, radio-kanaler, meny og overlegg – pluss en rad
med trykkflater nederst (kilder, forrige/spill-pause/neste, volum −/+). Brukes av oled_display.py når KI_AMP_DISPLAY=tft.
"""
import glob
import json
import math
import os
import time
import urllib.request

from PIL import Image, ImageDraw, ImageFont

W, H = 320, 240
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
f_tab, f_title, f_sub, f_big, f_small, f_btn = F(FONT_B, 12), F(FONT_B, 22), F(FONT_R, 15), F(FONT_B, 30), F(FONT_R, 12), F(FONT_B, 14)
BG, FG, DIM, ACC, TRACK, PANEL = (8, 9, 12), (238, 246, 255), (125, 138, 148), (232, 86, 42), (42, 48, 54), (24, 26, 30)
LABELS = {"radio": "RADIO", "airplay": "AIR", "bt": "BT", "aux": "AUX1", "aux2": "AUX2", "usb": "USB"}
NAMES = {"radio": "Radio", "airplay": "AirPlay", "bt": "Bluetooth", "aux": "AUX 1", "aux2": "AUX 2", "usb": "USB"}
SUB = {"radio": "Velg kanal 1–6", "airplay": "Venter på enhet …", "bt": "Ingen enhet", "aux": "3,5 mm inngang 1", "aux2": "3,5 mm inngang 2", "usb": "USB-lyd fra PC"}
PORT = os.environ.get("KI_AMP_PORT", "8765")

_m = {"scroll": 0.0, "cover": None, "cover_id": None, "vol": None, "vol_t": 0.0, "inp": None, "inp_t": 0.0}


def find_fb():
    """Framebufferen fbtft lagde (fb_ili9341 / fb_st7789v) – ellers None."""
    for n in sorted(glob.glob("/sys/class/graphics/fb*/name")):
        try:
            if open(n).read().strip().startswith("fb_"):
                return "/dev/" + n.split("/")[-2]
        except Exception:
            pass
    return None


def to_rgb565(img):
    import numpy as np
    a = np.asarray(img.convert("RGB"), dtype=np.uint16)
    v = ((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5) | (a[:, :, 2] >> 3)
    return v.astype("<u2").tobytes()


def api(path, body):
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/api/{path}", data=json.dumps(body).encode(),
                                                      method="POST", headers={"Content-Type": "application/json"}), timeout=2).read()
    except Exception as e:
        print("TFT-touch:", e, flush=True)


def fmt(s):
    s = int(max(0, s)); return f"{s // 60}:{s % 60:02d}"


def fit(draw, text, font, w):
    if draw.textlength(text, font=font) <= w:
        return text
    while text and draw.textlength(text + "…", font=font) > w:
        text = text[:-1]
    return text + "…"


# ---------------------------------------------------------------- trykkflater (x0, y0, x1, y1, handling)
def zones(c):
    keys = [k for k in ("radio", "airplay", "bt", "aux", "aux2", "usb") if k in (c.get("inputs") or ["radio", "airplay", "bt", "aux", "aux2", "usb"])]
    z = []
    w = W / len(keys)
    for i, k in enumerate(keys):
        z.append((i * w, 0, (i + 1) * w, 30, ("input", {"input": k})))
    bar_y = H - 44
    for i, (lab, act) in enumerate((("⏮", ("transport", {"action": "previous"})), ("⏯", ("transport", {"action": "playpause"})),
                                    ("⏭", ("transport", {"action": "next"})), ("−", ("volume", {"delta": -5})), ("+", ("volume", {"delta": 5})))):
        z.append((i * 64, bar_y, (i + 1) * 64, H, act))
    return z, keys


def tap(c, x, y):
    for x0, y0, x1, y1, act in zones(c)[0]:
        if x0 <= x < x1 and y0 <= y < y1:
            api(*act); return act
    return None


# ---------------------------------------------------------------- tegning
def cover_image(track):
    cid = track.get("cover") or ""
    if cid != _m["cover_id"]:
        _m["cover_id"] = cid; _m["cover"] = None
        if cid and os.path.exists("/run/pultamp_cover"):
            try:
                _m["cover"] = Image.open("/run/pultamp_cover").convert("RGB").resize((96, 96))
            except Exception:
                _m["cover"] = None
    return _m["cover"]


def main_screen(img, draw, c, track, pos_now, now):
    inp = c.get("input", "airplay"); vol = int(c.get("volume", 0)); r = c.get("radio") or {}
    z, keys = zones(c)
    # faner øverst
    w = W / len(keys)
    for i, k in enumerate(keys):
        x0 = i * w
        active = k == inp
        if active:
            draw.rectangle((x0 + 2, 2, x0 + w - 2, 28), fill=ACC)
        draw.text((x0 + w / 2 - draw.textlength(LABELS[k], font=f_tab) / 2, 7), LABELS[k], font=f_tab, fill=FG if active else DIM)
    draw.line((0, 31, W, 31), fill=TRACK)
    # albumbilde / ikon
    cov = cover_image(track) if inp in ("airplay", "bt") else None
    if inp == "radio" and r.get("art_local") and os.path.exists(r["art_local"]):
        try: cov = Image.open(r["art_local"]).convert("RGB").resize((96, 96))
        except Exception: cov = None
    ax, ay = 12, 44
    if cov:
        img.paste(cov, (ax, ay))
    else:
        draw.rounded_rectangle((ax, ay, ax + 96, ay + 96), 10, fill=PANEL)
        draw.text((ax + 48 - draw.textlength(LABELS.get(inp, inp), font=f_tab) / 2, ay + 40), LABELS.get(inp, inp), font=f_tab, fill=DIM)
    # tekst
    tx = ax + 96 + 14; tw = W - tx - 10
    if inp == "radio" and r.get("station"):
        title = r["station"]; sub = " – ".join(x for x in (r.get("artist"), r.get("song")) if x) or "Radio"
        if c.get("preset"): sub = f"Kanal {c['preset']} · " + sub
    elif inp in ("airplay", "bt") and track.get("title"):
        title, sub = track["title"], track.get("artist", "")
    else:
        title, sub = NAMES.get(inp, inp), SUB.get(inp, "")
        if inp == "bt" and track.get("bt_device"): sub = track["bt_device"]
        if inp == "usb" and c.get("usbsw"): sub = f"{(c.get('usb_pc_names') or ['PC 1', 'PC 2'])[(c.get('usb_pc') or 1) - 1]} · 48 kHz"
    wt = draw.textlength(title, font=f_title)
    if wt > tw:
        _m["scroll"] = (_m["scroll"] + 2.0) % (wt + 60)
        clip = Image.new("RGB", (int(tw), 30), BG); cd = ImageDraw.Draw(clip)
        cd.text((-_m["scroll"], 0), title, font=f_title, fill=FG); cd.text((-_m["scroll"] + wt + 60, 0), title, font=f_title, fill=FG)
        img.paste(clip, (tx, ay + 2))
    else:
        _m["scroll"] = 0; draw.text((tx, ay + 2), title, font=f_title, fill=FG)
    draw.text((tx, ay + 38), fit(draw, sub, f_sub, tw), font=f_sub, fill=DIM)
    # fremdrift / nivåmeter
    py = ay + 72
    if inp in ("airplay", "bt", "radio") and track.get("duration"):
        p = min(1, pos_now() / track["duration"])
        draw.rounded_rectangle((tx, py, W - 10, py + 6), 3, fill=TRACK); draw.rounded_rectangle((tx, py, tx + (W - 10 - tx) * p, py + 6), 3, fill=FG)
        draw.text((tx, py + 10), f"{fmt(pos_now())} / {fmt(track['duration'])}", font=f_small, fill=DIM)
        playing = (r.get("mode") == "play") if inp == "radio" else track.get("playing")
        if playing:
            draw.polygon([(W - 20, py + 11), (W - 10, py + 17), (W - 20, py + 23)], fill=DIM)
        else:
            draw.rectangle((W - 20, py + 11, W - 17, py + 23), fill=DIM); draw.rectangle((W - 13, py + 11, W - 10, py + 23), fill=DIM)
    elif inp in ("aux", "aux2", "usb"):
        for i in range(int((W - 10 - tx) / 8)):
            h = 3 + 18 * abs(math.sin(now * 3 + i * 0.7)) * (0.3 + 0.7 * abs(math.sin(now * 0.9 + i)))
            draw.rectangle((tx + i * 8, py + 22 - h, tx + i * 8 + 5, py + 22), fill=DIM)
    # radio: kanaler 1–6
    if inp == "radio":
        presets = c.get("presets") or []
        for i in range(6):
            x0 = 12 + i * 50; on = c.get("preset") == i + 1
            draw.rounded_rectangle((x0, 140, x0 + 44, 164), 6, fill=ACC if on else PANEL)
            draw.text((x0 + 22 - draw.textlength(str(i + 1), font=f_tab) / 2, 145), str(i + 1), font=f_tab, fill=FG if on else DIM)
    # volum
    vy = H - 44 - 22
    draw.text((12, vy - 2), "MUTE" if c.get("mute") else f"VOL {vol}", font=f_tab, fill=ACC if c.get("mute") else DIM)
    segs = 30
    for i in range(segs):
        x0 = 90 + i * 7
        draw.rectangle((x0, vy + 8 - i * 0.25, x0 + 4, vy + 12), fill=FG if (i < round(vol / 100 * segs) and not c.get("mute")) else TRACK)
    # trykkflater nederst
    draw.line((0, H - 45, W, H - 45), fill=TRACK)
    playing = (r.get("mode") == "play") if inp == "radio" else track.get("playing")
    for i, lab in enumerate(("prev", "play", "next", "-", "+")):
        x0 = i * 64; cx, cy = x0 + 32, H - 22
        draw.rectangle((x0 + 3, H - 41, x0 + 61, H - 3), fill=PANEL)
        if lab == "prev":
            draw.polygon([(cx + 8, cy - 9), (cx - 4, cy), (cx + 8, cy + 9)], fill=FG); draw.rectangle((cx - 9, cy - 9, cx - 6, cy + 9), fill=FG)
        elif lab == "next":
            draw.polygon([(cx - 8, cy - 9), (cx + 4, cy), (cx - 8, cy + 9)], fill=FG); draw.rectangle((cx + 6, cy - 9, cx + 9, cy + 9), fill=FG)
        elif lab == "play":
            if playing:
                draw.rectangle((cx - 9, cy - 9, cx - 3, cy + 9), fill=FG); draw.rectangle((cx + 3, cy - 9, cx + 9, cy + 9), fill=FG)
            else:
                draw.polygon([(cx - 7, cy - 10), (cx + 10, cy), (cx - 7, cy + 10)], fill=FG)
        elif lab == "-":
            draw.rectangle((cx - 10, cy - 2, cx + 10, cy + 2), fill=FG)
        else:
            draw.rectangle((cx - 10, cy - 2, cx + 10, cy + 2), fill=FG); draw.rectangle((cx - 2, cy - 10, cx + 2, cy + 10), fill=FG)


def overlay(draw, c, track, now):
    m = _m
    vol, inp = int(c.get("volume", 0)), c.get("input", "airplay")
    if m["vol"] is not None and vol != m["vol"]:
        m["vol_t"] = now
    if m["inp"] is not None and inp != m["inp"]:
        m["inp_t"] = now
    m.update(vol=vol, inp=inp)
    menu = c.get("menu")
    if menu:
        idx = menu.get("idx", 1); presets = c.get("presets") or []
        p = presets[idx - 1] if idx - 1 < len(presets) else None
        draw.rectangle((0, 0, W, H), fill=BG)
        draw.text((16, 20), "KANAL", font=f_tab, fill=DIM); draw.text((16, 48), str(idx), font=f_big, fill=ACC)
        draw.text((70, 56), fit(draw, (p or {}).get("title") or "– tom –", f_title, W - 86), font=f_title, fill=FG)
        draw.text((16, 120), "vri = velg · trykk = spill · hold = lagre", font=f_small, fill=DIM)
        return True
    if c.get("bt_pairing"):
        draw.rectangle((0, 0, W, H), fill=BG)
        r = (now * 40) % 60
        for k in (0, 20, 40):
            rr = (r + k) % 60 + 20
            draw.ellipse((160 - rr, 110 - rr, 160 + rr, 110 + rr), outline=TRACK)
        draw.text((160 - draw.textlength("Parring" + "." * (1 + int(now * 2) % 3), font=f_title) / 2, 92), "Parring" + "." * (1 + int(now * 2) % 3), font=f_title, fill=FG)
        draw.text((160 - draw.textlength("Velg «Pultforsterker» på telefonen", font=f_sub) / 2, 160), "Velg «Pultforsterker» på telefonen", font=f_sub, fill=DIM)
        return True
    if now - m["inp_t"] < 1.0:
        draw.rectangle((0, 0, W, H), fill=BG)
        t = NAMES.get(inp, inp).upper(); draw.text((160 - draw.textlength(t, font=f_big) / 2, 100), t, font=f_big, fill=FG)
        return True
    return False


def boot(draw, p):
    draw.rectangle((0, 0, W, H), fill=BG)
    draw.ellipse((145, 60, 175, 90), outline=FG, width=3); draw.line((160, 55, 160, 76), fill=FG, width=3)
    draw.text((160 - draw.textlength("PULTFORSTERKER", font=f_title) / 2, 110), "PULTFORSTERKER", font=f_title, fill=FG)
    draw.rounded_rectangle((80, 160, 240, 168), 4, fill=TRACK); draw.rounded_rectangle((80, 160, 80 + 160 * p, 168), 4, fill=ACC)
    s = "Starter AirPlay" if p < 0.5 else ("Starter Bluetooth" if p < 0.9 else "Klar")
    draw.text((160 - draw.textlength(s, font=f_small) / 2, 178), s, font=f_small, fill=DIM)


def frame(c, track, pos_now, boot_p=None, net=None):
    img = Image.new("RGB", (W, H), BG); draw = ImageDraw.Draw(img); now = time.time()
    if boot_p is not None:
        boot(draw, boot_p)
    elif net is not None:
        head, line = ("NETTVERK", net) if net else ("INGEN NETTVERK", "sjekk kabelen")
        draw.text((160 - draw.textlength(head, font=f_tab) / 2, 90), head, font=f_tab, fill=DIM)
        draw.text((160 - draw.textlength(line, font=f_big) / 2, 115), line, font=f_big, fill=FG)
    elif not overlay(draw, c, track, now):
        main_screen(img, draw, c, track, pos_now, now)
    return img


class Touch:
    """XPT2046 via ads7846 (evdev). Kalibrering: KI_AMP_TOUCH_CAL=xmin,xmax,ymin,ymax[,swap]."""
    def __init__(self, ctrl_fn):
        self.ctrl_fn = ctrl_fn; self.dev = None
        cal = os.environ.get("KI_AMP_TOUCH_CAL", "200,3900,200,3900").split(",")
        self.xmin, self.xmax, self.ymin, self.ymax = (int(v) for v in cal[:4]); self.swap = len(cal) > 4 and cal[4] == "swap"
        try:
            import evdev
            for p in evdev.list_devices():
                d = evdev.InputDevice(p)
                if "ADS7846" in d.name.upper() or "XPT" in d.name.upper():
                    self.dev = d; break
            if self.dev:
                print("Touch:", self.dev.name, flush=True)
        except Exception as e:
            print("Touch ikke tilgjengelig:", e, flush=True)

    def run(self):
        if not self.dev:
            return
        import evdev
        from evdev import ecodes
        x = y = None; down_t = None
        for ev in self.dev.read_loop():
            if ev.type == ecodes.EV_ABS:
                if ev.code == ecodes.ABS_X: x = ev.value
                elif ev.code == ecodes.ABS_Y: y = ev.value
            elif ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
                if ev.value:
                    down_t = time.time()
                elif x is not None and y is not None and down_t and time.time() - down_t < 0.6:
                    px = (x - self.xmin) / max(1, self.xmax - self.xmin); py = (y - self.ymin) / max(1, self.ymax - self.ymin)
                    if self.swap: px, py = py, px
                    tap(self.ctrl_fn(), max(0, min(W - 1, px * W)), max(0, min(H - 1, py * H)))
