"""Utganger: SSD1306 128×32 via luma.oled (Node, OLED-utgave), ST7735 via luma.lcd (Node rev A/B) eller PNG-filer
(--sim). Pluss bakgrunnslyset for ST7735 (GPIO23, aktiv lav). OLED-en har ingen bakgrunnslys: display_s1.OledContrast."""
import os, time


class LumaSSD1306:
    """0,91″ SSD1306 på I²C (port/adresse/rotasjon fra node_pins.json → skjerm). luma åpner /dev/i2c-1 delt –
    ki-amp leser ADS1115 (0x48) på samme buss samtidig, hver overføring er én atomisk I²C-transaksjon i kjernen."""
    def __init__(self, sk):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        addr = sk.get("adresse", "0x3C"); addr = int(addr, 16) if isinstance(addr, str) else int(addr)
        self.dev = ssd1306(i2c(port=int(sk.get("i2c_port", 1)), address=addr), width=int(sk.get("width", 128)),
                           height=int(sk.get("height", 32)), rotate=int(sk.get("rotate", 2)))

        # Samme registre som oppstartsskjermen (skjold_early.py), som ser riktig ut: standard klokke (0xD5 0x80 –
        # 0xF0 ga flimring), lang forlading (0xD9 0xF1) og høy VCOMH (0xDB 0x40) → jevnt og sterkt lys.
        try: self.dev.command(0xD5, 0x80); self.dev.command(0xD9, 0xF1); self.dev.command(0xDB, 0x40)
        except Exception: pass
        self.prev = None   # forrige sides bytes per side (8 rader) – bare endrede sider/kolonner sendes

    def show(self, img, tag=""):
        im = img.convert("L").point(lambda v: 255 if v > 64 else 0).convert("1")
        if im.size != self.dev.size: im = im.resize(self.dev.size)
        try: self._partial(im)
        except Exception: self.prev = None; self.dev.display(im)

    def _partial(self, im):
        """Rullende tekst flimret: hele bildet (512 byte) over I²C for hver ramme. Her sendes bare de sidene og
        kolonnene som er endret siden forrige ramme, med SSD1306-ens kolonne-/sideadressering (0x21/0x22)."""
        im = self.dev.preprocess(im)
        w, h = im.size; px = im.load(); pages = h // 8
        cur = [bytes(sum((1 << b) for b in range(8) if px[x, p * 8 + b]) for x in range(w)) for p in range(pages)]
        prev, self.prev = self.prev, cur
        for p in range(pages):
            if prev is not None and prev[p] == cur[p]: continue
            x0, x1 = 0, w - 1
            if prev is not None:
                while x0 < w and prev[p][x0] == cur[p][x0]: x0 += 1
                while x1 > x0 and prev[p][x1] == cur[p][x1]: x1 -= 1
            self.dev.command(0x21, x0, x1)        # kolonneområde
            self.dev.command(0x22, p, p)          # én side
            self.dev.data(list(cur[p][x0:x1 + 1]))

    def close(self, keep=False):
        """keep=True: la siste bilde stå (omstart/slå av – skjold-shutdown tegner sluttbildet etterpå)."""
        try:
            if keep: self.dev.persist = True
            else: self.dev.hide()
            self.dev.cleanup()
        except Exception: pass


class _IngenGPIO:
    """Stand-in for RPi.GPIO som luma.lcd bare bruker til bakgrunnslyset. Nyere luma.lcd godtar ikke gpio_LIGHT=None
    (GPIO.setup(None) → «Channel must be an integer»), og vi styrer lyset selv med Backlight (PWM på GPIO 13)."""
    OUT, IN, HIGH, LOW, BCM = 0, 1, 1, 0, 11
    def setmode(self, *a, **k): pass
    def setwarnings(self, *a, **k): pass
    def setup(self, *a, **k): pass
    def output(self, *a, **k): pass
    def cleanup(self, *a, **k): pass


class LumaST7735:
    def __init__(self, sk):
        from luma.core.interface.serial import spi
        from luma.lcd.device import st7735
        ser = spi(port=sk["spi_port"], device=sk["spi_device"], gpio_DC=sk["pinner"]["A0"]["gpio"],
                  gpio_RST=sk["pinner"]["RESET"]["gpio"], bus_speed_hz=sk["bus_speed_hz"])
        # Bakgrunnslyset styres av Backlight under, ikke av luma: luma får en GPIO-stand-in som ikke gjør noe
        # (ellers tar luma GPIO18, som er reservert for I²S, eller krasjer på gpio_LIGHT=None).
        self.dev = st7735(ser, width=sk["width"], height=sk["height"], rotate=sk["rotate"], bgr=sk["bgr"],
                          h_offset=sk["h_offset"], v_offset=sk["v_offset"], gpio=_IngenGPIO(), gpio_LIGHT=0)

        # Billige ST7735-paneler gir bleke, gråaktige farger. Litt mer metning og kontrast (justeres i node_pins.json →
        # skjerm_tft.farge: {"metning", "kontrast", "gamma"}; 1.0 = av).
        f = sk.get("farge") if isinstance(sk.get("farge"), dict) else {}
        self.metning, self.kontrast, self.gamma = float(f.get("metning", 1.25)), float(f.get("kontrast", 1.1)), float(f.get("gamma", 0.9))
        self._lut = None
        if abs(self.gamma - 1.0) > 0.01:
            self._lut = [int(round(255 * (i / 255) ** self.gamma)) for i in range(256)] * 3

    def _farge(self, img):
        from PIL import ImageEnhance
        img = img.convert("RGB")
        if abs(self.metning - 1.0) > 0.01: img = ImageEnhance.Color(img).enhance(self.metning)
        if abs(self.kontrast - 1.0) > 0.01: img = ImageEnhance.Contrast(img).enhance(self.kontrast)
        if self._lut: img = img.point(self._lut)
        return img

    def show(self, img, tag=""): self.dev.display(self._farge(img))
    def close(self):
        try: self.dev.cleanup()
        except Exception: pass


def fargetest(w=160, h=128):
    """Testbilde for TFT-en: rød, grønn, blå, hvit og Skjold-gull med navn. Er rød og blå byttet, sett bgr i
    skjerm_tft i /etc/skjold/node_pins.json til motsatt verdi."""
    from PIL import Image, ImageDraw
    from .gfx import font
    im = Image.new("RGB", (w, h), (0, 0, 0)); d = ImageDraw.Draw(im)
    felt = [("RØD", (255, 0, 0)), ("GRØNN", (0, 255, 0)), ("BLÅ", (0, 0, 255)), ("HVIT", (255, 255, 255)), ("GULL", (217, 164, 65))]
    bh = h // len(felt)
    for i, (n, c) in enumerate(felt):
        d.rectangle([0, i * bh, w, (i + 1) * bh - 1], fill=c)
        d.text((6, i * bh + bh // 2), n, fill=(0, 0, 0) if sum(c) > 300 else (255, 255, 255), font=font("bold", 12), anchor="lm")
    return im


class PngSink:
    """--sim: skriver rammer til mappen. every=N lagrer hver N-te ramme; named() brukes av --shots."""
    def __init__(self, outdir, every=0, keep_latest=True):
        self.outdir, self.every, self.n, self.keep = outdir, every, 0, keep_latest
        os.makedirs(outdir, exist_ok=True)

    def show(self, img, tag=""):
        self.n += 1
        if self.keep: img.save(os.path.join(self.outdir, "latest.png"))
        if self.every and self.n % self.every == 0:
            img.save(os.path.join(self.outdir, "frame_%05d%s.png" % (self.n, ("_" + tag) if tag else "")))

    def close(self): pass


class Backlight:
    """Bakgrunnslyset med gpiozero. Fullt lys og av er en fast utgang (ingen PWM); bare dimming bruker PWM.
    Node har ikke maskinvare-PWM ledig (3,5 mm-lyden bruker PWM0/1), og programvare-PWM får ujevne pulser når CPU-en
    har mye å gjøre – det ga flimring og svakere lys også på «fullt». Uten maskinvare: bare husker nivået."""
    def __init__(self, cfg, sim=False):
        self.level, self.led = None, None
        self.hz, self.high = cfg.get("pwm_hz", 500), bool(cfg.get("aktiv_hoy", False))
        if not sim:
            try:
                import gpiozero
                self.led = gpiozero.PWMLED(cfg.get("gpio", 23), active_high=self.high, frequency=self.hz)
            except Exception as e:
                print("Bakgrunnslys utilgjengelig:", e, flush=True)

    def set(self, v):
        v = round(max(0.0, min(1.0, v)), 3)
        if v >= 0.97: v = 1.0                     # «nesten fullt» = fullt: fast utgang, ingen flimring
        if v == self.level: return
        self.level = v
        if self.led is None: return
        try:
            pin = self.led.pin
            if v in (0.0, 1.0):
                if pin.frequency: pin.frequency = None    # PWM av
                pin.state = int(bool(v) == self.high)     # fast på/av (aktiv høy eller lav)
            else:
                if not pin.frequency: pin.frequency = self.hz
                self.led.value = v
        except Exception:
            try: self.led.value = v
            except Exception: pass

    def close(self):
        if self.led is not None:
            try: self.led.value = 0; self.led.close()
            except Exception: pass
