"""3MF for IKEA-plata på Elko-ramme: fronten (toppen ned) og bakplata (skjørtet opp) på én plate, 250 × 250 mm.
Holderen for BILRESA og låseringen for TIMMERFLOTTE printes fra original/ (uendret)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fjernkontroll"))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import lag_3mf as L   # noqa: E402

L.STL = "stl"
L.write("ikea-elko-plate.3mf", "IKEA BILRESA + TIMMERFLOTTE – plate for Elko-ramme", [
    ("front", "Front (toppen ned)", 1, (2, 20), None),
    ("bak", "Bakplate over Elko-rammen (fronten ned)", 1, (2, 130), None),
], {1: "#ECE9E3"})
