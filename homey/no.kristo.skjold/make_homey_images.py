"""Lager Homey-bilder etter App Store-krav: driverbilder med enheten på hvit
bakgrunn, og et appbilde med enhetene i et rom. Kilde: de mørke renderne."""
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "branding", "homey_kilde")


def cutout(path):
    im = Image.open(path).convert("RGBA")
    bg = im.getpixel((0, 0))[:3]
    w, h = im.size
    # flomfyll fra kantene med bakgrunnsfargen -> gjennomsiktig
    mark = (255, 0, 255, 0)
    work = im.copy()
    for p in [(x, 0) for x in range(0, w, 7)] + [(x, h - 1) for x in range(0, w, 7)] + \
             [(0, y) for y in range(0, h, 7)] + [(w - 1, y) for y in range(0, h, 7)]:
        if work.getpixel(p)[:3] == bg:
            ImageDraw.floodfill(work, p, mark, thresh=1)
    alpha = Image.new("L", (w, h), 255)
    px, ap = work.load(), alpha.load()
    for y in range(h):
        for x in range(w):
            if px[x, y] == mark:
                ap[x, y] = 0
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(alpha)
    return im.crop(im.getbbox())


def place(canvas, dev, box_w, cx, bottom, shadow=0.35):
    s = box_w / dev.width
    dev = dev.resize((int(dev.width * s), int(dev.height * s)), Image.LANCZOS)
    x, y = int(cx - dev.width / 2), int(bottom - dev.height)
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).ellipse([x + dev.width * .08, bottom - dev.height * .07,
                                x + dev.width * .92, bottom + dev.height * .05], fill=int(255 * shadow))
    sh = sh.filter(ImageFilter.GaussianBlur(dev.width * .04))
    canvas.paste(Image.new("RGBA", canvas.size, (40, 30, 20, 255)), (0, 0), sh)
    canvas.alpha_composite(dev, (x, y))


def driver_image(dev, out_dir):
    c = Image.new("RGBA", (1000, 1000), (255, 255, 255, 255))
    place(c, dev, 820 if dev.width > dev.height else 700, 500, 860, 0.22)
    c = c.convert("RGB")
    for name, size in (("xlarge", 1000), ("large", 500), ("small", 75)):
        c.resize((size, size), Image.LANCZOS).save(os.path.join(out_dir, f"{name}.png"), optimize=True)


def room(devs):
    W, H = 1000, 700
    c = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(c)
    desk = 470
    for y in range(desk):  # varm vegg med lys fra venstre
        t = y / desk
        d.line([(0, y), (W, y)], fill=(int(226 - 30 * t), int(214 - 30 * t), int(196 - 30 * t)))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-250, -300, 600, 450], fill=90)
    c.paste(Image.new("RGBA", (W, H), (255, 240, 215, 255)), (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    # bilde på veggen
    d.rectangle([640, 70, 880, 250], fill=(60, 52, 46))
    d.rectangle([652, 82, 868, 238], fill=(214, 120, 70))
    d.ellipse([700, 120, 780, 200], fill=(240, 196, 120))
    d.polygon([(652, 238), (740, 170), (800, 210), (868, 160), (868, 238)], fill=(70, 90, 80))
    # plante
    d.rectangle([90, 370, 150, desk], fill=(190, 170, 150))
    for i, (dx, dy) in enumerate([(-50, -120), (-10, -160), (30, -130), (60, -90), (-70, -70)]):
        d.ellipse([120 + dx - 28, 370 + dy - 14, 120 + dx + 28, 370 + dy + 14], fill=(60 + i * 8, 110 + i * 6, 70))
        d.line([(120, 372), (120 + dx, 370 + dy)], fill=(70, 100, 60), width=4)
    # trebenk
    for y in range(desk, H):
        t = (y - desk) / (H - desk)
        d.line([(0, y), (W, y)], fill=(int(150 - 50 * t), int(104 - 40 * t), int(70 - 30 * t)))
    for i in range(18):
        yy = desk + 12 + i * 12
        d.line([(0, yy), (W, yy + (i % 3) * 4)], fill=(120, 82, 54), width=1)
    d.rectangle([0, desk - 4, W, desk + 4], fill=(170, 122, 84))
    s1, node = devs
    place(c, s1, 470, 430, desk + 120)
    place(c, node, 230, 780, desk + 105)
    return c.convert("RGB")


if __name__ == "__main__":
    devs = {k: cutout(os.path.join(SRC, f"{k}.png")) for k in ("s1", "node", "core", "pultforsterker")}   # touch: bilde fra designets render (touch_1_forfra_skra), ikke herfra
    for k, dev in devs.items():
        driver_image(dev, os.path.join(ROOT, "drivers", k, "assets", "images"))
    r = room((devs["s1"], devs["node"]))
    for name, size in (("xlarge", (1000, 700)), ("large", (500, 350)), ("small", (250, 175))):
        r.resize(size, Image.LANCZOS).save(os.path.join(ROOT, "assets", "images", f"{name}.png"), optimize=True)
