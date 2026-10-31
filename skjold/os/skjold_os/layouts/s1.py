"""Skjold S1: to skjermvarianter av samme kabinett (skjold/design/s1/pultforsterker_revb_metall.js).

  s1-oled  128×64 SSD1309 2,42″, monokrom (drawOLED0)  -> s1_oled.S1OledLayout, 1-bit, pikselfont
  s1-tft   320×240 ILI9341/ST7789V (drawTFT0)          -> s1_tft.S1TftLayout, overlegg = overlay() ×2,5 fra y=40
Felles overlegg (omstart, paring, hold/«Lagret», meny, kildebytte, ingen kontakt) ligger i s1_common.
Maskinvare: display_s1.py (luma.oled ssd1309 på I²C 0x3C / fbtft-framebuffer).
"""
from .s1_oled import S1OledLayout
from .s1_tft import S1TftLayout

__all__ = ["S1OledLayout", "S1TftLayout"]
