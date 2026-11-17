#!/usr/bin/env bash
# Skjold S1: sørg for at det finnes en Lyrion Music Server (radio, YouTube Music og biblioteker går via Lyrion).
# Kalles av install.sh og update.sh. På Pi 4/5 installeres Lyrion alltid (også Touch/Node) som reserve når
# hovedserveren ikke svarer. Ellers gjøres ingenting når
#   - enheten er Node, Core, Touch eller testbenk (de bruker en server på nettet),
#   - KI_AMP_LYRION=0 eller KI_AMP_LMS_SERVER peker på en annen maskin i /etc/ki-amp.env,
#   - en annen Lyrion-server svarer på nettet (da brukes den, så rom kan grupperes på samme server).
# Ellers installeres Lyrion her (pi/install_lyrion.sh) og KI_AMP_LMS_SERVER=127.0.0.1 settes.
set -uo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
ENV=/etc/ki-amp.env
val() { sudo sed -n "s/^$1=//p" "$ENV" 2>/dev/null | tail -1; }
BOARD="${KI_AMP_BOARD:-$(val KI_AMP_BOARD)}"; PRODUCT="$(val KI_AMP_PRODUCT)"
[ "$BOARD" = test ] && { echo "  Lyrion: ikke på testbenken"; exit 0; }
[ "${KI_AMP_LYRION:-$(val KI_AMP_LYRION)}" = 0 ] && { echo "  Lyrion: slått av (KI_AMP_LYRION=0)"; exit 0; }
LMS="$(val KI_AMP_LMS_SERVER)"
# Pi 4/5 (nok minne): installer Lyrion her også som reserve. Når hovedserveren (KI_AMP_LMS_SERVER) ikke svarer,
# bytter daemonen og Squeezelite til den innebygde, og tilbake når hovedserveren er der igjen.
PI45=0; grep -qE "Raspberry Pi (4|5|Compute Module (4|5))" /proc/device-tree/model 2>/dev/null && PI45=1
if [ "$PI45" = 1 ] && ! dpkg -s lyrionmusicserver >/dev/null 2>&1; then
  echo "  Pi 4/5: installerer Lyrion Music Server som reserve (innebygd)"
  sudo bash "$SRC/install_lyrion.sh" || echo "ADVARSEL: Lyrion ble ikke installert – prøv: sudo bash pi/install_lyrion.sh" >&2
fi
case "$BOARD" in node) echo "  Lyrion: Node bruker en server på nettet"; exit 0 ;; esac
[ "$PRODUCT" = touch ] && { echo "  Lyrion: Touch bruker en server på nettet${LMS:+ ($LMS)}"; exit 0; }
case "$LMS" in ""|127.0.0.1|localhost) ;; *) echo "  Lyrion: bruker $LMS"; exit 0 ;; esac
if dpkg -s lyrionmusicserver >/dev/null 2>&1; then
  echo "  Lyrion Music Server er installert"
else
  # finnes det allerede en server på nettet? (Lyrions UDP-oppdagelse, port 3483)
  ANNEN="$(python3 - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); s.settimeout(3)
try:
    s.sendto(b"eIPAD\0NAME\0JSON\0", ("255.255.255.255", 3483)); print(s.recvfrom(1024)[1][0])
except OSError:
    pass
PY
)"
  if [ -n "$ANNEN" ]; then echo "  Lyrion: bruker serveren på $ANNEN"; exit 0; fi
  echo "  ingen Lyrion-server på nettet – installerer Lyrion Music Server her"
  sudo bash "$SRC/install_lyrion.sh" || { echo "ADVARSEL: Lyrion ble ikke installert – prøv: sudo bash pi/install_lyrion.sh" >&2; exit 0; }
fi
if [ -z "$LMS" ] && [ -f "$ENV" ]; then
  sudo sed -i '/^KI_AMP_LMS_SERVER=/d' "$ENV" && echo "KI_AMP_LMS_SERVER=127.0.0.1" | sudo tee -a "$ENV" >/dev/null
  sudo systemctl try-restart ki-amp 2>/dev/null || true
fi
exit 0
