#!/usr/bin/env python3
"""Skjold Node (OLED-utgave) – selvtest av OLED, ADS1115/potmeter, knapper og LED-ringer.

På Pi:      sudo systemctl stop ki-amp skjold-os     (de eier knappene og skjermen)
            /opt/skjold/venv/bin/python tools/node_selftest.py      (Ctrl+C avslutter)
Uten Pi:    python3 tools/node_selftest.py --dry-run  (simulerer hendelser, lagrer skjermbilder som PNG)

Leser alle pinner fra config/node_pins.json (schema 2). Krever på Pi: python3-gpiozero, python3-lgpio,
luma.oled, smbus2 og Pillow (installeres av driver/installer_node.sh). i2cdetect -y 1 skal vise 3c og 48.
"""
import argparse, json, os, sys, time

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROT, "config", "node_pins.json"), encoding="utf-8"))
SK, ADC, POT, KN, LEDS = P["skjerm"], P["adc"], P["potmeter"], P["knapper"], P["leds"]
W, H = SK["width"], SK["height"]

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None


# ---------------------------------------------------------------- skjerm
class Skjerm:
    def __init__(self, sim, utmappe):
        self.sim, self.utmappe, self.n, self.dev = sim, utmappe, 0, None
        if not sim:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            self.dev = ssd1306(i2c(port=SK["i2c_port"], address=int(SK["adresse"], 16)), width=W, height=H, rotate=SK["rotate"])
            self.dev.contrast(SK.get("kontrast", 255))

    def vis(self, img, navn):
        if self.dev:
            self.dev.display(img.convert("1"))
        elif self.utmappe:
            self.n += 1
            sti = os.path.join(self.utmappe, "selftest_%02d_%s.png" % (self.n, navn))
            img.convert("1").resize((W * 4, H * 4), Image.NEAREST).save(sti)
            print("  [sim] skjermbilde → %s" % sti)


def font(st):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if os.path.exists(f):
            return ImageFont.truetype(f, st)
    return ImageFont.load_default()


def testbilde():
    """Hel kant (sjekk at ingen kolonne/rad mangler), sjakkbrett i hjørnene, pil nede til venstre = orientering."""
    img = Image.new("1", (W, H), 0); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=1)
    for y in range(2, 8):
        for x in range(2, 8):
            if (x + y) % 2: d.point((x, y), 1); d.point((W - 1 - x, y), 1)
    d.line([1, H - 2, 9, H - 10], fill=1); d.line([1, H - 2, 5, H - 2], fill=1); d.line([1, H - 2, 1, H - 6], fill=1)
    d.text((14, 3), "SKJOLD NODE", fill=1, font=font(11))
    d.text((14, 17), "selvtest · kant hel?", fill=1, font=font(8))
    return img


def statusbilde(linje, volum, pot_ok):
    img = Image.new("1", (W, H), 0); d = ImageDraw.Draw(img)
    d.text((1, 0), "SELVTEST", fill=1, font=font(8))
    d.text((W - 1, 0), ("POT %3d" % volum) if pot_ok else "INGEN ADC", fill=1, font=font(8), anchor="ra")
    d.text((1, 11), linje[:24], fill=1, font=font(9))
    d.rectangle([1, H - 7, W - 2, H - 2], outline=1)
    if pot_ok: d.rectangle([2, H - 6, 2 + int((W - 5) * volum / 100), H - 3], fill=1)
    return img


# ---------------------------------------------------------------- ADS1115
class Ads1115:
    """A0 mot GND, ±4,096 V, kontinuerlig, 128 SPS. Bare smbus2 – rører ikke bussen ellers."""
    def __init__(self, port, addr):
        from smbus2 import SMBus
        self.bus, self.addr = SMBus(port), addr
        self.bus.write_i2c_block_data(addr, 0x01, [0x42, 0x83])   # MUX=100 (AIN0), PGA=001, MODE=0, DR=100, COMP av
        time.sleep(0.01)

    def volt(self):
        hi, lo = self.bus.read_i2c_block_data(self.addr, 0x00, 2)
        raw = (hi << 8) | lo
        if raw >= 0x8000: raw -= 0x10000
        return raw * 4.096 / 32768


class FalskAdc:
    def __init__(self): self.v = 0.0
    def volt(self): return self.v


def pot_prosent(v):
    p = max(0.0, min(1.0, v / POT["vref_v"])) * 100
    return round(100 - p if POT.get("inverter") else p)


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
    if a.ut: os.makedirs(a.ut, exist_ok=True)

    if not a.sim and not os.path.exists("/dev/i2c-%d" % SK["i2c_port"]):
        sys.exit("Fant ikke /dev/i2c-%d – er dtparam=i2c_arm=on satt (og i2c-dev lastet)? Bruk --dry-run for simulering." % SK["i2c_port"])

    print("Skjold Node selvtest (%s)" % ("SIMULERING" if a.sim else "maskinvare"))
    try:
        skjerm = Skjerm(a.sim, a.ut)
    except Exception as e:
        print("  OLED (0x%s) svarer ikke: %s – fortsetter uten skjerm" % (SK["adresse"][2:], e)); skjerm = Skjerm(True, None)
    gz = lag_gpio(a.sim)
    print("1) Testbilde – sjekk at kanten er hel og teksten står rett vei (pil nede til venstre).")
    skjerm.vis(testbilde(), "testbilde")

    if a.sim:
        adc = FalskAdc()
    else:
        try:
            adc = Ads1115(ADC["i2c_port"], int(ADC["adresse"], 16)); adc.volt()
            print("2) ADS1115 funnet på %s." % ADC["adresse"])
        except Exception as e:
            adc = None; print("2) ADS1115 (%s) svarer ikke: %s – sjekk VDD/GND/SDA/SCL og ADDR→GND." % (ADC["adresse"], e))

    if gz:
        leds = [] if a.ingen_led else [gz.PWMLED(l["gpio"], frequency=LEDS["pwm_hz"]) for l in LEDS["liste"]]
    else:
        leds = [] if a.ingen_led else [FalskLED(l["for"]) for l in LEDS["liste"]]
    print("3) LED-ringer blinker én og én:")
    for l, cfg in zip(leds, LEDS["liste"]):
        print("   LED %-6s GPIO%-2d pinne %d" % (cfg["for"], cfg["gpio"], cfg["pin"]))
        l.on(); time.sleep(0 if a.sim else 0.4); l.off()

    logg, tilstand = [], {"volum": 0, "siste": "Trykk en knapp"}
    def tegn(navn="status"):
        skjerm.vis(statusbilde(tilstand["siste"], tilstand["volum"], adc is not None), navn)

    def hendelse(tekst, led_for=None):
        print("   " + tekst); logg.append(tekst); tilstand["siste"] = tekst
        tegn({"◀◀": "prev", "▶▶": "next"}.get(tekst.split()[0], tekst.split()[0].lower().replace("/", "")))
        for l, cfg in zip(leds, LEDS["liste"]):
            if cfg["for"] == led_for:
                l.on(); time.sleep(0 if a.sim else 0.15); l.off()

    print("4) Trykk knappene og vri potmeteret.%s" % ("" if a.sim else " Ctrl+C avslutter."))
    knapper = {}
    if gz:
        for k in KN["liste"]:
            b = gz.Button(k["gpio"], pull_up=True, bounce_time=KN["bounce_ms"] / 1000, hold_time=k["hold_s"])
            b.when_pressed = lambda k=k: hendelse("%s trykk" % k["etikett"], k["id"])
            b.when_held = lambda k=k: hendelse("%s hold %.0fs" % (k["etikett"], k["hold_s"]), k["id"])
            knapper[k["id"]] = b

    def les_pot():
        if adc is None: return
        v = adc.volt(); p = pot_prosent(v)
        if abs(p - tilstand["volum"]) >= POT["hysterese"]:
            tilstand["volum"] = p; hendelse("Pot %.2f V = %d" % (v, p))

    if a.sim:
        simuler(gz, knapper, hendelse, adc, les_pot)
        print("Simulering ferdig: %d hendelser registrert." % len(logg))
        forventet = len(KN["liste"]) + 2
        if len(logg) < forventet:
            sys.exit("FEIL: forventet minst %d hendelser, fikk %d" % (forventet, len(logg)))
        print("OK")
        return
    try:
        while True:
            les_pot(); time.sleep(1.0 / POT["poll_hz"])
    except KeyboardInterrupt:
        pass


def simuler(gz, knapper, hendelse, adc, les_pot):
    """Driver mock-pinnene (gpiozero) eller kaller hendelsene direkte når gpiozero mangler; skrur på falsk pot."""
    if gz and knapper:
        from gpiozero import Device
        f = Device.pin_factory
        for k in KN["liste"]:
            p = f.pin(k["gpio"]); p.drive_low(); time.sleep(0.05); p.drive_high(); time.sleep(0.02)
    else:
        print("   (gpiozero ikke installert – kaller hendelsene direkte)")
        for k in KN["liste"]:
            hendelse("%s trykk" % k["etikett"], k["id"])
    for v in (0.0, 0.01, 1.65, 1.66, 3.3):   # 0,01/1,66 V er under hysteresen og skal ikke gi hendelse
        adc.v = v; les_pot()


if __name__ == "__main__":
    main()
