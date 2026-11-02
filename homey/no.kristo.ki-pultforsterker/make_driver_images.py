"""Driverbilder (small 75, large 500, xlarge 1000) fra produktrenderne; Core = ikonet på ren bakgrunn."""
# Kjør: python3 make_driver_images.py ../../skjold/nettside/assets/img drivers /tmp   (etter make_driver_icons.py)
import sys, io, cairosvg
from PIL import Image, ImageOps
IMG, DRV, S = sys.argv[1], sys.argv[2], sys.argv[3]
BG = (17, 17, 19)
def crop_square(path, pad=0.10):
    im = Image.open(path).convert("RGB")
    mask = Image.eval(im.convert("L"), lambda v: 255 if v > 30 else 0)
    l, t, r, b = mask.getbbox()
    side = int(max(r - l, b - t) * (1 + 2 * pad)); cx, cy = (l + r) // 2, (t + b) // 2
    out = Image.new("RGB", (side, side), BG); out.paste(im, (side // 2 - cx, side // 2 - cy))
    return out
def core_img():
    svg = open(f"{DRV}/core/assets/icon.svg").read().replace('stroke="#000"', 'stroke="#e9e4d8"').replace('fill="#000"', 'fill="#e9e4d8"')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=820, output_height=820)
    out = Image.new("RGB", (1000, 1000), BG); ic = Image.open(io.BytesIO(png)).convert("RGBA"); out.paste(ic, (90, 90), ic)
    return out
srcs = {"s1": lambda: crop_square(f"{IMG}/02-s1-m.png"), "node": lambda: crop_square(f"{IMG}/01-node-m.png"), "core": core_img}
sheet = Image.new("RGB", (1500, 500))
for i, (name, fn) in enumerate(srcs.items()):
    big = fn()
    for k, n in (("small", 75), ("large", 500), ("xlarge", 1000)):
        big.resize((n, n), Image.LANCZOS).save(f"{DRV}/{name}/assets/images/{k}.png", optimize=True)
    sheet.paste(big.resize((500, 500), Image.LANCZOS), (i * 500, 0))
sheet.save(f"{S}/images.png")
