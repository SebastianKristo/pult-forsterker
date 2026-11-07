#!/bin/sh
# Renders av Skjold Fjernkontroll til render/ (OpenSCAD, fargeskjema Tomorrow, 1600 × 1100).
# 01–09 viser standard (kort variant), 21–25 Bone White-fargene, *_full.png full variant (valgfri).
# Skjermen viser aktivitetslista (render/skjerm-1-aktiviteter.png, laget av lag_skjermbilder.py): OpenSCAD tegner det
# aktive området i magenta, og skjerm_i_render.py legger skjermbildet inn i perspektiv (som Skjold Radio).
# Uten skjerm (CI/server): xvfb-run -a ./lag_render.sh
cd "$(dirname "$0")"
mkdir -p render
[ -f render/skjerm-1-aktiviteter.png ] || python3 lag_skjermbilder.py
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
r() {   # navn  samlet|eksplodert  kamera  lys|mork  [full|kort]
  E=0; P=samlet; [ "$2" = eksplodert ] && { E=25; P=eksplodert; }
  V=${5:-kort}
  ( openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$P\"" -D "farge=\"$4\"" -D "variant=\"$V\"" -D 'skjerm="nokkel"' -o "render/$1.png" skjold_fjernkontroll.scad
    openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D 'part="skjermflate"' -D "variant=\"$V\"" -D "skjermE=$E" -o "$TMP/$1.png" skjold_fjernkontroll.scad
    python3 skjerm_i_render.py "render/$1.png" "$TMP/$1.png" render/skjerm-1-aktiviteter.png ) &
}
# standard (kort variant, 184 mm)
SKRA=30,95,7,50,0,-38,320
OVEN=27.5,92,7,15,0,-90,385
EKSP=30,93,22,55,0,-38,390
SIDE=27.5,92,6,80,0,-90,355
NAER=27.5,120,10,42,0,-22,150
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
# Bone White matt PLA (topp) og mørk matt PETG (bunn); siste bilde med grå PETG-bunn
r 21_skra_bone samlet $SKRA bone
r 22_ovenfra_bone samlet $OVEN bone
r 23_side_bone samlet $SIDE bone
r 24_naer_bone samlet $NAER bone
r 25_skra_bone_gra samlet $SKRA bone_gra
# full variant (valgfri, 227 mm, med talltaster og smarthus-rad)
SKRAF=30,117,7,50,0,-38,365
OVENF=27.5,113.5,7,15,0,-90,465
EKSPF=30,115,22,55,0,-38,445
SIDEF=27.5,113.5,6,80,0,-90,435
r 01_skra_lys_full samlet $SKRAF lys full
r 02_ovenfra_lys_full samlet $OVENF lys full
r 03_eksplodert_lys_full eksplodert $EKSPF lys full
r 04_skra_mork_full samlet $SKRAF mork full
r 05_ovenfra_mork_full samlet $OVENF mork full
r 07_side_lys_full samlet $SIDEF lys full
wait
