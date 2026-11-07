#!/bin/sh
# Renders av Skjold Fjernkontroll til render/ (OpenSCAD, fargeskjema Tomorrow, 1600 × 1100).
# Skjermen viser aktivitetslista (render/skjerm-1-aktiviteter.png, laget av lag_skjermbilder.py): OpenSCAD tegner det
# aktive området i magenta, og skjerm_i_render.py legger skjermbildet inn i perspektiv (som Skjold Radio).
# Uten skjerm (CI/server): xvfb-run -a ./lag_render.sh
cd "$(dirname "$0")"
mkdir -p render
[ -f render/skjerm-1-aktiviteter.png ] || python3 lag_skjermbilder.py
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
r() {
  E=0; P=samlet; [ "$2" = eksplodert ] && { E=25; P=eksplodert; }
  ( openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$P\"" -D "farge=\"$4\"" -D 'skjerm="nokkel"' -o "render/$1.png" skjold_fjernkontroll.scad
    openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D 'part="skjermflate"' -D "skjermE=$E" -o "$TMP/$1.png" skjold_fjernkontroll.scad
    python3 skjerm_i_render.py "render/$1.png" "$TMP/$1.png" render/skjerm-1-aktiviteter.png ) &
}
SKRA=30,108,7,50,0,-38,345
OVEN=27,104,7,15,0,-90,430
EKSP=30,106,22,55,0,-38,420
SIDE=27,104,6,80,0,-90,400
NAER=27,152,10,42,0,-22,135
HALE=27,8,6,72,0,-28,120
r 01_skra_lys samlet $SKRA lys
r 02_ovenfra_lys samlet $OVEN lys
r 03_eksplodert_lys eksplodert $EKSP lys
r 04_skra_mork samlet $SKRA mork
r 05_ovenfra_mork samlet $OVEN mork
r 06_eksplodert_mork eksplodert $EKSP mork
r 07_side_lys samlet $SIDE lys
r 08_naer_lys samlet $NAER lys
r 09_hale_lys samlet $HALE lys
wait
