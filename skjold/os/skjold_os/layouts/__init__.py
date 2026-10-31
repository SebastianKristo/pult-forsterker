"""Én layout per skjermstørrelse. Tegnemotoren (gfx/fx) er felles.

  node      160×128 ST7735S (Skjold Node)                – ferdig
  s1-oled   128×64  OLED (S1, drawOLED0 i design/s1/pultforsterker_revb_metall.js) – krok
  s1-tft    320×240 TFT  (S1, drawTFT0)                   – krok
"""
from .node import NodeLayout
from .s1 import S1OledLayout, S1TftLayout

LAYOUTS = {"node": NodeLayout, "s1-oled": S1OledLayout, "s1-tft": S1TftLayout}

def get(name): return LAYOUTS[name]()
