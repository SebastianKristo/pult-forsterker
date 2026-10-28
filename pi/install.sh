#!/usr/bin/env bash
# KI Pultforsterker v2 – installasjon på Raspberry Pi OS Lite (64-bit, Bookworm+)
# Kjør som vanlig bruker:  bash install.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
# KI_AMP_OUT=dac        : I2S-DAC / hovedkort (standard)
# KI_AMP_OUT=headphones : TEST uten hovedkort – lyd ut på Pi 4 sin 3,5 mm-kontakt (bcm2835 Headphones, 16 bit)
OUT="${KI_AMP_OUT:-dac}"
if [ "$OUT" = headphones ]; then PB_CARD=Headphones; PB_DEV="plughw:Headphones"; PB_FMT=S16LE; else PB_CARD=sndrpihifiberry; PB_DEV="hw:sndrpihifiberry"; PB_FMT=S32LE; fi

echo "== 1/9  Oppdaterer systemet"
sudo apt-get update && sudo apt-get -y full-upgrade
sudo timedatectl set-timezone Europe/Oslo 2>/dev/null || true

echo "== 2/9  config.txt: I2S-DAC, I2C, USB-gadget (dwc2), serial console av"
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
if [ "$OUT" = headphones ]; then
  grep -qxF 'dtparam=audio=on' "$CFG" || echo 'dtparam=audio=on' | sudo tee -a "$CFG"
  sudo sed -i 's/^dtoverlay=hifiberry-dac/#dtoverlay=hifiberry-dac/' "$CFG"
  LINES='dtparam=i2c_arm=on dtoverlay=spi0-1cs dtoverlay=dwc2,dr_mode=peripheral enable_uart=0'
else
  sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$CFG"
  LINES='dtoverlay=hifiberry-dac dtparam=i2c_arm=on dtoverlay=spi0-1cs dtoverlay=dwc2,dr_mode=peripheral enable_uart=0'
fi
for line in $LINES; do
  grep -qxF "#$line" "$CFG" && { echo "  hopper over $line (kommentert ut for hånd)"; continue; }
  grep -qxF "$line" "$CFG" || echo "$line" | sudo tee -a "$CFG"
done
sudo sed -i 's/ console=serial0,115200//' /boot/firmware/cmdline.txt 2>/dev/null || true
grep -q '^dwc2' /etc/modules || echo dwc2 | sudo tee -a /etc/modules
grep -q '^i2c-dev' /etc/modules || echo i2c-dev | sudo tee -a /etc/modules   # /dev/i2c-1 for OLED
sudo raspi-config nonint do_serial_hw 1 2>/dev/null || true   # frigjør GPIO 14/15 til X9C

echo "== 3/9  Pakker"
sudo apt-get -y install --no-install-recommends \
  build-essential git autoconf automake libtool pkg-config \
  libpopt-dev libconfig-dev libasound2-dev avahi-daemon libavahi-client-dev \
  libssl-dev libsoxr-dev libplist-dev libsodium-dev libavutil-dev libavcodec-dev \
  libavformat-dev uuid-dev libgcrypt-dev xxd alsa-utils libplist-utils libglib2.0-dev \
  bluez bluez-alsa-utils python3-dbus \
  python3-pip python3-pil python3-smbus i2c-tools python3-aiohttp python3-zeroconf python3-gpiozero python3-websocket python3-spidev curl

echo "== 4/9  ALSA dmix → loopback → CamillaDSP (loudness + digitalt volum) → DAC"
sed "s/sndrpihifiberry/$PB_CARD/g" "$SRC/asound.conf" | sudo tee /etc/asound.conf >/dev/null
echo snd-aloop | sudo tee /etc/modules-load.d/aloop.conf >/dev/null
echo 'options snd-aloop index=5 pcm_substreams=1' | sudo tee /etc/modprobe.d/aloop.conf >/dev/null
sudo modprobe snd-aloop index=5 pcm_substreams=1 || true
CDSP_VER=v2.0.3
cd /tmp && rm -f camilladsp.tar.gz && curl -L -o camilladsp.tar.gz \
  "https://github.com/HEnquist/camilladsp/releases/download/${CDSP_VER}/camilladsp-linux-aarch64.tar.gz"
sudo tar -xzf camilladsp.tar.gz -C /usr/local/bin camilladsp && sudo chmod 755 /usr/local/bin/camilladsp
sudo mkdir -p /etc/camilladsp
sed -e "s#hw:sndrpihifiberry#$PB_DEV#" -e "/playback:/s/S32LE/$PB_FMT/" "$SRC/camilladsp.yml" | sudo tee /etc/camilladsp/config.yml >/dev/null
sudo install -m 644 "$SRC/camilladsp.service" /etc/systemd/system/camilladsp.service
sudo systemctl daemon-reload && sudo systemctl enable --now camilladsp

echo "== 5/9  NQPTP + Shairport Sync (AirPlay 2)"
cd /tmp && rm -rf nqptp && git clone https://github.com/mikebrady/nqptp.git
cd nqptp && autoreconf -fi && ./configure --with-systemd-startup && make -j"$(nproc)" && sudo make install
sudo systemctl enable --now nqptp
cd /tmp && rm -rf shairport-sync && git clone https://github.com/mikebrady/shairport-sync.git
cd shairport-sync && autoreconf -fi
./configure --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl \
            --with-systemd --with-airplay-2 --with-metadata --with-pipe --with-dbus-interface
make -j"$(nproc)" && sudo make install
sudo install -m 644 "$SRC/shairport-sync.conf" /etc/shairport-sync.conf
sudo systemctl reload dbus 2>/dev/null || true   # D-Bus-policy fra make install
id shairport-sync >/dev/null 2>&1 || sudo useradd -r -M -g audio -s /usr/sbin/nologin shairport-sync
sudo install -m 644 "$SRC/shairport-sync.service" /etc/systemd/system/shairport-sync.service   # 5.x legger ikke inn unit selv
sudo systemctl daemon-reload && sudo systemctl enable --now shairport-sync

echo "== 6/9  Bluetooth A2DP-mottak (bluealsa + parring uten PIN)"
sudo hostnamectl set-hostname pultamp 2>/dev/null || true
bash "$SRC/ki-bluetooth-setup.sh"

echo "== 6b    Music Assistant (Squeezelite / Slimproto)"
sudo apt-get -y install --no-install-recommends squeezelite >/dev/null
sudo systemctl disable --now squeezelite 2>/dev/null || true      # Debians egen tjeneste – vi bruker ki-squeezelite
sudo install -m 644 "$SRC/ki-squeezelite.service" /etc/systemd/system/ki-squeezelite.service
sudo systemctl daemon-reload && sudo systemctl enable --now ki-squeezelite

echo "== 7/9  USB-lyd (Pi-en blir et USB-lydkort for PC-en via USB-C bak)"
sudo install -m 755 "$SRC/ki-usb-gadget.sh" /usr/local/bin/ki-usb-gadget.sh
sudo install -m 644 "$SRC/ki-usb-audio.service" /etc/systemd/system/ki-usb-audio.service
sudo systemctl enable ki-usb-audio

echo "== 8/9  OLED (SSD1309 2,42\")"
sudo pip3 install --break-system-packages luma.oled
sudo install -m 755 "$SRC/oled_display.py" /usr/local/bin/oled_display.py
sudo install -m 644 "$SRC/oled-display.service" /etc/systemd/system/oled-display.service

echo "== 9/9  KI-daemon (knapper, relé, volum, LED, HTTP-API, mDNS)"
sudo install -m 755 "$SRC/ki_amp_daemon.py" /usr/local/bin/ki_amp_daemon.py
sudo install -m 644 "$SRC/ki-amp.service" /etc/systemd/system/ki-amp.service
[ -f /etc/ki-amp.env ] || sudo install -m 600 "$SRC/ki-amp.env" /etc/ki-amp.env
if [ "$OUT" = headphones ]; then
  sudo sed -i -e "s#^KI_AMP_DSP_PLAYBACK=.*#KI_AMP_DSP_PLAYBACK=$PB_DEV#" -e '/^KI_AMP_DSP_FORMAT=/d' /etc/ki-amp.env
  echo "KI_AMP_DSP_FORMAT=$PB_FMT" | sudo tee -a /etc/ki-amp.env >/dev/null
  echo "== TESTMODUS: lyd ut på 3,5 mm-kontakten. Sett volum på jacken: amixer -c Headphones sset Headphone 100%"
fi
sudo systemctl daemon-reload
sudo systemctl enable --now oled-display ki-amp

echo
echo "Ferdig – start på nytt (sudo reboot)."
echo "  AirPlay: «Pultforsterker» på iPhone/Mac   Bluetooth: hold AIRPLAY 2 s, så parr fra telefonen"
echo "  USB: koble PC til USB-C bak – «UAC2 Gadget» dukker opp som lydenhet"
echo "  API: http://$(hostname -I | awk '{print $1}'):8765/api/status"
