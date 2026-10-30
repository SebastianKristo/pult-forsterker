#!/usr/bin/env bash
# Pultforsterker v2 – installasjon på Raspberry Pi OS Lite (64-bit, Bookworm+)
# Kjør som vanlig bruker:  bash install.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
# KI_AMP_OUT=dac        : I2S-DAC / hovedkort (standard)
# KI_AMP_OUT=headphones : TEST uten hovedkort – lyd ut på Pi 4 sin 3,5 mm-kontakt (bcm2835 Headphones, 16 bit)
# KI_AMP_BOARD=main     : hovedkort rev B (PCM5102A + PCM1808 på I2S, lydkortet heter «pultamp», TFT/touch mulig)
# KI_AMP_DISPLAY=tft    : 2,8" SPI TFT (KI_AMP_TFT=ili9341|st7789v) med touch i stedet for OLED
OUT="${KI_AMP_OUT:-dac}"; BOARD_SEL="${KI_AMP_BOARD:-}"; DISPLAY_SEL="${KI_AMP_DISPLAY:-oled}"; TFT_SEL="${KI_AMP_TFT:-ili9341}"
if [ "$OUT" = headphones ]; then PB_CARD=Headphones; PB_DEV="plughw:Headphones"; PB_FMT=S16LE
elif [ "$BOARD_SEL" = main ]; then PB_CARD=pultamp; PB_DEV="hw:pultamp"; PB_FMT=S32LE
else PB_CARD=sndrpihifiberry; PB_DEV="hw:sndrpihifiberry"; PB_FMT=S32LE; fi

echo "== 1/9  Oppdaterer systemet"
sudo apt-get update && sudo apt-get -y full-upgrade
sudo timedatectl set-timezone Europe/Oslo 2>/dev/null || true

echo "== 2/9  config.txt: I2S-DAC, I2C, USB-gadget (dwc2), serial console av"
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
if [ "$OUT" = headphones ]; then
  grep -qxF 'dtparam=audio=on' "$CFG" || echo 'dtparam=audio=on' | sudo tee -a "$CFG"
  sudo sed -i 's/^dtoverlay=hifiberry-dac/#dtoverlay=hifiberry-dac/' "$CFG"
  LINES='dtparam=i2c_arm=on dtoverlay=spi0-1cs,no_miso dtoverlay=dwc2,dr_mode=peripheral enable_uart=0'
elif [ "$BOARD_SEL" = main ]; then
  sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/; s/^dtoverlay=hifiberry-dac$/#dtoverlay=hifiberry-dac/; s/^dtoverlay=spi0-1cs,no_miso$/#dtoverlay=spi0-1cs,no_miso/' "$CFG"
  sudo apt-get -y install --no-install-recommends device-tree-compiler >/dev/null
  dtc -@ -I dts -O dtb -o /tmp/ki-pultamp-i2s.dtbo "$SRC/ki-pultamp-i2s.dts" && sudo install -m 644 /tmp/ki-pultamp-i2s.dtbo /boot/firmware/overlays/
  LINES='dtoverlay=ki-pultamp-i2s dtparam=i2c_arm=on dtparam=spi=on dtoverlay=dwc2,dr_mode=peripheral enable_uart=0'
  if [ "$DISPLAY_SEL" = tft ]; then   # TFT på SPI0 CE0 (DC 5, RST 6), touch på CE1 (IRQ 17)
    sudo sed -i '/^dtoverlay=fbtft,/d; /^dtoverlay=ads7846,/d' "$CFG"
    echo "dtoverlay=fbtft,spi0-0,$TFT_SEL,dc_pin=5,reset_pin=6,rotate=90,speed=32000000" | sudo tee -a "$CFG"
    echo "dtoverlay=ads7846,cs=1,penirq=17,penirq_pull=2,speed=50000,keep_vref_on=1,swapxy=1,xmin=200,xmax=3900,ymin=200,ymax=3900,pmax=255,xohms=150" | sudo tee -a "$CFG"
  fi
else
  sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$CFG"
  LINES='dtoverlay=hifiberry-dac dtparam=i2c_arm=on dtoverlay=spi0-1cs,no_miso dtoverlay=dwc2,dr_mode=peripheral enable_uart=0'
fi
sudo sed -i 's/^dtoverlay=spi0-1cs$/dtoverlay=spi0-1cs,no_miso/' "$CFG"   # GPIO 9 (MISO) brukes til BT-LED på hovedkortet
for line in $LINES; do
  # bare dwc2 respekteres hvis den er kommentert ut for hånd – Pi OS leverer «#dtparam=i2c_arm=on» som standard
  case "$line" in dtoverlay=dwc2*) grep -qxF "#$line" "$CFG" && { echo "  hopper over $line (kommentert ut for hånd)"; continue; } ;; esac
  grep -qxF "$line" "$CFG" || echo "$line" | sudo tee -a "$CFG"
done
sudo sed -i 's/ console=serial0,115200//' /boot/firmware/cmdline.txt 2>/dev/null || true
# /etc/modules leses ikke lenger på Debian 13 – bruk modules-load.d
printf 'dwc2\ni2c-dev\n' | sudo tee /etc/modules-load.d/ki-amp.conf >/dev/null
sudo raspi-config nonint do_i2c 0 2>/dev/null || true   # /dev/i2c-1 for OLED
sudo modprobe i2c-dev 2>/dev/null || true
sudo raspi-config nonint do_serial_hw 1 2>/dev/null || true   # frigjør GPIO 14/15 til X9C

echo "== 3/9  Pakker"
sudo apt-get -y install --no-install-recommends \
  build-essential git autoconf automake libtool pkg-config \
  libpopt-dev libconfig-dev libasound2-dev avahi-daemon libavahi-client-dev \
  libssl-dev libsoxr-dev libplist-dev libsodium-dev libavutil-dev libavcodec-dev \
  libavformat-dev uuid-dev libgcrypt-dev xxd alsa-utils libplist-utils libglib2.0-dev \
  bluez bluez-alsa-utils python3-dbus \
  python3-pip python3-pil python3-smbus python3-smbus2 python3-evdev python3-numpy i2c-tools python3-aiohttp python3-zeroconf python3-gpiozero python3-websocket python3-spidev curl

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
B="$(mktemp -d)" && cd "$B" && git clone https://github.com/mikebrady/nqptp.git
cd nqptp && autoreconf -fi && ./configure --with-systemd-startup && make -j"$(nproc)" && sudo make install
sudo systemctl enable --now nqptp
B="$(mktemp -d)" && cd "$B" && git clone https://github.com/mikebrady/shairport-sync.git
cd shairport-sync && autoreconf -fi
./configure --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl \
            --with-airplay-2 --with-metadata --with-pipe --with-dbus-interface
make -j"$(nproc)" && sudo make install
sudo install -m 644 "$SRC/shairport-sync.conf" /etc/shairport-sync.conf
sudo install -m 644 "$SRC/shairport-sync-dbus.conf" /etc/dbus-1/system.d/shairport-sync-dbus.conf
sudo systemctl reload dbus 2>/dev/null || true
sudo systemctl reload dbus 2>/dev/null || true   # D-Bus-policy fra make install
id shairport-sync >/dev/null 2>&1 || sudo useradd -r -M -g audio -s /usr/sbin/nologin shairport-sync
sudo install -m 644 "$SRC/shairport-sync.service" /etc/systemd/system/shairport-sync.service   # 5.x legger ikke inn unit selv
sudo systemctl daemon-reload && sudo systemctl enable --now shairport-sync

echo "== 6/9  Bluetooth A2DP-mottak (bluealsa + parring uten PIN)"
OLDHOST=$(hostname)
sudo hostnamectl set-hostname pultamp 2>/dev/null || true
# /etc/hosts må kjenne det nye navnet, ellers klager sudo «unable to resolve host»
if grep -q "^127.0.1.1" /etc/hosts; then
  sudo sed -i "s/^127.0.1.1.*/127.0.1.1\tpultamp/" /etc/hosts 2>/dev/null
else
  echo -e "127.0.1.1\tpultamp" | sudo tee -a /etc/hosts >/dev/null 2>&1
fi
bash "$SRC/ki-bluetooth-setup.sh"

echo "== 6b    Lyrion-radio (Squeezelite)"
sudo apt-get -y install --no-install-recommends squeezelite >/dev/null
sudo systemctl disable --now squeezelite 2>/dev/null || true      # Debians egen tjeneste – vi bruker ki-squeezelite
sudo install -m 644 "$SRC/ki-squeezelite.service" /etc/systemd/system/ki-squeezelite.service
sudo systemctl daemon-reload && sudo systemctl enable --now ki-squeezelite

echo "== Talemeldinger"
bash "$SRC/ki-voice-setup.sh"
sudo mkdir -p /usr/local/share/ki-amp/sounds && sudo install -m 644 "$SRC"/sounds/*.wav /usr/local/share/ki-amp/sounds/   # ferdiginnspilte talemeldinger

echo "== 7/9  USB-lyd (Pi-en blir et USB-lydkort for PC-en via USB-C bak)"
sudo install -m 755 "$SRC/ki-usb-gadget.sh" /usr/local/bin/ki-usb-gadget.sh
sudo install -m 644 "$SRC/ki-usb-audio.service" /etc/systemd/system/ki-usb-audio.service
sudo install -m 644 "$SRC/ki-aux1.service" "$SRC/ki-aux2.service" /etc/systemd/system/
if [ "$BOARD_SEL" = main ]; then sudo systemctl enable ki-aux1 ki-aux2; fi   # AUX 1 (I2S-ADC) og AUX 2 (USB-kodek) bare på hovedkortet
sudo systemctl enable ki-usb-audio

echo "== 8/9  OLED (SSD1309 2,42\")"
sudo pip3 install --break-system-packages luma.oled
sudo install -m 755 "$SRC/oled_display.py" /usr/local/bin/oled_display.py
sudo install -m 644 "$SRC/oled_small.py" "$SRC/tft_screen.py" /usr/local/bin/
sudo install -m 644 "$SRC/oled-display.service" /etc/systemd/system/oled-display.service

echo "== 9/9  KI-daemon (knapper, relé, volum, LED, HTTP-API, mDNS)"
sudo install -m 755 "$SRC/ki_amp_daemon.py" /usr/local/bin/ki_amp_daemon.py
sudo install -m 644 "$SRC/ki-amp.service" /etc/systemd/system/ki-amp.service
[ -f /etc/ki-amp.env ] || sudo install -m 600 "$SRC/ki-amp.env" /etc/ki-amp.env
if [ "$OUT" = headphones ]; then
  sudo sed -i -e "s#^KI_AMP_DSP_PLAYBACK=.*#KI_AMP_DSP_PLAYBACK=$PB_DEV#" -e '/^KI_AMP_DSP_FORMAT=/d' /etc/ki-amp.env
  echo "KI_AMP_DSP_FORMAT=$PB_FMT" | sudo tee -a /etc/ki-amp.env >/dev/null
  sudo sed -i 's/^KI_AMP_BOARD=.*/KI_AMP_BOARD=test/' /etc/ki-amp.env      # testbenk-pinner (knapper/LED rett på Pi-en)
elif [ "$BOARD_SEL" = main ]; then
  sudo sed -i -e "s#^KI_AMP_DSP_PLAYBACK=.*#KI_AMP_DSP_PLAYBACK=$PB_DEV#" -e 's/^KI_AMP_BOARD=.*/KI_AMP_BOARD=main/' -e "s/^KI_AMP_DISPLAY=.*/KI_AMP_DISPLAY=$DISPLAY_SEL/" -e "s/^KI_AMP_TFT=.*/KI_AMP_TFT=$TFT_SEL/" -e 's/^KI_AMP_LEVELS=.*/KI_AMP_LEVELS=1/' /etc/ki-amp.env
  echo "== TESTMODUS: lyd ut på 3,5 mm-kontakten. Sett volum på jacken: amixer -c Headphones sset PCM 100%"
fi
sudo systemctl daemon-reload
sudo systemctl enable --now oled-display ki-amp

echo
echo "Ferdig – start på nytt (sudo reboot)."
echo "  AirPlay: «Pultforsterker» på iPhone/Mac   Bluetooth: hold AIRPLAY 2 s, så parr fra telefonen"
echo "  USB: koble PC til USB-C bak – «UAC2 Gadget» dukker opp som lydenhet"
echo "  API: http://$(hostname -I | awk '{print $1}'):8765/api/status"
