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
r() {   # navn  samlet|eksplodert|front_av  kamera  lys|mork  [full|kort]  [oppsett]
  E=0; P=samlet; F=0; [ "$2" = eksplodert ] && { E=25; P=eksplodert; }; [ "$2" = front_av ] && F=14
  V=${5:-kort}; O=${6:-rutenett}
  ( openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$P\"" -D "farge=\"$4\"" -D "variant=\"$V\"" -D "oppsett=\"$O\"" -D "frontE=$F" -D 'skjerm="nokkel"' -o "render/$1.png" skjold_fjernkontroll.scad
    openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D 'part="skjermflate"' -D "variant=\"$V\"" -D "skjermE=$E" -o "$TMP/$1.png" skjold_fjernkontroll.scad
    python3 skjerm_i_render.py "render/$1.png" "$TMP/$1.png" render/skjerm-1-aktiviteter.png ) &
}
# standard (kort variant, 201,5 mm)
SKRA=30,101.75,7,50,0,-38,353
OVEN=27.5,98.75,7,15,0,-90,418
EKSP=30,99.75,22,55,0,-38,430
SIDE=27.5,98.75,6,80,0,-90,392
NAER=27.5,112,10,42,0,-22,185
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
# full variant (valgfri, 244,5 mm, med talltaster og smarthus-rad)
SKRAF=30,123.25,7,50,0,-38,398
OVENF=27.5,120.25,7,15,0,-90,505
EKSPF=30,121.75,22,55,0,-38,488
SIDEF=27.5,120.25,6,80,0,-90,473
r 01_skra_lys_full samlet $SKRAF lys full
r 02_ovenfra_lys_full samlet $OVENF lys full
r 03_eksplodert_lys_full eksplodert $EKSPF lys full
r 04_skra_mork_full samlet $SKRAF mork full
r 05_ovenfra_mork_full samlet $OVENF mork full
r 07_side_lys_full samlet $SIDEF lys full
# frontplatene A/B/C (lys og Bone White) og frontplaten løftet av
r 31_front_rutenett samlet $SKRA lys kort rutenett
r 32_front_vannrett samlet $SKRA lys kort vannrett
r 33_front_stor samlet $SKRA lys kort stor
r 34_front_rutenett_bone samlet $SKRA bone kort rutenett
r 35_front_vannrett_bone samlet $SKRA bone kort vannrett
r 36_front_stor_bone samlet $SKRA bone kort stor
r 37_front_av front_av 30,95,20,55,0,-38,330 bone kort vannrett
# innmaten: bunnen med alle kjøpte deler (tastekortet gjennomsiktig), og montering (eksplodert, uten skjermbilde)
ri() {   # navn  part  kamera  [kort|full]
  openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$2\"" -D 'farge="bone"' -D "variant=\"${4:-kort}\"" -o "render/$1.png" skjold_fjernkontroll.scad &
}
ri 10_inni_ovenfra inni 27.5,98.75,4,0,0,-90,368
ri 11_inni_skra inni 28,100.75,4,45,0,-35,279
ri 12_montering montering 30,100.75,34,62,0,-40,524
ri 10_inni_ovenfra_full inni 27.5,120.25,4,0,0,-90,449 full
wait
python3 lag_oppsett.py
