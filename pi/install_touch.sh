#!/usr/bin/env bash
# Skjold Touch: skjerm-app i kiosk på 7″ berøringsskjerm med ekte multitouch.
# Bruker Wayland (cage + Chromium/ozone) slik at berøring går som touch-hendelser
# via libinput – ikke som en emulert musepeker. Pekeren vises aldri med bare touch.
#   sudo bash pi/install_touch.sh [bruker]      (KI_TOUCH_ROTATE=0|90|180|270)
set -euo pipefail
USR="${1:-${SUDO_USER:-pi}}"
ROT="${KI_TOUCH_ROTATE:-0}"
URL="${KI_TOUCH_URL:-http://127.0.0.1:8765/?kiosk=1}"

apt-get update -qq
apt-get install -y -qq cage seatd libinput-tools fonts-ibm-plex >/dev/null 2>&1 || apt-get install -y -qq cage seatd libinput-tools
apt-get install -y -qq chromium >/dev/null 2>&1 || apt-get install -y -qq chromium-browser
CHR="$(command -v chromium || command -v chromium-browser)"
usermod -aG video,input,render "$USR" || true
systemctl enable --now seatd

# KI_AMP_PRODUCT=touch for daemonen
ENV=/etc/ki-amp.env
touch "$ENV"; grep -q '^KI_AMP_PRODUCT=' "$ENV" && sed -i 's/^KI_AMP_PRODUCT=.*/KI_AMP_PRODUCT=touch/' "$ENV" || echo KI_AMP_PRODUCT=touch >> "$ENV"

# Rotasjon: skjerm via wlr-randr i cage, touch følger via libinput-kalibrering
case "$ROT" in
  90)  M="0 -1 1 1 0 0" ;; 180) M="-1 0 1 0 -1 1" ;; 270) M="0 1 0 -1 0 1" ;; *) M="" ;;
esac
if [ -n "$M" ]; then
  echo "ENV{ID_INPUT_TOUCHSCREEN}==\"1\", ENV{LIBINPUT_CALIBRATION_MATRIX}=\"$M\"" > /etc/udev/rules.d/99-skjold-touch.rules
else rm -f /etc/udev/rules.d/99-skjold-touch.rules; fi
udevadm control --reload-rules && udevadm trigger -s input || true

cat > /usr/local/bin/skjold-touch-ui <<S
#!/bin/sh
# venter til daemonen svarer, så Chromium ikke viser feilside
for i in \$(seq 60); do curl -fs -o /dev/null http://127.0.0.1:8765/api/status && break; sleep 1; done
[ "$ROT" != 0 ] && command -v wlr-randr >/dev/null && wlr-randr --output "\$(wlr-randr | head -1 | cut -d' ' -f1)" --transform $ROT || true
exec "$CHR" --kiosk --app="$URL" \\
  --ozone-platform=wayland --enable-features=UseOzonePlatform,OverlayScrollbar \\
  --touch-events=enabled --disable-pinch --overscroll-history-navigation=0 \\
  --disable-features=TouchpadOverscrollHistoryNavigation,Translate,HardwareMediaKeyHandling \\
  --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble \\
  --check-for-update-interval=31536000 --password-store=basic --autoplay-policy=no-user-gesture-required \\
  --user-data-dir=/home/$USR/.cache/skjold-touch
S
chmod +x /usr/local/bin/skjold-touch-ui
apt-get install -y -qq wlr-randr >/dev/null 2>&1 || true

cat > /etc/systemd/system/skjold-touch.service <<S
[Unit]
Description=Skjold Touch skjerm (cage kiosk)
After=systemd-user-sessions.service seatd.service ki-amp.service
Wants=ki-amp.service
Conflicts=getty@tty1.service

[Service]
User=$USR
PAMName=login
TTYPath=/dev/tty1
StandardInput=tty
Environment=XDG_RUNTIME_DIR=/run/user/%U
Environment=WLR_LIBINPUT_NO_DEVICES=1
Environment=XCURSOR_SIZE=1
RuntimeDirectory=skjold-touch
ExecStartPre=+/bin/sh -c 'mkdir -p /run/user/\$(id -u $USR) && chown $USR /run/user/\$(id -u $USR) && chmod 700 /run/user/\$(id -u $USR)'
# -d: ingen dekorasjoner, -s: tillat VT-bytte
ExecStart=/usr/bin/cage -d -s -- /usr/local/bin/skjold-touch-ui
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
S
systemctl daemon-reload
systemctl disable getty@tty1.service 2>/dev/null || true
systemctl set-default graphical.target
systemctl enable skjold-touch.service
systemctl restart ki-amp.service 2>/dev/null || true
systemctl restart skjold-touch.service
echo "Skjold Touch-skjerm installert. Test touch: sudo libinput debug-events (skal vise TOUCH_DOWN, ikke POINTER_MOTION)."
