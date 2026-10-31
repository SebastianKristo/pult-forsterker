#!/usr/bin/env bash
# Skjold – installer Lyrion Music Server på denne enheten (valgfritt; ellers brukes en eksisterende server på nettet).
# Henter siste stabile versjon fra LMS-Community sin oppdateringsliste og sjekker MD5.
#   sudo bash pi/install_lyrion.sh
# Webgrensesnitt etterpå: http://<enhet>.local:9000
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Kjør som root (sudo)" >&2; exit 1; }
LISTE="https://raw.githubusercontent.com/LMS-Community/lms-server-repository/master/stable.xml"
case "$(dpkg --print-architecture)" in arm64|armhf) TAG=debarm ;; *) TAG=deb ;; esac

if dpkg -s lyrionmusicserver >/dev/null 2>&1; then echo "Lyrion Music Server er allerede installert"; exit 0; fi
XML="$(curl -fsSL --retry 5 "$LISTE")"
LINJE="$(printf '%s' "$XML" | grep -o "<$TAG url=\"[^\"]*\"[^>]*md5=\"[0-9a-f]*\"" | head -1)"
URL="$(printf '%s' "$LINJE" | sed -n 's/.*url="\([^"]*\)".*/\1/p')"
MD5="$(printf '%s' "$LINJE" | sed -n 's/.*md5="\([0-9a-f]*\)".*/\1/p')"
[ -n "$URL" ] && [ -n "$MD5" ] || { echo "Fant ikke $TAG i $LISTE" >&2; exit 1; }
F="$(mktemp -d)/lyrion.deb"
echo "Laster ned $URL"
curl -fL --retry 5 -o "$F" "$URL"
echo "$MD5  $F" | md5sum -c - >/dev/null || { echo "MD5 stemmer ikke for $URL" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y "$F"
systemctl enable --now lyrionmusicserver 2>/dev/null || true
echo "Lyrion Music Server installert: http://$(hostname).local:9000"
