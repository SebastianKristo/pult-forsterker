"""Én layout per skjermstørrelse. Tegnemotoren (gfx/fx) er felles.

  node-oled32  128×32 SSD1306 OLED (Skjold Node, OLED-utgave) – standard for Node
  node      160×128 ST7735S (Skjold Node rev A/B)        – ferdig, beholdes
  s1-oled   128×64  OLED (S1, drawOLED0 i design/s1/pultforsterker_revb_metall.js) – krok
  s1-tft    320×240 TFT  (S1, drawTFT0)                   – krok
"""
from .node import NodeLayout
from .node_oled32 import NodeOled32Layout
from .s1 import S1OledLayout, S1TftLayout

LAYOUTS = {"node-oled32": NodeOled32Layout, "node": NodeLayout, "s1-oled": S1OledLayout, "s1-tft": S1TftLayout}

def get(name): return LAYOUTS[name]()
