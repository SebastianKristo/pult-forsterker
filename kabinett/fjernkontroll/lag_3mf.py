"""Lag 3MF-platene for Skjold Fjernkontroll (Creality K2 / K2 Pro / K2 Plus, 250 × 250 mm):

  skjold-fjernkontroll-k2.3mf         topp (forsiden ned) med SKJOLD i gull, og bunn          filament 1 lys · 2 mørk · 3 gull
  skjold-fjernkontroll-k2-taster.3mf  alle hetter (flensen ned) med symbolene felt inn, gullring
                                      og Skjold-tast, smarthus-tastene i lys farge, og IR-vinduet  1 lys · 2 mørk · 3 gull · 4 klar

Standard er kort variant (uten talltastene og smarthus-raden), fra stl/. Full variant: samme tre plater med «-full»
i navnet, fra stl_full/.
Kjør etter at STL-ene er eksportert:  python3 lag_3mf.py   (eller ./lag_stl.sh, som gjør alt)
Hver del får filamentnummer i Metadata/model_settings.config (Creality Print / OrcaSlicer).
Mørk variant: bytt filament 1 og 2 i sliceren (mørk topp, lys bunn og lyse taster med mørke symboler).
Hettene ligger i samme mønster som på fjernkontrollen (spredt litt ut), så de er lette å finne igjen."""
import itertools
import math
import zipfile

import trimesh
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)   # trimesh: tomme snitt gir 0/0 i tyngdepunktet

BED = 250
# fil, navn, filament, min-hjørne (x, y) eller None, «samme flytt som»
PLATES = {
    "skjold-fjernkontroll-k2.3mf": ("Skjold Fjernkontroll – topp og bunn (PLA/PETG)", [
        ("topp", "Topp (forsiden ned)", 1, (20, 3.5), None),
        ("logo", "SKJOLD (gull, felt inn i toppen)", 3, None, "topp"),
        ("bunn", "Bunn", 2, (100, 3.5), None),
    ], {1: "#ECE9E3", 2: "#2E2D2C", 3: "#D99E40"}),
    "skjold-fjernkontroll-k2-taster.3mf": ("Skjold Fjernkontroll – taster og IR-vindu", [
        ("knapper", "Taster (mørke, flensen ned)", 2, (40, 30), None),
        ("symboler_lyse", "Symboler på de mørke tastene", 1, None, "knapper"),
        ("knapper_lys", "Smarthus-taster (lyse)", 1, None, "knapper"),
        ("symboler_morke", "Symboler på de lyse tastene og Skjold-tasten", 2, None, "knapper"),
        ("gull", "Gullring (D-pad) og Skjold-tast", 3, None, "knapper"),
        ("ir_vindu", "IR-vindu (klar eller natur PETG, forsiden ned)", 4, (160, 30), None),
    ], {1: "#ECE9E3", 2: "#2E2D2C", 3: "#D99E40", 4: "#DDE6EA"}),
}


def mesh_xml(m):
    v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def place(parts):
    out, moved = [], {}
    for f, name, fil, pos, same in parts:
        m = trimesh.load(f"{STL}/{f}.stl")
        if same:
            T = moved[same]
        elif pos == "diag":   # for lang for plata: 45° og midt på (full variant, 252 mm)
            T = trimesh.transformations.rotation_matrix(math.radians(45), [0, 0, 1])
            b = m.copy().apply_transform(T).bounds
            T = trimesh.transformations.translation_matrix([BED/2 - (b[0][0] + b[1][0])/2, BED/2 - (b[0][1] + b[1][1])/2, -b[0][2]]) @ T
        else:
            b = m.bounds
            T = trimesh.transformations.translation_matrix([pos[0] - b[0][0], pos[1] - b[0][1], -b[0][2]])
        m.apply_transform(T)
        moved[f] = T
        assert m.bounds[1][0] <= BED and m.bounds[1][1] <= BED and m.bounds[0][0] >= 0 and m.bounds[0][1] >= 0, (f, m.bounds)
        out.append((f, name, fil, m))
    # ingen deler overlapper på plata (symbolene og logoen ligger i lommene sine og berører bare)
    for (fa, _, _, a), (fb, _, _, b) in itertools.combinations(out, 2):
        (a0, a1), (b0, b1) = a.bounds, b.bounds
        if a1[0] <= b0[0] or b1[0] <= a0[0] or a1[1] <= b0[1] or b1[1] <= a0[1]:
            continue
        v = a.intersection(b, engine="manifold").volume
        assert v < 0.05, (fa, fb, v)
    return out


def write(fn, title, parts, colors):
    objs, items, cfg = [], [], []
    for i, (f, name, fil, m) in enumerate(place(parts), 1):
        objs.append(f'<object id="{i}" name="{name}" type="model">{mesh_xml(m)}</object>')
        items.append(f'<item objectid="{i}"/>')
        cfg.append(f'<object id="{i}"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/>'
                   f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/></part></object>')
    farger = ";".join(f"{k}={v}" for k, v in sorted(colors.items()))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><metadata name="Designer">Skjold</metadata>'
             f'<metadata name="Description">Filamenter: {farger}</metadata>'
             '<metadata name="License">CC BY-NC-SA 4.0</metadata>'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    conf = '<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(cfg) + "</config>"
    with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", conf)
    print("skrev", fn)


STL = "stl"


def plater(variant):
    """{filnavn: (tittel, deler, farger)} for varianten. Full variant er 254,5 mm, lengre enn plata (250 mm):
    toppen og bunnen ligger da på hver sin plate, på skrå (45°)."""
    ut = {}
    for fn, (title, parts, colors) in PLATES.items():
        if variant == "kort":
            ut[fn] = (title, [p for p in parts if p[0] != "knapper_lys"], colors)   # standard har ikke smarthus-raden
            continue
        fn = fn.replace("skjold-fjernkontroll-", "skjold-fjernkontroll-full-")
        title = title.replace("Skjold Fjernkontroll", "Skjold Fjernkontroll Full")
        if fn.endswith("-k2.3mf"):
            diag = [(f, n, fil, "diag" if pos else None, same) for f, n, fil, pos, same in parts]
            ut[fn.replace("-k2.3mf", "-k2-topp.3mf")] = (title.replace("topp og bunn", "topp"), [p for p in diag if p[0] != "bunn"], colors)
            ut[fn.replace("-k2.3mf", "-k2-bunn.3mf")] = (title.replace("topp og bunn", "bunn"), [p for p in diag if p[0] == "bunn"], colors)
        else:
            ut[fn] = (title, parts, colors)
    return ut


def main():
    """Standard (kort) fra stl/, full variant fra stl_full/ (filene heter skjold-fjernkontroll-full-…)."""
    global STL
    for variant in ("kort", "full"):
        STL = "stl" if variant == "kort" else "stl_full"
        for fn, (title, parts, colors) in plater(variant).items():
            write(fn, title, parts, colors)


if __name__ == "__main__":
    main()
