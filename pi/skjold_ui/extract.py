#!/usr/bin/env python3
"""Henter S1-skjermens tegnekode ut av designfilen, slik at skjermen blir piksel-identisk med designet.

    python3 pi/skjold_ui/extract.py <mappe med skjold_s1_programvare>

Skriver web/s1_draw.js (seksjonen «display drawing» fra s1/pultforsterker_revb_metall.js + dataene den bruker),
web/skjold_settings.js og web/skjold_welcome.js. Kjør på nytt når designet endres.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(src):
    js = open(os.path.join(src, "s1", "pultforsterker_revb_metall.js"), encoding="utf-8").read().split("\n")
    rv = open(os.path.join(src, "s1", "revb_features.js"), encoding="utf-8").read().replace("export ", "")

    def find(pat):
        for i, l in enumerate(js):
            if re.search(pat, l):
                return i
        raise SystemExit("fant ikke " + pat)

    a = find(r"^// ---------- display drawing")
    b = find(r"^// printable desk-mount brackets")
    sect = js[a:b]
    # QR uten nett: bruk vendret qrcode-generator (web/qrcode.js) i stedet for esm.sh
    sect = [("let QRLIB=(window.qrcode||null);" if l.startswith("let QRLIB=null; import(") else l) for l in sect]
    pick = lambda pat: js[find(pat)]
    out = [
        "// AUTOGENERERT av pi/skjold_ui/extract.py fra designfilen s1/pultforsterker_revb_metall.js – ikke rediger.",
        rv,
        pick(r"^const cvs="), pick(r"^const cvt="), pick(r"^const cvb="),
        "const texO={needsUpdate:false},texT={needsUpdate:false},texB={needsUpdate:false};",
        "let LEDK=1; const setLed=()=>{}; const bc=null;",
        pick(r"^const WL="), pick(r"^const TRACKS="), pick(r"^const NOWP="), pick(r"^const AUXSRC="),
        pick(r"^const USBSRC="), pick(r"^const PRESETS="), pick(r"^const INPUTS="),
        pick(r"^const NIGHT_STEPS_ON"),
        "\n".join(js[find(r"^function nightMode"):find(r"^function nightMode") + 3]),
        pick(r"^const S=\{rebootT"),
        "\n".join(sect),
        "function refresh(){}",
    ]
    web = os.path.join(HERE, "web")
    text = "\n".join(out) + "\n"
    # Rettelser som skal overleve et nytt uttrekk (gjør ingenting når designfila allerede har dem):
    # «Blåtann» i all skjermtekst, og fremdriftslinja bruker låtens egentlige varighet.
    for a, b in (("pill('BLUETOOTH');", "pill('BLÅTANN');"),
                 ("velg den i Bluetooth på telefonen", "velg den i Blåtann på telefonen"),
                 ("S.wl==='bt'?'BLUETOOTH':'AIRPLAY'", "S.wl==='bt'?'BLÅTANN':'AIRPLAY'"),
                 ("dur=244, p=", "dur=(INPUTS[0].dur>1?INPUTS[0].dur:244), p=")):
        text = text.replace(a, b)
    with open(os.path.join(web, "s1_draw.js"), "w", encoding="utf-8") as fh:
        fh.write(text)
    for f in ("skjold_settings.js", "skjold_welcome.js"):
        shutil.copy(os.path.join(src, "felles", f), os.path.join(web, f))
    print("skrev", os.path.join(web, "s1_draw.js"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "design"))
