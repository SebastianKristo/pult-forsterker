#!/usr/bin/env python3
"""Lager oppstartslogoen (pi/touch/oppstart*.png) til Plymouth-skjermen på Touch og S1.

Skjold-logoen: fem avrundede stolper som henger fra samme topplinje (høyde 22/33/42/33/22, bredde 4,6, mellomrom 3,4 –
samme mål som appikonet i skjold/app/tools/make_icons.py), den lange midtstolpen gyllen. Til høyre «SKJOLD» i hvitt og
«LAB» i lys gull, med luft mellom bokstavene. Gjennomsiktig bakgrunn; -90/-180/-270 er dreid for paneler på høykant.

Kjør fra repoet:  python3 pi/touch/lag_oppstart.py   (trenger Pillow og fontTools[woff2]; skriften er Sora fra skjold/app)
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

HER = os.path.dirname(os.path.abspath(__file__))
SORA = os.path.join(HER, "..", "..", "skjold", "app", "node_modules", "@fontsource", "sora", "files")
HVIT, GULL, LYS_GULL = (242, 242, 238, 255), (217, 164, 65, 255), (220, 205, 170, 255)
HOYDER, BREDDE, MELLOM = (22, 33, 42, 33, 22), 4.6, 3.4
SS = 4   # tegnes større og skaleres ned, så kantene blir myke


def sora(vekt: int, px: int) -> ImageFont.FreeTypeFont:
    from fontTools.ttLib import TTFont
    f = TTFont(os.path.join(SORA, f"sora-latin-{vekt}-normal.woff2"))
    f.flavor = None
    buf = io.BytesIO(); f.save(buf); buf.seek(0)
    return ImageFont.truetype(buf, px)


def sperret(d: ImageDraw.ImageDraw, x: float, y: float, tekst: str, font, farge, sperr: float) -> float:
    """Tekst med ekstra luft mellom bokstavene. Returnerer x etter siste bokstav."""
    for i, c in enumerate(tekst):
        d.text((x, y), c, font=font, fill=farge)
        x += d.textlength(c, font=font) + (sperr if i < len(tekst) - 1 else 0)
    return x


def lag(enhet: float = 2.6) -> Image.Image:
    """enhet: piksler per logo-enhet i ferdig bilde (2,6 → stolpene er 109 px høye)."""
    u = enhet * SS
    logo_b, logo_h = (5 * BREDDE + 4 * MELLOM) * u, max(HOYDER) * u
    cap = 19 * u                      # versalhøyde for teksten
    f_fet, f_lett = sora(600, int(cap * 1.38)), sora(300, int(cap * 1.38))
    sperr, rom = 0.32 * cap, 0.55 * cap
    tmp = Image.new("RGBA", (10, 10)); td = ImageDraw.Draw(tmp)
    b_skjold = sum(td.textlength(c, font=f_fet) for c in "SKJOLD") + 5 * sperr
    b_lab = sum(td.textlength(c, font=f_lett) for c in "LAB") + 2 * sperr
    luft = 11 * u
    W = int(logo_b + luft + b_skjold + rom + b_lab + 2 * u)
    H = int(logo_h + 2 * u)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    top = u
    for i, h in enumerate(HOYDER):
        x = u + i * (BREDDE + MELLOM) * u
        d.rounded_rectangle((x, top, x + BREDDE * u, top + h * u), radius=BREDDE * u / 2, fill=GULL if i == 2 else HVIT)
    # teksten står midt på de korte stolpene (der øyet leser logoen), som i Skjold Lab-merket
    midt = top + HOYDER[0] * u * 0.62
    bb = f_fet.getbbox("SKJOLD")
    ty = midt - (bb[1] + bb[3]) / 2
    x = u + logo_b + luft
    x = sperret(d, x, ty, "SKJOLD", f_fet, HVIT, sperr) + rom
    sperret(d, x, ty, "LAB", f_lett, LYS_GULL, sperr)
    return im.resize((W // SS, H // SS), Image.LANCZOS)


def main():
    im = lag()
    im.save(os.path.join(HER, "oppstart.png"), optimize=True)
    for n in (90, 180, 270):
        im.rotate(-n, expand=True).save(os.path.join(HER, f"oppstart-{n}.png"), optimize=True)
    print("Laget oppstart.png", im.size, "og dreide utgaver")


if __name__ == "__main__":
    main()
