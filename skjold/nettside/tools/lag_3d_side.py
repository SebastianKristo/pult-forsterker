#!/usr/bin/env python3
"""Lager /3d/ og /en/3d/: alle 3D-printfilene for alle produktene, med bilde, status, søk og filter.

    python3 skjold/nettside/tools/lag_3d_side.py

Leser filene rett fra kabinett/ (samme produkter som 3D-pakken i kabinett/tools/pakk_3d.py), lager små bilder i
assets/img/3d/ og skriver 3d/index.html og en/3d/index.html. Nedlastingene går til filene på GitHub (main), og
«Last ned alt» til skjold-3d-print.zip i siste utgivelse. Kjør på nytt når filer kommer til eller endres.
"""
import glob
import html
import os
import re

from PIL import Image

NETT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROT = os.path.dirname(os.path.dirname(NETT))
KAB = os.path.join(ROT, "kabinett")
GH = "https://github.com/SebastianKristo/pult-forsterker"
RAW = GH + "/raw/main/"
ZIP = GH + "/releases/latest/download/skjold-3d-print.zip"

# id, navn, kategori, kilde (under kabinett/), undermapper som er egne produkter, bilde (render eller nettside-bilde),
# testet (False = tegnet og kontrollert, ikke printet/testet), produktside, flasher, tekst (no, en)
P = [
    ("s1", "Skjold S1 · frontplate", "lyd", "skjold-s1/print", [], "@s1-studio.jpg", None, "/s1/", None,
     ("Frontplaten til forsterkeren, i to utgaver: OLED og TFT, med innfelt sort innlegg.",
      "The front plate for the amplifier, in two versions: OLED and TFT, with an inlaid black insert.")),
    ("rost", "Skjold Røst", "lyd", "rost", [], "render/01_rost.png", False, "/rost/", "/flasher/rost/",
     ("Liten aktiv høyttaler for bad og kjøkken: 3″ element, 2,42″ OLED, fem knapper og volumhjul.",
      "Small active speaker for bathroom and kitchen: 3″ driver, 2.42″ OLED, five buttons and a volume wheel.")),
    ("rost-rund", "Skjold Røst Rund", "lyd", "rost_rund", [], "render/rund_front.png", False, "/rost/", "/flasher/rost/",
     ("Røst med rund kropp og grill hele veien rundt. Samme innmat, utskiftbare elementplater.",
      "Røst with a round body and grille all the way round. Same insides, swappable driver plates.")),
    ("radio", "Skjold Radio", "lyd", "radio", [], "render/01_forfra_lys.png", None, None, None,
     ("Bordradio med 4,3″ skjerm, seks favorittknapper og navigasjonshjul. Raspberry Pi inni.",
      "Table radio with a 4.3″ display, six favourite buttons and a navigation wheel. Raspberry Pi inside.")),
    ("stav", "Skjold Stav", "kontroll", "fjernkontroll", ["dokk"], "render/01_skra_lys.png", False, "/stav/", None,
     ("Fjernkontroll med 2,8″ berøringsskjerm, IR-læring og aktiviteter. Tre tasteoppsett.",
      "Remote with a 2.8″ touch screen, IR learning and activities. Three key layouts.")),
    ("dokk", "Skjold Dokk", "kontroll", "fjernkontroll/dokk", [], "render/00_hero.png", False, "/stav/#dokk", "/flasher/ir/",
     ("Ladedokk for Stav på 65°, med pogo-lading, og utgaver med IR og flat dokk.",
      "Charging dock for Stav at 65°, with pogo charging, plus versions with IR and a flat dock.")),
    ("hjul", "Skjold Hjul", "kontroll", "hjul", [], "render/01_hjul.png", None, None, None,
     ("Rund fjernkontroll på batteri med stor dreieknapp og fire favorittknapper.",
      "Round battery remote with a large rotary knob and four favourite buttons.")),
    ("hjul-s", "Skjold Hjul S", "kontroll", "hjul-s", [], "render/01_hjul_s.png", False, None, None,
     ("Hjul med rund 1,28″ fargeskjerm i midten som viser cover og tittel.",
      "Hjul with a round 1.28″ colour display in the middle showing cover art and title.")),
    ("kassett", "Skjold Spole · kassett", "kassett", "kassett", [], "render/01_spiller.png", None, "/spole/", "/flasher/kassett/",
     ("Kassettspilleren med NFC: sett inn en kassett, så starter musikken. Spoler som går rundt.",
      "The NFC cassette player: insert a cassette and the music starts. Reels that turn.")),
    ("hylle", "Skjold Kassetthylle", "kassett", "hylle", [], "render/01_hylle.png", False, "/spole/", None,
     ("Hylle for kassettene: den du tar ut, spilles. Lys under hver plass.",
      "Shelf for the cassettes: the one you take out plays. A light under each slot.")),
    ("sensor", "Skjold Sensor", "smarthus", "sensor", [], "@sensor-skra.jpg", False, "/sensor/", "/flasher/sensor/",
     ("Romsensor for temperatur, fukt, lys og bevegelse. ESP32, D1 mini eller ESP32 D1 mini.",
      "Room sensor for temperature, humidity, light and motion. ESP32, D1 mini or ESP32 D1 mini.")),
    ("bryter", "Skjold Bryter", "smarthus", "bryter", [], "@bryter-forfra.jpg", False, "/bryter/", "/flasher/bryter/",
     ("Fem vippebrytere i en boks under pulten, med skjult feste som klikker.",
      "Five toggle switches in a box under the desk, with a hidden mount that clicks.")),
    ("sans", "Skjold Sans", "smarthus", "sans", ["konsepter"], "render/montert.png", None, None, None,
     ("Skjoldformet multisensor for bad: bevegelse, temperatur, fukt og lys.",
      "Shield-shaped multisensor for the bathroom: motion, temperature, humidity and light.")),
    ("nokkel", "Skjold Nøkkel", "tilbehor", "nokkel", [], "render/01_skra_lys.png", False, None, None,
     ("Kabinett som gjør et ESP32-S3-kort om til en FIDO2-sikkerhetsnøkkel (passkeys).",
      "Enclosure that turns an ESP32-S3 board into a FIDO2 security key (passkeys).")),
]
KAT = {"lyd": ("Lyd", "Audio"), "kontroll": ("Fjernkontroller", "Remotes"), "kassett": ("Kassetter", "Cassettes"),
       "smarthus": ("Smarthus", "Smart home"), "tilbehor": ("Tilbehør", "Accessories")}


def storrelse(b):
    return f"{b / 1e6:.1f} MB".replace(".", ",") if b >= 1e6 else f"{max(1, round(b / 1e3))} kB"


def filer(kilde, egne):
    rot = os.path.join(KAB, kilde)
    mf, stl = [], []
    for d, mapper, fs in os.walk(rot):
        rel = os.path.relpath(d, rot)
        mapper[:] = sorted(m for m in mapper if not (rel == "." and m in egne) and m not in ("asm", "stl_asm", "__pycache__", "render"))
        for f in sorted(fs):
            p = os.path.join(d, f)
            r = os.path.relpath(p, ROT)
            if f.endswith(".3mf"):
                mf.append(r)
            elif f.endswith(".stl"):
                stl.append(r)
    return mf, stl


def les_meg(kilde):
    for n in ("LES_MEG.md", "LES_MEG_frontplate.md"):
        if os.path.exists(os.path.join(KAB, kilde, n)):
            return f"{GH}/blob/main/kabinett/{kilde}/{n}"
    return f"{GH}/tree/main/kabinett/{kilde}"


def bilde(pid, kilde, b):
    os.makedirs(os.path.join(NETT, "assets/img/3d"), exist_ok=True)
    src = os.path.join(NETT, "assets/img", b[1:]) if b.startswith("@") else os.path.join(KAB, kilde, b)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    m = 720 / w
    im = im.resize((720, round(h * m)), Image.LANCZOS)
    # samme form på alle kortene (4:3), beskåret fra midten
    H = 540
    if im.size[1] > H:
        t = (im.size[1] - H) // 2
        im = im.crop((0, t, 720, t + H))
    else:
        ny = Image.new("RGB", (720, H), im.getpixel((2, 2)))
        ny.paste(im, (0, (H - im.size[1]) // 2))
        im = ny
    im.save(os.path.join(NETT, f"assets/img/3d/{pid}.webp"), quality=80)
    im.save(os.path.join(NETT, f"assets/img/3d/{pid}.jpg"), quality=80, optimize=True, progressive=True)


def filnavn(r):
    n = os.path.basename(r)
    return re.sub(r"\.(3mf|stl)$", "", n)


def kort(p, en):
    pid, navn, kat, kilde, egne, b, testet, side, flasher, tekst = p
    mf, stl = filer(kilde, egne)
    bilde(pid, kilde, b)
    L = 1 if en else 0
    pre = "/en" if en else ""
    status = "" if testet is None else (f'<span class="d3-status">{"Not tested yet" if en else "Ikke testet ennå"}</span>' if testet is False else "")
    lenker = [(("Build guide" if en else "Byggeveiledning"), les_meg(kilde))]
    if side:
        lenker.append((("Product page" if en else "Produktside"), pre + side))
    if flasher:
        lenker.append((("Firmware" if en else "Fastvare"), flasher))
    lenker.append((("All files on GitHub" if en else "Alle filene på GitHub"), f"{GH}/tree/main/kabinett/{kilde}"))
    stl_sum = sum(os.path.getsize(os.path.join(ROT, r)) for r in stl)

    def liste(lst, sti_ut=False):
        rader = []
        for r in lst:
            sz = os.path.getsize(os.path.join(ROT, r))
            under = os.path.relpath(r, os.path.join("kabinett", kilde))
            vis = under if sti_ut else filnavn(r)
            rader.append(f'<li><a href="{RAW}{html.escape(r)}" download>{html.escape(vis)}</a><span>{storrelse(sz)}</span></li>')
        return "".join(rader)
    blokker = ""
    if mf:
        blokker += (f'<details class="d3-filer" open><summary>{"Ready plates for Creality K2 (3MF)" if en else "Ferdige plater for Creality K2 (3MF)"}'
                    f' <b>{len(mf)}</b></summary><ul>{liste(mf, any("/" in os.path.relpath(r, os.path.join("kabinett", kilde)) for r in mf))}</ul></details>')
    if stl:
        blokker += (f'<details class="d3-filer"><summary>{"Single parts (STL)" if en else "Enkeltdeler (STL)"} <b>{len(stl)}</b>'
                    f' <span>{storrelse(stl_sum)}</span></summary><ul>{liste(stl, True)}</ul></details>')
    sok = " ".join([navn, KAT[kat][L], tekst[L], kilde]).lower()
    return (f'<article class="d3-kort" data-kat="{kat}" data-sok="{html.escape(sok)}" id="{pid}">'
            f'<picture><source srcset="/assets/img/3d/{pid}.webp" type="image/webp"><img src="/assets/img/3d/{pid}.jpg" alt="{html.escape(navn)}" width="720" height="540" loading="lazy"></picture>'
            f'<div class="d3-inn"><div class="d3-topp"><span class="d3-kat">{KAT[kat][L]}</span>{status}</div>'
            f'<h2>{html.escape(navn)}</h2><p>{html.escape(tekst[L])}</p>'
            f'<div class="d3-lenker">{"".join(f"<a href=\"{u}\">{t}</a>" for t, u in lenker)}</div>{blokker}</div></article>'), len(mf), len(stl)


def side(en):
    mal = os.path.join(NETT, "en/stav/index.html" if en else "stav/index.html")
    s = open(mal).read()
    url, andre = ("/en/3d/", "/3d/") if en else ("/3d/", "/en/3d/")
    tittel = "3D files for every product – Skjold Lab" if en else "3D-filer for alle produktene – Skjold Lab"
    besk = ("All the 3D print files for Skjold Lab: ready plates for Creality K2 and single STL parts, with build guides."
            if en else "Alle 3D-printfilene fra Skjold Lab: ferdige plater for Creality K2 og enkeltdeler i STL, med byggeveiledninger.")
    s = re.sub(r"<title>[^<]*</title>", f"<title>{tittel}</title>", s, count=1)
    s = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*"', lambda m: m.group(1) + besk + '"', s)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*"', lambda m: m.group(1) + tittel + '"', s)
    stav, stav_en = "/stav/", "/en/stav/"
    s = s.replace(f"https://skjold-lab.com{stav_en}", "https://skjold-lab.com/en/3d/").replace(f"https://skjold-lab.com{stav}", "https://skjold-lab.com/3d/")
    s = s.replace(' aria-current="page">', '>')
    s = s.replace(f'href="{stav}" lang="nb"', 'href="/3d/" lang="nb"').replace(f'href="{stav_en}" lang="en"', 'href="/en/3d/" lang="en"')
    s = s.replace(' data-her>', '>')
    s = s.replace(f'<a href="{url}">', f'<a href="{url}" aria-current="page">', 1)
    s = s.replace('<link rel="stylesheet" href="/assets/skjold.css', '<link rel="stylesheet" href="/assets/3d.css?v=1">\n<link rel="stylesheet" href="/assets/skjold.css', 1)
    s = s.replace('</head>', '<script src="/assets/3d.js?v=1" defer></script>\n</head>', 1)
    kortene, n3, ns = [], 0, 0
    for p in P:
        k, a, b = kort(p, en)
        kortene.append(k); n3 += a; ns += b
    filt = "".join(f'<button type="button" class="d3-filter" data-kat="{k}" aria-pressed="false">{v[1 if en else 0]}</button>' for k, v in KAT.items())
    alle = "All" if en else "Alle"
    main = f'''<main id="hoved">
<section class="p-hero node-bg" style="padding-bottom:40px">
  <div class="k" data-reveal="0">{"3D FILES" if en else "3D-FILER"}</div>
  <h1 data-reveal="80">{"Print it yourself" if en else "Print den selv"}</h1>
  <p data-reveal="160">{("Every Skjold enclosure as ready plates for Creality K2 (colours, brims and settings included) and as single STL parts for other printers. Each product has a build guide with parts, wiring and assembly." if en else "Alle Skjold-kabinettene som ferdige plater for Creality K2 (med farger, brim og innstillinger) og som enkeltdeler i STL for andre printere. Hvert produkt har en byggeveiledning med deler, kobling og montering.")}</p>
  <div class="knapper" data-reveal="240"><a class="knapp knapp-m" href="{ZIP}">{"Download everything (zip)" if en else "Last ned alt (zip)"} ›</a><a class="knapp knapp-o" href="{GH}/tree/main/kabinett">{"Source on GitHub" if en else "Kilden på GitHub"} ›</a></div>
  <p class="d3-tall" data-reveal="300">{len(P)} {"products" if en else "produkter"} · {n3} {"plates" if en else "plater"} · {ns} {"parts" if en else "deler"}</p>
</section>
<section class="seksjon d3" aria-label="{"3D files" if en else "3D-filer"}">
  <div class="d3-verktoy">
    <label class="d3-sok"><span class="sr">{"Search" if en else "Søk"}</span><input type="search" placeholder="{"Search, e.g. speaker, ESP32, dock" if en else "Søk, f.eks. høyttaler, ESP32, dokk"}" data-d3-sok></label>
    <div class="d3-filtre" role="group" aria-label="{"Category" if en else "Kategori"}"><button type="button" class="d3-filter" data-kat="" aria-pressed="true">{alle}</button>{filt}</div>
  </div>
  <p class="d3-ingen" hidden>{"Nothing matched." if en else "Fant ingenting."}</p>
  <div class="d3-rutenett">{"".join(kortene)}</div>
  <div class="d3-tips">
    <h2>{"Good to know" if en else "Greit å vite"}</h2>
    <ul>
      <li>{"<b>3MF</b> opens in Creality Print or OrcaSlicer with colours and settings. Use <b>STL</b> for other printers." if en else "<b>3MF</b> åpnes i Creality Print eller OrcaSlicer med farger og innstillinger. Bruk <b>STL</b> til andre printere."}</li>
      <li>{"PETG or ASA is recommended (PLA softens in warm and humid rooms). Parts with clips and springs need PETG." if en else "PETG eller ASA anbefales (PLA blir mykt i varme og fuktige rom). Deler med klips og fjærer trenger PETG."}</li>
      <li>{"Most products are designed and checked by script (collisions, overhangs, fit), but not yet printed and tested. The badge says so." if en else "De fleste produktene er tegnet og kontrollert med skript (kollisjoner, overheng, passform), men ikke printet og testet ennå. Merket sier fra."}</li>
      <li>{"Licence for the 3D models: CC BY-NC-SA 4.0 – build your own, but not for sale." if en else "Lisens for 3D-modellene: CC BY-NC-SA 4.0 – bygg selv, men ikke for salg."}</li>
    </ul>
  </div>
</section>
</main>'''
    a = s.index('<main id="hoved">'); b = s.index('</main>') + 7
    s = s[:a] + main + s[b:]
    ut = os.path.join(NETT, "en/3d/index.html" if en else "3d/index.html")
    os.makedirs(os.path.dirname(ut), exist_ok=True)
    open(ut, "w").write(s)
    print("skrev", os.path.relpath(ut, NETT), f"({len(P)} produkter, {n3} 3MF, {ns} STL)")


if __name__ == "__main__":
    side(False)
    side(True)
