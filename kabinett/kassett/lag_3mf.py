"""Lager de ferdige platene for Creality K2 (Creality Print / OrcaSlicer) fra STL-ene i stl/.

    python3 lag_3mf.py            # skriver skjold-kassett-k2.3mf, -k2-kassetter.3mf og -k2-klar.3mf
    (bakplatene som holder coveret ligger i -k2-kassetter.3mf, én per kassett)

Alle delene ligger allerede i utskriftsretning i stl/. Hvert objekt får filamentnummer (extruder) i
Metadata/model_settings.config, slik at CFS printer alt i én omgang:
1 = lys (lokk og spoler), 2 = sort (bunn, kassettbak, trinser), 3 = sennep (kassettfront), 4 = klar (rute, lysleder).
Platene holdes innenfor 250 × 250 mm, så de passer K2, K2 Pro og K2 Plus."""
import os
import zipfile
from xml.sax.saxutils import escape

import trimesh

HER = os.path.dirname(os.path.abspath(__file__))

# (fil, navn, filament, x, y) – x/y er nedre venstre hjørne på plata (mm)
HOVED = [("spiller_topp", "Spiller – lokk (toppen ned)", 1, 3, 3),
         ("spiller_bunn", "Spiller – bunn med drivverk", 2, 128, 3)]
for i in range(4):
    HOVED += [("kassett_bak", f"Kassett {i + 1} – bak", 2, 3 + 54 * i, 99),
              ("kassett_front", f"Kassett {i + 1} – front", 3, 3 + 54 * i, 173)]
for i in range(8):
    HOVED.append(("spole", f"Spole {i + 1}", 1, 219 + 16 * (i % 2), 99 + 16.5 * (i // 2)))
HOVED += [("trinse", "Trinse 1", 2, 221, 176), ("trinse", "Trinse 2", 2, 221, 189), ("motortrinse", "Motortrinse", 2, 236, 177)]
# Ekstra kassetter (og bakplaten som holder coveret uten lim – den mangler på hovedplata, som er full)
KASSETTER = []
for i in range(4):
    KASSETTER += [("kassett_bak", f"Kassett {i + 1} – bak", 2, 3 + 62 * i, 3),
                  ("kassett_front", f"Kassett {i + 1} – front (etikettvindu)", 3, 3 + 62 * i, 78),
                  ("etikettplate", f"Kassett {i + 1} – bakplate for coveret (platen ned)", 2, 6 + 62 * i, 153),
                  ("spole", f"Kassett {i + 1} – spole 1", 1, 6 + 62 * i, 208), ("spole", f"Kassett {i + 1} – spole 2", 1, 26 + 62 * i, 208)]
KLAR = [("vindu", "Rute (klar PETG, 100 % fyll)", 4, 10, 10), ("lysleder", "Lysleder (klar PETG)", 4, 70, 10)]


def model_xml(items, title):
    res, build, cfg = [], [], []
    for oid, (fil, navn, ext, x, y) in enumerate(items, 1):
        m = trimesh.load(os.path.join(HER, "stl", fil + ".stl"))
        m.merge_vertices()
        m.apply_translation([-m.bounds[0][0], -m.bounds[0][1], -m.bounds[0][2]])
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        res.append(f'<object id="{oid}" name="{escape(navn)}" type="model"><mesh><vertices>{v}</vertices>'
                   f'<triangles>{t}</triangles></mesh></object>')
        build.append(f'<item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0" printable="1"/>')
        cfg.append(f'<object id="{oid}"><metadata key="name" value="{escape(navn)}"/><metadata key="extruder" value="{ext}"/>'
                   f'<part id="{oid}" subtype="normal_part"><metadata key="name" value="{escape(navn)}"/>'
                   f'<metadata key="extruder" value="{ext}"/></part></object>')
        assert x + m.extents[0] <= 250 and y + m.extents[1] <= 250, f"{navn} er utenfor 250 × 250 mm"
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{escape(title)}</metadata><metadata name="Designer">Skjold</metadata>'
             '<metadata name="License">CC BY-NC-SA 4.0</metadata>'
             f'<resources>{"".join(res)}</resources><build>{"".join(build)}</build></model>')
    return model, '<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(cfg) + "</config>"


def skriv(navn, items, title):
    model, cfg = model_xml(items, title)
    with zipfile.ZipFile(os.path.join(HER, navn), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                   '<Default Extension="config" ContentType="text/xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", cfg)
    print(navn, os.path.getsize(os.path.join(HER, navn)) // 1024, "kB")


if __name__ == "__main__":
    skriv("skjold-kassett-k2.3mf", HOVED, "Skjold Kassett – spiller med spoler + 4 kassetter (Creality K2)")
    skriv("skjold-kassett-k2-kassetter.3mf", KASSETTER, "Skjold Kassett – 4 kassetter med bakplate for coveret (Creality K2)")
    skriv("skjold-kassett-k2-klar.3mf", KLAR, "Skjold Kassett – rute og lysleder i klar PETG (Creality K2)")
