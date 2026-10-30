#!/usr/bin/env bash
# Skjold Node – driveroppsett på Raspberry Pi OS (Bookworm/Trixie). Kjøres som root.
# Brukes av pi-gen stage-skjold (chroot) og manuelt:  sudo ./driver/installer_node.sh
# - legger blokken fra config/config.txt.node inn i /boot/firmware/config.txt (idempotent)
# - installerer gpiozero/lgpio (apt) og luma.lcd (pip i /opt/skjold/venv)
# - kopierer node_pins.json til /etc/skjold/node_pins.json
set -euo pipefail
HER="$(cd "$(dirname "$0")/.." && pwd)"
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
START="# >>> skjold-node >>>"; SLUTT="# <<< skjold-node <<<"
VENV=/opt/skjold/venv

if [ -f "$CFG" ]; then
  sed -i "/^$START\$/,/^$SLUTT\$/d" "$CFG"
  # dtparam=spi/audio/i2c fjernes fra resten av fila så blokken vår gjelder alene
  sed -i -E '/^dtparam=(spi|audio|i2c_arm)=/d' "$CFG"
  { echo "$START"; cat "$HER/config/config.txt.node"; echo "$SLUTT"; } >> "$CFG"
  echo "config.txt oppdatert ($CFG)"
else
  echo "ADVARSEL: fant ikke config.txt – hopper over" >&2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends python3-gpiozero python3-lgpio python3-pil python3-spidev python3-venv fonts-dejavu-core
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install --no-cache-dir "luma.lcd==2.11.0"

install -d /etc/skjold
install -m 0644 "$HER/config/node_pins.json" /etc/skjold/node_pins.json
# SPI/GPIO-tilgang for tjenestebrukeren (standard i Pi OS: gruppene spi og gpio)
id skjold >/dev/null 2>&1 && usermod -aG spi,gpio skjold || true
echo "Ferdig. Start på nytt og kjør: $VENV/bin/python $HER/tools/node_selftest.py"
