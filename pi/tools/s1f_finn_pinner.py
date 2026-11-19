#!/usr/bin/env python3
"""Skjold S1 rev F: finn ut hvilke pinner knappene og LED-ringene faktisk er koblet til, og lagre dem.

Du trykker knappene én etter én, og så tennes lysringene én etter én mens du sier hvilken som lyser.
Resultatet lagres i /etc/skjold/s1f_pins.yaml (den vinner over standardfila og overskrives ikke av oppdateringer).

    sudo systemctl stop ki-amp
    sudo python3 pi/tools/s1f_finn_pinner.py          # knapper og lys
    sudo python3 pi/tools/s1f_finn_pinner.py lys      # bare lysene
    sudo python3 pi/tools/s1f_finn_pinner.py knapper  # bare knappene
    sudo systemctl start ki-amp
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_s1f as s1  # noqa: E402

UT = "/etc/skjold/s1f_pins.yaml"
NAVN = {"bt": "BT/AirPlay", "aux": "AUX", "radio": "RADIO", "usb": "USB", "power": "av/på"}
REKKE = ("bt", "aux", "radio", "usb", "power")
RESERVERT = {0, 1, 18, 19, 21}            # HAT-EEPROM og lydkortet (I²S)
ALLE = [2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 20, 22, 23, 24, 25, 26, 27]   # 9/10/11 = volumhjulet, testes ikke


def lagre(tekst, seksjon, nokkel, verdi):
    """Bytt verdien på «  nokkel: …» inne i «seksjon:», og behold kommentaren."""
    ut, inne = [], False
    for linje in tekst.splitlines(keepends=True):
        if re.match(r"^\S", linje):
            inne = linje.startswith(seksjon + ":")
        m = re.match(r"^(\s+)" + re.escape(nokkel) + r":\s*\S+(.*)$", linje.rstrip("\n"))
        if inne and m:
            linje = f"{m.group(1)}{nokkel}: {verdi}   # funnet med s1f_finn_pinner.py\n"
        ut.append(linje)
    return "".join(ut)


def finn_knapper(pins, ledige):
    from gpiozero import DigitalInputDevice
    inn = {}
    for g in ledige:
        try:
            inn[g] = DigitalInputDevice(g, pull_up=True)
        except Exception as e:
            print(f"  (hopper over GPIO{g}: {e})")
    time.sleep(0.2)
    holdt = {g for g, d in inn.items() if d.value}   # står lav fra start = noe annet holder den nede
    if holdt:
        print("  Disse står lave uten at du trykker, og blir ikke brukt:", ", ".join(f"GPIO{g}" for g in sorted(holdt)))
    funnet = {}
    for navn in REKKE:
        print(f"\nTrykk og hold {NAVN[navn]}-knappen (venter i 20 s) …", flush=True)
        g = None
        start = time.time()
        while time.time() - start < 20:
            aktive = [p for p, d in inn.items() if d.value and p not in holdt and p not in funnet.values()]
            if len(aktive) == 1:
                g = aktive[0]
                break
            time.sleep(0.02)
        if g is None:
            print("  Fant ingen pinne – sjekk at knappen går til GND og en GPIO (C og NO).")
            continue
        print(f"  {NAVN[navn]} = GPIO{g}. Slipp knappen.")
        while inn[g].value:
            time.sleep(0.02)
        funnet[navn] = g
    for d in inn.values():
        d.close()
    return funnet


def finn_lys(pins, kandidater):
    from gpiozero import DigitalOutputDevice
    ah = pins.get("led_active_high", True) is not False
    funnet = {}
    print("\nNå tennes én pinne om gangen. Skriv hvilken ring som lyser:")
    print("  b = BT/AirPlay, a = AUX, r = RADIO, u = USB, p = av/på, Enter = ingen")
    kort = {"b": "bt", "a": "aux", "r": "radio", "u": "usb", "p": "power"}
    for g in kandidater:
        if len(funnet) == 5:
            break
        try:
            led = DigitalOutputDevice(g, active_high=ah, initial_value=True)
        except Exception as e:
            print(f"  (hopper over GPIO{g}: {e})")
            continue
        try:
            svar = input(f"  GPIO{g} er på – hvilken ring lyser? ").strip().lower()[:1]
        finally:
            led.close()
        if svar in kort:
            funnet[kort[svar]] = g
            print(f"  {NAVN[kort[svar]]}-lyset = GPIO{g}")
    mangler = [NAVN[n] for n in REKKE if n not in funnet]
    if mangler:
        print("\nFant ikke lyset til:", ", ".join(mangler),
              "– sjekk transistoren (GPIO → 1 kΩ → B, E til GND, C til ringens −, ringens + til +24 V/+5 V).")
    return funnet


def main():
    if os.geteuid() != 0:
        sys.exit("Kjør med sudo (fila lagres i /etc/skjold).")
    hva = sys.argv[1] if len(sys.argv) > 1 else "alt"
    pins = s1.load_pins()
    with open(pins["_file"]) as fh:
        tekst = fh.read()
    print("Pinner fra", pins["_file"])
    print("Stopp ki-amp først hvis den kjører: sudo systemctl stop ki-amp")
    andre = {pins.get("relay"), (pins.get("usb_switch") or {}).get("pulse"), pins.get("headphone_detect"), pins.get("dac_xsmt")}
    andre |= set((pins.get("encoder") or {}).values())
    andre.discard(None)

    knapper = {}
    if hva in ("alt", "knapper"):
        ledige = [g for g in ALLE if g not in RESERVERT and g not in andre]
        knapper = finn_knapper(pins, ledige)
        for n, g in knapper.items():
            tekst = lagre(tekst, "buttons", n, g)

    if hva in ("alt", "lys"):
        brukt = set(knapper.values()) or {g for g in (pins.get("buttons") or {}).values() if g is not None}
        forst = [g for g in (pins.get("leds") or {}).values() if g is not None]
        resten = [g for g in ALLE if g not in forst]
        kandidater = [g for g in forst + resten if g not in RESERVERT and g not in andre and g not in brukt]
        lys = finn_lys(pins, kandidater)
        for n, g in lys.items():
            tekst = lagre(tekst, "leds", n, g)

    os.makedirs(os.path.dirname(UT), exist_ok=True)
    with open(UT, "w") as fh:
        fh.write(tekst)
    ny = s1.load_pins(UT)
    print("\nLagret i", UT)
    print("  knapper:", ny.get("buttons"))
    print("  lys:    ", ny.get("leds"))
    brukt = [g for g in list(ny["buttons"].values()) + list(ny["leds"].values()) if g is not None]
    dobbel = sorted({g for g in brukt if brukt.count(g) > 1})
    if dobbel:
        print("ADVARSEL: samme pinne brukt to ganger:", ", ".join(f"GPIO{g}" for g in dobbel), "– kjør verktøyet på nytt.")
    print("Start Skjold igjen: sudo systemctl start ki-amp")


if __name__ == "__main__":
    main()
