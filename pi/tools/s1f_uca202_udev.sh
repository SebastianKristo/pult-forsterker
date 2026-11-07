#!/usr/bin/env bash
# Skjold S1 rev F: gi de to Behringer UCA202/UCA222/UFO202 (samme PCM2902-brikke, ALSA-id «CODEC») faste ALSA-navn (UCA_AUX1 og UCA_AUX2) etter hvilken USB-port de sitter i.
# Kortet i den «laveste» porten (sortert USB-sti) blir AUX 1. Bytter de plass: kjør med --swap.
#   sudo bash pi/tools/s1f_uca202_udev.sh [--swap]
set -euo pipefail
RULES=/etc/udev/rules.d/85-skjold-uca202.rules
ports=()
for c in /sys/class/sound/card*; do
  [ -e "$c/id" ] || continue
  id=$(cat "$c/id")
  case "$id" in CODEC*|UCA_AUX*) ;; *) continue ;; esac
  dev=$(readlink -f "$c/device")              # …/usb1/1-1/1-1.2/1-1.2:1.0
  port=$(basename "$(dirname "$dev")")         # 1-1.2
  ports+=("$port")
done
if [ "${#ports[@]}" -lt 2 ]; then
  echo "Fant ${#ports[@]} USB-lydkort (UCA202/UCA222/UFO202 – trenger 2). Sjekk «aplay -l» og at begge er koblet til." >&2
  exit 1
fi
mapfile -t ports < <(printf '%s\n' "${ports[@]}" | sort -V | head -n2)
a1=${ports[0]}; a2=${ports[1]}
[ "${1:-}" = --swap ] && { t=$a1; a1=$a2; a2=$t; }
cat <<R | sudo tee "$RULES" >/dev/null
# Skjold S1 rev F – generert av pi/tools/s1f_uca202_udev.sh
SUBSYSTEM=="sound", KERNELS=="$a1", ATTR{id}="UCA_AUX1"
SUBSYSTEM=="sound", KERNELS=="$a2", ATTR{id}="UCA_AUX2"
R
sudo udevadm control --reload-rules && sudo udevadm trigger -s sound || true
echo "AUX 1 = UCA202 i port $a1 (også hodetelefon), AUX 2 = UCA202 i port $a2. Gjelder etter omstart."
