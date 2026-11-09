"""3MF-plate for Skjold Dokk (Creality K2, 250 × 250 mm): vugga (Bone White), sokkelen (mørk) med gullstripa felt inn,
og lokket til vektlomma. Ingen støtte: vugga står på bunnen (ryggen heller 25° bakover), sokkelen står på bunnen
(vektlomma og fotsporene er åpne nedover; taket over vektlomma er en bro på 30 mm).
Kjør etter lag_dokk.sh har laget stl/:  python3 lag_3mf_dokk.py"""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import lag_3mf  # noqa: E402

lag_3mf.STL = os.path.join(HER, "stl")
lag_3mf.write(os.path.join(HER, "skjold-dokk-k2.3mf"), "Skjold Dokk – vugge, sokkel og lokk (PLA/PETG)", [
    ("vugge", "Vugge (Bone White)", 1, (12, 20), None),
    ("sokkel", "Sokkel (mørk)", 2, (95, 20), None),
    ("gull", "Gullstripe (felt inn i sokkelen)", 3, None, "sokkel"),
    ("lokk", "Lokk til vektlomma (mørk)", 2, (12, 150), None),
], {1: "#CEC6B4", 2: "#2E2D2C", 3: "#D99E40"})
# bare vugga (til en sokkel som allerede er printet)
lag_3mf.write(os.path.join(HER, "skjold-dokk-k2-vugge.3mf"), "Skjold Dokk – bare vugga (passer på sokkelen)", [
    ("vugge", "Vugge (Bone White)", 1, (90, 80), None)], {1: "#CEC6B4"})
# propp til lysdiodehullet foran (for deg som ikke vil ha lys)
lag_3mf.write(os.path.join(HER, "skjold-dokk-k2-led-propp.3mf"), "Skjold Dokk – propp til lysdiodehullet", [
    ("led_propp", "Propp (mørk, stående)", 2, (120, 120), None)], {2: "#2E2D2C"})
