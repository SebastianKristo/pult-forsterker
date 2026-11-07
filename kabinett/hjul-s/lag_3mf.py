"""K2-plate for Skjold Hjul S (gjenbruker 3MF-skriveren fra kabinett/kassett/lag_3mf.py).

    python3 lag_3mf.py     # skriver skjold-hjul-s-k2.3mf: bordstativ, bunnlokk og veggplate
Filament: 1 = lys (stativ, veggplate), 2 = sort (bunnlokk)."""
import importlib.util
import os

HER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("k3mf", os.path.join(HER, "..", "kassett", "lag_3mf.py"))
k = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k)
k.HER = HER

HOVED = [("stativ", "Bordstativ", 1, 5, 5), ("bunnlokk", "Bunnlokk", 2, 95, 5), ("veggplate", "Veggplate (magneter)", 1, 5, 100)]

if __name__ == "__main__":
    k.skriv("skjold-hjul-s-k2.3mf", HOVED, "Skjold Hjul S – stativ for M5Stack Dial (Creality K2)")
