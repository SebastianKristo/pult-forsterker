"""KROK for Skjold S1. Ikke ferdig – Node er prioritert.

Kildene å oversette er drawOLED0 (128×64, monokrom SSD1309/SSD1306) og drawTFT0 (320×240)
samt overlay() i skjold/design/s1/pultforsterker_revb_metall.js. Slik gjør du det:
  1. Lag en metode draw_<screen>(c, vm) per skjerm, som i NodeLayout. ViewModel-en (app.Ui.viewmodel)
     er den samme for alle layouter, så bare tegningen skal skrives.
  2. fx.splash/reboot/switch_src/welcome/draw_clock er skrevet for vilkårlig w×h der designet gjør det
     (welcome og draw_clock skalerer selv; splash/reboot/switch er Node-mål og må tilpasses).
  3. OLED: sett MONO = True, så app-en konverterer til 1-bit og bruker luma.oled (ssd1309) i display.py.
Inntil da arver S1-layoutene Node-tegningen skalert, så --layout s1-* gir et brukbart (men ikke riktig) bilde.
"""
from PIL import Image
from .node import NodeLayout


class _Scaled(NodeLayout):
    MONO = False
    def render(self, vm):
        im = super().render(vm)
        out = Image.new("RGB", (self.OUT_W, self.OUT_H))
        k = min(self.OUT_W / 160, self.OUT_H / 128); im = im.resize((int(160 * k), int(128 * k)), Image.LANCZOS)
        out.paste(im, ((self.OUT_W - im.width) // 2, (self.OUT_H - im.height) // 2))
        return out.convert("1").convert("RGB") if self.MONO else out


class S1OledLayout(_Scaled):
    OUT_W, OUT_H, MONO, name = 128, 64, True, "s1-oled"     # TODO: drawOLED0


class S1TftLayout(_Scaled):
    OUT_W, OUT_H, name = 320, 240, "s1-tft"                 # TODO: drawTFT0
