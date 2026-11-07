#!/bin/sh
# Renders av Skjold Fjernkontroll til render/ (OpenSCAD, fargeskjema Tomorrow, 1600 × 1100).
# Skjermen viser aktivitetslista (render/skjerm-1-aktiviteter.png, laget av lag_skjermbilder.py): OpenSCAD tegner det
# aktive området i magenta, og skjerm_i_render.py legger skjermbildet inn i perspektiv (som Skjold Radio).
# Uten skjerm (CI/server): xvfb-run -a ./lag_render.sh
cd "$(dirname "$0")"
mkdir -p render
[ -f render/skjerm-1-aktiviteter.png ] || python3 lag_skjermbilder.py
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
r() {   # navn  samlet|eksplodert  kamera  lys|mork  [full|kort]
  E=0; P=samlet; [ "$2" = eksplodert ] && { E=25; P=eksplodert; }
  V=${5:-full}
  ( openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$P\"" -D "farge=\"$4\"" -D "variant=\"$V\"" -D 'skjerm="nokkel"' -o "render/$1.png" skjold_fjernkontroll.scad
    openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D 'part="skjermflate"' -D "variant=\"$V\"" -D "skjermE=$E" -o "$TMP/$1.png" skjold_fjernkontroll.scad
    python3 skjerm_i_render.py "render/$1.png" "$TMP/$1.png" render/skjerm-1-aktiviteter.png ) &
}
SKRA=30,119,7,50,0,-38,370
OVEN=27.5,115,7,15,0,-90,470
EKSP=30,117,22,55,0,-38,450
SIDE=27.5,115,6,80,0,-90,440
NAER=27.5,165,10,42,0,-22,150
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
# kort variant (187 mm, uten talltastene og smarthus-raden)
SKRAK=30,97,7,50,0,-38,320
OVENK=27.5,93.5,7,15,0,-90,390
EKSPK=30,95,22,55,0,-38,390
SIDEK=27.5,93.5,6,80,0,-90,360
r 11_skra_lys_kort samlet $SKRAK lys kort
r 12_ovenfra_lys_kort samlet $OVENK lys kort
r 13_eksplodert_lys_kort eksplodert $EKSPK lys kort
r 14_skra_mork_kort samlet $SKRAK mork kort
r 15_ovenfra_mork_kort samlet $OVENK mork kort
r 16_side_lys_kort samlet $SIDEK lys kort
wait
