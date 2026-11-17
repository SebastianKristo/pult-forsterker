"""Wi-Fi-oppsett over Bluetooth (Improv Wi-Fi, https://www.improv-wifi.com/ble/) for Skjold.

Telefonen kobler seg til enheten over Bluetooth og sender nettnavn og passord – fra improv-wifi.com i Chrome
(Android, Mac, Windows) eller en app som kan Improv. Skjold kobler til med nmcli og svarer med adressen til web-UI.

Kjøres som egen prosess av daemonen når du trykker «Bluetooth» i Wi-Fi-oppsettet på Touch (python3 -m skjold_improv),
og avslutter seg selv når enheten er koblet til, eller etter 10 minutter. Skriver én JSON-linje per hendelse på stdout:
  {"state": "ready" | "connecting" | "done" | "error" | "stopped", "ssid"?, "error"?, "url"?}

Trykket på Touch er godkjenningen, så tjenesten starter som «autorisert». Krever bluezero (pip) og BlueZ.
Protokolldelene (pakker inn/ut) er rene funksjoner og testes uten maskinvare.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time

SVC = "00467768-6228-2272-4663-277478268000"
CH_STATE = "00467768-6228-2272-4663-277478268001"
CH_ERROR = "00467768-6228-2272-4663-277478268002"
CH_RPC = "00467768-6228-2272-4663-277478268003"
CH_RESULT = "00467768-6228-2272-4663-277478268004"
CH_CAPS = "00467768-6228-2272-4663-277478268005"

AUTH_REQUIRED, AUTHORIZED, PROVISIONING, PROVISIONED = 1, 2, 3, 4
ERR_NONE, ERR_INVALID, ERR_UNKNOWN_RPC, ERR_UNABLE, ERR_NOT_AUTH = 0, 1, 2, 3, 4
CMD_WIFI = 1
TIMEOUT_S = 600


def checksum(b) -> int:
    return sum(b) & 0xFF


def parse_rpc(data) -> tuple[int, list[str]]:
    """RPC-pakke [kommando, lengde, data …, sjekksum] → (kommando, [strenger]). ValueError ved feil pakke."""
    b = bytes(data)
    if len(b) < 3 or b[1] != len(b) - 3 or checksum(b[:-1]) != b[-1]:
        raise ValueError("ugyldig pakke")
    cmd, body, out, i = b[0], b[2:-1], [], 0
    while i < len(body):
        n = body[i]; i += 1
        if i + n > len(body):
            raise ValueError("ugyldig lengde")
        out.append(body[i:i + n].decode("utf-8", "replace")); i += n
    return cmd, out


def build_result(cmd: int, strings: list[str]) -> list[int]:
    """Svar-pakke [kommando, lengde, (len, streng)…, sjekksum] som liste med byte."""
    body = b"".join(bytes([len(s.encode())]) + s.encode() for s in strings)
    pkt = bytes([cmd, len(body)]) + body
    return list(pkt + bytes([checksum(pkt)]))


def wifi_rpc(data) -> tuple[str, str]:
    """Pakken med Wi-Fi-innstillinger → (ssid, passord)."""
    cmd, s = parse_rpc(data)
    if cmd != CMD_WIFI:
        raise KeyError("ukjent kommando")
    if not s or not s[0]:
        raise ValueError("mangler nettnavn")
    return s[0], s[1] if len(s) > 1 else ""


def emit(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def _ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except OSError:
        return ""
    finally:
        s.close()


def connect_wifi(ssid: str, psk: str, run=subprocess.run) -> tuple[bool, str]:
    run(["nmcli", "connection", "down", "skjold-oppsett"], capture_output=True, timeout=20)   # oppsett-nettet må ned først
    cmd = ["nmcli", "device", "wifi", "connect", ssid] + (["password", psk] if psk else [])
    r = run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return True, ""
    run(["nmcli", "connection", "delete", "id", ssid], capture_output=True, timeout=20)
    return False, (r.stderr or r.stdout or "").strip()[:200]


def main(name: str = "Skjold", port: int = 8765) -> int:
    try:
        from bluezero import adapter, peripheral   # type: ignore
    except Exception as e:
        emit(state="error", error=f"Bluetooth-oppsett mangler bluezero ({e})"); return 1
    try:
        dongle = next(iter(adapter.Adapter.available()))
        if not dongle.powered:
            dongle.powered = True
    except Exception as e:
        emit(state="error", error=f"fant ingen Bluetooth-adapter ({e})"); return 1

    chars: dict = {}
    state = {"v": AUTHORIZED, "err": ERR_NONE, "res": []}

    def set_char(key, val):
        c = chars.get(key)
        if c is None:
            return
        def gjor():   # D-Bus-objektene eies av GLib-løkka: oppdater dem der, ikke fra tilkoblingstråden
            try: c.set_value(val)
            except Exception: pass
            return False
        try:
            from gi.repository import GLib   # type: ignore
            GLib.idle_add(gjor)
        except Exception:
            gjor()

    def set_state(v):
        state["v"] = v; set_char("state", [v])

    def set_error(v):
        state["err"] = v; set_char("error", [v])

    def provision(ssid, psk):
        emit(state="connecting", ssid=ssid)
        set_error(ERR_NONE); set_state(PROVISIONING)
        ok, err = connect_wifi(ssid, psk)
        if ok:
            time.sleep(3)
            url = f"http://{_ip() or socket.gethostname() + '.local'}:{port}/"
            state["res"] = build_result(CMD_WIFI, [url]); set_char("result", state["res"])
            set_state(PROVISIONED); emit(state="done", ssid=ssid, url=url)
            threading.Timer(8, stop).start()
        else:
            set_error(ERR_UNABLE); set_state(AUTHORIZED); emit(state="error", ssid=ssid, error=err or "fikk ikke koblet til")

    def on_rpc(value, options=None):
        try:
            ssid, psk = wifi_rpc(value)
        except KeyError:
            set_error(ERR_UNKNOWN_RPC); return
        except ValueError:
            set_error(ERR_INVALID); return
        threading.Thread(target=provision, args=(ssid, psk), daemon=True).start()

    def notifier(key):
        def cb(notifying, characteristic):
            chars[key] = characteristic if notifying else chars.get(key)
        return cb

    p = peripheral.Peripheral(dongle.address, local_name=name[:20])
    p.add_service(srv_id=1, uuid=SVC, primary=True)
    p.add_characteristic(srv_id=1, chr_id=1, uuid=CH_STATE, value=[AUTHORIZED], notifying=False, flags=["read", "notify"],
                         read_callback=lambda: [state["v"]], notify_callback=notifier("state"))
    p.add_characteristic(srv_id=1, chr_id=2, uuid=CH_ERROR, value=[ERR_NONE], notifying=False, flags=["read", "notify"],
                         read_callback=lambda: [state["err"]], notify_callback=notifier("error"))
    p.add_characteristic(srv_id=1, chr_id=3, uuid=CH_RPC, value=[], notifying=False, flags=["write"], write_callback=on_rpc)
    p.add_characteristic(srv_id=1, chr_id=4, uuid=CH_RESULT, value=[], notifying=False, flags=["read", "notify"],
                         read_callback=lambda: state["res"], notify_callback=notifier("result"))
    p.add_characteristic(srv_id=1, chr_id=5, uuid=CH_CAPS, value=[0], notifying=False, flags=["read"], read_callback=lambda: [0])

    def stop():
        emit(state="stopped")
        try: p.mainloop.quit()
        except Exception: pass

    threading.Timer(TIMEOUT_S, stop).start()
    emit(state="ready", name=name[:20])
    try:
        p.publish()
    except Exception as e:
        emit(state="error", error=f"Bluetooth: {e}"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or ["Skjold"]), *([int(sys.argv[2])] if len(sys.argv) > 2 else [])))
