#!/usr/bin/env python3
"""Lager de ferdige K2-platene for frontplaten til Skjold S1 fra de to STL-filene per variant.

    python3 kabinett/skjold-s1/print/lag_3mf.py

Plata er ett objekt med to deler (khaki plate + sort innlegg), forsiden ned. Filament og utskriftsinnstillinger ligger i
fila (Metadata/model_settings.config), så Creality Print og OrcaSlicer setter riktig farge på hver del selv.
"""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HER)
sys.path.insert(0, os.path.join(HER, "..", "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402

L.STL = "."
# Lang, flat plate (186 × 44 × 4 mm): rolig første lag så den sorte teksten blir skarp, og brim mot at endene løfter seg
INNST = {"enable_support": "0", "brim_type": "outer_only", "brim_width": "5", "brim_object_gap": "0",
         "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.1"}
for v, skjerm in (("oled", "OLED"), ("tft", "TFT")):
    khaki = f"skjold_s1_frontplate_{v}_khaki"
    L.OBJ_INNST = {khaki: INNST}
    L.write(f"skjold_s1_frontplate_{v}.3mf", f"Skjold S1 – frontplate for {skjerm}-skjerm (PETG, forsiden ned)", [
        (khaki, "Frontplate (Light Khaki, forsiden ned)", 1, (32, 103), None),
        (f"skjold_s1_frontplate_{v}_sort_innlegg", "Tekst, ramme og symboler (sort)", 2, None, khaki)],
        {1: "#C9B79A", 2: "#101010"})
    print("skrev", f"skjold_s1_frontplate_{v}.3mf")
