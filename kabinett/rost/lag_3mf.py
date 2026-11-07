"""Lag 3MF-platene for Skjold Røst (Creality K2 / K2 Pro / K2 Plus, 250 × 250 mm):

  skjold-rost-k2.3mf        kropp med toppanel, frontplate med innfelt logo, knott og knappehetter (PETG/ASA, 3 farger)
  skjold-rost-k2-bunn.3mf   grill og bunnplate (PETG/ASA, sort)
  skjold-rost-k2-tpu.3mf    pakninger i skjøtene, krage, DC-skive og USB-propp (TPU 95A)

Kjør etter at STL-ene er eksportert:  python3 lag_3mf.py
Hver del får filamentnummer i Metadata/model_settings.config (Creality Print / OrcaSlicer). Logoen ligger
nøyaktig der den skal i frontplaten (samme plassering), så den printes i egen farge i samme utskrift."""
import math
import zipfile
import trimesh

BED = 250
PLATES = {
    "skjold-rost-k2.3mf": ("Skjold Røst – kropp, front og knott (PETG/ASA)", [
        # fil, navn, filament, rotasjon om z, min-hjørne (x, y), «samme som» (legg nøyaktig likt som en annen del)
        ("kropp", "Kropp (bakveggen ned)", 1, 0, (4, 4), None),
        ("front", "Frontplate (baksiden ned)", 2, 0, (114, 4), None),
        ("logo", "Logo SKJOLD (innfelt i fronten)", 3, 0, None, "front"),
        ("knott", "Knott (toppen ned)", 3, 0, (4, 146), None),
        ("knapp", "Knappehetter av/på og 1–4 (toppen ned)", 2, 0, (4, 190), None),
    ]),
    "skjold-rost-k2-bunn.3mf": ("Skjold Røst – grill og bunn (PETG/ASA)", [
        ("grill", "Grill (forsiden ned)", 2, 0, (4, 4), None),
        ("bunn", "Bunn (innsiden ned, føttene opp)", 2, 0, (102, 4), None),
    ]),
    "skjold-rost-k2-tpu.3mf": ("Skjold Røst – pakninger (TPU 95A)", [
        ("pakning_front", "Pakning front", 1, 0, (4, 4), None),
        ("pakning_bunn", "Pakning bunn", 1, 0, (110, 4), None),
        ("krage", "Krage EC11", 1, 0, (136, 130), None),
        ("dc_skive", "Skive DC-kontakt", 1, 0, (156, 130), None),
        ("usb_propp", "Propp USB-C", 1, 0, (176, 130), None),
    ]),
}
COLORS = {1: "#ECE9E3", 2: "#232325", 3: "#D99E40"}


def mesh_xml(m):
    v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def place(parts):
    out, moved = [], {}
    for f, name, fil, rot, pos, same in parts:
        m = trimesh.load(f"stl/{f}.stl")
        if rot:
            m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1]))
        if same:
            m.apply_translation(moved[same])
        else:
            b = m.bounds
            d = [pos[0] - b[0][0], pos[1] - b[0][1], -b[0][2]]
            m.apply_translation(d)
            moved[f] = d
        assert m.bounds[1][0] <= BED and m.bounds[1][1] <= BED and m.bounds[0][0] >= 0 and m.bounds[0][1] >= 0, (f, m.bounds)
        out.append((f, name, fil, m))
    # ingen overlapp mellom delene på plata (bortsett fra logoen, som ligger i lomma i fronten)
    for i, (fa, _, _, a) in enumerate(out):
        for fb, _, _, b in out[i + 1:]:
            if "logo" in (fa, fb):
                continue
            (a0, a1), (b0, b1) = a.bounds, b.bounds
            assert a1[0] <= b0[0] or b1[0] <= a0[0] or a1[1] <= b0[1] or b1[1] <= a0[1], (fa, fb)
    return out


def write(fn, title, parts):
    objs, items, cfg = [], [], []
    for i, (f, name, fil, m) in enumerate(place(parts), 1):
        objs.append(f'<object id="{i}" name="{name}" type="model">{mesh_xml(m)}</object>')
        items.append(f'<item objectid="{i}"/>')
        cfg.append(f'<object id="{i}"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/>'
                   f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/></part></object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><metadata name="Designer">Skjold</metadata>'
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


def main():
    for fn, (title, parts) in PLATES.items():
        write(fn, title, parts)


if __name__ == "__main__":
    main()
