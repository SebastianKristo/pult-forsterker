#!/usr/bin/env python3
"""Pultforsterker v2 – OLED 2,42" SSD1309 128x64 (I2C 0x3C, RES på GPIO 4).

Layout etter design_handoff (hovedskjerm):
  y 1–10   : fire felt AIR / BT / AUX / USB (aktiv = fylt), BT stiplet når BT er av
  y 14–28  : tittel, fet, ruller hvis bredere enn 124 px
  y 31     : artist / kilde (dim)
  y 37–44  : play/pause + fremdriftslinje + tid (AirPlay/BT) eller nivåmeter (AUX/USB)
  y 50–60  : VOL + 24 segmenter + tall, eller MUTE
Overlegg: parring, standby (skjerm av), oppstart.
Metadata: AirPlay fra Shairport Sync-pipen, Bluetooth fra BlueZ (MediaPlayer1 over D-Bus).
Kilde/volum/mute/strøm leses fra /run/pultamp_ctrl.json (skrevet av ki_amp_daemon.py).
"""
import base64
import json
import math
import os
import re
import select
import threading
import time

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1309
from PIL import ImageFont

PIPE = "/run/shairport-sync/metadata"   # ikke /tmp: fs.protected_fifos hindrer root i å åpne en annen brukers FIFO der
CTRL_FILE = "/run/pultamp_ctrl.json"
STATUS_FILE = "/run/pultamp_status.json"
COVER_FILE = "/run/pultamp_cover"   # albumbilde fra AirPlay (jpg/png), serveres av ki_amp_daemon på /api/cover
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
f_tag, f_title, f_sub, f_small, f_vol, f_num = F(FONT_B, 7), F(FONT_B, 11), F(FONT_R, 8), F(FONT_R, 7), F(FONT_B, 7), F(FONT_B, 12)
LABELS = {"airplay": "AIR", "bt": "BT", "aux": "AUX", "usb": "USB"}
SRC_TEXT = {"aux": ("Analog inngang", "3,5 mm jack"), "usb": ("USB-lyd", "PC"), "airplay": ("AirPlay", "Venter på enhet …"), "bt": ("Bluetooth", "")}

try:
    device = ssd1309(i2c(port=1, address=0x3C), gpio_RST=4)
except Exception as e:   # ingen OLED koblet til: kjør videre som metadata-tjeneste (AirPlay/BT → API, HA, Homey)
    print("OLED ikke funnet – kjører uten skjerm:", e, flush=True)
    device = None
track = {"album": "", "cover": "", "paused": False, "playing": False, "title": "", "artist": "", "duration": 0, "position": 0, "pos_t": 0.0, "bt_device": "", "source": ""}
boot_until = time.time() + 1.6
scroll_x = 0.0


# ---------- AirPlay-metadata ----------
item_re = re.compile(r"<item><type>([0-9a-f]+)</type><code>([0-9a-f]+)</code><length>(\d+)</length>(?:\s*<data encoding=\"base64\">\s*([^<]*)</data>)?</item>", re.S)


def airplay_thread():
    buf = ""
    while True:
        if not os.path.exists(PIPE):
            time.sleep(1); continue
        with open(PIPE, "r", errors="replace") as fh:
            while True:
                r, _, _ = select.select([fh], [], [], 1.0)
                if not r:
                    continue
                chunk = fh.read(4096)
                if not chunk:
                    break
                buf += chunk
                for m in item_re.finditer(buf):
                    t, c = bytes.fromhex(m.group(1)).decode("ascii", "replace"), bytes.fromhex(m.group(2)).decode("ascii", "replace")
                    data = base64.b64decode(m.group(4)).decode("utf-8", "replace") if m.group(4) else ""
                    if t == "core" and c == "minm": track["title"] = data
                    elif t == "core" and c == "asar": track["artist"] = data
                    elif t == "core" and c == "asal": track["album"] = data
                    elif t == "core" and c == "astm":
                        try: track["duration"] = int.from_bytes(base64.b64decode(m.group(4)), "big") / 1000
                        except Exception: pass
                    elif t == "ssnc" and c == "PICT":   # albumbilde
                        try:
                            img = base64.b64decode(m.group(4) or "")
                            if img:
                                with open(COVER_FILE + ".tmp", "wb") as fh: fh.write(img)
                                os.replace(COVER_FILE + ".tmp", COVER_FILE)
                                import hashlib; track["cover"] = hashlib.sha1(img).hexdigest()[:12]
                            else:
                                track["cover"] = ""
                        except Exception: pass
                    elif t == "ssnc" and c == "mdst":   # ny metadata-sekvens (nytt spor) – bildet kommer etterpå
                        pass
                    elif t == "ssnc" and c in ("pbeg", "prsm"): track.update(playing=True, paused=False, source="airplay")
                    elif t == "ssnc" and c == "pfls":   # pause/flush – behold tittelen
                        track.update(playing=False, paused=True)
                    elif t == "ssnc" and c == "pend":
                        track.update(playing=False, paused=False, title="", artist="", album="", duration=0, position=0, cover="")
                    elif t == "ssnc" and c == "prgr":
                        try:
                            s, cur, e = (int(x) for x in data.split("/")); track["position"] = (cur - s) / 44100; track["duration"] = (e - s) / 44100; track["pos_t"] = time.time()
                        except Exception: pass
                if "</item>" in buf:
                    buf = buf[buf.rfind("</item>") + 7:]
                elif len(buf) > 4_000_000:   # albumbilder kan være store – kast bare ved åpenbart søppel
                    buf = ""


# ---------- Bluetooth-metadata (BlueZ MediaPlayer1) ----------
def bt_thread():
    try:
        import dbus
    except ImportError:
        return
    bus = dbus.SystemBus()
    while True:
        try:
            om = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
            objs = om.GetManagedObjects()
            for path, ifs in objs.items():   # stol på parrede enheter, så de kobler til igjen av seg selv
                d1 = ifs.get("org.bluez.Device1")
                if d1 and d1.get("Paired") and not d1.get("Trusted"):
                    dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties").Set("org.bluez.Device1", "Trusted", dbus.Boolean(True))
            found = False
            for path, ifs in objs.items():
                mp = ifs.get("org.bluez.MediaPlayer1")
                if mp is None:
                    continue
                found = True
                dev = objs.get(str(mp.get("Device", path.rsplit("/", 1)[0])), {}).get("org.bluez.Device1", {})
                tr = mp.get("Track", {})
                status = str(mp.get("Status", ""))
                playing = status == "playing"
                if playing or track["source"] == "bt":
                    track.update(source="bt", cover="", playing=playing, paused=status == "paused", title=str(tr.get("Title", "")), artist=str(tr.get("Artist", "")), album=str(tr.get("Album", "")),
                                 duration=int(tr.get("Duration", 0)) / 1000, position=int(mp.get("Position", 0)) / 1000, pos_t=time.time())
                track["bt_device"] = str(dev.get("Alias", "")) if dev else track["bt_device"]
            if not found:
                track["bt_device"] = ""
                if track["source"] == "bt":
                    track.update(playing=False, title="", artist="", source="")
        except Exception:
            pass
        time.sleep(1)


def write_status():
    try:
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w") as fh:
            out = {k: track[k] for k in ("playing", "paused", "source", "title", "artist", "album", "duration", "bt_device", "cover")}
            out["position"] = round(pos_now(), 1)
            json.dump(out, fh)
        os.replace(tmp, STATUS_FILE)
    except Exception:
        pass


def read_ctrl():
    try:
        with open(CTRL_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {"power": True, "input": "airplay", "volume": 0, "mute": False, "bt_pairing": False}


def pos_now():
    if not track["playing"]:
        return track["position"]
    return min(track["duration"] or 1e9, track["position"] + time.time() - track["pos_t"])


def fmt(s):
    s = int(max(0, s)); return f"{s // 60}:{s % 60:02d}"


def dim_text(draw, xy, text, font):
    """«Dim» tekst = tegnet, så annenhver piksel fjernes (prikkmønster)."""
    draw.text(xy, text, font=font, fill=255)
    x0, y0 = xy; w = draw.textlength(text, font=font); h = font.size + 3
    for x in range(int(x0), int(x0 + w) + 1):
        for y in range(int(y0), int(y0 + h)):
            if (x + y) % 2: draw.point((x, y), fill=0)


def draw_main(draw, c):
    global scroll_x
    inp = c.get("input", "airplay"); bt_on = c.get("bt_on", True) or c.get("bt_pairing")
    # inngangsfelter
    x = 2
    for k in ("airplay", "bt", "aux", "usb"):
        w = draw.textlength(LABELS[k], font=f_tag) + 7
        if k == inp:
            draw.rectangle((x, 1, x + w, 10), fill=255); draw.text((x + 3.5, 1), LABELS[k], font=f_tag, fill=0)
        else:
            if k == "bt" and not bt_on:
                for xx in range(int(x), int(x + w), 3): draw.point((xx, 1), 255); draw.point((xx, 10), 255)
            else:
                draw.rectangle((x, 1, x + w, 10), outline=255)
            dim_text(draw, (x + 3.5, 1), LABELS[k], f_tag)
        if k == "bt" and track["bt_device"] and inp != "bt":
            draw.rectangle((x + w - 3, 2, x + w - 2, 3), fill=255)
        x += w + 2.5
    # tittel + undertekst
    has_meta = inp in ("airplay", "bt") and track["playing"] and track["title"]
    title, sub = (track["title"], track["artist"]) if has_meta else SRC_TEXT.get(inp, ("", ""))
    if inp == "bt" and not has_meta:
        sub = track["bt_device"] or "Ingen enhet tilkoblet"
    tw = draw.textlength(title, font=f_title)
    if tw > 124:
        scroll_x = (scroll_x + 1.4) % (tw + 30)
        draw.text((2 - scroll_x, 14), title, font=f_title, fill=255); draw.text((2 - scroll_x + tw + 30, 14), title, font=f_title, fill=255)
    else:
        scroll_x = 0; draw.text((2, 14), title, font=f_title, fill=255)
    draw.rectangle((0, 11, 127, 13), fill=0); draw.rectangle((0, 28, 127, 29), fill=0)
    dim_text(draw, (2, 29), sub, f_sub)
    # rad 3
    if inp in ("airplay", "bt"):
        if track["playing"]:
            draw.polygon([(2, 37.5), (7, 40.5), (2, 43.5)], fill=255)
        else:
            draw.rectangle((2, 37.5, 3.8, 43.5), fill=255); draw.rectangle((5, 37.5, 6.8, 43.5), fill=255)
        draw.rectangle((11, 39.5, 97, 40.9), outline=255)
        if track["duration"]:
            p = 11 + 86 * min(1, pos_now() / track["duration"])
            draw.rectangle((11, 39.5, p, 40.9), fill=255); draw.rectangle((p - 1, 38.5, p + 1, 42.5), fill=255)
        t = fmt(pos_now()); draw.text((126 - draw.textlength(t, font=f_small), 37), t, font=f_small, fill=255)
    else:
        tt = time.time()
        for i in range(22):
            h = 1 + 6 * abs(math.sin(tt * 3 + i * 0.7)) * (0.3 + 0.7 * abs(math.sin(tt * 0.9 + i)))
            draw.rectangle((2 + i * 5.6, 44 - h, 2 + i * 5.6 + 4, 44), fill=255)
    # volum / mute
    vol = int(c.get("volume", 0))
    if c.get("mute"):
        draw.rectangle((2, 50, 6, 55), fill=255); draw.polygon([(6, 50), (10, 47.5), (10, 57.5), (6, 55)], fill=255)
        draw.line((13, 49.5, 19, 55.5), fill=255); draw.line((13, 55.5, 19, 49.5), fill=255)
        draw.text((126 - draw.textlength("MUTE", font=f_num), 47), "MUTE", font=f_num, fill=255)
        dim_text(draw, (26, 52), f"vol {vol}", f_small)
    else:
        dim_text(draw, (2, 52), "VOL", f_vol)
        step = 84 / 24; on = round(vol / 100 * 24)
        for i in range(24):
            x0 = 17 + i * step; h = 3 + i * 0.25
            draw.rectangle((x0, 59 - h, x0 + step - 1, 59), fill=255 if i < on else 0, outline=255 if i < on else None)
            if i >= on: draw.point((x0 + 1, 59), 255)
        draw.text((126 - draw.textlength(str(vol), font=f_num), 47), str(vol), font=f_num, fill=255)
    # loudness-indikator: liten "LD" under kildefeltene til høyre (vises bare når aktiv og på digital kilde)
    if c.get("loudness") and c.get("input") != "aux":
        dim_text(draw, (113, 12), "LD", f_small)


def draw_overlay(draw, c):
    if c.get("bt_pairing"):
        t = time.time(); r = 6 + (t * 10) % 21
        draw.ellipse((64 - r, 19 - r, 64 + r, 19 + r), outline=255)
        draw.text((64 - draw.textlength("Parring" + "." * (1 + int(t * 2) % 3), font=f_title) / 2, 35), "Parring" + "." * (1 + int(t * 2) % 3), font=f_title, fill=255)
        dim_text(draw, (64 - draw.textlength("Synlig som «Pultforsterker»", font=f_small) / 2, 48), "Synlig som «Pultforsterker»", f_small)
        dim_text(draw, (64 - draw.textlength("Hold AIRPLAY for å avbryte", font=f_small) / 2, 57), "Hold AIRPLAY for å avbryte", f_small)
        return True
    return False


def draw_boot(draw):
    p = 1 - max(0, boot_until - time.time()) / 1.6
    draw.ellipse((57, 13, 71, 27), outline=255); draw.rectangle((63, 11, 65, 20), fill=0); draw.line((64, 12, 64, 19), fill=255)
    draw.text((64 - draw.textlength("PULTFORSTERKER", font=f_title) / 2, 33), "PULTFORSTERKER", font=f_title, fill=255)
    draw.rectangle((34, 49, 94, 51), outline=255); draw.rectangle((34, 49, 34 + 60 * p, 51), fill=255)
    s = "Starter AirPlay" if p < 0.5 else ("Starter Bluetooth" if p < 0.9 else "Klar")
    dim_text(draw, (64 - draw.textlength(s, font=f_small) / 2, 55), s, f_small)


def main():
    global boot_until
    threading.Thread(target=airplay_thread, daemon=True).start()
    threading.Thread(target=bt_thread, daemon=True).start()
    was_on = True
    while True:
        c = read_ctrl()
        write_status()
        if device is None:
            time.sleep(0.5); continue
        if not c.get("power", True):
            if was_on:
                device.hide(); was_on = False
            time.sleep(0.2); continue
        if not was_on:
            device.show(); was_on = True; boot_until = time.time() + 1.6
        with canvas(device) as draw:
            if time.time() < boot_until:
                draw_boot(draw)
            elif not draw_overlay(draw, c):
                draw_main(draw, c)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
