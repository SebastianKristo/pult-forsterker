#!/usr/bin/env bash
# Skjold Node (OLED-utgave) – driveroppsett på Raspberry Pi OS (Bookworm/Trixie). Kjøres som root.
# Brukes av pi-gen stage-skjold (chroot), Skjold Flasher (firstboot) og manuelt:  sudo ./driver/installer_node.sh
# - legger blokken fra config/config.txt.node inn i /boot/firmware/config.txt (idempotent)
#   I²C på (400 kHz), SPI AV (GPIO7 = SPI0 CE1 er knappen ▶▶), 3,5 mm-lyd på
# - slår på I²C også via raspi-config (nonint do_i2c 0) og i2c-dev
# - installerer gpiozero/lgpio/smbus2/i2c-tools (apt) og luma.oled + smbus2 (pip i /opt/skjold/venv)
# - kopierer node_pins.json til /etc/skjold/node_pins.json
# - setter Skjold OS-layouten node-oled32 i /etc/default/skjold-os og installerer Skjold OS
set -euo pipefail
HER="$(cd "$(dirname "$0")/.." && pwd)"
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
START="# >>> skjold-node >>>"; SLUTT="# <<< skjold-node <<<"
VENV=/opt/skjold/venv

if [ -f "$CFG" ]; then
  sed -i "/^$START\$/,/^$SLUTT\$/d" "$CFG"
  # dtparam=spi/audio/i2c fjernes fra resten av fila så blokken vår gjelder alene (rev A/B hadde spi=on – må bort)
  sed -i -E '/^dtparam=(spi|audio|i2c_arm|i2c_arm_baudrate)=/d' "$CFG"
  { echo "$START"; cat "$HER/config/config.txt.node"; echo "$SLUTT"; } >> "$CFG"
  echo "config.txt oppdatert ($CFG)"
else
  echo "ADVARSEL: fant ikke config.txt – hopper over" >&2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends python3-gpiozero python3-lgpio python3-pil python3-smbus2 python3-venv \
  i2c-tools fonts-dejavu-core
# raspi-config setter dtparam=i2c_arm=on (står allerede i blokken) og laster i2c-dev; finnes ikke alltid i chroot
if command -v raspi-config >/dev/null 2>&1; then raspi-config nonint do_i2c 0 || true; fi
echo i2c-dev > /etc/modules-load.d/skjold-node-i2c.conf
modprobe i2c-dev 2>/dev/null || true
python3 -m venv --system-site-packages "$VENV"
# luma.oled: SSD1306 128×32 over I²C. smbus2: ADS1115 (potmeteret) leses direkte med registerskriv/-les (ingen Blinka).
"$VENV/bin/pip" install --no-cache-dir "luma.oled==3.14.0" "smbus2>=0.4.3"

install -d /etc/skjold
install -m 0644 "$HER/config/node_pins.json" /etc/skjold/node_pins.json
# I²C/GPIO-tilgang for tjenestebrukeren (standard i Pi OS: gruppene i2c og gpio)
if id skjold >/dev/null 2>&1; then usermod -aG i2c,gpio skjold || true; fi

# Skjold OS: OLED-layouten. Den gamle ST7735-layouten finnes fortsatt (SKJOLD_OS_ARGS=--layout node).
if [ -f /etc/default/skjold-os ] && grep -q '^SKJOLD_OS_ARGS=' /etc/default/skjold-os; then
  sed -i -E 's/^SKJOLD_OS_ARGS=.*/SKJOLD_OS_ARGS=--layout node-oled32/' /etc/default/skjold-os
else
  printf '# Skrevet av skjold/node/driver/installer_node.sh\nSKJOLD_OS_ARGS=--layout node-oled32\n' > /etc/default/skjold-os
fi
bash "$HER/../os/install.sh" || echo "ADVARSEL: Skjold OS ble ikke installert" >&2
echo "Ferdig. Start på nytt og sjekk: i2cdetect -y 1  (skal vise 3c og 48)"
echo "Selvtest: sudo systemctl stop ki-amp skjold-os && $VENV/bin/python $HER/tools/node_selftest.py"
