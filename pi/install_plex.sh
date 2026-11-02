#!/usr/bin/env bash
# Skjold – Plex-spiller på Pi-en (valgfritt). Pi-en dukker opp som høyttaler («cast»-mål) i Plexamp-appen på mobil/PC,
# og lyden går samme vei som de andre kildene: ALSA «plex» (softvol «KI Plex») → dmix → loopback → CamillaDSP.
#
#   bash pi/install_plex.sh                       Plexamp headless (krever Plex Pass, Node.js 20+)
#   KI_PLEX_PLAYER=caldera bash pi/install_plex.sh  Caldera Music headless (nyere spiller fra Plexamp-utvikleren, uten Node)
#
# Kjør som vanlig bruker (bruker sudo selv). Krever en Plex Media Server med et musikkbibliotek på nettet.
# Til slutt logges spilleren inn med en kode fra https://plex.tv/claim (bare første gang).
# Valgfritt: KI_PLEXAMP_VERSION=4.13.2 (fast versjon), KI_AMP_NAME=… (spillernavn), KI_PLEX_SKIP_LOGIN=1.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
PLAYER="${KI_PLEX_PLAYER:-plexamp}"
U=ki-plex; H=/var/lib/ki-plex
NAME_SEL="${KI_AMP_NAME:-$(sudo sed -n 's/^KI_AMP_NAME=//p' /etc/ki-amp.env 2>/dev/null | tail -n1)}"; NAME_SEL="${NAME_SEL:-$(hostname)}"
case "$PLAYER" in plexamp|caldera) ;; *) echo "KI_PLEX_PLAYER må være plexamp eller caldera" >&2; exit 1 ;; esac
[ "$(dpkg --print-architecture)" = arm64 ] || echo "ADVARSEL: ikke 64-bit OS – Plex-spillerne krever arm64 (Raspberry Pi OS 64-bit)" >&2

echo "== Plex 1/5  Bruker $U og lyd (ALSA «plex»)"
id "$U" >/dev/null 2>&1 || sudo useradd -r -m -d "$H" -s /usr/sbin/nologin -g audio "$U"
sudo usermod -aG audio "$U"
# Spillerens «standard»-lydenhet = Skjold-kilden «plex» (eget nivå, mikses inn i CamillaDSP som resten)
printf '# Skrevet av pi/install_plex.sh – spilleren sin standard lydenhet er Skjold-kilden «plex»\npcm.!default { type plug; slave.pcm "plex" }\n' \
  | sudo -u "$U" tee "$H/.asoundrc" >/dev/null
if ! grep -q 'pcm.plex' /etc/asound.conf 2>/dev/null; then   # eldre installasjon: legg til «plex» i /etc/asound.conf
  PB_CARD=$(sudo grep -oP "^KI_AMP_DSP_PLAYBACK=(plug)?hw:\K[^,]+" /etc/ki-amp.env 2>/dev/null || echo sndrpihifiberry)
  sed "s/sndrpihifiberry/$PB_CARD/g" "$SRC/asound.conf" | sudo tee /etc/asound.conf >/dev/null
fi

if [ "$PLAYER" = plexamp ]; then
  echo "== Plex 2/5  Node.js 20+"
  NODE_MAJ=$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0); NODE_MAJ=${NODE_MAJ:-0}
  if [ "$NODE_MAJ" -lt 20 ]; then
    APT_MAJ=$(apt-cache policy nodejs 2>/dev/null | sed -nE 's/^ *Candidate: ([0-9]+).*/\1/p' | head -n1); APT_MAJ=${APT_MAJ:-0}
    if [ "$APT_MAJ" -ge 20 ]; then
      sudo apt-get -y install --no-install-recommends nodejs
    else   # Bookworm har Node 18 – hent Node 20 fra NodeSource
      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
      sudo apt-get -y install nodejs
    fi
  fi
  echo "  node $(node -v)"

  echo "== Plex 3/5  Plexamp headless"
  if [ -z "${KI_PLEXAMP_VERSION:-}" ]; then   # siste versjon fra Plex, ellers kjent fungerende
    KI_PLEXAMP_VERSION=$(curl -fsSL --max-time 15 https://plexamp.plex.tv/headless/version.json 2>/dev/null \
      | grep -oE 'headless-v[0-9]+(\.[0-9]+)+' | head -n1 | sed 's/headless-v//' || true)
    KI_PLEXAMP_VERSION="${KI_PLEXAMP_VERSION:-4.13.2}"
  fi
  URL="https://plexamp.plex.tv/headless/Plexamp-Linux-headless-v${KI_PLEXAMP_VERSION}.tar.bz2"
  if [ "$(sudo cat "$H/.ki-plexamp-version" 2>/dev/null)" != "$KI_PLEXAMP_VERSION" ]; then
    T="$(mktemp -d)"; echo "  laster ned $URL"
    curl -fL --retry 3 -o "$T/plexamp.tar.bz2" "$URL"
    tar -xjf "$T/plexamp.tar.bz2" -C "$T"
    sudo rm -rf "$H/plexamp" && sudo mv "$T/plexamp" "$H/plexamp" && sudo chown -R "$U:audio" "$H/plexamp"
    echo "$KI_PLEXAMP_VERSION" | sudo -u "$U" tee "$H/.ki-plexamp-version" >/dev/null; rm -rf "$T"
  else
    echo "  Plexamp $KI_PLEXAMP_VERSION er allerede installert"
  fi
  EXEC="/usr/bin/node $H/plexamp/js/index.js"; WD="$H/plexamp"
else
  echo "== Plex 2/5  (Caldera trenger ikke Node.js)"
  echo "== Plex 3/5  Caldera Music headless"
  if [ ! -x "$H/caldera-music/caldera-music" ]; then
    curl -fsSL https://releases.caldera.homes/music/headless/install.sh -o /tmp/caldera-install.sh
    # installeres i hjemmemappa til ki-plex; en eventuell «systemctl --user»-feil til slutt er ufarlig (vi lager egen tjeneste)
    sudo -u "$U" -H bash /tmp/caldera-install.sh || true
    rm -f /tmp/caldera-install.sh
  fi
  [ -x "$H/caldera-music/caldera-music" ] || { echo "Fant ikke $H/caldera-music/caldera-music etter installasjonen" >&2; exit 1; }
  EXEC="$H/caldera-music/caldera-music"; WD="$H/caldera-music"
fi

echo "== Plex 4/5  Tjenesten ki-plex"
sudo tee /etc/systemd/system/ki-plex.service >/dev/null <<UNIT
[Unit]
Description=Skjold – Plex-spiller ($PLAYER)
After=network-online.target sound.target camilladsp.service ki-amp.service
Wants=network-online.target

[Service]
# Lyd: ~/.asoundrc gjør ALSA «default» = «plex» (softvol «KI Plex» → dmix → loopback → CamillaDSP)
User=$U
Group=audio
WorkingDirectory=$WD
ExecStart=$EXEC
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo sed -i '/^KI_AMP_PLEX=/d' /etc/ki-amp.env 2>/dev/null || true
echo "KI_AMP_PLEX=1" | sudo tee -a /etc/ki-amp.env >/dev/null
sudo systemctl daemon-reload
sudo systemctl stop ki-plex 2>/dev/null || true

echo "== Plex 5/5  Innlogging"
LOGGED_IN=0
if [ "$PLAYER" = plexamp ]; then
  sudo find "$H/.local/share/Plexamp" -type f 2>/dev/null | grep -qi token && LOGGED_IN=1
else
  sudo find "$H" -maxdepth 4 -path '*caldera*' -type f \( -iname '*token*' -o -iname '*auth*' -o -iname '*.json' \) 2>/dev/null | grep -q . && LOGGED_IN=1
fi
if [ "$LOGGED_IN" = 1 ] || [ "${KI_PLEX_SKIP_LOGIN:-0}" = 1 ]; then
  echo "  allerede logget inn (slett $H/.local og kjør på nytt for å logge inn med en annen konto)"
elif [ ! -t 0 ]; then
  echo "  Ikke en terminal – logg inn senere: sudo systemctl stop ki-plex && kjør bash pi/install_plex.sh i SSH"
else
  echo
  echo "  1. Åpne https://plex.tv/claim i nettleseren (logget inn på Plex-kontoen din) og kopier koden."
  if [ "$PLAYER" = plexamp ]; then
    echo "  2. Lim inn koden her, og skriv spillernavnet (forslag: $NAME_SEL)."
    echo "  3. Når det står «Plexamp is now signed in and ready!»: trykk Ctrl+C – installasjonen fortsetter."
    echo
    trap 'true' INT   # Ctrl+C stopper bare innloggingen, ikke dette skriptet
    sudo -u "$U" -H bash -c "cd '$WD' && exec /usr/bin/node js/index.js" || true
    trap - INT
  else
    echo
    sudo -u "$U" -H "$EXEC" --login --player-name "$NAME_SEL" || true
  fi
fi
sudo systemctl enable --now ki-plex
sudo systemctl try-restart ki-amp 2>/dev/null || true   # daemonen leser KI_AMP_PLEX=1 → kilden «Plex»

IP=$(hostname -I | awk '{print $1}')
echo
echo "Ferdig. Plex-spilleren «$NAME_SEL» kjører (sudo systemctl status ki-plex)."
if [ "$PLAYER" = plexamp ]; then
  echo "  Første gang: åpne http://$IP:32500 → logg inn → velg musikkbiblioteket."
  echo "  Under Settings → Playback → Audio Device: velg «default» (= Skjold-kilden Plex)."
fi
echo "  Spill: Plexamp-appen → høyttalerikonet → velg «$NAME_SEL». Skjold bytter til kilden Plex automatisk."
