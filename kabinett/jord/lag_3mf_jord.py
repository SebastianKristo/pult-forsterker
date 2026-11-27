"""3MF for Skjold Jord (Bambu Lab P3C med fem hoder, eller én skriver med flere farger):
  skjold-jord.3mf   kroppen (forsiden ned) med SKJOLD og dråpen i gull, lokket, og TPU-delene
                    1 = PETG (kropp og lokk) · 3 = gull PLA (logoen) · 4 = TPU 95A (pakning, mansjett og USB-plugg)
Kroppen og lokket i PETG (tåler sol og fukt bedre enn PLA). Gjenbruker skriveren fra fjernkontrollen."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fjernkontroll"))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import lag_3mf as L   # noqa: E402

L.STL = "stl"
L.EKSTRA_INNST["kropp"] = L.stotte(1)   # trestøtte fra plata (USB-åpningen), grensesnitt i PLA (hode 1 brukes ikke ellers)
L.EKSTRA_INNST["kropp"]["support_interface_filament"] = "3"
FARGER = {1: "#2E2D2C", 3: "#D99E40", 4: "#4A7FB8"}
L.write("skjold-jord.3mf", "Skjold Jord – kropp, lokk og TPU-deler", [
    ("kropp", "Kropp (forsiden ned, PETG)", 1, (20, 20), None),
    ("logo", "SKJOLD og dråpe (gull, felt inn)", 3, None, "kropp"),
    ("lokk", "Lokk (yttersiden ned, PETG)", 1, (150, 20), None),
    ("pakning", "Pakning til lokket (TPU 95A)", 4, (20, 150), None),
    ("mansjett", "Mansjett rundt sensoren (TPU 95A, kragen ned)", 4, (100, 160), None),
    ("plugg", "Plugg for USB-C (TPU 95A)", 4, (160, 160), None),
], FARGER)
