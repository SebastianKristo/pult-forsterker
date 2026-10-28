#!/usr/bin/env bash
# KI Pultforsterker v2 – installasjon på Raspberry Pi OS Lite (64-bit, Bookworm+)
# Kjør som vanlig bruker:  bash install.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"

echo "== 1/9  Oppdaterer systemet"
sudo apt-get update && sudo apt-get -y full-upgrade

echo "== 2/9  config.txt: I2S-DAC, I2C, USB-gadget (dwc2), serial console av"
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$CFG"
for line in 'dtoverlay=hifiberry-dac' 'dtparam=i2c_arm=on' 'dtoverlay=dwc2,dr_mode=peripheral' 'enable_uart=0'; do
  grep -qxF "$line" "$CFG" || echo "$line" | sudo tee -a "$CFG"
done
sudo sed -i 's/ console=serial0,115200//' /boot/firmware/cmdline.txt 2>/dev/null || true
grep -q '^dwc2' /etc/modules || echo dwc2 | sudo tee -a /etc/modules
sudo raspi-config nonint do_serial_hw 1 2>/dev/null || true   # frigjør GPIO 14/15 til X9C

echo "== 3/9  Pakker"
sudo apt-get -y install --no-install-recommends \
  build-essential git autoconf automake libtool pkg-config \
  libpopt-dev libconfig-dev libasound2-dev avahi-daemon libavahi-client-dev \
  libssl-dev libsoxr-dev libplist-dev libsodium-dev libavutil-dev libavcodec-dev \
  libavformat-dev uuid-dev libgcrypt-dev xxd alsa-utils \
  bluez bluez-alsa-utils python3-dbus \
  python3-pip python3-pil python3-smbus i2c-tools python3-aiohttp python3-zeroconf python3-gpiozero python3-websocket curl

echo "== 4/9  ALSA dmix → loopback → CamillaDSP (loudness + digitalt volum) → DAC"
sudo install -m 644 "$SRC/asound.conf" /etc/asound.conf
echo snd-aloop | sudo tee /etc/modules-load.d/aloop.conf >/dev/null
echo 'options snd-aloop index=5 pcm_substreams=1' | sudo tee /etc/modprobe.d/aloop.conf >/dev/null
sudo modprobe snd-aloop index=5 pcm_substreams=1 || true
CDSP_VER=v2.0.3
cd /tmp && rm -f camilladsp.tar.gz && curl -L -o camilladsp.tar.gz \
  "https://github.com/HEnquist/camilladsp/releases/download/${CDSP_VER}/camilladsp-linux-aarch64.tar.gz"
sudo tar -xzf camilladsp.tar.gz -C /usr/local/bin camilladsp && sudo chmod 755 /usr/local/bin/camilladsp
sudo mkdir -p /etc/camilladsp
[ -f /etc/camilladsp/config.yml ] || sudo install -m 644 "$SRC/camilladsp.yml" /etc/camilladsp/config.yml
sudo install -m 644 "$SRC/camilladsp.service" /etc/systemd/system/camilladsp.service
sudo systemctl daemon-reload && sudo systemctl enable --now camilladsp

echo "== 5/9  NQPTP + Shairport Sync (AirPlay 2)"
cd /tmp && rm -rf nqptp && git clone https://github.com/mikebrady/nqptp.git
cd nqptp && autoreconf -fi && ./configure --with-systemd-startup && make -j"$(nproc)" && sudo make install
sudo systemctl enable --now nqptp
cd /tmp && rm -rf shairport-sync && git clone https://github.com/mikebrady/shairport-sync.git
cd shairport-sync && autoreconf -fi
./configure --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl \
            --with-systemd --with-airplay-2 --with-metadata --with-pipe
make -j"$(nproc)" && sudo make install
sudo install -m 644 "$SRC/shairport-sync.conf" /etc/shairport-sync.conf
sudo systemctl enable --now shairport-sync

echo "== 6/9  Bluetooth A2DP-mottak (bluealsa)"
sudo sed -i 's/^#\?Class = .*/Class = 0x200414/; s/^#\?DiscoverableTimeout = .*/DiscoverableTimeout = 120/' /etc/bluetooth/main.conf
grep -q '^Class' /etc/bluetooth/main.conf || printf '[General]\nClass = 0x200414\nDiscoverableTimeout = 120\n' | sudo tee -a /etc/bluetooth/main.conf
sudo mkdir -p /etc/systemd/system/bluealsa.service.d
printf '[Service]\nExecStart=\nExecStart=/usr/bin/bluealsa -p a2dp-sink\n' | sudo tee /etc/systemd/system/bluealsa.service.d/override.conf
sudo install -m 644 "$SRC/bluealsa-aplay.service" /etc/systemd/system/bluealsa-aplay.service
sudo hostnamectl set-hostname pultamp 2>/dev/null || true
printf 'system-alias Pultforsterker\nagent NoInputNoOutput\ndefault-agent\npairable on\n' | sudo bluetoothctl >/dev/null 2>&1 || true
sudo systemctl enable --now bluealsa bluealsa-aplay

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
sudo systemctl daemon-reload
sudo systemctl enable --now oled-display ki-amp

echo
echo "Ferdig – start på nytt (sudo reboot)."
echo "  AirPlay: «Pultforsterker» på iPhone/Mac   Bluetooth: hold AIRPLAY 2 s, så parr fra telefonen"
echo "  USB: koble PC til USB-C bak – «UAC2 Gadget» dukker opp som lydenhet"
echo "  API: http://$(hostname -I | awk '{print $1}'):8765/api/status"
