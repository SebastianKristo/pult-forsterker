"""Skjold OS – UI-et på enheten (Skjold Node 160×128 ST7735S, senere S1 OLED/TFT).

Én tegnemotor (gfx.Canvas + fx) og én layout per skjermstørrelse (layouts/).
Daemonen (pi/ki_amp_daemon.py) eier knapper, encoder og LED-ringer; Skjold OS eier
SPI-skjermen og bakgrunnslyset og viser tilstanden ved å polle /api/status.
"""
__version__ = "0.1.0"
