#!/usr/bin/env bash
# Pultforsterker – Bluetooth A2DP-mottaker (telefon → Pi). Trygt å kjøre flere ganger.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
BT_NAME="${KI_AMP_NAME:-Pultforsterker}"; BT_NAME="${BT_NAME//[|\\]/}"
sudo apt-get -y install --no-install-recommends bluez bluez-tools bluez-alsa-utils >/dev/null
sudo rfkill unblock bluetooth || true

# Adapteren: lydklasse, navn, alltid på, synlig bare når daemonen ber om det (parringsknapp/API)
CONF=/etc/bluetooth/main.conf
set_kv() { # seksjon nøkkel verdi
  if sudo grep -qE "^#?\s*$2\s*=" "$CONF"; then sudo sed -i -E "s|^#?\s*$2\s*=.*|$2 = $3|" "$CONF"
  else sudo sed -i "/^\[$1\]/a $2 = $3" "$CONF"; fi
}
grep -q '^\[Policy\]' "$CONF" || echo -e '\n[Policy]' | sudo tee -a "$CONF" >/dev/null
set_kv General Name "$BT_NAME"
set_kv General Class 0x200414
set_kv General DiscoverableTimeout 120
set_kv General PairableTimeout 0
set_kv General JustWorksRepairing always
set_kv Policy AutoEnable true

# bluealsa-daemonen må ta imot (a2dp-sink). Binæren heter bluealsad fra bluez-alsa 4.x, bluealsa før det.
BA="$(command -v bluealsad || command -v bluealsa)"
sudo mkdir -p /etc/systemd/system/bluealsa.service.d
printf '[Service]\nExecStart=\nExecStart=%s -S -p a2dp-sink\n' "$BA" | sudo tee /etc/systemd/system/bluealsa.service.d/override.conf >/dev/null

# Avspilling til dmix (deles med AirPlay/USB → CamillaDSP)
sudo install -m 644 "$SRC/bluealsa-aplay.service" /etc/systemd/system/bluealsa-aplay.service

# Agent som godtar parring uten PIN (forsterkeren har ingen skjerm å bekrefte på)
sudo tee /etc/systemd/system/ki-bt-agent.service >/dev/null <<'UNIT'
[Unit]
Description=Pultforsterker – Bluetooth-parring uten PIN
After=bluetooth.service
Requires=bluetooth.service

[Service]
ExecStartPre=/usr/bin/bluetoothctl power on
ExecStart=/usr/bin/bt-agent -c NoInputNoOutput
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl restart bluetooth
sleep 2
sudo systemctl enable --now bluealsa bluealsa-aplay ki-bt-agent
sudo systemctl restart bluealsa bluealsa-aplay
bluetoothctl system-alias "$BT_NAME" >/dev/null || true
bluetoothctl pairable on >/dev/null || true
echo "Bluetooth klar: $(bluetoothctl show | grep -E 'Name|Powered|Pairable' | tr -s ' \t' ' ' | paste -sd ',')"
