#!/usr/bin/env python3
"""Pultforsterker v2 – daemon på Raspberry Pi Zero 2 W.

Innganger: airplay | bt | aux | usb
  airplay/bt/usb kommer alle fra Pi-ens DAC (PCM5102A); aux er 3,5 mm bak.
  Relé 1+2 (L/R) velger DAC eller AUX inn til forsterkeren.
Front: 4 inngangsknapper med LED-ring, 16 mm POWER-knapp (kort trykk = standby,
  hold 3 s = omstart), encoder (volum, trykk = mute). OLED styres av oled_display.py.
Bak: KCD1 bryter all strøm (maskinvare). Strømrelé bryter 24 V til forsterkerkortet i standby.
Volum: 2 x X9C103S (INC/UD/CS delt).
LED-ringer: 2 x 4-kanals MOSFET-kort (3,3 V-jumper), POWER-ringen dimmes med PWM i standby.
HTTP-API (port 8765) + mDNS for Home Assistant-integrasjonen og Homey-appen.

API:
  GET  /api/status
  POST /api/power  {"on":bool}   POST /api/toggle
  POST /api/input  {"input":"airplay|bt|aux|usb"}
  POST /api/volume {"volume":0-100} | {"delta":±n}
  POST /api/loudness {"on":bool, "level":0-10}
  POST /api/mute   {"mute":bool}
  POST /api/bt     {"pairing":true}   (gjør Pi-en synlig 2 min)
  GET  /api/cover  (albumbilde fra AirPlay, jpg/png)
  POST /api/transport {"action":"play|pause|playpause|next|previous|stop"}  (AirPlay/Bluetooth)
"""
import asyncio
import json
import math
import threading
import os
import re
import socket
import subprocess
import time

from aiohttp import web

PORT = int(os.environ.get("KI_AMP_PORT", "8765"))
NAME = os.environ.get("KI_AMP_NAME", "Pultforsterker")
VERSION = "2.0"
STATUS_FILE = "/run/pultamp_status.json"
COVER_FILE = "/run/pultamp_cover"   # spor-metadata fra oled_display.py / bt
CTRL_FILE = "/run/pultamp_ctrl.json"       # til oled_display.py
STATE_FILE = "/var/lib/ki-amp/state.json"
RELAY_ACTIVE_LOW = os.environ.get("RELAY_ACTIVE_LOW", "1") == "1"
# Maks X9C-trinn (0-99) ved volum 100 %. 6 ohm / 40 W-høyttalere på 24 V: 85 holder forsterkeren under 40 W.
MAX_TAP = max(10, min(99, int(os.environ.get("KI_AMP_MAX_TAP", "85"))))
DSP_WS = os.environ.get("KI_AMP_DSP_WS", "ws://127.0.0.1:1234")   # CamillaDSP (loudness + digitalt volum for AirPlay/BT/USB)
DSP_CAPTURE = os.environ.get("KI_AMP_DSP_CAPTURE", "hw:Loopback,1")
DSP_PLAYBACK = os.environ.get("KI_AMP_DSP_PLAYBACK", "hw:sndrpihifiberry")
DSP_FILE = os.environ.get("KI_AMP_DSP_FILE", "/etc/camilladsp/config.yml")
DSP_FORMAT = os.environ.get("KI_AMP_DSP_FORMAT", "S32LE")   # S16LE for Pi-ens 3,5 mm-utgang (testmodus)

# ---------- GPIO (BCM) ----------
# KI_AMP_BOARD=modules : modulbygget (XH-M562, X9C103S, relékort) – standard
# KI_AMP_BOARD=main    : Pultforsterker hovedkort rev A (PGA2311 på SPI0, TPA3116 SDZ, relé på kortet)
BOARD = os.environ.get("KI_AMP_BOARD", "modules")
PIN_RELAY_AMP = 27      # modules: relé 3 (24 V til forsterker)   main: TPA3116 SDZ (høy = på)
PIN_RELAY_AUX = 22      # relé: lav = DAC, høy = AUX (begge)
PIN_X9C_INC, PIN_X9C_UD, PIN_X9C_CS = 26, 14, 15   # modules (serial console må være av)
ENC = (23, 24, 25)      # CLK, DT, SW
if BOARD == "main":
    BTN = {"airplay": 5, "bt": 6, "aux": 14, "usb": 15}
    LED = {"airplay": 7, "bt": 9, "aux": 17, "usb": 20}
    LED_POWER = 12      # PWM0
    PIN_DAC_XSMT = 26
else:
    BTN = {"airplay": 5, "bt": 6, "aux": 12, "usb": 13}
    LED = {"airplay": 7, "bt": 8, "aux": 9, "usb": 10}
    LED_POWER = 11      # PWM
    PIN_DAC_XSMT = None
BTN_POWER = 16

INPUTS = ["airplay", "bt", "aux", "usb"]
state = {"power": True, "input": "airplay", "volume": 30, "mute": False, "bt_pairing": False,
         "loudness": True, "loudness_level": 5}   # loudness 0-10 (dB bassløft ved lavt volum)
_x9c_pos = None
_pairing_until = 0.0

# ---------- maskinvare ----------
try:
    from gpiozero import Button, DigitalOutputDevice, OutputDevice, PWMLED, RotaryEncoder, LED as GLED
    HW = True
    if BOARD == "main":
        relay_amp = OutputDevice(PIN_RELAY_AMP, active_high=True, initial_value=True)      # SDZ: høy = forsterker på
        relay_aux = OutputDevice(PIN_RELAY_AUX, active_high=True, initial_value=False)     # MOSFET -> relé: høy = AUX
        dac_xsmt = OutputDevice(PIN_DAC_XSMT, active_high=True, initial_value=True)
        import spidev
        pga = spidev.SpiDev(); pga.open(0, 0); pga.max_speed_hz = 1000000; pga.mode = 0
    else:
        relay_amp = OutputDevice(PIN_RELAY_AMP, active_high=not RELAY_ACTIVE_LOW, initial_value=True)
        relay_aux = OutputDevice(PIN_RELAY_AUX, active_high=not RELAY_ACTIVE_LOW, initial_value=False)
        x_inc = DigitalOutputDevice(PIN_X9C_INC, initial_value=True)
        x_ud = DigitalOutputDevice(PIN_X9C_UD, initial_value=False)
        x_cs = DigitalOutputDevice(PIN_X9C_CS, initial_value=True)
    leds = {k: GLED(v) for k, v in LED.items()}
    led_power = PWMLED(LED_POWER, frequency=400)
except Exception as e:
    print("Kjører uten GPIO:", e)
    HW = False


def x9c_step(n):
    if not HW or n == 0:
        return
    x_ud.value = n > 0
    x_cs.off(); time.sleep(5e-6)
    for _ in range(abs(n)):
        x_inc.off(); time.sleep(5e-6)
        x_inc.on(); time.sleep(5e-6)
    x_cs.on()


def vol_db(v):
    return -80.0 if v <= 0 else max(-60.0, 40.0 * math.log10(v / 100.0))


def pga_write(gain_code):
    """PGA2311: 16 bit (høyre, venstre). 0 = mute, 255 = +31,5 dB; 192 = 0 dB; 0,5 dB per trinn."""
    if HW and BOARD == "main":
        pga.xfer2([gain_code & 0xFF, gain_code & 0xFF])


def apply_volume():
    """AUX: analogt volum (X9C på modulbygget, PGA2311 på hovedkortet). AirPlay/BT/USB: analogt på fast nivå, volum + loudness i CamillaDSP."""
    global _x9c_pos
    if BOARD == "main":
        if state["mute"] or not state["power"]:
            pga_write(0)
        elif state["input"] == "aux":
            pga_write(0 if state["volume"] <= 0 else max(1, min(192, round(192 + 2 * vol_db(state["volume"])))))   # 0 dB ved 100 %
        else:
            pga_write(192 - 2 * round((99 - MAX_TAP) / 99 * 12))   # MAX_TAP 85 -> ca. -1,7 dB
        dsp.update(); return
    if state["mute"] or not state["power"]:
        target = 0
    elif state["input"] == "aux":
        target = round(state["volume"] * MAX_TAP / 100)
    else:
        target = MAX_TAP
    if _x9c_pos is None:
        x9c_step(-100); _x9c_pos = 0
    x9c_step(target - _x9c_pos); _x9c_pos = target
    dsp.update()


# ---------- CamillaDSP (loudness + digitalt volum) ----------
def dsp_config():
    lvl = state["loudness_level"] if state["loudness"] else 0
    return f"""devices:
  samplerate: 44100
  chunksize: 1024
  queuelimit: 4
  capture: {{type: Alsa, channels: 2, device: "{DSP_CAPTURE}", format: S32LE}}
  playback: {{type: Alsa, channels: 2, device: "{DSP_PLAYBACK}", format: {DSP_FORMAT}}}
filters:
  loud:
    type: Loudness
    parameters: {{fader: Main, reference_level: -10.0, high_boost: {lvl * 0.5:.1f}, low_boost: {float(lvl):.1f}, attenuate_mid: false}}
pipeline:
  - type: Filter
    channel: 0
    names: [loud]
  - type: Filter
    channel: 1
    names: [loud]
"""


class Dsp:
    """Egen tråd som holder CamillaDSP oppdatert via websocket (python3-websocket)."""
    def __init__(self):
        self._ev = threading.Event(); self._last_cfg = None
        threading.Thread(target=self._run, daemon=True).start()

    def update(self):
        self._ev.set()

    def _send(self, ws, cmd):
        ws.send(json.dumps(cmd)); return json.loads(ws.recv())

    def _run(self):
        try:
            import websocket
        except Exception as e:
            print("CamillaDSP-styring av (python3-websocket mangler):", e); return
        self._ev.set()   # skyv oppsett og volum ved oppstart
        while True:
            self._ev.wait(); self._ev.clear()
            cfg = dsp_config()
            try:   # samme oppsett på disk, så CamillaDSP starter riktig etter omstart/krasj
                if not os.path.exists(DSP_FILE) or open(DSP_FILE).read() != cfg:
                    with open(DSP_FILE + ".tmp", "w") as fh: fh.write(cfg)
                    os.replace(DSP_FILE + ".tmp", DSP_FILE)
            except Exception as e:
                print("CamillaDSP-fil:", e)
            try:
                ws = websocket.create_connection(DSP_WS, timeout=2)
                if cfg != self._last_cfg:
                    self._send(ws, {"SetConfig": cfg}); self._last_cfg = cfg
                db = vol_db(state["volume"]) if state["input"] != "aux" else 0.0
                self._send(ws, {"SetVolume": db})
                self._send(ws, {"SetMute": bool(state["mute"]) or not state["power"]})
                ws.close()
            except Exception as e:   # CamillaDSP ikke klar ennå – prøv igjen
                print("CamillaDSP:", e, flush=True); self._last_cfg = None; time.sleep(2); self._ev.set()


dsp = Dsp()


def apply_input():
    if not HW:
        return
    relay_aux.value = state["input"] == "aux"
    for k, led in leds.items():
        led.value = state["power"] and k == state["input"]
    if state["input"] != "bt" or not state["bt_pairing"]:
        pass  # BT-LED pulserer under parring (se pairing_task)


def apply_power():
    if not HW:
        return
    relay_amp.value = state["power"]
    led_power.value = 1.0 if state["power"] else 0.1
    apply_input()
    apply_volume()
    # OLED av i standby håndteres av oled_display.py via ctrl-filen
    units = [u for u in ("shairport-sync", "bluealsa-aplay", "ki-usb-audio", "ki-squeezelite")   # bare tjenester som er slått på
             if subprocess.run(["systemctl", "is-enabled", "--quiet", u], check=False).returncode == 0]
    subprocess.run(["systemctl", "start" if state["power"] else "stop", *units],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_state():
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as fh:
            json.dump({k: state[k] for k in ("input", "volume", "mute", "loudness", "loudness_level")}, fh)
    except Exception:
        pass


def load_state():
    try:
        with open(STATE_FILE) as fh:
            state.update({k: v for k, v in json.load(fh).items() if k in state})
    except Exception:
        pass


def write_ctrl():
    try:
        tmp = CTRL_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(state, fh)
        os.replace(tmp, CTRL_FILE)
    except Exception:
        pass


def changed():
    write_ctrl(); save_state()


def read_status():
    try:
        with open(STATUS_FILE) as fh:
            st = json.load(fh)
    except Exception:
        st = {}
    return {**state, "playing": bool(st.get("playing")), "paused": bool(st.get("paused")), "source": st.get("source", ""), "cover": st.get("cover", ""), "title": st.get("title", ""), "artist": st.get("artist", ""),
            "duration": st.get("duration", 0), "position": st.get("position", 0), "bt_device": st.get("bt_device", ""),
            "name": NAME, "version": VERSION, "id": socket.gethostname()}


# ---------- handlinger ----------
def set_power(on):
    state["power"] = bool(on); apply_power(); changed()


def set_input(inp):
    if inp in INPUTS:
        prev = state["input"]
        state["input"] = inp; apply_input(); apply_volume(); changed()
        if prev != inp:
            threading.Thread(target=_pause_others, args=(inp,), daemon=True).start()


def _pause_others(inp):
    """Som en ekte inngangsvelger: stopp AirPlay/Bluetooth som spiller på en annen kilde enn den valgte."""
    st = read_status()
    if not st.get("playing") or st.get("source") in ("", inp):
        return
    try:
        if st.get("source") == "bt":
            _busctl("call", "org.bluez", _bt_player(), "org.bluez.MediaPlayer1", "Pause")
        elif st.get("source") == "airplay":
            _busctl("call", SPS[0], SPS[1], SPS[2], "Pause")
    except Exception as e:
        print("Pause annen kilde:", e, flush=True)


def set_loudness(on=None, level=None):
    if on is not None:
        state["loudness"] = bool(on)
    if level is not None:
        state["loudness_level"] = max(0, min(10, int(level)))
    apply_volume(); changed()


def set_volume(v):
    state["volume"] = max(0, min(100, int(v)))
    if state["volume"] > 0:
        state["mute"] = False
    apply_volume(); changed()


def set_mute(m):
    state["mute"] = bool(m); apply_volume(); changed()


def bt_pairing(on=True):
    global _pairing_until
    state["bt_pairing"] = bool(on)
    _pairing_until = time.time() + 120 if on else 0
    for args in ([["power", "on"], ["pairable", "on"], ["discoverable", "on"]] if on else [["discoverable", "off"]]):
        subprocess.run(["bluetoothctl", *args], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    changed()


# ---------- knapper ----------
_power_press_t = 0.0


def setup_buttons():
    if not HW:
        return []
    objs = []
    for name, pin in BTN.items():
        b = Button(pin, pull_up=True, bounce_time=0.05, hold_time=2.0)
        if name == "airplay":
            b.when_released = lambda b=b: (set_input("airplay") if not b.was_held else None)
            b.when_held = lambda: bt_pairing(not state["bt_pairing"])   # hold AIRPLAY 2 s = BT-parring av/på
        else:
            b.when_pressed = lambda n=name: set_input(n)
        objs.append(b)
    p = Button(BTN_POWER, pull_up=True, bounce_time=0.05, hold_time=3.0)

    def on_pressed():
        global _power_press_t
        _power_press_t = time.time()

    def on_released():
        if not p.was_held and time.time() - _power_press_t < 0.5:
            set_power(not state["power"])

    p.when_pressed = on_pressed
    p.when_released = on_released
    p.when_held = lambda: (save_state(), subprocess.run(["systemctl", "reboot"], check=False))
    objs.append(p)
    vol = RotaryEncoder(ENC[0], ENC[1], max_steps=0, wrap=False)
    vol.when_rotated_clockwise = lambda: set_volume(state["volume"] + 2)
    vol.when_rotated_counter_clockwise = lambda: set_volume(state["volume"] - 2)
    objs.append(vol)
    sw = Button(ENC[2], pull_up=True, bounce_time=0.05)
    sw.when_pressed = lambda: set_mute(not state["mute"])
    objs.append(sw)
    return objs


async def pairing_task():
    """BT-LED pulserer under parring, og parring slås av etter 2 min eller når en enhet kobler til."""
    import math
    while True:
        if state["bt_pairing"]:
            if time.time() > _pairing_until or read_status().get("bt_device"):
                bt_pairing(False); apply_input()
            elif HW:
                leds["bt"].value = (math.sin(time.time() * 2 * math.pi * 1.1) + 1) / 2 > 0.5
        await asyncio.sleep(0.05)


# ---------- HTTP ----------
def j(_r=None):
    return web.json_response(read_status())


async def h_status(_r): return j()
async def h_power(r): set_power((await r.json()).get("on", True)); return j()
async def h_toggle(_r): set_power(not state["power"]); return j()
async def h_input(r):
    inp = (await r.json()).get("input", "")
    if inp not in INPUTS:
        return web.json_response({"error": f"input må være en av {INPUTS}"}, status=400)
    set_input(inp); return j()
async def h_volume(r):
    b = await r.json()
    set_volume(state["volume"] + int(b["delta"]) if "delta" in b else int(b.get("volume", state["volume"]))); return j()
async def h_mute(r): set_mute((await r.json()).get("mute", True)); return j()
async def h_bt(r): bt_pairing((await r.json()).get("pairing", True)); return j()
async def h_cover(_r):
    try:
        with open(COVER_FILE, "rb") as fh:
            img = fh.read()
    except OSError:
        return web.Response(status=404)
    ctype = "image/png" if img[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return web.Response(body=img, content_type=ctype, headers={"Cache-Control": "max-age=3600"})


def follow_source():
    """Bytt kilde automatisk når AirPlay eller Bluetooth begynner å spille (som en vanlig forsterker med auto-input)."""
    last = (None, False)
    while True:
        time.sleep(1)
        try:
            st = read_status()
            cur = (st.get("source"), bool(st.get("playing")))
            if cur != last and cur[1] and cur[0] in ("airplay", "bt") and state["power"] and state["input"] != cur[0]:
                print("Auto-kilde:", cur[0], flush=True)
                set_input(cur[0])
            last = cur
        except Exception as e:
            print("Auto-kilde:", e, flush=True)


async def h_transport(r):
    a = (await r.json()).get("action", "")
    if a not in TRANSPORT:
        return web.json_response({"error": f"action må være en av {sorted(TRANSPORT)}"}, status=400)
    try:
        await asyncio.get_running_loop().run_in_executor(None, transport, a)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    await asyncio.sleep(0.6)   # la metadata rekke å oppdatere seg
    return j()
async def h_loudness(r):
    b = await r.json(); set_loudness(b.get("on"), b.get("level")); return j()


# ---------- avspillingskontroll (AirPlay via Shairport Sync D-Bus, Bluetooth via BlueZ AVRCP) ----------
TRANSPORT = {"play", "pause", "playpause", "next", "previous", "stop"}
SPS = ("org.gnome.ShairportSync", "/org/gnome/ShairportSync", "org.gnome.ShairportSync.RemoteControl")
SPS_CMD = {"play": "Play", "pause": "Pause", "playpause": "PlayPause", "next": "Next", "previous": "Previous", "stop": "Stop"}
BT_CMD = {"play": "Play", "pause": "Pause", "next": "Next", "previous": "Previous", "stop": "Stop"}


def _busctl(*args):
    r = subprocess.run(["busctl", "--system", *args], capture_output=True, text=True, timeout=4)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or "busctl feilet")
    return r.stdout


def _bt_player():
    out = _busctl("tree", "--list", "org.bluez")
    players = [l.strip() for l in out.splitlines() if re.search(r"/dev_[0-9A-F_]+/player\d+$", l.strip())]
    if not players:
        raise RuntimeError("ingen Bluetooth-enhet med avspillingskontroll tilkoblet")
    return players[0]


def transport(action):
    st = read_status()
    src = st.get("source") or ("bt" if state["input"] == "bt" else "airplay")
    if src == "bt" or state["input"] == "bt":
        if action == "playpause":
            action = "pause" if st.get("playing") else "play"
        _busctl("call", "org.bluez", _bt_player(), "org.bluez.MediaPlayer1", BT_CMD[action])
    else:
        _busctl("call", SPS[0], SPS[1], SPS[2], SPS_CMD[action])


def _local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def start_mdns():
    try:
        from zeroconf import ServiceInfo, Zeroconf
        info = ServiceInfo("_kipultamp._tcp.local.", f"{NAME}._kipultamp._tcp.local.",
                           addresses=[socket.inet_aton(_local_ip())], port=PORT,
                           properties={"id": socket.gethostname(), "version": VERSION, "name": NAME, "type": "pultforsterker"},
                           server=f"{socket.gethostname()}.local.")
        zc = Zeroconf(); zc.register_service(info); return zc
    except Exception as e:
        print("mDNS ikke startet:", e); return None


async def on_startup(app):
    app["zc"] = start_mdns()
    app["btn"] = setup_buttons()
    app["pair"] = asyncio.create_task(pairing_task())


async def on_cleanup(app):
    if app.get("zc"):
        app["zc"].close()


def main():
    load_state()
    apply_power(); changed()
    if os.environ.get("KI_AMP_AUTO_INPUT", "1") == "1":
        threading.Thread(target=follow_source, daemon=True).start()
    app = web.Application()
    app.add_routes([web.get("/api/status", h_status), web.post("/api/power", h_power), web.post("/api/toggle", h_toggle),
                    web.post("/api/input", h_input), web.post("/api/volume", h_volume), web.post("/api/mute", h_mute),
                    web.post("/api/bt", h_bt), web.post("/api/loudness", h_loudness), web.post("/api/transport", h_transport), web.get("/api/cover", h_cover)])
    app.on_startup.append(on_startup); app.on_cleanup.append(on_cleanup)
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)


if __name__ == "__main__":
    main()
