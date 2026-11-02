"""Skjold-merket (fem søyler, branding/skjold/skjold_merke.svg) -> Homey-ikon og HA-brand-PNG-er."""
import os
from PIL import Image, ImageDraw, ImageFont

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BARS = [(1, 22), (9, 33), (18.7, 42), (28.4, 33), (36.4, 22)]  # x, høyde (viewBox 42x46, y=2, w=4.6)
FONT = os.path.join(R, "skjold/ios/Skjold/Fonts")


def mark(draw, ox, oy, s, fill):
    for x, h in BARS:
        draw.rounded_rectangle([ox + x * s, oy + 2 * s, ox + (x + 4.6) * s, oy + (2 + h) * s], radius=2.3 * s, fill=fill)


def icon(size, fill):
    k = 4; S = size * k
    im = Image.new("RGBA", (S, S)); s = S * 0.8 / 46
    mark(ImageDraw.Draw(im), (S - 40 * s) / 2 - s, (S - 42 * s) / 2 - 2 * s, s, fill)
    return im.resize((size, size), Image.LANCZOS)


def logo(h, fill, sub):
    k = 4; H = h * k; s = H / 64
    im = Image.new("RGBA", (int(400 * s), H)); d = ImageDraw.Draw(im)
    mark(d, 0, 9 * s, s, fill)
    f1 = ImageFont.truetype(f"{FONT}/Sora-SemiBold.ttf", int(30 * s)); f2 = ImageFont.truetype(f"{FONT}/IBMPlexMono-Regular.ttf", int(10.5 * s))
    x = 62 * s
    for ch in "SKJOLD":
        d.text((x, 30 * s), ch, font=f1, fill=fill, anchor="ls"); x += d.textlength(ch, font=f1) + 4.2 * s
    x = 63 * s
    for ch in "STREAMING AMPLIFIER":
        d.text((x, 50 * s), ch, font=f2, fill=sub, anchor="ls"); x += d.textlength(ch, font=f2) + 3.2 * s
    im = im.crop(im.getbbox())
    return im.resize((im.width // k, im.height // k), Image.LANCZOS)


if __name__ == "__main__":
    for d in ("custom_components/skjold/brand", "brands/skjold"):
        p = os.path.join(R, d); os.makedirs(p, exist_ok=True)
        for f in os.listdir(p):
            os.remove(os.path.join(p, f))
        icon(256, "#1d1d1c").save(f"{p}/icon.png"); icon(512, "#1d1d1c").save(f"{p}/icon@2x.png")
        icon(256, "#f2f1ec").save(f"{p}/dark_icon.png"); icon(512, "#f2f1ec").save(f"{p}/dark_icon@2x.png")
        logo(128, "#1d1d1c", "#6b6a66").save(f"{p}/logo.png"); logo(256, "#1d1d1c", "#6b6a66").save(f"{p}/logo@2x.png")
        logo(128, "#f2f1ec", "#a3a29c").save(f"{p}/dark_logo.png"); logo(256, "#f2f1ec", "#a3a29c").save(f"{p}/dark_logo@2x.png")
    rects = "".join(f'<rect x="{x + 3}" y="2" width="4.6" height="{h}" rx="2.3"/>' for x, h in BARS)
    open(os.path.join(R, "homey/no.kristo.skjold/assets/icon.svg"), "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 46"><g fill="#000">{rects}</g></svg>\n')
