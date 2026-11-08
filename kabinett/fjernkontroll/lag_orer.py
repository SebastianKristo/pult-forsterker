"""Museører for toppen: tynne skiver (Ø14 × 0,4 mm) i hjørnene, som holder enden med SKJOLD nede på plata.
Toppen printes med forsiden ned, og halen (smal, avrundet og med fas mot plata) er det som løfter seg først.
Skivene overlapper kanten noen millimeter og vris/skjæres av etter print. Lager orer.stl i hver STL-mappe."""
import sys
import trimesh

R, H = 7.0, 0.4


def orer(lengde, bredde=55.0):
    pts = [(5.0, lengde - 5.0), (bredde - 5.0, lengde - 5.0), (bredde / 2, lengde + 1.5),   # halen (SKJOLD)
           (5.0, 5.0), (bredde - 5.0, 5.0)]                                                 # nesen
    disker = [trimesh.creation.cylinder(radius=R, height=H, sections=64).apply_translation((x, y, H / 2)) for x, y in pts]
    return trimesh.util.concatenate(disker)


if __name__ == "__main__":
    for d in sys.argv[1:] or ["stl", "stl_full", "stl_hu", "stl_en"]:
        b = trimesh.load(f"{d}/topp.stl").bounds
        t = trimesh.load(f"{d}/topp.stl")
        # skivene skal bare røre toppen (lag_3mf.py tillater ikke overlapp): trekk toppen fra
        trimesh.boolean.difference([orer(b[1][1] - b[0][1], b[1][0] - b[0][0]), t]).export(f"{d}/orer.stl")
        print("skrev", f"{d}/orer.stl")
