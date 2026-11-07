"""Driverbilder (small 75, large 500, xlarge 1000) for tilbehøret Skjold Røst, Kassett og Hjul, laget fra renderne i
kabinett/*/render: lys bakgrunn fjernes, produktet sentreres på hvit bakgrunn som S1/Node/Core/Touch-bildene.
Kjør fra repo-roten: python3 homey/no.kristo.skjold/make_accessory_images.py"""
from PIL import Image, ImageChops, ImageFilter

BG = (255, 255, 255)   # samme hvite bakgrunn som S1, Node, Core og Touch
SRC = {"rost": "kabinett/rost/render/01_rost.png", "kassett": "kabinett/kassett/render/02_med_kassett.png",
       "hjul": "kabinett/hjul/render/01_hjul.png"}
OUT = "homey/no.kristo.skjold/drivers/{}/assets/images/{}.png"


def cutout(path, pad=0.12):
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
    diff = ImageChops.difference(im, bg).convert("L")
    mask = diff.point(lambda v: 255 if v > 14 else 0).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    box = mask.point(lambda v: 255 if v > 128 else 0).getbbox()
    im, mask = im.crop(box), mask.crop(box)
    side = int(max(im.size) * (1 + 2 * pad))
    out = Image.new("RGB", (side, side), BG)
    out.paste(im, ((side - im.width) // 2, (side - im.height) // 2), mask)
    return out


for kind, src in SRC.items():
    big = cutout(src).resize((1000, 1000), Image.LANCZOS)
    for k, n in (("small", 75), ("large", 500), ("xlarge", 1000)):
        big.resize((n, n), Image.LANCZOS).save(OUT.format(kind, k), optimize=True)
    print(kind, "ok")
