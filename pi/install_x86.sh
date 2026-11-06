#!/usr/bin/env bash
# Skjold Core på en vanlig PC, server eller Proxmox-LXC (Debian 12/13, amd64 eller arm64).
# Lyden går ut på PC-ens eget lydkort (analog linje-ut/hodetelefon/AUX), HDMI eller et USB-lydkort.
#
#   sudo bash pi/install_x86.sh                 # spør ikke – bruker KI_AMP_CARD eller første analoge kort
#   sudo KI_AMP_CARD=PCH KI_AMP_PCM=0 bash pi/install_x86.sh
#
# KI_AMP_CARD   ALSA-kortets id (se «cat /proc/asound/cards», f.eks. PCH, Generic, Device). Standard: første ikke-Loopback-kort.
# KI_AMP_PCM    enhetsnummer på kortet (aplay -l, «device N»). Standard 0 = analog utgang på de fleste Intel/AMD-kort.
# KI_AMP_NAME   navnet i AirPlay/Spotify/Lyrion. Standard «Skjold Core».
# KI_AMP_SPOTIFY=0  uten Spotify Connect.
#
# Kjøres som root (i en LXC) eller med sudo. Trygg å kjøre flere ganger; senere oppdateringer går via appen eller pi/update.sh.
# Forutsetter at snd-aloop er lastet på verten (Proxmox) eller kan lastes her (vanlig PC) – skjold-lxc.sh gjør det på verten.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" = 0 ] || { echo "Kjør som root: sudo bash $0" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
NAME_SEL="${KI_AMP_NAME:-Skjold Core}"; SPOTIFY="${KI_AMP_SPOTIFY:-1}"
case "$(uname -m)" in x86_64|amd64) CDSP_ARCH=amd64 ;; aarch64|arm64) CDSP_ARCH=aarch64 ;; *) echo "Ukjent arkitektur $(uname -m)" >&2; exit 1 ;; esac

echo "== 1/8  Pakker"
apt-get update
apt-get -y install --no-install-recommends sudo ca-certificates curl gnupg unzip git \
  build-essential autoconf automake libtool pkg-config xxd \
  libpopt-dev libconfig-dev libasound2-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev libplist-dev \
  libsodium-dev libavutil-dev libavcodec-dev libavformat-dev uuid-dev libgcrypt-dev libplist-utils libglib2.0-dev \
  alsa-utils python3 python3-pip python3-dbus python3-aiohttp python3-zeroconf python3-websocket python3-numpy \
  python3-pil python3-paho-mqtt ffmpeg dbus kmod
# Ingen python3-gpiozero: daemonen kjører da uten GPIO (som Skjold Core). timezone som Pi-installasjonen
timedatectl set-timezone Europe/Oslo 2>/dev/null || ln -sf /usr/share/zoneinfo/Europe/Oslo /etc/localtime

echo "== 2/8  Lydkort"
if ! grep -q "Loopback" /proc/asound/cards 2>/dev/null; then
  modprobe snd-aloop pcm_substreams=1 2>/dev/null || true
  echo snd-aloop > /etc/modules-load.d/aloop.conf 2>/dev/null || true
fi
grep -q "Loopback" /proc/asound/cards || { echo "FEIL: ALSA-kortet «Loopback» (snd-aloop) finnes ikke. I en LXC må verten laste det: modprobe snd-aloop" >&2; exit 1; }
CARD="${KI_AMP_CARD:-}"
if [ -z "$CARD" ]; then   # første kort som ikke er Loopback; foretrekk et analogt/HDA-kort
  CARD=$(awk -F'[][]' '/^ *[0-9]+ \[/ {gsub(/ /,"",$2); print $2}' /proc/asound/cards | grep -v '^Loopback$' | head -n1)
  for c in PCH Generic Intel HDMI; do grep -q "\[$c *\]" /proc/asound/cards && { [ "$c" = HDMI ] || { CARD=$c; break; }; }; done
fi
[ -n "$CARD" ] || { echo "FEIL: fant ikke noe lydkort (aplay -l). Er /dev/snd sendt inn i containeren?" >&2; exit 1; }
PCM="${KI_AMP_PCM:-0}"
PB_DEV="plughw:$CARD,$PCM"
echo "  Utgang: $PB_DEV"
aplay -l | sed 's/^/  /' || true

echo "== 3/8  CamillaDSP"
CDSP_VER=v2.0.3
T="$(mktemp -d)"
curl -fsSL -o "$T/c.tar.gz" "https://github.com/HEnquist/camilladsp/releases/download/${CDSP_VER}/camilladsp-linux-${CDSP_ARCH}.tar.gz"
tar -xzf "$T/c.tar.gz" -C /usr/local/bin camilladsp && chmod 755 /usr/local/bin/camilladsp
mkdir -p /etc/camilladsp
sed -e "s#hw:sndrpihifiberry#$PB_DEV#" -e "/playback:/s/S32LE/S16LE/" "$SRC/camilladsp.yml" > /etc/camilladsp/config.yml
install -m 644 "$SRC/camilladsp.service" /etc/systemd/system/camilladsp.service

echo "== 4/8  /etc/ki-amp.env (Skjold Core uten GPIO)"
[ -f /etc/ki-amp.env ] || install -m 600 "$SRC/ki-amp.env" /etc/ki-amp.env
setenv() { sed -i "/^$1=/d" /etc/ki-amp.env; echo "$1=$2" >> /etc/ki-amp.env; }
setenv KI_AMP_BOARD node
setenv KI_AMP_NODE_GPIO 0
setenv KI_AMP_PRODUCT core
setenv KI_AMP_DISPLAY none
setenv KI_AMP_DSP_PLAYBACK "$PB_DEV"
setenv KI_AMP_DSP_FORMAT S16LE
setenv KI_AMP_NAME "$NAME_SEL"
setenv KI_AMP_SPOTIFY "$SPOTIFY"
setenv KI_AMP_PLATFORM x86
sed "s/sndrpihifiberry/$CARD/g" "$SRC/asound.conf" > /etc/asound.conf

echo "== 5/8  NQPTP + Shairport Sync (AirPlay 2)"
if ! command -v nqptp >/dev/null; then
  B="$(mktemp -d)" && git clone -q https://github.com/mikebrady/nqptp.git "$B/nqptp"
  (cd "$B/nqptp" && autoreconf -fi >/dev/null 2>&1 && ./configure -q --with-systemd-startup && make -s -j"$(nproc)" && make -s install)
fi
systemctl enable --now nqptp || true
if ! shairport-sync -V 2>/dev/null | grep -qi airplay2; then
  B="$(mktemp -d)" && git clone -q https://github.com/mikebrady/shairport-sync.git "$B/sps"
  (cd "$B/sps" && autoreconf -fi >/dev/null 2>&1 && ./configure -q --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl \
     --with-airplay-2 --with-metadata --with-pipe --with-dbus-interface && make -s -j"$(nproc)" && make -s install)
fi
id shairport-sync >/dev/null 2>&1 || useradd -r -M -g audio -s /usr/sbin/nologin shairport-sync

echo "== 6/8  Lyrion + Squeezelite"
apt-get -y install --no-install-recommends squeezelite
systemctl disable --now squeezelite 2>/dev/null || true
install -m 644 "$SRC/ki-squeezelite.service" /etc/systemd/system/ki-squeezelite.service
if [ -f "$SRC/install_lyrion.sh" ] && ! systemctl list-unit-files 2>/dev/null | grep -q '^lyrionmusicserver'; then
  bash "$SRC/install_lyrion.sh" || echo "ADVARSEL: Lyrion ble ikke installert – prøv: bash pi/install_lyrion.sh" >&2
fi

echo "== 7/8  Spotify Connect"
if [ "$SPOTIFY" = 1 ]; then
  install -d -m 755 /usr/share/keyrings
  curl -fsSL https://dtcooper.github.io/raspotify/key.asc | gpg --dearmor --yes -o /usr/share/keyrings/raspotify-archive-keyrings.gpg
  echo 'deb [signed-by=/usr/share/keyrings/raspotify-archive-keyrings.gpg] https://dtcooper.github.io/raspotify raspotify main' \
    > /etc/apt/sources.list.d/raspotify.list
  if apt-get update && apt-get -y install --no-install-recommends raspotify; then
    systemctl disable --now raspotify 2>/dev/null || true
    install -m 755 "$SRC/ki-spotify-event" /usr/local/bin/ki-spotify-event
    install -m 644 "$SRC/ki-spotify.service" /etc/systemd/system/ki-spotify.service
    mkdir -p /var/cache/ki-spotify
    systemctl daemon-reload && systemctl enable ki-spotify
  else
    echo "ADVARSEL: raspotify/librespot kunne ikke installeres – Spotify Connect er av"; setenv KI_AMP_SPOTIFY 0
  fi
fi

echo "== 8/8  Daemon, web-app og tjenester (pi/update.sh)"
install -m 755 "$SRC/oled_display.py" /usr/local/bin/oled_display.py   # bare metadata-tjeneste (KI_AMP_DISPLAY=none)
install -m 644 "$SRC/oled-display.service" /etc/systemd/system/oled-display.service
systemctl daemon-reload
systemctl enable camilladsp shairport-sync ki-squeezelite oled-display ki-amp 2>/dev/null || true
systemctl restart camilladsp || true
bash "$SRC/update.sh"
systemctl enable --now avahi-daemon 2>/dev/null || true
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "Ferdig. Skjold Core spiller på $PB_DEV."
echo "  Web-UI:  http://${IP:-<ip>}:8765"
echo "  AirPlay: «$NAME_SEL»   Spotify Connect: «$NAME_SEL»   Lyrion: http://${IP:-<ip>}:9000"
echo "  Test lyd: speaker-test -D $PB_DEV -c 2 -t sine -l 1"
