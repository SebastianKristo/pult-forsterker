#!/usr/bin/env bash
# Skjold S1 rev F: skjermen (4,58″ 960 × 320 på HDMI0) – cage + Chromium viser designets egen tegnekode.
#   sudo bash pi/install_skjold_ui.sh [bruker]
# Kalles av install.sh og update.sh når KI_AMP_DISPLAY=bar958 eller KI_AMP_BOARD=s1f.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
USR="${1:-${SUDO_USER:-pi}}"; UIDN="$(id -u "$USR")"
apt-get install -y -qq --no-install-recommends cage seatd fonts-liberation >/dev/null
apt-get install -y -qq --no-install-recommends chromium >/dev/null 2>&1 || apt-get install -y -qq --no-install-recommends chromium-browser >/dev/null
usermod -aG video,input,render "$USR" || true
systemctl enable --now seatd
# HDMI0 i 960 × 320 (HDMI-RGB21-driverkortet), uten overscan
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
if [ -f "$CFG" ] && ! grep -q "skjold-ui" "$CFG"; then
  printf '\n# skjold-ui: 4,58" 960x320 på HDMI0\nhdmi_group:0=2\nhdmi_mode:0=87\nhdmi_cvt:0=960 320 60 6 0 0 0\ndisable_overscan=1\n' >> "$CFG"
fi
sed -e "s#@USER@#$USR#g" -e "s#@UID@#$UIDN#g" -e "s#@SRC@#$SRC#g" "$SRC/pi/skjold-ui.service" > /etc/systemd/system/skjold-ui.service
mkdir -p /etc/skjold && chown "$USR" /etc/skjold
systemctl daemon-reload
systemctl disable getty@tty1.service 2>/dev/null || true
systemctl set-default graphical.target
systemctl enable skjold-ui.service
systemctl restart skjold-ui.service || true
echo "skjold-ui installert: skjermen viser http://127.0.0.1:8766/ (logg: journalctl -u skjold-ui -f)"
