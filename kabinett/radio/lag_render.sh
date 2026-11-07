#!/bin/sh
# Renders av Skjold Radio til render/ (OpenSCAD, fargeskjema Tomorrow, 1600 × 1100).
# Skjermen viser «nå spilles» (render/skjerm-1-radio.png): OpenSCAD tegner det aktive området i magenta, og
# skjerm_i_render.py legger skjermbildet inn i perspektiv. Nye skjermbilder: node pi/skjold_ui/test_render.js kabinett/radio/render radio
cd "$(dirname "$0")"
mkdir -p render
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
# uten skjerm (CI/server): kjør med xvfb-run -a ./lag_render.sh
r() {
  E=0; [ "$2" = eksplodert ] && E=40
  ( openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$2\"" -D "farge=\"$4\"" -D 'skjerm="nokkel"' -o "render/$1.png" skjold_radio.scad
    openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D 'part="skjermflate"' -D "skjermE=$E" -o "$TMP/$1.png" skjold_radio.scad
    python3 skjerm_i_render.py "render/$1.png" "$TMP/$1.png" render/skjerm-1-radio.png ) &
}
FRONT=120,-560,70,120,62,68
SKRA=520,-430,300,120,62,62
EKSP=640,-600,380,120,85,62
BAK=470,620,300,120,62,62
NAER=-170,-250,190,95,0,70
r 01_forfra_lys samlet $FRONT lys
r 02_skra_lys samlet $SKRA lys
r 03_eksplodert_lys eksplodert $EKSP lys
r 04_forfra_mork samlet $FRONT mork
r 05_skra_mork samlet $SKRA mork
r 06_eksplodert_mork eksplodert $EKSP mork
r 07_bak_lys samlet $BAK lys
r 08_naer_lys samlet $NAER lys
wait
