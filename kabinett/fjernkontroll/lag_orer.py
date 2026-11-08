"""Museører for toppen: tynne skiver (Ø14 × 0,4 mm) i hjørnene, som holder enden med SKJOLD nede på plata.
Toppen printes med forsiden ned, og halen (smal, avrundet og med fas mot plata) er det som løfter seg først.
Skivene overlapper kanten noen millimeter og vris/skjæres av etter print. Lager orer.stl i hver STL-mappe."""
import sys
import trimesh

R, H = 7.0, 0.4


def orer(lengde, bredde=55.0):
    # halehjørnene løfter seg mest (smal, rund hale med fas): større og tykkere skiver der
    pts = [(4.0, lengde - 6.0, 10.0, 0.6), (bredde - 4.0, lengde - 6.0, 10.0, 0.6),        # halehjørnene
           (bredde / 2, lengde + 1.5, R, H),                                                 # midt på halen
           (5.0, 5.0, R, H), (bredde - 5.0, 5.0, R, H)]                                      # nesen
    disker = [trimesh.creation.cylinder(radius=r, height=h, sections=72).apply_translation((x, y, h / 2)) for x, y, r, h in pts]
    return trimesh.util.concatenate(disker)


if __name__ == "__main__":
    for d in sys.argv[1:] or ["stl", "stl_full", "stl_hu", "stl_en"]:
        b = trimesh.load(f"{d}/topp.stl").bounds
        t = trimesh.load(f"{d}/topp.stl")
        # skivene skal bare røre toppen (lag_3mf.py tillater ikke overlapp): trekk toppen fra
        trimesh.boolean.difference([orer(b[1][1] - b[0][1], b[1][0] - b[0][0]), t]).export(f"{d}/orer.stl")
        print("skrev", f"{d}/orer.stl")
