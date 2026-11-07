#!/bin/sh
# Renders av Skjold Radio til render/ (OpenSCAD, fargeskjema Tomorrow, 1600 × 1100).
cd "$(dirname "$0")"
mkdir -p render
# uten skjerm (CI/server): kjør med xvfb-run -a ./lag_render.sh
r() { openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$2\"" -D "farge=\"$4\"" -o "render/$1.png" skjold_radio.scad & }
FRONT=120,-560,70,120,62,68
SKRA=520,-430,300,120,62,62
EKSP=640,-600,380,120,85,62
BAK=470,620,300,120,62,62
r 01_forfra_lys samlet $FRONT lys
r 02_skra_lys samlet $SKRA lys
r 03_eksplodert_lys eksplodert $EKSP lys
r 04_forfra_mork samlet $FRONT mork
r 05_skra_mork samlet $SKRA mork
r 06_eksplodert_mork eksplodert $EKSP mork
r 07_bak_lys samlet $BAK lys
wait
