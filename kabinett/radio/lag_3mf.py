"""Lag 3MF-platene for Skjold Radio (Creality K2 / K2 Pro / K2 Plus, 250 × 250 mm):

  skjold-radio-k2.3mf          kropp (toppflaten ned), hjul, volumknott og knappehetter (PETG/ASA, 3 farger)
  skjold-radio-k2-kammer.3mf   lydkammer (baffelen ned) og lokk (PETG/ASA, 100 % fyll i baffelen gir best lyd)
  skjold-radio-k2-grill.3mf    grill (forsiden ned) og skjermbrakett (PETG/ASA, sort)
  skjold-radio-k2-bunn.3mf     bunnplate (undersiden ned)

Kjør etter at STL-ene er eksportert:  python3 lag_3mf.py   (eller ./lag_stl.sh, som gjør alt)
Hver del får filamentnummer i Metadata/model_settings.config (Creality Print / OrcaSlicer):
1 = kroppsfarge (lys), 2 = sort/mørk, 3 = gull. Mørk variant: bytt filament 1 og 3 i sliceren."""
import math
import zipfile
import trimesh

BED = 250
PLATES = {
    "skjold-radio-k2.3mf": ("Skjold Radio – kropp, hjul og knapper (PETG/ASA)", [
        # fil, navn, filament, rotasjon om z, min-hjørne (x, y), «samme som»
        ("kropp", "Kropp (toppflaten ned)", 1, 0, (7, 4), None),
        ("knott", "Navigasjonshjul", 3, 0, (7, 186), None),
        ("volum", "Volumknott", 3, 0, (60, 186), None),
        ("knapp", "Knappehetter 1–6 og av/på (toppen ned)", 2, 0, (90, 186), None),
    ]),
    "skjold-radio-k2-kammer.3mf": ("Skjold Radio – lydkammer og lokk (PETG/ASA)", [
        ("kammer", "Lydkammer (baffelen ned)", 2, 0, (21, 4), None),
        ("lokk", "Lokk for kammeret", 2, 0, (29, 100), None),
    ]),
    "skjold-radio-k2-grill.3mf": ("Skjold Radio – grill og skjermbrakett (PETG/ASA)", [
        ("grill", "Grill (forsiden ned)", 2, 0, (17, 4), None),
        ("brakett", "Skjermbrakett", 2, 0, (63, 108), None),
    ]),
    "skjold-radio-k2-bunn.3mf": ("Skjold Radio – bunnplate (PETG/ASA)", [
        ("bunn", "Bunnplate (undersiden ned)", 1, 0, (10, 52), None),
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
    # ingen overlapp mellom delene på plata
    for i, (fa, _, _, a) in enumerate(out):
        for fb, _, _, b in out[i + 1:]:
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
