#!/usr/bin/env bash
# Kiosk-skjermene (skjold-ui på S1/Radio, skjold-touch på Touch): ingen musepeker og ingen Google Oversett.
#  - HDMI-portenes CEC-fjernkontroll (vc4-hdmi-0/1) melder seg som tastatur + mus. Finnes det en «mus», tegner cage
#    en peker. libinput ignorerer dem, så setet bare har berøring (eller ingenting) og pekeren forsvinner.
#  - Chromium-policy: oversetting av (TranslateEnabled=false), uansett språk og startvalg.
#   sudo bash pi/tools/kiosk_hardening.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Kjør som root (sudo)" >&2; exit 1; }
R=/etc/udev/rules.d/90-skjold-no-cec-pointer.rules
NY='SUBSYSTEM=="input", ATTRS{name}=="vc4-hdmi*", ENV{LIBINPUT_IGNORE_DEVICE}="1"'
if [ "$(cat "$R" 2>/dev/null)" != "$NY" ]; then
  echo "$NY" > "$R"
  udevadm control --reload-rules 2>/dev/null && udevadm trigger --subsystem-match=input 2>/dev/null || true
fi
for d in /etc/chromium/policies/managed /etc/chromium-browser/policies/managed; do
  mkdir -p "$d" && printf '{\n  "TranslateEnabled": false\n}\n' > "$d/skjold-kiosk.json"
done
echo "kiosk: ingen CEC-peker, ingen oversetting"
