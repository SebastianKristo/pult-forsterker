"""Pultforsterker – skjermbilder for 0,91" OLED 128 × 32 (SSD1306, I2C).

Samme innhold som den store skjermen, tilpasset 32 piksler høyde:
  hovedbilde (kilde, status, tittel som ruller, artist, volum, fremdrift / nivåmeter / kanaler),
  overlegg ved volumendring, mute, kildebytte, Bluetooth-parring og -tilkobling, kanalmeny og oppstart.
Brukes av oled_display.py når KI_AMP_OLED=ssd1306_128x32.
"""
import math
import time

from PIL import ImageFont

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
f_tag, f_title, f_sub, f_big, f_mid, f_boot = F(FONT_B, 7), F(FONT_B, 11), F(FONT_R, 8), F(FONT_B, 16), F(FONT_B, 12), F(FONT_B, 9)
LABELS = {"radio": "RAD", "airplay": "AIR", "bt": "BT", "aux": "AUX", "usb": "USB"}
NAMES = {"radio": "Radio", "airplay": "AirPlay", "bt": "Bluetooth", "aux": "AUX", "usb": "USB"}
SUB = {"radio": "Lyrion", "airplay": "Venter på enhet", "bt": "Ingen enhet", "aux": "3,5 mm inn", "usb": "Lydkort for PC"}

W, H = 128, 32
_mem = {"vol": None, "vol_t": 0.0, "inp": None, "inp_t": 0.0, "dev": None, "dev_t": 0.0, "mute": None, "scroll": 0.0}


def fmt(s):
    s = int(max(0, s)); return f"{s // 60}:{s % 60:02d}"


def dim(draw, xy, text, font):
    """Undertekst. På 32 px er prikk-dempingen fra den store skjermen uleselig, så teksten tegnes hel."""
    draw.text(xy, text, font=font, fill=255)


def fit(draw, text, font, w):
    """Kort ned tekst med … til den får plass i w piksler."""
    if draw.textlength(text, font=font) <= w:
        return text
    while text and draw.textlength(text + "…", font=font) > w:
        text = text[:-1]
    return text + "…"


def center(draw, y, text, font, fill=255):
    draw.text(((W - draw.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)


def bt_icon(draw, cx, cy, s, fill=255):
    draw.line([(cx - s * 0.55, cy - s * 0.45), (cx + s * 0.5, cy + s * 0.5), (cx, cy + s), (cx, cy - s),
               (cx + s * 0.5, cy - s * 0.5), (cx - s * 0.55, cy + s * 0.45)], fill=fill, width=1)


def power_icon(draw, cx, cy, r):
    draw.arc((cx - r, cy - r, cx + r, cy + r), 300, 240, fill=255)
    draw.line((cx, cy - r - 1, cx, cy), fill=255)


def speaker(draw, x, y, muted):
    draw.rectangle((x, y + 3, x + 3, y + 7), fill=255)
    draw.polygon([(x + 3, y + 3), (x + 7, y), (x + 7, y + 10), (x + 3, y + 7)], fill=255)
    if muted:
        draw.line((x + 10, y + 2, x + 16, y + 8), fill=255); draw.line((x + 10, y + 8, x + 16, y + 2), fill=255)
    else:
        draw.arc((x + 5, y + 1, x + 11, y + 9), 300, 60, fill=255); draw.arc((x + 6, y - 2, x + 15, y + 12), 300, 60, fill=255)


def vol_bar(draw, x, y, w, h, vol, segs=20):
    step = w / segs; on = round(vol / 100 * segs)
    for i in range(segs):
        hh = max(2, round(h * (0.35 + 0.65 * i / (segs - 1))))
        x0 = x + i * step
        if i < on:
            draw.rectangle((x0, y + h - hh, x0 + step - 2, y + h), fill=255)
        else:
            draw.point((x0, y + h), fill=255)


# ------------------------------------------------------------------ overlegg (returnerer True når de tegnet noe)
def overlay(draw, c, track, now):
    m = _mem
    vol, inp, mute = int(c.get("volume", 0)), c.get("input", "airplay"), bool(c.get("mute"))
    dev = track.get("bt_device", "")
    if m["vol"] is not None and vol != m["vol"]:
        m["vol_t"] = now
    if m["inp"] is not None and inp != m["inp"]:
        m["inp_t"] = now
    if m["dev"] is not None and dev and dev != m["dev"]:
        m["dev_t"] = now
    if m["mute"] is not None and mute != m["mute"]:
        m["vol_t"] = now
    m.update(vol=vol, inp=inp, dev=dev, mute=mute)

    menu = c.get("menu")
    if menu:   # kanalmeny: vri = velg, trykk = spill, hold = lagre
        idx = menu.get("idx", 1); presets = c.get("presets") or []
        p = presets[idx - 1] if idx - 1 < len(presets) else None
        name = (p or {}).get("title") or "– tom –"
        draw.text((0, 0), "KANAL", font=f_tag, fill=255)
        for i in range(6):   # prikker for plass 1–6
            x = 34 + i * 7
            draw.rectangle((x, 2, x + 4, 6), fill=255 if i + 1 == idx else 0, outline=255)
        draw.text((W - 1 - draw.textlength("hold=lagre", font=f_tag), 0), "hold=lagre", font=f_tag, fill=255)
        draw.text((0, 10), str(idx), font=f_big, fill=255)
        draw.text((14, 13), fit(draw, name, f_mid, 106), font=f_mid, fill=255)
        if c.get("preset") == idx and inp == "radio":
            draw.polygon([(122, 15), (127, 19), (122, 23)], fill=255)
        return True
    if c.get("bt_pairing"):
        r = (now * 9) % 14
        for k in (0, 7):
            rr = (r + k) % 14 + 3
            draw.ellipse((14 - rr, 16 - rr, 14 + rr, 16 + rr), outline=255)
        draw.rectangle((5, 6, 23, 26), fill=0); bt_icon(draw, 14, 16, 7)
        draw.text((34, 3), "Parring" + "." * (1 + int(now * 2) % 3), font=f_title, fill=255)
        dim(draw, (34, 19), "Velg Pultforsterker", f_sub)
        return True
    if now - m["dev_t"] < 2.5 and dev:
        bt_icon(draw, 10, 16, 7); draw.line((18, 18, 21, 21, 27, 12), fill=255, width=2)
        draw.text((34, 3), "Tilkoblet", font=f_title, fill=255)
        dim(draw, (34, 19), fit(draw, dev, f_sub, 94), f_sub)
        return True
    if now - m["inp_t"] < 1.2:
        center(draw, 2, NAMES.get(inp, inp).upper(), f_big)
        s = c.get("station") if inp == "radio" and c.get("station") else SUB.get(inp, "")
        if inp == "bt" and dev:
            s = dev
        tw = draw.textlength(s, font=f_tag); dim(draw, ((W - tw) / 2, 23), s, f_tag)
        return True
    if now - m["vol_t"] < 1.4:
        speaker(draw, 0, 3, mute)
        if mute:
            draw.text((26, 0), "MUTE", font=f_big, fill=255)
            dim(draw, (26, 22), f"volum {vol}", f_tag)
        else:
            t = str(vol); draw.text((W - draw.textlength(t, font=f_big), 0), t, font=f_big, fill=255)
            draw.text((22, 3), "VOLUM", font=f_tag, fill=255)
            vol_bar(draw, 0, 20, W, 10, vol, 32)
        return True
    return False


# ------------------------------------------------------------------ hovedbilde
def main_screen(draw, c, track, pos_now):
    now = time.time()
    inp = c.get("input", "airplay"); vol = int(c.get("volume", 0))
    r = c.get("radio") or {}
    # linje 1: kilde-merke, status, tid/kanal, volum
    tag = LABELS.get(inp, inp.upper()); tw = draw.textlength(tag, font=f_tag) + 6
    draw.rectangle((0, 0, tw, 8), fill=255); draw.text((3, 0), tag, font=f_tag, fill=0)
    playing = (r.get("mode") == "play") if inp == "radio" else track.get("playing")
    x = tw + 4
    if inp in ("airplay", "bt", "radio"):
        if playing:
            draw.polygon([(x, 1), (x + 5, 4), (x, 7)], fill=255)
        else:
            draw.rectangle((x, 1, x + 1, 7), fill=255); draw.rectangle((x + 3, 1, x + 4, 7), fill=255)
        x += 9
    if inp == "bt" and track.get("bt_device"):
        bt_icon(draw, x + 2, 4, 3); x += 8
    if inp == "radio" and c.get("preset"):
        dim(draw, (x, 0), f"KANAL {c['preset']}", f_tag)
    elif inp in ("airplay", "bt") and track.get("duration"):
        dim(draw, (x, 0), f"{fmt(pos_now())} / {fmt(track['duration'])}", f_tag)
    if c.get("mute"):
        t = "MUTE"; draw.rectangle((W - draw.textlength(t, font=f_tag) - 5, 0, W - 1, 8), fill=255)
        draw.text((W - draw.textlength(t, font=f_tag) - 3, 0), t, font=f_tag, fill=0)
    else:
        t = str(vol); tl = draw.textlength(t, font=f_tag)
        draw.text((W - 1 - tl, 0), t, font=f_tag, fill=255)
        vol_bar(draw, W - tl - 26, 0, 21, 7, vol, 7)

    # linje 2: tittel (ruller), linje 3: artist / undertekst
    if inp == "radio" and r.get("station"):
        title = r["station"]; sub = " – ".join(x for x in (r.get("artist"), r.get("song")) if x) or "Radio"
    elif inp in ("airplay", "bt") and track.get("title"):
        title, sub = track["title"], track.get("artist", "")
    else:
        title, sub = NAMES.get(inp, inp), SUB.get(inp, "")
        if inp == "bt" and track.get("bt_device"):
            sub = track["bt_device"]
    w = draw.textlength(title, font=f_title)
    if w > W:
        _mem["scroll"] = (_mem["scroll"] + 1.2) % (w + 24)
        draw.text((-_mem["scroll"], 10), title, font=f_title, fill=255)
        draw.text((-_mem["scroll"] + w + 24, 10), title, font=f_title, fill=255)
    else:
        _mem["scroll"] = 0; draw.text((0, 10), title, font=f_title, fill=255)
    draw.rectangle((0, 22, W, 23), fill=0)

    if inp in ("aux", "usb"):   # nivåmeter-animasjon
        dim(draw, (0, 24), sub, f_tag)
        x0 = draw.textlength(sub, font=f_tag) + 6
        for i in range(int((W - x0) / 4)):
            h = 1 + 6 * abs(math.sin(now * 3 + i * 0.7)) * (0.3 + 0.7 * abs(math.sin(now * 0.9 + i)))
            draw.rectangle((x0 + i * 4, 31 - h, x0 + i * 4 + 2, 31), fill=255)
        return
    dim(draw, (0, 23), fit(draw, sub, f_sub, W), f_sub)
    if inp in ("airplay", "bt") and track.get("duration"):   # fremdrift helt nederst
        p = min(1, pos_now() / track["duration"])
        draw.line((0, 31, W - 1, 31), fill=0)
        for xx in range(0, W, 2):
            draw.point((xx, 31), fill=255)
        draw.line((0, 31, int((W - 1) * p), 31), fill=255)


def boot(draw, p):
    power_icon(draw, 8, 12, 6)
    draw.text((22, 3), "PULTFORSTERKER", font=f_boot, fill=255)
    draw.rectangle((22, 18, 126, 21), outline=255); draw.rectangle((22, 18, 22 + 104 * p, 21), fill=255)
    s = "Starter AirPlay" if p < 0.5 else ("Starter Bluetooth" if p < 0.9 else "Klar")
    dim(draw, (22, 23), s, f_tag)
