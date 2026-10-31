#!/usr/bin/env python3
"""Skjold Node – selvtest av skjerm, encoder, knapper, bakgrunnslys og LED-ringer.

På Pi:      python3 tools/node_selftest.py            (Ctrl+C avslutter)
Uten Pi:    python3 tools/node_selftest.py --dry-run  (simulerer hendelser, lagrer skjermbilder som PNG)

Leser alle pinner fra config/node_pins.json. Krever på Pi: python3-gpiozero, python3-lgpio,
luma.lcd og Pillow (installeres av driver/installer_node.sh). Bruker gpiozero, så device-tree-
alternativ B i config.txt.node må IKKE være aktivt.
"""
import argparse, json, os, sys, time

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROT, "config", "node_pins.json"), encoding="utf-8"))
SK, ENC, KN, LEDS = P["skjerm"], P["encoder"], P["knapper"], P["leds"]
W, H = SK["width"], SK["height"]

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None


# ---------------------------------------------------------------- skjerm
class Skjerm:
    def __init__(self, sim, utmappe):
        self.sim, self.utmappe, self.n = sim, utmappe, 0
        self.dev = None
        if not sim:
            from luma.core.interface.serial import spi
            from luma.lcd.device import st7735
            ser = spi(port=SK["spi_port"], device=SK["spi_device"], gpio_DC=SK["pinner"]["A0"]["gpio"],
                      gpio_RST=SK["pinner"]["RESET"]["gpio"], bus_speed_hz=SK["bus_speed_hz"])
            # bakgrunnslyset styres av oss (Q1, aktiv lav), ikke av luma
            self.dev = st7735(ser, width=W, height=H, rotate=SK["rotate"], bgr=SK["bgr"],
                              h_offset=SK["h_offset"], v_offset=SK["v_offset"], gpio_LIGHT=None)

    def vis(self, img, navn):
        if self.dev:
            self.dev.display(img)
        elif self.utmappe:
            self.n += 1
            sti = os.path.join(self.utmappe, "selftest_%02d_%s.png" % (self.n, navn))
            img.save(sti)
            print("  [sim] skjermbilde → %s" % sti)


def font(st):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if os.path.exists(f):
            return ImageFont.truetype(f, st)
    return ImageFont.load_default()


def testbilde():
    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img)
    farger = ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#ffff00", "#00ffff", "#ff00ff", "#808080"]
    bw = W // len(farger)
    for i, c in enumerate(farger):
        d.rectangle([i * bw, 0, (i + 1) * bw - 1, 40], fill=c)
    d.text((4, 44), "R  G  B  W  Y  C  M  g", fill="white", font=font(10))
    d.rectangle([0, 0, W - 1, H - 1], outline="white")          # kant: sjekk offset
    d.line([0, H - 1, 12, H - 13], fill="red")                    # pil nede til venstre = orientering
    d.text((4, 62), "SKJOLD NODE", fill="white", font=font(16))
    d.text((4, 84), "selvtest – rød = R?", fill="#aaaaaa", font=font(10))
    d.text((4, 98), "kant hel? tekst rett vei?", fill="#aaaaaa", font=font(10))
    return img


def statusbilde(linjer, volum):
    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img)
    d.text((4, 2), "SELVTEST", fill="#e3b23c", font=font(12))
    for i, l in enumerate(linjer[-6:]):
        d.text((4, 20 + i * 14), l, fill="white", font=font(10))
    d.rectangle([4, H - 14, W - 5, H - 5], outline="white")
    d.rectangle([4, H - 14, 4 + int((W - 9) * volum / 100), H - 5], fill="#3a9a4c")
    return img


# ---------------------------------------------------------------- GPIO
def lag_gpio(sim):
    if sim:
        try:  # gpiozero med mock-pinner, hvis installert
            from gpiozero import Device
            from gpiozero.pins.mock import MockFactory, MockPWMPin
            Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        except ImportError:
            return None
    import gpiozero
    return gpiozero


class FalskLED:
    def __init__(self, navn): self.navn, self.value = navn, 0
    def on(self): self.value = 1
    def off(self): self.value = 0
    def close(self): pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", "--sim", dest="sim", action="store_true", help="simuler uten Pi-maskinvare")
    ap.add_argument("--ut", default=None, help="mappe for PNG-skjermbilder i simulering")
    ap.add_argument("--ingen-led", action="store_true", help="hopp over LED-ringene")
    a = ap.parse_args()
    if Image is None:
        sys.exit("Pillow mangler: pip install pillow")

    if not a.sim and not os.path.exists("/dev/spidev0.0"):
        sys.exit("Fant ikke /dev/spidev0.0 – er dtparam=spi=on satt? Bruk --dry-run for simulering.")

    print("Skjold Node selvtest (%s)" % ("SIMULERING" if a.sim else "maskinvare"))
    skjerm = Skjerm(a.sim, a.ut)
    gz = lag_gpio(a.sim)
    print("1) Testbilde – sjekk farger (rød øverst til venstre), hel kant og at teksten står rett vei.")
    skjerm.vis(testbilde(), "testbilde")

    bl_cfg = SK["bakgrunnslys"]
    if gz:
        bl = gz.PWMLED(bl_cfg["gpio"], active_high=bl_cfg["aktiv_hoy"], frequency=bl_cfg["pwm_hz"])
        leds = [] if a.ingen_led else [gz.PWMLED(l["gpio"], frequency=LEDS["pwm_hz"]) for l in LEDS["liste"]]
    else:
        bl = FalskLED("bakgrunnslys")
        leds = [] if a.ingen_led else [FalskLED(l["for"]) for l in LEDS["liste"]]

    print("2) Bakgrunnslys: av → på.")
    bl.off(); time.sleep(0 if a.sim else 0.5); bl.on()
    print("3) LED-ringer blinker én og én:")
    for l, cfg in zip(leds, LEDS["liste"]):
        print("   LED %-6s GPIO%-2d pinne %d" % (cfg["for"], cfg["gpio"], cfg["pin"]))
        l.on(); time.sleep(0 if a.sim else 0.4); l.off()

    logg, tilstand = [], {"volum": 50}
    def hendelse(tekst, led_for=None):
        print("   " + tekst); logg.append(tekst)
        skjerm.vis(statusbilde(logg, tilstand["volum"]), {"◀◀": "prev", "▶▶": "next"}.get(tekst.split()[0], tekst.split()[0].lower().replace("/", "")))
        for l, cfg in zip(leds, LEDS["liste"]):
            if cfg["for"] == led_for:
                l.on(); time.sleep(0 if a.sim else 0.15); l.off()

    print("4) Trykk knappene og vri/trykk encoderen.%s" % ("" if a.sim else " Ctrl+C avslutter."))
    knapper, enc, sw = {}, None, None
    if gz:
        for k in KN["liste"]:
            b = gz.Button(k["gpio"], pull_up=True, bounce_time=KN["bounce_ms"] / 1000, hold_time=k["hold_s"])
            b.when_pressed = lambda k=k: hendelse("%s trykk" % k["etikett"], k["id"])
            b.when_held = lambda k=k: hendelse("%s hold %.0fs" % (k["etikett"], k["hold_s"]), k["id"])
            knapper[k["id"]] = b
        enc = gz.RotaryEncoder(ENC["A"]["gpio"], ENC["B"]["gpio"], max_steps=0, bounce_time=None)
        def vri(retning):
            tilstand["volum"] = max(0, min(100, tilstand["volum"] + retning))
            hendelse("Encoder %s  vol %d" % ("med klokka" if retning > 0 else "mot klokka", tilstand["volum"]))
        enc.when_rotated_clockwise = lambda: vri(+1)
        enc.when_rotated_counter_clockwise = lambda: vri(-1)
        sw = gz.Button(ENC["SW"]["gpio"], pull_up=True, bounce_time=0.01, hold_time=ENC["hold_innstillinger_s"])
        sw.when_pressed = lambda: hendelse("Volum trykk")
        sw.when_held = lambda: hendelse("Volum hold 3s")

    if a.sim:
        simuler(gz, knapper, enc, sw, hendelse, tilstand)
        print("Simulering ferdig: %d hendelser registrert." % len(logg))
        forventet = len(KN["liste"]) + 2 + 1
        if len(logg) < forventet:
            sys.exit("FEIL: forventet minst %d hendelser, fikk %d" % (forventet, len(logg)))
        print("OK")
        return
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        bl.on()


def simuler(gz, knapper, enc, sw, hendelse, tilstand):
    """Driver mock-pinnene (gpiozero) eller kaller hendelsene direkte når gpiozero mangler."""
    if gz and knapper:
        from gpiozero import Device
        f = Device.pin_factory
        for k in KN["liste"]:
            p = f.pin(k["gpio"]); p.drive_low(); time.sleep(0.05); p.drive_high(); time.sleep(0.02)
        a, b = f.pin(ENC["A"]["gpio"]), f.pin(ENC["B"]["gpio"])
        for seq in ([(0, 1), (0, 0), (1, 0), (1, 1)], [(1, 0), (0, 0), (0, 1), (1, 1)]):  # ett hakk hver vei
            for va, vb in seq:
                (a.drive_high if va else a.drive_low)(); (b.drive_high if vb else b.drive_low)(); time.sleep(0.01)
        s = f.pin(ENC["SW"]["gpio"]); s.drive_low(); time.sleep(0.05); s.drive_high(); time.sleep(0.05)
    else:
        print("   (gpiozero ikke installert – kaller hendelsene direkte)")
        for k in KN["liste"]:
            hendelse("%s trykk" % k["etikett"], k["id"])
        for r in (+1, -1):
            tilstand["volum"] += r
            hendelse("Encoder %s  vol %d" % ("med klokka" if r > 0 else "mot klokka", tilstand["volum"]))
        hendelse("Volum trykk")


if __name__ == "__main__":
    main()
