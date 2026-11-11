#!/usr/bin/env bash
# Skjold Touch: skjerm-app i kiosk på 7″ berøringsskjerm med ekte multitouch.
# Bruker Wayland (cage + Chromium/ozone) slik at berøring går som touch-hendelser
# via libinput – ikke som en emulert musepeker. Pekeren vises aldri med bare touch.
#   sudo bash pi/install_touch.sh [bruker]      (KI_TOUCH_ROTATE=0|90|180|270)
set -euo pipefail
USR="${1:-${SUDO_USER:-pi}}"
ROT="${KI_TOUCH_ROTATE:-0}"
URL="${KI_TOUCH_URL:-http://127.0.0.1:8765/touch.html}"

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
# --use-fake-ui-for-media-stream: intercom får bruke mikrofonen uten spørsmål (kiosken har ingen dialogruter)
for i in \$(seq 60); do curl -fs -o /dev/null http://127.0.0.1:8765/api/status && break; sleep 1; done
[ "$ROT" != 0 ] && command -v wlr-randr >/dev/null && wlr-randr --output "\$(wlr-randr | head -1 | cut -d' ' -f1)" --transform $ROT || true
exec "$CHR" --kiosk --app="$URL" \\
  --ozone-platform=wayland --enable-features=UseOzonePlatform,OverlayScrollbar \\
  --force-device-scale-factor=1 --touch-events=enabled --disable-pinch --overscroll-history-navigation=0 \\
  --disable-features=TouchpadOverscrollHistoryNavigation,Translate,HardwareMediaKeyHandling \\
  --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble \\
  --check-for-update-interval=31536000 --password-store=basic --autoplay-policy=no-user-gesture-required \\
  --use-fake-ui-for-media-stream \\
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

HER="$(cd "$(dirname "$0")" && pwd)"

# --- Volumhjul (EC11): KI_TOUCH_ENC="A,B,SW" (BCM-pinner). Uten denne brukes bare volumet på skjermen. ---
if [ -n "${KI_TOUCH_ENC:-}" ]; then
  grep -q '^KI_TOUCH_ENC=' "$ENV" && sed -i "s/^KI_TOUCH_ENC=.*/KI_TOUCH_ENC=$KI_TOUCH_ENC/" "$ENV" || echo "KI_TOUCH_ENC=$KI_TOUCH_ENC" >> "$ENV"
fi

# --- Oppstartslogo: Skjold-stolpene i stedet for regnbuen og oppstartsteksten (KI_TOUCH_SPLASH=0 hopper over) ---
if [ "${KI_TOUCH_SPLASH:-1}" = 1 ] && [ -f "$HER/touch/oppstart.png" ]; then
  if apt-get install -y -qq plymouth plymouth-themes >/dev/null 2>&1; then
    T=/usr/share/plymouth/themes/skjold; mkdir -p "$T"; cp "$HER/touch/oppstart.png" "$T/logo.png"
    printf '[Plymouth Theme]\nName=Skjold\nDescription=Skjold Touch\nModuleName=script\n\n[script]\nImageDir=%s\nScriptFile=%s/skjold.script\n' "$T" "$T" > "$T/skjold.plymouth"
    cat > "$T/skjold.script" <<'P'
Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);
logo = Image("logo.png");
s = Sprite(logo);
s.SetX(Window.GetWidth() / 2 - logo.GetWidth() / 2);
s.SetY(Window.GetHeight() / 2 - logo.GetHeight() / 2);
P
    plymouth-set-default-theme skjold >/dev/null 2>&1 || true
    CMD=/boot/firmware/cmdline.txt; [ -f "$CMD" ] || CMD=/boot/cmdline.txt
    if [ -f "$CMD" ]; then
      for o in quiet splash plymouth.ignore-serial-consoles logo.nologo vt.global_cursor_default=0; do
        grep -qw -- "$o" "$CMD" || sed -i "1 s/\$/ $o/" "$CMD"
      done
    fi
    CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
    [ -f "$CFG" ] && { grep -q '^disable_splash=' "$CFG" || echo 'disable_splash=1' >> "$CFG"; }
    command -v update-initramfs >/dev/null && update-initramfs -u >/dev/null 2>&1 || true
  else
    echo "Oppstartslogo: fikk ikke installert plymouth – hopper over."
  fi
fi

# --- Stemmeassistent (valgfritt): KI_TOUCH_VOICE=1 ---
# Home Assistant Assist med wyoming-satellite og vekkeord lokalt (openWakeWord). Mikrofon og høyttaler er ALSA-enheter:
#   KI_TOUCH_MIC / KI_TOUCH_SPK  (se «arecord -L» og «aplay -L»; standard passer ReSpeaker Lite hvis kortet heter «Lite»)
if [ "${KI_TOUCH_VOICE:-0}" = 1 ]; then
  apt-get install -y -qq git python3-venv python3-dev alsa-utils libopenblas0 >/dev/null 2>&1 || true
  V=/opt/skjold-voice; mkdir -p "$V"
  [ -d "$V/wyoming-satellite" ] || git clone -q --depth 1 https://github.com/rhasspy/wyoming-satellite.git "$V/wyoming-satellite"
  [ -d "$V/wyoming-openwakeword" ] || git clone -q --depth 1 https://github.com/rhasspy/wyoming-openwakeword.git "$V/wyoming-openwakeword"
  ( cd "$V/wyoming-satellite" && python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip wheel setuptools \
      && .venv/bin/pip install -q -f 'https://synesthesiam.github.io/prebuilt-apps/' -e '.[all]' ) || echo "Stemme: wyoming-satellite ble ikke installert."
  ( cd "$V/wyoming-openwakeword" && script/setup >/dev/null ) || echo "Stemme: openWakeWord ble ikke installert."
  install -m 755 "$HER/skjold-voice-event" /usr/local/bin/skjold-voice-event
  [ -f /etc/skjold-voice.env ] || echo "WAKE_WORD=ok_nabu" > /etc/skjold-voice.env
  MIC="${KI_TOUCH_MIC:-plughw:CARD=Lite,DEV=0}"; SPK="${KI_TOUCH_SPK:-plughw:CARD=Lite,DEV=0}"
  NAVN="$(grep -s '^KI_AMP_NAME=' "$ENV" | cut -d= -f2- | tr -d '"')"; NAVN="${NAVN:-Skjold Touch}"
  cat > /etc/systemd/system/skjold-wakeword.service <<S
[Unit]
Description=Skjold Touch – vekkeord (openWakeWord)
After=network-online.target

[Service]
EnvironmentFile=/etc/skjold-voice.env
WorkingDirectory=$V/wyoming-openwakeword
ExecStart=$V/wyoming-openwakeword/script/run --uri tcp://127.0.0.1:10400 --preload-model \${WAKE_WORD}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
S
  cat > /etc/systemd/system/skjold-voice.service <<S
[Unit]
Description=Skjold Touch – stemmesatellitt for Home Assistant Assist
After=network-online.target sound.target skjold-wakeword.service ki-amp.service
Requires=skjold-wakeword.service

[Service]
EnvironmentFile=/etc/skjold-voice.env
WorkingDirectory=$V/wyoming-satellite
ExecStart=$V/wyoming-satellite/script/run --name "$NAVN" --uri tcp://0.0.0.0:10700 \\
  --mic-command "arecord -D $MIC -r 16000 -c 1 -f S16_LE -t raw" \\
  --snd-command "aplay -D $SPK -r 22050 -c 1 -f S16_LE -t raw" \\
  --wake-uri tcp://127.0.0.1:10400 --wake-word-name \${WAKE_WORD} \\
  --detection-command "/usr/local/bin/skjold-voice-event listen" \\
  --transcript-command "/usr/local/bin/skjold-voice-event think" \\
  --synthesize-command "/usr/local/bin/skjold-voice-event reply" \\
  --tts-played-command "/usr/local/bin/skjold-voice-event idle" \\
  --error-command "/usr/local/bin/skjold-voice-event error"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
S
  systemctl daemon-reload
  systemctl enable --now skjold-wakeword.service skjold-voice.service || true
  echo "Stemme installert. Legg til enheten i Home Assistant: Innstillinger → Enheter → Wyoming Protocol (port 10700)."
  echo "Sjekk mikrofon og høyttaler:  arecord -L   og   aplay -L   (KI_TOUCH_MIC / KI_TOUCH_SPK)."
fi

echo "Skjold Touch-skjerm installert. Test touch: sudo libinput debug-events (skal vise TOUCH_DOWN, ikke POINTER_MOTION)."
