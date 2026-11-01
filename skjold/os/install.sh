#!/usr/bin/env bash
# Skjold OS – installer/oppdater skjerm-UI-et. Idempotent, kjøres som root.
#   sudo ./skjold/os/install.sh
# Forutsetter /opt/skjold/venv fra skjold/node/driver/installer_node.sh (luma.oled, smbus2, gpiozero, Pillow).
# Node-layout: /etc/default/skjold-os (installer_node.sh skriver SKJOLD_OS_ARGS=--layout node-oled32).
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"
DEST=/opt/skjold/os
VENV=/opt/skjold/venv
[ "$(id -u)" = 0 ] || { echo "Kjør som root (sudo)" >&2; exit 1; }

if [ ! -x "$VENV/bin/python" ]; then
  echo "Mangler $VENV – lager den (kjør helst skjold/node/driver/installer_node.sh først)"
  apt-get install -y --no-install-recommends python3-venv python3-pil python3-gpiozero python3-lgpio python3-smbus2 i2c-tools fonts-dejavu-core
  python3 -m venv --system-site-packages "$VENV"
  "$VENV/bin/pip" install --no-cache-dir "luma.oled==3.14.0" "smbus2>=0.4.3"
fi
# eldre venv (ST7735-Node) mangler luma.oled
"$VENV/bin/python" -c "import luma.oled" 2>/dev/null || "$VENV/bin/pip" install --no-cache-dir "luma.oled==3.14.0" "smbus2>=0.4.3" || true
dpkg -s fonts-dejavu-core >/dev/null 2>&1 || apt-get install -y --no-install-recommends fonts-dejavu-core || true

install -d "$DEST" /var/lib/skjold
rm -rf "$DEST/skjold_os"
cp -r "$HER/skjold_os" "$DEST/"
find "$DEST" -name __pycache__ -prune -exec rm -rf {} +
# node_pins.json: /etc/skjold/node_pins.json (lagt der av installer_node.sh), ellers fra repoet
if [ ! -f /etc/skjold/node_pins.json ] && [ -f "$HER/../node/config/node_pins.json" ]; then
  install -d /etc/skjold && install -m 0644 "$HER/../node/config/node_pins.json" /etc/skjold/node_pins.json
fi
[ -f /etc/default/skjold-os ] || printf '# Ekstra argumenter, f.eks. --layout node-oled32 --api http://127.0.0.1:8765\nSKJOLD_OS_ARGS=\n' > /etc/default/skjold-os

install -m 0644 "$HER/skjold-os.service" /etc/systemd/system/skjold-os.service
# oled_display.py skal ikke tegne (Skjold OS eier skjermen), men kjøre videre som metadata-tjeneste (AirPlay/BT-metadata)
if [ -f /etc/ki-amp.env ]; then
  sed -i '/^KI_AMP_DISPLAY=/d' /etc/ki-amp.env && echo "KI_AMP_DISPLAY=none" >> /etc/ki-amp.env
  systemctl try-restart oled-display.service 2>/dev/null || true
fi
systemctl daemon-reload
systemctl enable skjold-os.service
systemctl restart skjold-os.service || true
echo "Skjold OS installert i $DEST (journalctl -u skjold-os -f)"
