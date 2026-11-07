"""K2-plater for Skjold Kassetthylle (gjenbruker 3MF-skriveren fra kabinett/kassett/lag_3mf.py).

    python3 lag_3mf.py     # skriver skjold-hylle-k2.3mf (én modul à 3 plasser + endestykker) og skjold-hylle-k2-klar.3mf
Print én hovedplate per modul (2 moduler = 6 plasser). Filament: 1 = lys (modul), 2 = sort (lokk, endestykker), 4 = klar."""
import importlib.util
import os

HER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("k3mf", os.path.join(HER, "..", "kassett", "lag_3mf.py"))
k = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k)
k.HER = HER

HOVED = [("modul", "Hyllemodul (3 plasser)", 1, 3, 3), ("ende_esp", "Endestykke med ESP32-C3", 2, 196, 3),
         ("ende_blind", "Endestykke (blind)", 2, 196, 52), ("lokk", "Lokk bak (lesere)", 2, 3, 100)]
KLAR = [("lysleder", "Lysledere (klar PETG, 3 stk)", 4, 10, 10)]

if __name__ == "__main__":
    k.skriv("skjold-hylle-k2.3mf", HOVED, "Skjold Kassetthylle – modul med 3 plasser (Creality K2)")
    k.skriv("skjold-hylle-k2-klar.3mf", KLAR, "Skjold Kassetthylle – lysledere i klar PETG (Creality K2)")
