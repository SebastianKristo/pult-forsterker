#!/usr/bin/env bash
# Pultforsterker – feilsøking av lydkjeden. Kjør: bash ~/pult-forsterker/pi/ki-diag.sh
echo "== Tjenester"; for s in camilladsp nqptp shairport-sync bluealsa bluealsa-aplay ki-amp oled-display ki-usb-audio; do printf '  %-16s %s\n' "$s" "$(systemctl is-active $s)"; done
echo "== Lydkort"; aplay -l | grep '^card'
echo "== Loopback-modul"; lsmod | grep -q snd_aloop && echo "  snd_aloop lastet" || echo "  MANGLER snd_aloop"
echo "== /etc/ki-amp.env (DSP)"; grep -E '^KI_AMP_(DSP|BOARD|OUT)' /etc/ki-amp.env
echo "== CamillaDSP-config (devices)"; grep -A6 '^devices' /etc/camilladsp/config.yml
echo "== CamillaDSP-logg (siste 15)"; sudo tail -n 15 /var/log/camilladsp.log 2>/dev/null
echo "== Shairport-logg (siste 15)"; journalctl -u shairport-sync -n 15 --no-pager
echo "== ki-amp-logg (siste 10)"; journalctl -u ki-amp -n 10 --no-pager
echo "== oled-display-logg (siste 5)"; journalctl -u oled-display -n 5 --no-pager
echo "== Metadata-pipe"; ls -l /run/shairport-sync/ 2>&1; cat /run/pultamp_status.json 2>&1; echo
echo "== API-status"; curl -s localhost:8765/api/status; echo
echo "== Mixer på 3,5 mm"; amixer -c Headphones scontents 2>/dev/null | grep -E "Simple|Playback.*\[" | head -4
