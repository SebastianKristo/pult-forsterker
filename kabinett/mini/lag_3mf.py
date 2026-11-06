"""Lag skjold-mini-k2.3mf: alle delene til én Skjold Mini på én 250 × 250 mm plate (Creality K2 / K2 Pro / K2 Plus).
Kjør etter at STL-ene er eksportert:  python3 lag_3mf.py
Hver del får filamentnummer (1 = lys, 2 = sort, 3 = gull) i Metadata/model_settings.config (Creality Print / OrcaSlicer)."""
import math
import struct
import zipfile
import numpy as np
import trimesh

PARTS = [  # fil, navn, filament, rotasjon om z (grader), plassering (min-hjørne x, y)
    ("kropp", "Kropp (bakveggen ned)", 1, 0, (3, 3)),
    ("front", "Frontplate (forsiden ned)", 2, 0, (108, 3)),
    ("knott", "Knott (toppen ned)", 3, 0, (212, 6)),
    ("bunn", "Bunn", 2, 0, (3, 148)),
    ("grill", "Grill (forsiden ned)", 2, 90, (108, 150)),
]
COLORS = {1: "#ECE9E3", 2: "#232325", 3: "#D99E40"}


def mesh_xml(m):
    v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def main():
    objs, items, cfg = [], [], []
    for i, (f, name, fil, rot, (x, y)) in enumerate(PARTS, 1):
        m = trimesh.load(f"stl/{f}.stl")
        if rot:
            m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1]))
        b = m.bounds
        m.apply_translation([x - b[0][0], y - b[0][1], -b[0][2]])
        assert m.bounds[1][0] <= 250 and m.bounds[1][1] <= 250, f
        objs.append(f'<object id="{i}" name="{name}" type="model">{mesh_xml(m)}</object>')
        items.append(f'<item objectid="{i}"/>')
        cfg.append(f'<object id="{i}"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/>'
                   f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/></part></object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Skjold Mini – alle deler (Creality K2)</metadata><metadata name="Designer">Skjold</metadata>'
             '<metadata name="License">CC BY-NC-SA 4.0</metadata>'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    conf = '<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(cfg) + "</config>"
    with zipfile.ZipFile("skjold-mini-k2.3mf", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", conf)
    print("skrev skjold-mini-k2.3mf")


if __name__ == "__main__":
    main()
