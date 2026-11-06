#!/usr/bin/env bash
# Skjold – Snapcast (beta): synkron lyd til flere høyttalere.
#   Hovedenheten:  sudo bash pi/install_snapcast.sh server
#   Andre rom:     sudo bash pi/install_snapcast.sh client <hovedenhetens IP eller navn>
# Serveren leser lyden fra en FIFO (/tmp/snapfifo). Lyrion/Squeezelite på hovedenheten kan skrive dit med
#   KI_AMP_SNAP_FIFO=1 (squeezelite -o - | snapfifo), se docs. Klientene spiller gjennom ALSA-enheten «default».
set -euo pipefail
ROLE="${1:-}"; SERVER="${2:-}"
case "$ROLE" in
  server)
    apt-get update -qq && apt-get install -y -qq snapserver
    cat > /etc/snapserver.conf <<CONF
[stream]
source = pipe:///tmp/snapfifo?name=Skjold&sampleformat=48000:16:2&mode=create
[http]
enabled = true
[tcp]
enabled = true
CONF
    systemctl enable --now snapserver
    systemctl restart snapserver
    echo "Snapserver kjører. JSON-RPC på port 1705, web på 1780." ;;
  client)
    [ -n "$SERVER" ] || { echo "Bruk: $0 client <server>"; exit 1; }
    apt-get update -qq && apt-get install -y -qq snapclient
    echo "SNAPCLIENT_OPTS=\"--host $SERVER --soundcard default\"" > /etc/default/snapclient
    systemctl enable --now snapclient
    systemctl restart snapclient
    echo "Snapclient kobler til $SERVER." ;;
  *) echo "Bruk: $0 server | client <server>"; exit 1 ;;
esac
