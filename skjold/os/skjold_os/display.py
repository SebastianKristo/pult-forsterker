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

    def show(self, img, tag=""):
        im = img.convert("L").point(lambda v: 255 if v > 64 else 0).convert("1")
        if im.size != self.dev.size: im = im.resize(self.dev.size)
        self.dev.display(im)

    def close(self):
        try: self.dev.hide(); self.dev.cleanup()
        except Exception: pass


class LumaST7735:
    def __init__(self, sk):
        from luma.core.interface.serial import spi
        from luma.lcd.device import st7735
        ser = spi(port=sk["spi_port"], device=sk["spi_device"], gpio_DC=sk["pinner"]["A0"]["gpio"],
                  gpio_RST=sk["pinner"]["RESET"]["gpio"], bus_speed_hz=sk["bus_speed_hz"])
        # Bakgrunnslyset styres av Backlight under (Q1 high-side, aktiv lav), ikke av luma (gpio_LIGHT=None,
        # ellers tar luma GPIO18 som er reservert for I²S).
        self.dev = st7735(ser, width=sk["width"], height=sk["height"], rotate=sk["rotate"], bgr=sk["bgr"],
                          h_offset=sk["h_offset"], v_offset=sk["v_offset"], gpio_LIGHT=None)

    def show(self, img, tag=""): self.dev.display(img)
    def close(self):
        try: self.dev.cleanup()
        except Exception: pass


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
    """PWM-dimming med gpiozero (programvare-PWM, 500 Hz). Uten maskinvare: bare husker nivået."""
    def __init__(self, cfg, sim=False):
        self.level, self.led = None, None
        if not sim:
            try:
                import gpiozero
                self.led = gpiozero.PWMLED(cfg.get("gpio", 23), active_high=bool(cfg.get("aktiv_hoy", False)),
                                           frequency=cfg.get("pwm_hz", 500))
            except Exception as e:
                print("Bakgrunnslys utilgjengelig:", e, flush=True)

    def set(self, v):
        v = round(max(0.0, min(1.0, v)), 3)
        if v == self.level: return
        self.level = v
        if self.led is not None:
            try: self.led.value = v
            except Exception: pass

    def close(self):
        if self.led is not None:
            try: self.led.value = 0; self.led.close()
            except Exception: pass
