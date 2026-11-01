"""Skjold S1-skjermer, samme oppsett som pi/oled_display.py og pi/tft_screen.py:

  OLED  luma.oled ssd1309 på I²C port 1, adresse 0x3C, RST=GPIO4 (KI_AMP_OLED=ssd1306_128x64|_128x32 + KI_AMP_OLED_ADDR støttes)
  TFT   fbtft-framebufferen (dtoverlay=fbtft,spi0-0,ili9341|st7789v,dc_pin=5,reset_pin=6,rotate=90 i config.txt), RGB565
Lysstyrke: OLED-en har ikke bakgrunnslys – OledContrast styrer kontrasten (0 = display av). TFT-ens LED er ikke
koblet til en GPIO i pi/install.sh, så FbBacklight demper selve bildet i stedet.
"""
import glob, os


class LumaSSD1309:
    def __init__(self):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306, ssd1309
        kind = os.environ.get("KI_AMP_OLED", "ssd1309_128x64"); addr = int(os.environ.get("KI_AMP_OLED_ADDR", "0x3C"), 16)
        if kind.startswith("ssd1306"):
            self.dev = ssd1306(i2c(port=1, address=addr), width=128, height=32 if kind.endswith("x32") else 64)
        else:
            self.dev = ssd1309(i2c(port=1, address=addr), gpio_RST=4)
        self.level = 1.0

    def show(self, img, tag=""):
        im = img.convert("L").point(lambda v: 255 if v > 64 else 0).convert("1")
        if im.size != self.dev.size: im = im.resize(self.dev.size)
        self.dev.display(im)

    def close(self):
        try: self.dev.cleanup()
        except Exception: pass


class OledContrast:
    """Samme grensesnitt som display.Backlight: set(0–1). 0 = hide() (panelet av), ellers kontrast."""
    def __init__(self, sink, full=255): self.sink, self.level, self.full = sink, None, full

    def set(self, v):
        v = round(max(0.0, min(1.0, v)), 3)
        if v == self.level: return
        self.level = v; d = getattr(self.sink, "dev", None)
        if d is None: return
        try:
            if v <= 0: d.hide()
            else: d.show(); d.contrast(max(1, int(self.full * v)))
        except Exception: pass

    def close(self): self.set(0)


def find_fb():
    for n in sorted(glob.glob("/sys/class/graphics/fb*/name")):
        try:
            if open(n).read().strip().startswith("fb_"): return "/dev/" + n.split("/")[-2]
        except Exception: pass
    return None


class FbTFT:
    def __init__(self, path=None):
        self.path = path or os.environ.get("SKJOLD_FB") or find_fb()
        if not self.path: raise RuntimeError("ingen fbtft-framebuffer (sjekk dtoverlay=fbtft,... i config.txt)")
        sysd = "/sys/class/graphics/" + os.path.basename(self.path)
        try: self.size = tuple(int(x) for x in open(sysd + "/virtual_size").read().strip().split(","))
        except Exception: self.size = (320, 240)
        self.f = open(self.path, "wb", buffering=0); self.gain = 1.0

    def show(self, img, tag=""):
        import numpy as np
        if img.size != self.size: img = img.resize(self.size)
        a = np.asarray(img.convert("RGB"), dtype=np.float32)
        if self.gain < 1: a = a * self.gain
        a = a.astype(np.uint16)
        v = ((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5) | (a[:, :, 2] >> 3)
        self.f.seek(0); self.f.write(v.astype("<u2").tobytes()); self._last = img

    def close(self):
        try: self.f.seek(0); self.f.write(b"\0" * (self.size[0] * self.size[1] * 2)); self.f.close()
        except Exception: pass


class FbBacklight:
    """Ingen bakgrunnslys-pinne: dimmer bildet (gain) og tegner forrige ramme på nytt."""
    def __init__(self, sink): self.sink, self.level = sink, None

    def set(self, v):
        v = round(max(0.0, min(1.0, v)), 3)
        if v == self.level: return
        self.level = v; self.sink.gain = v
        if getattr(self.sink, "_last", None) is not None: self.sink.show(self.sink._last)

    def close(self): pass


def open_s1(layout_name):
    """(sink, backlight) for --layout s1-oled / s1-tft på maskinvare."""
    if layout_name == "s1-tft":
        s = FbTFT(); return s, FbBacklight(s)
    s = LumaSSD1309(); return s, OledContrast(s)
