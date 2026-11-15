#!/usr/bin/env bash
# Lydtest: send all lyd (etter EQ og volum) ut på Raspberry Pi 4 sin 3,5 mm-kontakt i stedet for forsterkeren/DAC-en.
# Virker på S1, Touch og Node. Slå av igjen for vanlig lyd.
#   sudo bash pi/tools/lydtest_jack.sh på     – lyd ut på 3,5 mm
#   sudo bash pi/tools/lydtest_jack.sh av     – tilbake til vanlig utgang
#   sudo bash pi/tools/lydtest_jack.sh test   – spill testtone venstre/høyre rett på 3,5 mm (uten Skjold)
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Kjør som root (sudo)" >&2; exit 1; }
ENV=/etc/ki-amp.env
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
MERKE="# skjold-lydtest"
har_jack() { aplay -l 2>/dev/null | grep -q "Headphones"; }
case "${1:-}" in
  på|pa|on)
    if ! har_jack; then
      # Pi-ens egen lydutgang er slått av når forsterkeren/DAC-en er satt opp: slå den på (krever omstart)
      grep -q "^dtparam=audio=on" "$CFG" || echo "dtparam=audio=on  $MERKE" >> "$CFG"
      sed -i '/^KI_AMP_JACK_TEST=/d' "$ENV"; echo "KI_AMP_JACK_TEST=1" >> "$ENV"
      echo "3,5 mm-utgangen er slått på i $CFG. Start Pi-en på nytt: sudo reboot"
      echo "Etter omstart går lyden ut på 3,5 mm."
      exit 0
    fi
    sed -i '/^KI_AMP_JACK_TEST=/d' "$ENV"; echo "KI_AMP_JACK_TEST=1" >> "$ENV"
    amixer -q -c Headphones sset PCM 100% unmute 2>/dev/null || amixer -q -c Headphones sset Headphone 100% unmute 2>/dev/null || true
    systemctl restart ki-amp
    echo "Lyd ut på 3,5 mm. Spill noe fra appen (eller: sudo bash $0 test). Tilbake: sudo bash $0 av"
    ;;
  av|off)
    sed -i '/^KI_AMP_JACK_TEST=/d' "$ENV"
    if grep -q "$MERKE" "$CFG"; then
      sed -i "/$MERKE/d" "$CFG"; echo "3,5 mm-utgangen er slått av igjen i $CFG (gjelder etter omstart)."
    fi
    systemctl restart ki-amp
    echo "Vanlig lydutgang igjen."
    ;;
  test)
    har_jack || { echo "Fant ikke 3,5 mm-utgangen (Headphones). Kjør først: sudo bash $0 på" >&2; exit 1; }
    amixer -q -c Headphones sset PCM 100% unmute 2>/dev/null || true
    systemctl stop camilladsp 2>/dev/null || true
    speaker-test -D plughw:Headphones -c 2 -t wav -l 2 || true
    systemctl start camilladsp 2>/dev/null || true
    ;;
  *) echo "Bruk: sudo bash $0 på|av|test" >&2; exit 1 ;;
esac
