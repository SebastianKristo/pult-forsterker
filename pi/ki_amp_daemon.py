#!/usr/bin/env python3
"""KI Pultforsterker v2 – daemon på Raspberry Pi Zero 2 W.

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
  POST /api/mute   {"mute":bool}
  POST /api/bt     {"pairing":true}   (gjør Pi-en synlig 2 min)
"""
import asyncio
import json
import os
import socket
import subprocess
import time

from aiohttp import web

PORT = int(os.environ.get("KI_AMP_PORT", "8765"))
NAME = os.environ.get("KI_AMP_NAME", "Pultforsterker")
VERSION = "2.0"
STATUS_FILE = "/run/pultamp_status.json"   # spor-metadata fra oled_display.py / bt
CTRL_FILE = "/run/pultamp_ctrl.json"       # til oled_display.py
STATE_FILE = "/var/lib/ki-amp/state.json"
RELAY_ACTIVE_LOW = os.environ.get("RELAY_ACTIVE_LOW", "1") == "1"
# Maks X9C-trinn (0-99) ved volum 100 %. 6 ohm / 40 W-høyttalere på 24 V: 85 holder forsterkeren under 40 W.
MAX_TAP = max(10, min(99, int(os.environ.get("KI_AMP_MAX_TAP", "85"))))

# ---------- GPIO (BCM) ----------
PIN_RELAY_AMP = 27      # relé: 24 V til forsterkerkortet
PIN_RELAY_AUX = 22      # relé 1+2: lav = DAC, høy = AUX
PIN_X9C_INC, PIN_X9C_UD, PIN_X9C_CS = 26, 14, 15   # serial console må være av
ENC = (23, 24, 25)      # CLK, DT, SW
BTN = {"airplay": 5, "bt": 6, "aux": 12, "usb": 13}
BTN_POWER = 16
LED = {"airplay": 7, "bt": 8, "aux": 9, "usb": 10}
LED_POWER = 11          # PWM

INPUTS = ["airplay", "bt", "aux", "usb"]
state = {"power": True, "input": "airplay", "volume": 30, "mute": False, "bt_pairing": False}
_x9c_pos = None
_pairing_until = 0.0

# ---------- maskinvare ----------
try:
    from gpiozero import Button, DigitalOutputDevice, OutputDevice, PWMLED, RotaryEncoder, LED as GLED
    HW = True
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


def apply_volume():
    global _x9c_pos
    target = 0 if (state["mute"] or not state["power"]) else round(state["volume"] * MAX_TAP / 100)
    if _x9c_pos is None:
        x9c_step(-100); _x9c_pos = 0
    x9c_step(target - _x9c_pos); _x9c_pos = target


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
    subprocess.run(["systemctl", "start" if state["power"] else "stop", "shairport-sync", "bluealsa-aplay", "ki-usb-audio"],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_state():
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as fh:
            json.dump({k: state[k] for k in ("input", "volume", "mute")}, fh)
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
    return {**state, "playing": bool(st.get("playing")), "title": st.get("title", ""), "artist": st.get("artist", ""),
            "duration": st.get("duration", 0), "position": st.get("position", 0), "bt_device": st.get("bt_device", ""),
            "name": NAME, "version": VERSION, "id": socket.gethostname()}


# ---------- handlinger ----------
def set_power(on):
    state["power"] = bool(on); apply_power(); changed()


def set_input(inp):
    if inp in INPUTS:
        state["input"] = inp; apply_input(); changed()


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
    cmd = ["bluetoothctl"]
    script = "discoverable on\npairable on\n" if on else "discoverable off\n"
    subprocess.run(cmd, input=script, text=True, check=False, stdout=subprocess.DEVNULL)
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
                           properties={"id": socket.gethostname(), "version": VERSION, "name": NAME},
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
    app = web.Application()
    app.add_routes([web.get("/api/status", h_status), web.post("/api/power", h_power), web.post("/api/toggle", h_toggle),
                    web.post("/api/input", h_input), web.post("/api/volume", h_volume), web.post("/api/mute", h_mute),
                    web.post("/api/bt", h_bt)])
    app.on_startup.append(on_startup); app.on_cleanup.append(on_cleanup)
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)


if __name__ == "__main__":
    main()
