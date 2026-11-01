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

try:   # KI_AMP_DISPLAY=none (Skjold Node): ingen skjerm, bare metadata-tjeneste – luma trengs ikke
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306, ssd1309
except ImportError:
    i2c = canvas = ssd1306 = ssd1309 = None
from PIL import ImageFont

PIPE = "/run/shairport-sync/metadata"   # ikke /tmp: fs.protected_fifos hindrer root i å åpne en annen brukers FIFO der
CTRL_FILE = "/run/pultamp_ctrl.json"
STATUS_FILE = "/run/pultamp_status.json"
COVER_FILE = "/run/pultamp_cover"   # albumbilde fra AirPlay (jpg/png), serveres av ki_amp_daemon på /api/cover
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
f_tag, f_title, f_sub, f_small, f_vol, f_num = F(FONT_B, 7), F(FONT_B, 11), F(FONT_R, 8), F(FONT_R, 7), F(FONT_B, 7), F(FONT_B, 12)
LABELS = {"radio": "RAD", "airplay": "AIR", "bt": "BT", "aux": "AUX", "aux2": "AX2", "usb": "USB"}
SRC_TEXT = {"radio": ("Radio", "Velg kanal 1–6"), "aux": ("AUX 1", "3,5 mm inngang 1"), "aux2": ("AUX 2", "3,5 mm inngang 2"), "usb": ("USB-lyd", "PC"), "airplay": ("AirPlay", "Venter på enhet …"), "bt": ("Bluetooth", "")}

# KI_AMP_OLED: ssd1309_128x64 (2,42", standard) | ssd1306_128x32 (0,91") | ssd1306_128x64 (0,96")
# KI_AMP_DISPLAY=tft: 2,8" SPI TFT 320x240 (ILI9341/ST7789V via fbtft, touch via ads7846) i stedet for OLED
OLED = os.environ.get("KI_AMP_OLED", "ssd1309_128x64")
DISPLAY = os.environ.get("KI_AMP_DISPLAY", "oled").strip().lower()
tft = tft_fb = None
try:
    if DISPLAY == "none" or i2c is None:
        raise RuntimeError("KI_AMP_DISPLAY=none")
    elif DISPLAY == "tft":
        import tft_screen as tft
        tft_fb = tft.find_fb()
        if not tft_fb:
            raise RuntimeError("ingen fbtft-framebuffer (sjekk dtoverlay=fbtft,... i config.txt)")
        print("TFT:", tft_fb, flush=True)
        device = None
    elif OLED.startswith("ssd1306"):
        device = ssd1306(i2c(port=1, address=int(os.environ.get("KI_AMP_OLED_ADDR", "0x3C"), 16)), width=128,
                         height=32 if OLED.endswith("x32") else 64)
    else:
        device = ssd1309(i2c(port=1, address=0x3C), gpio_RST=4)
except Exception as e:   # ingen OLED koblet til: kjør videre som metadata-tjeneste (AirPlay/BT → API, HA, Homey)
    print("OLED ikke funnet – kjører uten skjerm:", e, flush=True)
    device = None
track = {"album": "", "cover": "", "paused": False, "playing": False, "title": "", "artist": "", "duration": 0, "position": 0, "pos_t": 0.0, "bt_device": "", "source": "", "airplay_device": ""}
boot_until = time.time() + 1.6
scroll_x = 0.0


# ---------- AirPlay-metadata ----------
item_re = re.compile(r"<item><type>([0-9a-f]+)</type><code>([0-9a-f]+)</code><length>(\d+)</length>(?:\s*<data encoding=\"base64\">\s*([^<]*)</data>)?</item>", re.S)


def airplay_thread():
    buf = ""
    while True:
        if not os.path.exists(PIPE):
            time.sleep(1); continue
        # Rå fil-deskriptor + os.read: gir det som ligger i pipen med en gang. (Tekst-read(4096) venter til
        # 4096 tegn har kommet, så metadata for en ny låt ble liggende til neste låt – «henger på forrige».)
        fd = os.open(PIPE, os.O_RDONLY | os.O_NONBLOCK)
        try:
            while True:
                r, _, _ = select.select([fd], [], [], 1.0)
                if not r:
                    continue
                try:
                    raw = os.read(fd, 65536)
                except BlockingIOError:
                    continue
                if not raw:
                    time.sleep(0.2); continue     # ingen skriver akkurat nå (Shairport startet på nytt) – vent
                buf += raw.decode("utf-8", "replace")
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
                                track["cover_key"] = (track["artist"], track["title"])
                                print("Albumbilde fra AirPlay", len(img), "byte", flush=True)
                            else:
                                track["cover"] = ""
                        except Exception: pass
                    elif t == "ssnc" and c == "snam":   # navnet på AirPlay-klienten («Sebastians iPhone»)
                        track["airplay_device"] = data
                    elif t == "ssnc" and c == "disc":   # klienten koblet fra
                        track["airplay_device"] = ""
                    elif t == "ssnc" and c == "mdst":   # ny metadata-sekvens (nytt spor): tøm gamle felt
                        track.update(title="", artist="", album="")
                    elif t == "ssnc" and c in ("pbeg", "prsm"): track.update(playing=True, paused=False, source="airplay")
                    elif t == "ssnc" and c == "pfls":   # pause/flush – behold tittelen
                        track.update(playing=False, paused=True)
                    elif t == "ssnc" and c == "pend":
                        track.update(playing=False, paused=False, title="", artist="", album="", duration=0, position=0, cover="")
                    elif t == "ssnc" and c == "pvol":   # volum fra iPhone/Mac: «airplay_volume,…» −30…0 dB, −144 = mute
                        try:
                            av = float(data.split(",")[0])
                            threading.Thread(target=_post_volume, args=(0 if av <= -30 else round(100 * (av + 30) / 30),), daemon=True).start()
                        except Exception: pass
                    elif t == "ssnc" and c == "prgr":
                        try:
                            s, cur, e = (int(x) for x in data.split("/")); track["position"] = (cur - s) / 44100; track["duration"] = (e - s) / 44100; track["pos_t"] = time.time()
                        except Exception: pass
                if "</item>" in buf:
                    buf = buf[buf.rfind("</item>") + 7:]
                elif len(buf) > 4_000_000:   # albumbilder kan være store – kast bare ved åpenbart søppel
                    buf = ""
        finally:
            os.close(fd)


# ---------- albumbilde: AirPlay sender det selv (PICT); ellers (Bluetooth, AirPlay uten bilde) slås det opp i iTunes ----------
def art_thread():
    import hashlib
    import urllib.parse
    import urllib.request
    last, since, tried = None, 0.0, set()
    while True:
        time.sleep(1)
        key = (track["artist"], track["title"]) if track["title"] else None
        if key != last:
            last, since = key, time.time()
            if track.get("cover_key") != key:
                track["cover"] = ""          # ikke vis forrige låts bilde
            continue
        if not key or track.get("cover_key") == key or key in tried or time.time() - since < 3:
            continue
        tried.add(key)
        try:
            q = urllib.parse.urlencode({"term": f"{key[0]} {key[1]}".strip(), "entity": "song", "limit": 1, "country": "NO"})
            with urllib.request.urlopen("https://itunes.apple.com/search?" + q, timeout=6) as r:
                res = json.loads(r.read()).get("results", [])
            if not res:
                print("Albumbilde: ingen treff for", key, flush=True); continue
            url = res[0].get("artworkUrl100", "").replace("100x100bb", "600x600bb")
            with urllib.request.urlopen(url, timeout=6) as r:
                img = r.read()
            if (track["artist"], track["title"]) != key:
                continue
            with open(COVER_FILE + ".tmp", "wb") as fh: fh.write(img)
            os.replace(COVER_FILE + ".tmp", COVER_FILE)
            track["cover"] = hashlib.sha1(img).hexdigest()[:12]; track["cover_key"] = key
            print("Albumbilde fra iTunes:", key, flush=True)
        except Exception as e:
            print("Albumbilde:", e, flush=True)


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
                    track.update(source="bt", playing=playing, paused=status == "paused", title=str(tr.get("Title", "")), artist=str(tr.get("Artist", "")), album=str(tr.get("Album", "")),
                                 duration=int(tr.get("Duration", 0)) / 1000, position=int(mp.get("Position", 0)) / 1000, pos_t=time.time())
                track["bt_device"] = str(dev.get("Alias", "")) if dev else track["bt_device"]
            if not found:
                track["bt_device"] = ""
                if track["source"] == "bt":
                    track.update(playing=False, title="", artist="", source="")
        except Exception:
            pass
        time.sleep(1)


def _post_volume(v):
    """AirPlay-volumet blir forsterkerens volum (som en vanlig AirPlay-høyttaler)."""
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{os.environ.get('KI_AMP_PORT', '8765')}/api/volume",
                               data=json.dumps({"volume": v, "source": "airplay"}).encode(), method="POST"), timeout=2).read()
    except Exception as e:
        print("AirPlay-volum:", e, flush=True)


def write_status():
    try:
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w") as fh:
            out = {k: track[k] for k in ("playing", "paused", "source", "title", "artist", "album", "duration", "bt_device", "cover", "airplay_device")}
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
    keys = ("radio", "airplay", "bt", "aux", "usb") if c.get("lyrion") or inp == "radio" else ("airplay", "bt", "aux", "usb")
    pad = 5 if len(keys) == 5 else 7
    for k in keys:
        w = draw.textlength(LABELS[k], font=f_tag) + pad
        if k == inp:
            draw.rectangle((x, 1, x + w, 10), fill=255); draw.text((x + pad / 2, 1), LABELS[k], font=f_tag, fill=0)
        else:
            if k == "bt" and not bt_on:
                for xx in range(int(x), int(x + w), 3): draw.point((xx, 1), 255); draw.point((xx, 10), 255)
            else:
                draw.rectangle((x, 1, x + w, 10), outline=255)
            dim_text(draw, (x + pad / 2, 1), LABELS[k], f_tag)
        if k == "bt" and track["bt_device"] and inp != "bt":
            draw.rectangle((x + w - 3, 2, x + w - 2, 3), fill=255)
        x += w + 2.5
    # tittel + undertekst
    has_meta = inp in ("airplay", "bt") and track["playing"] and track["title"]
    title, sub = (track["title"], track["artist"]) if has_meta else SRC_TEXT.get(inp, ("", ""))
    if inp == "radio":
        r = c.get("radio") or {}
        if r.get("station"):
            title = r["station"]
            sub = " – ".join(x for x in (r.get("artist"), r.get("song")) if x) or (f"Kanal {c['preset']}" if c.get("preset") else "Radio")
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
    if inp == "radio" and (c.get("radio") or {}).get("station"):
        playing = (c.get("radio") or {}).get("mode") == "play"
        if playing:
            draw.polygon([(2, 37.5), (7, 40.5), (2, 43.5)], fill=255)
        else:
            draw.rectangle((2, 37.5, 3.8, 43.5), fill=255); draw.rectangle((5, 37.5, 6.8, 43.5), fill=255)
        x = 14
        for i in range(6):   # kanal 1–6, aktiv fylt
            on = c.get("preset") == i + 1
            draw.rectangle((x, 37, x + 12, 44), fill=255 if on else 0, outline=255)
            draw.text((x + 4, 36.5), str(i + 1), font=f_small, fill=0 if on else 255)
            x += 15
    elif inp in ("airplay", "bt"):
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
    m = c.get("menu")
    if m:   # kanalmeny: vri = velg, trykk = spill, hold = lagre
        presets = c.get("presets") or []
        draw.text((2, 0), "RADIOKANALER", font=f_tag, fill=255)
        draw.text((126 - draw.textlength("vri · trykk", font=f_small), 0), "vri · trykk", font=f_small, fill=255)
        idx = m.get("idx", 1)
        first = min(max(1, idx - 1), max(1, len(presets) - 2))   # vis 3 rader, valgt rad i midten (6–50 plasser)
        for row, n in enumerate(range(first, first + 3)):
            y = 12 + row * 14
            p = presets[n - 1] if n - 1 < len(presets) else None
            name = (p or {}).get("title") or "– tom –"
            sel = n == idx
            if sel:
                draw.rectangle((0, y - 1, 127, y + 11), fill=255)
            col = 0 if sel else 255
            draw.text((3, y), str(n), font=f_title, fill=col)
            if sel or p:
                draw.text((15, y + 1), name[:20], font=f_sub, fill=col)
            else:
                dim_text(draw, (15, y + 1), name, f_sub)
            if n == c.get("preset") and c.get("input") == "radio":
                draw.polygon([(120, y + 2), (125, y + 5), (120, y + 8)], fill=col)
        draw.text((2, 55), "hold = lagre det som spiller her", font=f_small, fill=255)
        return True
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


SMALL = device is not None and device.height == 32 or OLED.endswith("x32")
if SMALL:
    import oled_small as small


# ---------- nettverk: IP vises etter oppstart og når forbindelsen kommer/går ----------
NET = {"ip": None, "show_until": 0.0}


def _ip_now():
    import socket
    try:   # kabelen ute og ikke Wi-Fi heller → ingen nett, selv om adressen fortsatt står på eth0
        up = lambda i: open(f"/sys/class/net/{i}/operstate").read().strip() == "up"
        if os.path.exists("/sys/class/net/eth0") and not up("eth0") and not (os.path.exists("/sys/class/net/wlan0") and up("wlan0")):
            return ""
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1)); ip = s.getsockname()[0]; s.close()
        return "" if ip.startswith("127.") else ip
    except Exception:
        return ""


def net_thread():
    while True:
        ip = _ip_now()
        if ip != NET["ip"]:
            if NET["ip"] is not None:          # endret etter oppstart: vis i 5 s
                NET["show_until"] = time.time() + 5
            print("Nettverk:", ip or "ingen", flush=True)
            NET["ip"] = ip
        time.sleep(3)


def draw_ip(draw, w, h):
    ip = NET["ip"]
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11 if h <= 32 else 13)
    sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8 if h <= 32 else 9)
    head, line = ("NETTVERK", ip) if ip else ("INGEN NETTVERK", "sjekk kabelen")
    draw.text(((w - draw.textlength(head, font=sm)) / 2, 2 if h <= 32 else 14), head, font=sm, fill=255)
    draw.text(((w - draw.textlength(line, font=big)) / 2, 14 if h <= 32 else 30), line, font=big, fill=255)


USBOV = {"pc": None, "until": 0.0}


def usb_icon(draw, cx, cy, s):
    """Enkelt USB-symbol: stamme, pil opp, sirkel nede, to grener."""
    draw.line((cx, cy - s, cx, cy + s), fill=255)
    draw.polygon([(cx, cy - s - 2), (cx - 2, cy - s + 1), (cx + 2, cy - s + 1)], fill=255)
    draw.ellipse((cx - 2, cy + s - 1, cx + 2, cy + s + 3), fill=255)
    draw.line((cx, cy + 2, cx - s * 0.6, cy - 1, cx - s * 0.6, cy - s * 0.4), fill=255)
    draw.rectangle((cx - s * 0.6 - 1, cy - s * 0.4 - 2, cx - s * 0.6 + 1, cy - s * 0.4), fill=255)
    draw.line((cx, cy + 4, cx + s * 0.6, cy + 1, cx + s * 0.6, cy - s * 0.3), fill=255)
    draw.ellipse((cx + s * 0.6 - 1.5, cy - s * 0.3 - 3, cx + s * 0.6 + 1.5, cy - s * 0.3), fill=255)


def draw_usbsw(draw, w, h, name):
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11 if h <= 32 else 12)
    sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7 if h <= 32 else 8)
    head = "USB → " + name
    if h <= 32:
        usb_icon(draw, 9, 15, 8)
        draw.text((22, 3), head, font=big, fill=255)
        draw.text((22, 19), "alt på USB fulgte med", font=sm, fill=255)
    else:
        usb_icon(draw, 64, 15, 9)
        draw.text(((w - draw.textlength(head, font=big)) / 2, 30), head, font=big, fill=255)
        t = next(x for x in ("Tastatur, disk og lyd fulgte med", "Alt på USB fulgte med") if draw.textlength(x, font=sm) <= w - 4)
        draw.text(((w - draw.textlength(t, font=sm)) / 2, 47), t, font=sm, fill=255)


def render(draw, c):
    if c.get("usbsw"):   # overlegg i 2,2 s når USB-switchen bytter PC
        pc = c.get("usb_pc")
        if USBOV["pc"] is not None and pc != USBOV["pc"]:
            USBOV["until"] = time.time() + 2.2
        USBOV["pc"] = pc
        if time.time() < USBOV["until"]:
            names = c.get("usb_pc_names") or ["PC 1", "PC 2"]
            draw_usbsw(draw, device.width if device else 128, device.height if device else 64, names[(pc or 1) - 1]); return
    if not (time.time() < boot_until) and (time.time() < NET["show_until"]):
        draw_ip(draw, device.width if device else 128, device.height if device else 64); return
    if SMALL:
        if time.time() < boot_until:
            small.boot(draw, 1 - max(0, boot_until - time.time()) / 1.6)
        elif not small.overlay(draw, c, track, time.time()):
            small.main_screen(draw, c, track, pos_now)
        return
    if time.time() < boot_until:
        draw_boot(draw)
    elif not draw_overlay(draw, c):
        draw_main(draw, c)


# ---------- demo: alle skjermbilder etter tur, uten daemon (python3 oled_display.py --demo) ----------
DEMO_PRESETS = [{"n": 1, "title": "NRK P1"}, {"n": 2, "title": "NRK P3"}, {"n": 3, "title": "P4 Lyden av Norge"},
                {"n": 4, "title": "Radio Norge"}, {"n": 5, "title": ""}, {"n": 6, "title": ""}]


def demo_frame(t):
    """Returnerer (navn, ctrl, track-oppdatering) for tidspunkt t (sekunder) i en 48 s løkke."""
    t %= 48
    c = {"power": True, "input": "airplay", "volume": 42, "mute": False, "bt_pairing": False, "presets": DEMO_PRESETS,
         "preset": 2, "lyrion": True}
    tr = {"playing": True, "paused": False, "title": "Midnight City – Extended Version", "artist": "M83",
          "duration": 243, "position": 61 + t, "pos_t": time.time(), "bt_device": ""}
    if t < 2:
        return "oppstart", c, tr, True
    if t < 7:
        return "AirPlay spiller", c, tr, False
    if t < 11:
        c["volume"] = int(42 + 30 * math.sin((t - 7) / 4 * math.pi)); return "volum", c, tr, False
    if t < 13:
        c["mute"] = True; return "mute", c, tr, False
    if t < 15:
        c["input"] = "bt"; tr.update(playing=False, title=""); return "kildebytte BT", c, tr, False
    if t < 20:
        c.update(input="bt", bt_pairing=True); tr.update(playing=False, title=""); return "BT-parring", c, tr, False
    if t < 25:
        c["input"] = "bt"; tr.update(bt_device="Sebastian sin iPhone", title="Teardrop", artist="Massive Attack",
                                     duration=330, position=12 + (t - 20)); return "BT tilkoblet / spiller", c, tr, False
    if t < 31:
        c["input"] = "radio"; c["radio"] = {"mode": "play", "station": "NRK P3", "song": "Flowers", "artist": "Miley Cyrus"}
        c["station"] = "NRK P3"; return "Radio", c, tr, False
    if t < 38:
        c["input"] = "radio"; c["menu"] = {"idx": 1 + int((t - 31) / 1.2) % 6}
        c["radio"] = {"mode": "play", "station": "NRK P3"}; return "kanalmeny", c, tr, False
    if t < 43:
        c["input"] = "aux"; return "AUX (nivåmeter)", c, tr, False
    c["input"] = "usb"; return "USB", c, tr, False


def demo():
    global boot_until
    t0 = time.time(); last = None
    while True:
        t = time.time() - t0
        name, c, tr, booting = demo_frame(t)
        track.update(tr)
        if booting and last != name:
            boot_until = time.time() + 1.6
        if name != last:
            print("Demo:", name, flush=True); last = name
        with canvas(device) as draw:
            if not booting:
                boot_until = 0
            render(draw, c)
        time.sleep(0.08)


def main():
    global boot_until
    import sys
    if "--demo" in sys.argv:
        if device is None:
            print("Fant ingen skjerm – sjekk koblingene og i2cdetect -y 1"); return
        demo(); return
    NET["show_until"] = boot_until + 4          # vis IP-adressen 4 s etter oppstartsbildet
    threading.Thread(target=net_thread, daemon=True).start()
    threading.Thread(target=airplay_thread, daemon=True).start()
    threading.Thread(target=bt_thread, daemon=True).start()
    threading.Thread(target=art_thread, daemon=True).start()
    was_on = True
    if tft_fb:   # TFT: egen løkke – baklys på GPIO 13 (PWM), touch via evdev
        bl = None
        try:
            from gpiozero import PWMLED
            bl = PWMLED(13, frequency=1000); bl.value = 1.0
        except Exception as e:
            print("TFT-baklys:", e, flush=True)
        threading.Thread(target=tft.Touch(read_ctrl).run, daemon=True).start()
        with open(tft_fb, "r+b", buffering=0) as fb:
            while True:
                c = read_ctrl(); write_status()
                if not c.get("power", True):
                    if was_on:
                        if bl: bl.value = 0.0
                        fb.seek(0); fb.write(bytes(tft.W * tft.H * 2)); was_on = False
                    time.sleep(0.2); continue
                if not was_on:
                    was_on = True; boot_until = time.time() + 1.6; NET["show_until"] = boot_until + 4
                    if bl: bl.value = 1.0
                bp = 1 - max(0, boot_until - time.time()) / 1.6 if time.time() < boot_until else None
                net = NET["ip"] if (bp is None and time.time() < NET["show_until"]) else None
                c["inputs"] = ["radio", "airplay", "bt", "aux", "aux2", "usb"] if c.get("lyrion") else ["airplay", "bt", "aux", "aux2", "usb"]
                fb.seek(0); fb.write(tft.to_rgb565(tft.frame(c, track, pos_now, bp, net)))
                time.sleep(0.08)
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
            device.show(); was_on = True; boot_until = time.time() + 1.6; NET["show_until"] = boot_until + 4
        with canvas(device) as draw:
            render(draw, c)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
