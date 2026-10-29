#!/usr/bin/env bash
# Pultforsterker – oppdater en Pi som allerede er installert (uten å kjøre hele install.sh).
#   cd ~/pult-forsterker && git pull && bash pi/update.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"

echo "== Programmer og tjenester"
# I2C for OLED (Pi OS leverer det avslått) og moduler via modules-load.d (Debian 13)
[ -e /dev/i2c-1 ] || { sudo raspi-config nonint do_i2c 0 2>/dev/null; sudo modprobe i2c-dev 2>/dev/null; } || true
[ -f /etc/modules-load.d/ki-amp.conf ] || printf 'dwc2\ni2c-dev\n' | sudo tee /etc/modules-load.d/ki-amp.conf >/dev/null
sudo install -m 755 "$SRC/ki_amp_daemon.py" "$SRC/oled_display.py" "$SRC/oled_small.py" /usr/local/bin/
sudo install -m 755 "$SRC/ki-usb-gadget.sh" /usr/local/bin/ki-usb-gadget.sh
for u in ki-amp.service oled-display.service camilladsp.service shairport-sync.service ki-usb-audio.service ki-squeezelite.service; do
  sudo install -m 644 "$SRC/$u" /etc/systemd/system/$u
done
sudo install -m 644 "$SRC/shairport-sync.conf" /etc/shairport-sync.conf
sudo install -m 644 "$SRC/shairport-sync-dbus.conf" /etc/dbus-1/system.d/shairport-sync-dbus.conf
sudo systemctl reload dbus 2>/dev/null || true
# nye nøkler i ki-amp.env legges til uten å røre dine verdier
while IFS= read -r line; do
  k="${line%%=*}"; [[ "$line" =~ ^KI_AMP_[A-Z_]+= ]] || continue
  sudo grep -q "^$k=" /etc/ki-amp.env || echo "$line" | sudo tee -a /etc/ki-amp.env >/dev/null
done < "$SRC/ki-amp.env"

echo "== Shairport Sync med fjernkontroll (D-Bus)"
if ! shairport-sync -V 2>&1 | grep -qi dbus; then
  sudo apt-get -y install --no-install-recommends libglib2.0-dev >/dev/null
  B="$(mktemp -d)" && cd "$B" && git clone -q https://github.com/mikebrady/shairport-sync.git && cd shairport-sync
  autoreconf -fi >/dev/null 2>&1
  ./configure -q --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl \
    --with-airplay-2 --with-metadata --with-pipe --with-dbus-interface
  make -s -j"$(nproc)" && sudo make -s install
  sudo systemctl reload dbus || true
  cd "$SRC"
else
  echo "  allerede bygget med D-Bus"
fi

echo "== Bluetooth"
bash "$SRC/ki-bluetooth-setup.sh"

echo "== Talemeldinger"
bash "$SRC/ki-voice-setup.sh"

echo "== Lyrion-radio (Squeezelite)"
command -v squeezelite >/dev/null || sudo apt-get -y install --no-install-recommends squeezelite >/dev/null
sudo systemctl disable --now squeezelite 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable --now ki-squeezelite
sudo systemctl restart shairport-sync oled-display ki-amp ki-squeezelite
sleep 2
bash "$SRC/ki-diag.sh" | sed -n '1,12p'
echo "Ferdig."
