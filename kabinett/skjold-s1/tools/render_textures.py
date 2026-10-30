#!/usr/bin/env python3
"""Teksturer til 3D-renderen (render3d.html): merking på front, bak, venstre side og bunn som PNG med gjennomsiktig bakgrunn
i nøyaktig målestokk (TEX px/mm), pluss et OLED-skjermbilde (128 × 64 → 2,42" aktivt område 55,0 × 27,5 mm).
Skriver til ../render/tex/. Koordinater som i DXF-ene (frontplate: origo i senter; bak/side: designpakkens system)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxfkit import read_dxf_polys   # noqa: E402
from PIL import Image, ImageDraw, ImageFont
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
S1 = os.path.join(HERE, "..")
OUT = os.path.join(S1, "render", "tex"); os.makedirs(OUT, exist_ok=True)
TEX = 12   # px/mm
MARK = (214, 216, 219, 255)


def tex_from_dxf(path, out, x0, y0, w, h, mirror_x=False):
    """MARKING-polygoner fra DXF -> RGBA-PNG der (x0, y0) er nedre venstre hjørne av flaten (w × h mm)."""
    polys = [p for lay, p in read_dxf_polys(path) if lay == "MARKING"]
    W, H = int(round(w * TEX)), int(round(h * TEX))
    acc = np.zeros((H, W), dtype=np.int32)
    for p in polys:
        pts = [((w - (x - x0) if mirror_x else (x - x0)) * TEX, (h - (y - y0)) * TEX) for x, y in p]
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(pts, fill=1); acc += np.array(m, dtype=np.int32)
    img = np.zeros((H, W, 4), dtype=np.uint8); img[acc % 2 == 1] = MARK
    Image.fromarray(img).save(out); print("skrev", os.path.basename(out), W, "x", H)


# frontplate 178 × 46, origo i senter, sett forfra
tex_from_dxf(os.path.join(S1, "platemetall", "skjold_s1_avrundet", "skjold_s1_frontplate_alu_merking.dxf"), os.path.join(OUT, "front.png"), -89, -23, 178, 46)
# bakpanel: designpakkens bak-fil er «sett bakfra», x = −kasse-x, y = z (0…48). Flaten vi teksturerer er 190,6 × 48.
tex_from_dxf(os.path.join(S1, "marking", "skjold_s1_merking_bakpanel_revb.dxf"), os.path.join(OUT, "back.png"), -95.3, 0, 190.6, 48, mirror_x=True)   # kolonner = kasse-x
# venstre side: sett fra venstre, x = kasse-y (−80…80), y = z
tex_from_dxf(os.path.join(S1, "marking", "skjold_s1_merking_venstre_side.dxf"), os.path.join(OUT, "left.png"), -80, 0, 160, 48)
# bunn: sett fra undersiden (x speilet), 190 × 160
tex_from_dxf(os.path.join(S1, "marking", "skjold_s1_merking_bunnplate.dxf"), os.path.join(OUT, "bottom.png"), -95, -80, 190, 160, mirror_x=True)   # kolonner = kasse-x

# OLED-bilde 128 × 64 i stil med oled_display.py: faner, tittel, artist, volum, HP
W, H = 128, 64
img = Image.new("RGB", (W, H), (8, 8, 9)); d = ImageDraw.Draw(img)
try:
    f_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 7)
    f_t = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
    f_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
except OSError:
    f_b = f_t = f_s = ImageFont.load_default()
x = 0
for i, tab in enumerate(("BT", "RADIO", "AUX", "USB")):
    tw = d.textlength(tab, font=f_b) + 8
    if i == 0:
        d.rectangle([x, 0, x + tw, 10], fill=(242, 242, 238)); d.text((x + 4, 1), tab, font=f_b, fill=(10, 10, 10))
    else:
        d.text((x + 4, 1), tab, font=f_b, fill=(139, 139, 134))
    x += tw + 2
d.text((W - 14, 1), "HP", font=f_b, fill=(242, 242, 238))
d.text((0, 16), "Teardrop", font=f_t, fill=(242, 242, 238))
d.text((0, 31), "Massive Attack · AirPlay", font=f_s, fill=(139, 139, 134))
d.text((0, 50), "VOL", font=f_b, fill=(139, 139, 134))
for i in range(24):
    on = i < 11
    d.rectangle([22 + i * 3.6, 50, 22 + i * 3.6 + 2.6, 57], fill=(242, 242, 238) if on else (60, 60, 58))
d.text((W - 16, 50), "46", font=f_b, fill=(242, 242, 238))
img = img.resize((W * 8, H * 8), Image.NEAREST); img.save(os.path.join(OUT, "oled.png")); print("skrev oled.png")
