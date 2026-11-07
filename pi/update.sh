#!/usr/bin/env bash
# Pultforsterker – oppdater en Pi som allerede er installert (uten å kjøre hele install.sh).
#   cd ~/pult-forsterker && git pull && bash pi/update.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
sudo mkdir -p /usr/local/share/ki-amp && (cd "$SRC/.." && pwd) | sudo tee /usr/local/share/ki-amp/src >/dev/null   # kildetreet, for oppdatering fra appen

# Raspberry Pi eller vanlig PC/Proxmox-LXC (pi/install_x86.sh): Pi-steg (I²C, USB-gadget, Blåtann) hoppes over på x86
IS_PI=0; [ -r /proc/device-tree/model ] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null && IS_PI=1

echo "== Programmer og tjenester"
# I2C for OLED (Pi OS leverer det avslått) og moduler via modules-load.d (Debian 13)
[ "$IS_PI" = 0 ] || [ -e /dev/i2c-1 ] || { sudo raspi-config nonint do_i2c 0 2>/dev/null; sudo modprobe i2c-dev 2>/dev/null; } || true
[ "$IS_PI" = 0 ] || [ -f /etc/modules-load.d/ki-amp.conf ] || printf 'dwc2\ni2c-dev\n' | sudo tee /etc/modules-load.d/ki-amp.conf >/dev/null
sudo install -m 755 "$SRC/ki_amp_daemon.py" "$SRC/oled_display.py" "$SRC/oled_small.py" /usr/local/bin/
sudo install -m 644 "$SRC/skjold_homekit.py" "$SRC/skjold_s1f.py" "$SRC/skjold_rec.py" "$SRC/skjold_roomeq.py" "$SRC/skjold_intercom.py" "$SRC/skjold_recognize.py" "$SRC/skjold_doorbell.py" "$SRC/skjold_routines.py" "$SRC/skjold_safeupdate.py" "$SRC/skjold_logos.py" "$SRC/skjold_homelayout.py" "$SRC/skjold_ma.py" "$SRC/skjold_nrk.py" "$SRC/skjold_cloud.py" "$SRC/skjold_programs.py" "$SRC/skjold_speakerprofiles.py" /usr/local/bin/   # Apple Hjem (HomeKit), Skjold S1 rev F
sudo install -m 644 "$SRC/skjold_xtc.py" "$SRC/skjold_spatial.py" "$SRC/skjold_placement.py" /usr/local/bin/ && sudo install -d /usr/local/bin/skjold_sync && sudo install -m 644 "$SRC"/skjold_sync/*.py /usr/local/bin/skjold_sync/   # romlig stereo, synkron multiroom, trådløs sub
sudo install -m 644 "$SRC/skjold_extras.py" /usr/local/bin/   # Roon, Plexamp, backup, automatisk standby, Skjold Wrapped
sudo install -m 644 "$SRC/skjold_smartradio.py" "$SRC/skjold_home_extras.py" "$SRC/skjold_pluginstore.py" "$SRC/skjold_health.py" "$SRC/skjold_libtag.py" "$SRC/skjold_ask.py" "$SRC/skjold_podsum.py" "$SRC/skjold_vinyl.py" /usr/local/bin/   # smart radio, helse, lydtagger, «Spill noe til …», podkastsammendrag
sudo install -m 644 "$SRC/skjold_nfc.py" "$SRC/skjold_hjul.py" "$SRC/skjold_rost.py" /usr/local/bin/   # Skjold Kassett (NFC) og Skjold Hjul (fjernkontroll)

# Intercom, låtgjenkjenning (fpcalc/Chromaprint), dørklokke, rutiner og trygg oppdatering (helsesjekk + tilbakerulling)
command -v fpcalc >/dev/null || sudo apt-get -y install --no-install-recommends libchromaprint-tools >/dev/null 2>&1 || true
sudo install -m 644 "$SRC/skjold-healthcheck.service" /etc/systemd/system/skjold-healthcheck.service
sudo mkdir -p /var/lib/skjold/rollback && sudo systemctl daemon-reload && sudo systemctl enable skjold-healthcheck.service >/dev/null 2>&1 || true
sudo mkdir -p /usr/local/share/ki-amp/logos/nrk /var/lib/ki-amp/logos && sudo install -m 644 "$SRC"/logos/nrk/*.svg "$SRC"/logos/nrk/*.png /usr/local/share/ki-amp/logos/nrk/   # innebygde NRK-logoer for /api/logo
sudo mkdir -p /usr/local/share/ki-amp && sudo install -m 644 "$SRC/config/s1f_pins.yaml" /usr/local/share/ki-amp/s1f_pins.yaml
bash "$SRC/install_webapp.sh"   # ny web-app fra siste skjold-v*-utgivelse (ikke den gamle pi/webapp)
sudo install -m 755 "$SRC/ki-usb-gadget.sh" /usr/local/bin/ki-usb-gadget.sh
sudo mkdir -p /usr/local/share/ki-amp/sounds && sudo install -m 644 "$SRC"/sounds/*.wav /usr/local/share/ki-amp/sounds/   # ferdiginnspilte talemeldinger
sudo install -m 755 "$SRC/tft_screen.py" /usr/local/bin/tft_screen.py
for u in ki-amp.service oled-display.service camilladsp.service shairport-sync.service ki-usb-audio.service ki-squeezelite.service ki-aux1.service ki-aux2.service; do
  sudo install -m 644 "$SRC/$u" /etc/systemd/system/$u
done
sudo install -m 644 "$SRC/shairport-sync.conf" /etc/shairport-sync.conf
PB_CARD=$(sudo grep -oP "^KI_AMP_DSP_PLAYBACK=(plug)?hw:\K[^,]+" /etc/ki-amp.env || echo sndrpihifiberry); sed "s/sndrpihifiberry/$PB_CARD/g" "$SRC/asound.conf" | sudo tee /etc/asound.conf >/dev/null   # per-kilde-nivåer (softvol)
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
if [ "$IS_PI" = 1 ]; then bash "$SRC/ki-bluetooth-setup.sh"; else echo "  hoppes over (ikke Raspberry Pi)"; fi

echo "== Talemeldinger"
bash "$SRC/ki-voice-setup.sh"

echo "== Lyrion-radio (Squeezelite)"
command -v ffmpeg >/dev/null || sudo apt-get -y install --no-install-recommends ffmpeg >/dev/null   # /api/play announce, radioopptak
command -v mount.cifs >/dev/null && command -v smbclient >/dev/null || sudo apt-get -y install --no-install-recommends cifs-utils smbclient >/dev/null   # radioopptak til SMB/NAS
python3 -c "import paho.mqtt" 2>/dev/null || sudo apt-get -y install --no-install-recommends python3-paho-mqtt >/dev/null || true   # MQTT-bro
python3 -c "import pyhap" 2>/dev/null || sudo pip3 install --break-system-packages -q "HAP-python==4.9.2" >/dev/null 2>&1 || true   # Apple Hjem (HomeKit)
python3 -c "import cryptography" 2>/dev/null || sudo apt-get install -y -q python3-cryptography >/dev/null 2>&1 || true   # Skjold Cloud (AES-GCM)
python3 -c "import cairosvg" 2>/dev/null || sudo apt-get install -y -q python3-cairosvg >/dev/null 2>&1 || true   # SVG-logoer → PNG for appene
python3 -c "import mutagen" 2>/dev/null || sudo apt-get install -y -q python3-mutagen >/dev/null 2>&1 || true   # Platesamling (FLAC-tagger)
sudo mkdir -p /usr/local/share/skjold-matter && sudo cp -r "$SRC/matter/package.json" "$SRC/matter/package-lock.json" "$SRC/matter/index.js" "$SRC/matter/mapping.js" "$SRC/matter/skjold-matter.service" "$SRC/matter/install.sh" "$SRC/matter/uninstall.sh" /usr/local/share/skjold-matter/   # Matter-pluginen (installeres når den slås på)
[ -f /var/lib/ki-amp/matter.on ] && { sudo bash /usr/local/share/skjold-matter/install.sh || echo "ADVARSEL: Skjold Matter ble ikke oppdatert" >&2; }
command -v squeezelite >/dev/null || sudo apt-get -y install --no-install-recommends squeezelite >/dev/null
sudo systemctl disable --now squeezelite 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable --now ki-squeezelite
# Kjernetjenestene skal starte ved oppstart. Hver for seg: én manglende enhet skal ikke stoppe de andre
# (på Proxmox/x86 ble enable kjørt før enhetsfilene fantes, så ki-amp og camilladsp startet ikke etter omstart).
sudo systemctl daemon-reload
for s in ki-amp camilladsp oled-display; do
  [ -f "/etc/systemd/system/$s.service" ] && { sudo systemctl enable "$s" >/dev/null 2>&1 || echo "ADVARSEL: kunne ikke slå på $s ved oppstart" >&2; }
done
sudo systemctl restart shairport-sync oled-display ki-amp ki-squeezelite
sleep 2
bash "$SRC/ki-diag.sh" | sed -n '1,12p'
echo "Ferdig."

# Skjold S1 rev F: skjermen (960 × 320) – cage + Chromium med designets tegnekode (pi/skjold_ui)
if [ "${KI_AMP_DISPLAY:-}" = bar958 ] || [ "${KI_AMP_BOARD:-}" = s1f ] || grep -qsE "^KI_AMP_(DISPLAY=bar958|BOARD=s1f)" /etc/ki-amp.env; then
  sudo bash "$(cd "$(dirname "$0")" && pwd)/install_skjold_ui.sh" "${SUDO_USER:-$USER}" || echo "ADVARSEL: skjold-ui ble ikke installert" >&2
fi
