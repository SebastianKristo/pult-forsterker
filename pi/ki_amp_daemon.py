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
  POST /api/voice  {"on":bool} (talemeldinger av/på) | {"say":"bt_pairing"} (test)
  GET  /api/cover  (albumbilde fra AirPlay, jpg/png)
  POST /api/transport {"action":"play|pause|playpause|next|previous|stop"}  (AirPlay/Bluetooth/Radio)
  GET  /api/presets                       radiokanaler 1–6 (Lyrion)
  POST /api/preset  {"n":1-6}             spill kanal n  |  {"n":1-6, "save":true} lagre det som spiller nå
  POST /api/presets {"import":true}       hent de 6 første favorittene fra Lyrion | {"presets":[{title,url,icon}…]}
Radio: Squeezelite-spilleren styres gjennom Lyrion Music Servers JSON-RPC (KI_AMP_LMS_SERVER, ellers oppdaget på nettet).
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
import hashlib
import urllib.request

from aiohttp import web

PORT = int(os.environ.get("KI_AMP_PORT", "8765"))
NAME = os.environ.get("KI_AMP_NAME", "Pultforsterker")
VERSION = "2.0"
STATUS_FILE = "/run/pultamp_status.json"
COVER_FILE = "/run/pultamp_cover"   # albumbilde fra oled_display.py (AirPlay/BT)
COVER_RADIO = "/run/pultamp_cover_radio"   # stasjons-/albumbilde fra Lyrion
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
elif BOARD == "radio":   # Radio Retro: Pi 4 + 3,5 mm + PAM8406, 6 favoritter, SOURCE/◀◀/▶▶, EC11, POWER i toppen
    BTN = {}
    LED = {}
    LED_POWER = 23      # LED-ringen via 2N2222A
    PIN_DAC_XSMT = None
    ENC = (17, 27, 22)
    FAV_BTN = [5, 6, 13, 19, 26, 16]
    FAV_LED = [2, 4, 7, 14, 15, 24]
    RADIO_BTN = {"source": 20, "prev": 21, "next": 12}
else:
    BTN = {"airplay": 5, "bt": 6, "aux": 12, "usb": 13}
    LED = {"airplay": 7, "bt": 8, "aux": 9, "usb": 10}
    LED_POWER = 11      # PWM
    PIN_DAC_XSMT = None
BTN_POWER = 3 if BOARD == "radio" else 16

INPUTS = ["radio", "airplay", "bt", "aux", "usb"]
CYCLE = ["radio", "airplay", "bt", "usb"] if BOARD == "radio" else INPUTS   # SOURCE-knappen
state = {"power": True, "input": "airplay", "volume": 30, "mute": False, "bt_pairing": False,
         "loudness": True, "loudness_level": 5, "voice": True,
         "presets": [None] * 6, "preset": 0}   # radiokanaler 1–6: {"title","url","icon"}; preset = aktiv (1–6, 0 = ingen)   # loudness 0-10 (dB bassløft ved lavt volum)
_x9c_pos = None
_pairing_until = 0.0

# ---------- maskinvare ----------
try:
    from gpiozero import Button, DigitalOutputDevice, OutputDevice, PWMLED, RotaryEncoder, LED as GLED
    HW = True
    class _Dummy:
        value = False
    if BOARD == "radio":
        relay_amp, relay_aux = _Dummy(), _Dummy()
        fav_leds = [GLED(p) for p in FAV_LED]
    elif BOARD == "main":
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
    if BOARD == "radio":   # bare digitalt volum (CamillaDSP) – forsterkeren har fast forsterkning
        dsp.update(); return
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


# ---------- Talemeldinger (piper → espeak-ng som reserve), spilles gjennom dmix/CamillaDSP ----------
PHRASES = {
    "bt_pairing": "Bluetooth-paring. Velg Pultforsterker på telefonen.",
    "bt_pairing_timeout": "Ingen enhet koblet til. Paring avsluttet.",
    "bt_connected": "Koblet til {name}.",
    "bt_disconnected": "Bluetooth frakoblet.",
    "input_airplay": "AirPlay.",
    "input_bt": "Bluetooth.",
    "input_aux": "AUX.",
    "input_usb": "USB.",
    "input_radio": "Radio.",
    "radio_preset": "{name}.",
    "radio_saved": "Lagret som kanal {n}.",
    "power_on": "Pultforsterker er klar.",
}
TTS_DIR = "/var/cache/ki-amp/tts"
PIPER_VOICE = os.environ.get("KI_AMP_PIPER_VOICE", "/opt/piper/no_NO-talesyntese-medium.onnx")


class Voice:
    def __init__(self):
        self._q = []; self._ev = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, key, delay=0.0, **kw):
        if not state.get("voice", True) or not state["power"] or key not in PHRASES:
            return
        self._q.append((time.time() + delay, PHRASES[key].format(**kw))); self._ev.set()

    def _wav(self, text):
        import hashlib
        os.makedirs(TTS_DIR, exist_ok=True)
        path = os.path.join(TTS_DIR, hashlib.sha1(text.encode()).hexdigest()[:16] + ".wav")
        if not os.path.exists(path):
            piper = subprocess.run(["sh", "-c", "command -v piper"], capture_output=True, text=True).stdout.strip()
            if piper and os.path.exists(PIPER_VOICE):
                subprocess.run([piper, "--model", PIPER_VOICE, "--output_file", path], input=text, text=True,
                               capture_output=True, timeout=30)
            if not os.path.exists(path):
                subprocess.run(["espeak-ng", "-v", "nb", "-s", "150", "-w", path, text], capture_output=True, timeout=15)
        return path if os.path.exists(path) else None

    def warm(self):   # lag faste fraser på forhånd, så første melding kommer uten forsinkelse
        for k, t in PHRASES.items():
            if "{" not in t:
                try: self._wav(t)
                except Exception: pass

    def _run(self):
        threading.Thread(target=self.warm, daemon=True).start()
        while True:
            self._ev.wait(); self._ev.clear()
            while self._q:
                t, text = self._q.pop(0)
                if t > time.time():
                    time.sleep(t - time.time())
                try:
                    wav = self._wav(text)
                    if wav and state.get("voice", True):
                        subprocess.run(["aplay", "-q", "-D", "default", wav], timeout=20, check=False)
                except Exception as e:
                    print("Talemelding:", e, flush=True)


voice = Voice()


def set_voice(on):
    state["voice"] = bool(on); changed()


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
    if BOARD == "radio":
        for i, led in enumerate(fav_leds):
            led.value = state["power"] and state["input"] == "radio" and state["preset"] == i + 1
    if state["input"] != "bt" or not state["bt_pairing"]:
        pass  # BT-LED pulserer under parring (se pairing_task)


def apply_power():
    if HW:
        relay_amp.value = state["power"]
        led_power.value = 1.0 if state["power"] else 0.1
        apply_input()
    apply_volume()   # mute i CamillaDSP + PGA2311 i standby
    # OLED av i standby håndteres av oled_display.py via ctrl-filen
    units = [u for u in ("shairport-sync", "bluealsa-aplay", "ki-usb-audio", "ki-squeezelite")   # bare tjenester som er slått på
             if subprocess.run(["systemctl", "is-enabled", "--quiet", u], check=False).returncode == 0]
    if not state["power"]:   # stopp det som spiller pent før tjenestene tas ned
        _pause_others("")
        if lyr.info.get("mode") == "play":
            lyr.cmd(["pause", "1"])
    subprocess.run(["systemctl", "start" if state["power"] else "stop", *units],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_state():
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as fh:
            json.dump({k: state[k] for k in ("input", "volume", "mute", "loudness", "loudness_level", "voice", "presets", "preset")}, fh)
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
            json.dump({**state, "lyrion": lyr.connected, "radio": lyr.info if state["input"] == "radio" else {}}, fh)
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
    if state["input"] == "radio":   # metadata fra Lyrion
        r = lyr.info
        st = {"playing": r.get("mode") == "play", "paused": r.get("mode") == "pause", "source": "radio",
              "cover": lyr.cover_id, "title": r.get("song") or r.get("station", ""),
              "artist": r.get("artist") or (r.get("station", "") if r.get("song") else ""),
              "album": r.get("station", ""), "duration": r.get("duration", 0), "position": r.get("time", 0),
              "bt_device": st.get("bt_device", "")}
    extra = {"presets": [{"n": i + 1, "title": (p or {}).get("title", "")} for i, p in enumerate(state["presets"])],
             "station": lyr.info.get("station", ""), "lyrion": lyr.connected}
    return {**state, **extra, "playing": bool(st.get("playing")), "paused": bool(st.get("paused")), "source": st.get("source", ""), "cover": st.get("cover", ""), "title": st.get("title", ""), "artist": st.get("artist", ""), "album": st.get("album", ""),
            "duration": st.get("duration", 0), "position": st.get("position", 0), "bt_device": st.get("bt_device", ""),
            "name": NAME, "version": VERSION, "id": socket.gethostname(), "presets": extra["presets"]}


# ---------- handlinger ----------
def set_power(on):
    was = state["power"]
    state["power"] = bool(on); apply_power(); changed()
    if state["power"] and not was:
        voice.say("power_on", delay=2.5)   # vent til tjenestene er oppe igjen


def set_input(inp, announce=True):
    if inp in INPUTS:
        prev = state["input"]
        state["input"] = inp; apply_input(); apply_volume(); changed()
        if prev != inp:
            threading.Thread(target=_pause_others, args=(inp,), daemon=True).start()
            if announce:
                voice.say("input_" + inp)


def _pause_others(inp):
    """Som en ekte inngangsvelger: stopp AirPlay/Bluetooth som spiller på en annen kilde enn den valgte."""
    st = read_status()
    if lyr.info.get("mode") == "play" and inp != "radio":
        lyr.cmd(["pause", "1"])
    if not st.get("playing") or st.get("source") in ("", inp, "radio"):
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


_pairing_known = ""


def bt_pairing(on=True, reason=""):
    global _pairing_until, _pairing_known
    if on and not state["bt_pairing"]:
        voice.say("bt_pairing")
    elif not on and state["bt_pairing"] and reason == "timeout":
        voice.say("bt_pairing_timeout")
    state["bt_pairing"] = bool(on)
    _pairing_until = time.time() + 120 if on else 0
    _pairing_known = read_status().get("bt_device", "") if on else ""
    for args in ([["power", "on"], ["pairable", "on"], ["discoverable", "on"]] if on else [["discoverable", "off"]]):
        subprocess.run(["bluetoothctl", *args], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    changed()


# ---------- knapper ----------
def _safe(fn, *a):
    try:
        fn(*a)
    except Exception as e:
        print("Knapp:", e, flush=True)


_power_press_t = 0.0


def setup_buttons():
    if not HW:
        return []
    objs = []
    if BOARD == "radio":
        for i, pin in enumerate(FAV_BTN):   # kort trykk = spill kanal, hold 2 s = lagre det som spiller
            b = Button(pin, pull_up=True, bounce_time=0.05, hold_time=2.0)
            b.when_released = lambda b=b, n=i + 1: (_safe(play_preset, n) if not b.was_held else None)
            b.when_held = lambda n=i + 1: _safe(save_preset, n)
            objs.append(b)
        src = Button(RADIO_BTN["source"], pull_up=True, bounce_time=0.05)
        src.when_pressed = lambda: set_input(CYCLE[(CYCLE.index(state["input"]) + 1) % len(CYCLE)] if state["input"] in CYCLE else CYCLE[0])
        objs.append(src)
        for k, act in (("prev", "previous"), ("next", "next")):
            b = Button(RADIO_BTN[k], pull_up=True, bounce_time=0.05)
            b.when_pressed = lambda a=act: _safe(transport, a)
            objs.append(b)
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
            dev = read_status().get("bt_device", "")
            if time.time() > _pairing_until:
                bt_pairing(False, "timeout"); apply_input()
            elif dev and dev != _pairing_known:   # en ny enhet koblet til
                bt_pairing(False, "connected"); apply_input()
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
async def h_voice(r):
    b = await r.json()
    if "on" in b:
        set_voice(b["on"])
    if b.get("say"):   # test: {"say":"bt_pairing"}
        voice.say(b["say"])
    return j()


async def h_cover(_r):
    try:
        with open(COVER_RADIO if state["input"] == "radio" else COVER_FILE, "rb") as fh:
            img = fh.read()
    except OSError:
        return web.Response(status=404)
    ctype = "image/png" if img[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return web.Response(body=img, content_type=ctype, headers={"Cache-Control": "max-age=3600"})


AUTO_INPUT = os.environ.get("KI_AMP_AUTO_INPUT", "1") == "1"


def follow_source():
    """Bytt kilde automatisk når AirPlay eller Bluetooth begynner å spille (som en vanlig forsterker med auto-input)."""
    last = (None, False)
    last_dev = None
    while True:
        time.sleep(1)
        try:
            st = read_status()
            dev = st.get("bt_device", "")
            if last_dev is not None and dev != last_dev and state["power"]:
                if dev:
                    voice.say("bt_connected", name=dev)
                else:
                    voice.say("bt_disconnected")
            last_dev = dev
            cur = (st.get("source"), bool(st.get("playing")))
            if lyr.info.get("mode") == "play" and state["input"] != "radio" and not st.get("playing"):
                cur = ("radio", True)
            if AUTO_INPUT and cur != last and cur[1] and cur[0] in ("airplay", "bt", "radio") and state["power"] and state["input"] != cur[0]:
                print("Auto-kilde:", cur[0], flush=True)
                set_input(cur[0], announce=False)
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


# ---------- Lyrion Music Server (radio via Squeezelite) ----------
LMS_SERVER = os.environ.get("KI_AMP_LMS_SERVER", "").strip()
LMS_PORT = int(os.environ.get("KI_AMP_LMS_PORT", "9000"))


def _player_mac():
    if os.environ.get("KI_AMP_LMS_PLAYER"):
        return os.environ["KI_AMP_LMS_PLAYER"].lower()
    try:
        return open("/sys/class/net/eth0/address").read().strip().lower()   # samme -m som ki-squeezelite.service
    except OSError:
        return "00:00:00:00:00:01"


class Lyrion:
    """Tynn JSON-RPC-klient mot Lyrion + poller for stasjon, låt og stasjonsbilde."""

    def __init__(self):
        self.host = LMS_SERVER or None
        self.port = LMS_PORT
        self.player = _player_mac()
        self.info = {}
        self.connected = False
        self.cover_id = ""
        self._art = None
        self._vol_ok = False
        if os.environ.get("KI_AMP_LMS", "1") == "1":
            threading.Thread(target=self._run, daemon=True).start()

    def discover(self):
        """Lyrions UDP-oppdagelse (port 3483) – svaret gir JSON-porten."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); s.settimeout(2)
        try:
            s.sendto(b"eIPAD\0NAME\0JSON\0", ("255.255.255.255", 3483))
            data, addr = s.recvfrom(1024)
            i, port = 1, LMS_PORT
            while i + 5 <= len(data):
                tag, ln = data[i:i + 4], data[i + 4]; val = data[i + 5:i + 5 + ln]; i += 5 + ln
                if tag == b"JSON":
                    port = int(val.decode())
            self.host, self.port = addr[0], port
            print("Lyrion funnet:", self.host, self.port, flush=True)
        except OSError:
            pass
        finally:
            s.close()

    def rpc(self, cmd, player=True):
        if not self.host:
            raise RuntimeError("Lyrion ikke funnet (sett KI_AMP_LMS_SERVER)")
        body = json.dumps({"id": 1, "method": "slim.request", "params": [self.player if player else "", cmd]}).encode()
        req = urllib.request.Request(f"http://{self.host}:{self.port}/jsonrpc.js", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4) as r:
            return json.loads(r.read()).get("result", {})

    def cmd(self, c):
        try:
            self.rpc(c)
        except Exception as e:
            print("Lyrion:", e, flush=True)

    def url(self, path):
        if not path:
            return ""
        return path if path.startswith("http") else f"http://{self.host}:{self.port}/{path.lstrip('/')}"

    def favorites(self):
        r = self.rpc(["favorites", "items", 0, 100, "want_url:1"], player=False)
        out = []
        for it in r.get("loop_loop", []):
            if int(it.get("isaudio", 0)) and it.get("url"):
                out.append({"title": it.get("name", ""), "url": it["url"], "icon": self.url(it.get("image", ""))})
        return out

    def _run(self):
        last_try = 0
        while True:
            time.sleep(1.5)
            if not self.host:
                if time.time() - last_try > 30:
                    last_try = time.time(); self.discover()
                continue
            try:
                r = self.rpc(["status", "-", 1, "tags:aAlcKNjJxuo"])
                loop = (r.get("playlist_loop") or [{}])[0]
                station = r.get("current_title") or loop.get("remote_title") or ""
                song, artist = loop.get("title", ""), loop.get("artist", "")
                if song and not artist and " - " in song and int(r.get("remote", 0) or 0):
                    artist, song = song.split(" - ", 1)
                if song == station:
                    song = ""
                art = loop.get("artwork_url") or (f"music/{loop['coverid']}/cover.jpg" if loop.get("coverid") else "")
                self.info = {"mode": r.get("mode", "stop"), "station": station or loop.get("album", ""), "song": song,
                             "artist": artist, "url": loop.get("url", ""), "art": self.url(art),
                             "duration": float(r.get("duration", 0) or 0), "time": float(r.get("time", 0) or 0)}
                if not self.connected:
                    print("Lyrion tilkoblet, spiller", self.player, flush=True)
                self.connected = True
                self._sync_volume(r)
                self._fetch_art()
                if not any(state["presets"]):
                    favs = self.favorites()[:6]
                    if favs:
                        state["presets"] = favs + [None] * (6 - len(favs)); changed()
                        print("Radiokanaler hentet fra Lyrion-favoritter:", [f["title"] for f in favs], flush=True)
                if state["input"] == "radio":
                    write_ctrl()
            except urllib.error.HTTPError as e:
                self.connected = False; print("Lyrion:", e, flush=True); time.sleep(10)
            except Exception as e:
                if self.connected:
                    print("Lyrion borte:", e, flush=True)
                self.connected = False; self.info = {}
                if not LMS_SERVER:
                    self.host = None

    def _sync_volume(self, r):
        """Lyrion-volumet holdes på 100 (volumet ligger i CamillaDSP). Endrer noen det i Lyrion, tar vi det over."""
        v = r.get("mixer volume")
        if v is None:
            return
        v = int(float(v))
        if self._vol_ok and v != 100 and v > 0 and state["input"] == "radio":
            set_volume(v)
        if v != 100:
            self.rpc(["mixer", "volume", 100])
        self._vol_ok = True

    def _fetch_art(self):
        art = self.info.get("art", "")
        if art == self._art:
            return
        self._art = art
        if not art:
            self.cover_id = ""; return
        try:
            with urllib.request.urlopen(art, timeout=5) as r:
                img = r.read()
            with open(COVER_RADIO + ".tmp", "wb") as fh:
                fh.write(img)
            os.replace(COVER_RADIO + ".tmp", COVER_RADIO)
            self.cover_id = hashlib.sha1(img).hexdigest()[:12]
        except Exception as e:
            print("Stasjonsbilde:", e, flush=True); self.cover_id = ""


lyr = Lyrion()


def play_preset(n, announce=True):
    p = state["presets"][n - 1] if 1 <= n <= 6 else None
    if not p:
        raise RuntimeError(f"radiokanal {n} er ikke lagret")
    if not state["power"]:
        set_power(True)
    lyr.rpc(["playlist", "play", p["url"], p.get("title", "")])
    lyr.info = {**lyr.info, "mode": "play", "station": p.get("title", ""), "song": "", "artist": "", "url": p["url"]}
    state["preset"] = n
    set_input("radio", announce=False)
    apply_input(); changed()
    if announce:
        voice.say("radio_preset", name=p.get("title") or f"kanal {n}")


def step_preset(d):
    filled = [i + 1 for i, p in enumerate(state["presets"]) if p]
    if not filled:
        raise RuntimeError("ingen radiokanaler lagret")
    cur = state["preset"] if state["preset"] in filled else filled[0] - (1 if d > 0 else -1)
    idx = (filled.index(cur) + d) % len(filled) if cur in filled else (0 if d > 0 else len(filled) - 1)
    play_preset(filled[idx])


def save_preset(n):
    i = lyr.info
    if not i.get("url"):
        raise RuntimeError("ingen radiokanal spiller nå")
    state["presets"][n - 1] = {"title": i.get("station") or i.get("song") or f"Kanal {n}", "url": i["url"], "icon": i.get("art", "")}
    state["preset"] = n; apply_input(); changed()
    voice.say("radio_saved", n=n)


async def h_presets(_r):
    return web.json_response({"presets": state["presets"], "active": state["preset"], "lyrion": lyr.connected})


async def h_preset(r):
    b = await r.json()
    n = int(b.get("n", 0))
    if not 1 <= n <= 6:
        return web.json_response({"error": "n må være 1–6"}, status=400)
    try:
        fn = save_preset if b.get("save") else play_preset
        await asyncio.get_running_loop().run_in_executor(None, fn, n)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    await asyncio.sleep(1.0)
    return j()


async def h_presets_set(r):
    b = await r.json()
    try:
        if b.get("import"):
            favs = await asyncio.get_running_loop().run_in_executor(None, lyr.favorites)
            state["presets"] = (favs[:6] + [None] * 6)[:6]
        elif isinstance(b.get("presets"), list):
            state["presets"] = ([p if p and p.get("url") else None for p in b["presets"]] + [None] * 6)[:6]
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    changed()
    return web.json_response({"presets": state["presets"], "active": state["preset"]})


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
    if state["input"] == "radio":
        if action in ("next", "previous"):
            step_preset(1 if action == "next" else -1); return
        lyr.cmd({"play": ["play"], "pause": ["pause", "1"], "playpause": ["pause"], "stop": ["stop"]}[action])
        if action == "play" and lyr.info.get("mode") == "stop" and state["preset"]:
            play_preset(state["preset"])
        return
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
    threading.Thread(target=follow_source, daemon=True).start()   # auto-kilde (kan slås av) + BT-talemeldinger
    app = web.Application()
    app.add_routes([web.get("/api/status", h_status), web.post("/api/power", h_power), web.post("/api/toggle", h_toggle),
                    web.post("/api/input", h_input), web.post("/api/volume", h_volume), web.post("/api/mute", h_mute),
                    web.post("/api/bt", h_bt), web.post("/api/loudness", h_loudness), web.post("/api/transport", h_transport), web.get("/api/cover", h_cover), web.post("/api/voice", h_voice),
                    web.get("/api/presets", h_presets), web.post("/api/preset", h_preset), web.post("/api/presets", h_presets_set)])
    app.on_startup.append(on_startup); app.on_cleanup.append(on_cleanup)
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)


if __name__ == "__main__":
    main()
