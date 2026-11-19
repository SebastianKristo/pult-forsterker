#!/usr/bin/env python3
"""Oppstartsbildet (Plymouth): Skjold-logoen stort, med enhetsnavnet under.

    python3 skjold_splash.py <logo.png> <ut.png> [--navn "Skjold S1"] [--rot 90] [--bredde 900]

Logoen (pi/touch/oppstart.png, liggende) skaleres til --bredde piksler, navnet skrives under i lys grå, og hele
bildet dreies likt med skjermen (--rot 90 = 90° med klokka, som oppstart-90.png). Uten navn blir det bare logoen.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

FONTER = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
          "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf")


def font(px):
    for f in FONTER:
        if os.path.exists(f):
            return ImageFont.truetype(f, px)
    return ImageFont.load_default(px)


def lag(logo_fil, navn="", rot=0, bredde=900):
    logo = Image.open(logo_fil).convert("RGBA")
    k = bredde / logo.width
    logo = logo.resize((bredde, round(logo.height * k)), Image.LANCZOS)
    navn = " ".join((navn or "").split())[:32]
    if not navn:
        bilde = logo
    else:
        px = max(24, round(logo.height * 0.34))
        f = font(px)
        sperre = round(px * 0.12)   # litt bokstavavstand, som ordmerket
        tekst = navn.upper()
        bredder = [f.getlength(c) for c in tekst]
        tw = round(sum(bredder) + sperre * (len(tekst) - 1))
        while tw > bredde and px > 16:   # langt navn: mindre skrift
            px -= 2; f = font(px); sperre = round(px * 0.12)
            bredder = [f.getlength(c) for c in tekst]; tw = round(sum(bredder) + sperre * (len(tekst) - 1))
        asc, desc = f.getmetrics()
        mellom = round(logo.height * 0.38)
        bilde = Image.new("RGBA", (bredde, logo.height + mellom + asc + desc), (0, 0, 0, 0))
        bilde.alpha_composite(logo, (0, 0))
        d = ImageDraw.Draw(bilde)
        x = (bredde - tw) / 2
        for c, w in zip(tekst, bredder):
            d.text((x, logo.height + mellom), c, font=f, fill=(201, 201, 196, 255))
            x += w + sperre
    if rot in (90, 180, 270):
        bilde = bilde.rotate(-rot, expand=True)   # PIL dreier mot klokka; oppstart-90.png er dreid med klokka
    return bilde


def main():
    a = argparse.ArgumentParser()
    a.add_argument("logo"); a.add_argument("ut")
    a.add_argument("--navn", default=""); a.add_argument("--rot", type=int, default=0); a.add_argument("--bredde", type=int, default=900)
    o = a.parse_args()
    lag(o.logo, o.navn, o.rot, o.bredde).save(o.ut)


if __name__ == "__main__":
    main()
