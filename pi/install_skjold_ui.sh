#!/usr/bin/env bash
# skjold-ui: cage + Chromium i kiosk.
#   Skjold S1 rev F: 4,58″ 960 × 320 på HDMI0 – designets egen tegnekode.   sudo bash pi/install_skjold_ui.sh [bruker]
#   Skjold Radio:    4,3″ DSI 800 × 480 – radioskjermen (web/radio.js).    sudo SKJOLD_UI_LAYOUT=radio bash pi/install_skjold_ui.sh [bruker]
# Kalles av install.sh og update.sh når KI_AMP_DISPLAY=bar958, KI_AMP_BOARD=s1f eller SKJOLD_UI_LAYOUT=radio (i /etc/ki-amp.env).
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
USR="${1:-${SUDO_USER:-pi}}"; UIDN="$(id -u "$USR")"
LAYOUT="${SKJOLD_UI_LAYOUT:-$(sed -n 's/^SKJOLD_UI_LAYOUT=//p' /etc/ki-amp.env 2>/dev/null | tail -1)}"; LAYOUT="${LAYOUT:-s1}"
if [ -f /etc/ki-amp.env ]; then   # husk oppsettet, så update.sh og tjenesten (EnvironmentFile) bruker det
  sed -i '/^SKJOLD_UI_LAYOUT=/d' /etc/ki-amp.env && echo "SKJOLD_UI_LAYOUT=$LAYOUT" >> /etc/ki-amp.env
fi
apt-get install -y -qq --no-install-recommends cage seatd fonts-liberation >/dev/null
apt-get install -y -qq --no-install-recommends chromium >/dev/null 2>&1 || apt-get install -y -qq --no-install-recommends chromium-browser >/dev/null
usermod -aG video,input,render "$USR" || true
systemctl enable --now seatd
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
if [ "$LAYOUT" = radio ]; then
  # Skjold Radio: DSI-skjermen (linja fra Waveshares wiki står i LES_MEG). Baklyset styres av skjermen (Lysstyrke i menyen).
  echo 'SUBSYSTEM=="backlight", RUN+="/bin/chmod 666 /sys/class/backlight/%k/brightness"' > /etc/udev/rules.d/90-skjold-backlight.rules
  udevadm control --reload-rules 2>/dev/null && udevadm trigger --subsystem-match=backlight 2>/dev/null || true
elif [ -f "$CFG" ] && ! grep -q "skjold-ui" "$CFG"; then   # S1: HDMI0 i 960 × 320 (HDMI-RGB21-driverkortet), uten overscan
  printf '\n# skjold-ui: 4,58" 960x320 på HDMI0\nhdmi_group:0=2\nhdmi_mode:0=87\nhdmi_cvt:0=960 320 60 6 0 0 0\ndisable_overscan=1\n' >> "$CFG"
fi
sed -e "s#@USER@#$USR#g" -e "s#@UID@#$UIDN#g" -e "s#@SRC@#$SRC#g" "$SRC/pi/skjold-ui.service" > /etc/systemd/system/skjold-ui.service
mkdir -p /etc/skjold && chown "$USR" /etc/skjold
systemctl daemon-reload
systemctl disable getty@tty1.service 2>/dev/null || true
systemctl set-default graphical.target
systemctl enable skjold-ui.service
systemctl restart skjold-ui.service || true
echo "skjold-ui installert ($LAYOUT): skjermen viser http://127.0.0.1:8766/ (logg: journalctl -u skjold-ui -f)"
