#!/usr/bin/env bash
# Skjold S1 som gave: installerer Skjold S1 (rev F, 4,58″-skjermen) og legger inn en bursdagshilsen.
#
#   bash pi/gave_s1.sh                      (som vanlig bruker på Pi-en, med internett)
#
# Når installasjonen er ferdig, starter S1 på nytt og viser «Ferdig installert – ta ut strømmen nå».
# Neste gang den får strøm, viser skjermen:
#
#   HIPP HIPP HURRA · Gratulerer med dagen, Pappa! · Fra Sebastian og Cybele
#
# Hilsenen står til noen trykker på en knapp eller vrir på hjulet, og vises bare den ene gangen.
#
# Valg (miljøvariabler):
#   GAVE_NAVN="Pappa"                 navnet i hilsenen
#   GAVE_FRA="Sebastian og Cybele"    hvem den er fra
#   GAVE_INSTALLER=0                  hopp over installasjonen (S1 er installert fra før, bare legg inn hilsenen)
#   GAVE_OMSTART=0                    ikke start på nytt til slutt (vis «Ferdig installert» med en gang hvis skjermen går)
#   KI_AMP_BOARD=s1f                  sendes videre til install.sh (standard: s1f, Skjold S1 rev F)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
NAVN="${GAVE_NAVN:-Pappa}"
FRA="${GAVE_FRA:-Sebastian og Cybele}"
HILSEN=/etc/skjold/greeting.json

if [ "$(id -u)" = 0 ]; then
  echo "Kjør skriptet som vanlig bruker (ikke med sudo): bash pi/gave_s1.sh" >&2
  exit 1
fi

cat <<TEKST

  ┌──────────────────────────────────────────────────────────┐
  │  Skjold S1 – gave                                        │
  │  Hilsen: «Gratulerer med dagen, $NAVN!»
  │          «Fra $FRA»
  └──────────────────────────────────────────────────────────┘

TEKST

# 1. Installer (eller oppdater) Skjold S1
if [ "${GAVE_INSTALLER:-1}" = 1 ]; then
  echo "== Installerer Skjold S1 (tar 15–40 minutter, la den stå) …"
  KI_AMP_BOARD="${KI_AMP_BOARD:-s1f}" bash "$SRC/install.sh"
else
  echo "== Hopper over installasjonen (GAVE_INSTALLER=0)"
fi

if [ ! -f /etc/systemd/system/skjold-ui.service ]; then
  echo "ADVARSEL: skjermprogrammet (skjold-ui) er ikke installert. Hilsenen vises bare på S1 rev F med 4,58″-skjermen." >&2
  echo "          Installer med KI_AMP_BOARD=s1f, eller kjør: sudo bash pi/install_skjold_ui.sh" >&2
fi

# 2. Legg inn hilsenen. «ferdig» = skjermen viser «Ferdig installert» ved neste start og gjør hilsenen klar;
#    oppstarten etter det viser gratulasjonen. Skrives med sync, så den overlever at strømmen tas.
echo "== Legger inn hilsenen"
sudo mkdir -p /etc/skjold
NAVN="$NAVN" FRA="$FRA" python3 - <<'PY' | sudo tee "$HILSEN" >/dev/null
import json, os
print(json.dumps({"name": os.environ["NAVN"][:24], "fra": os.environ["FRA"][:40], "state": "ferdig"}, ensure_ascii=False))
PY
UI_USER="$(sed -n 's/^User=//p' /etc/systemd/system/skjold-ui.service 2>/dev/null | head -1)"
[ -n "$UI_USER" ] && sudo chown -R "$UI_USER" /etc/skjold || true
sync

# 3. Ferdig: start på nytt (skjermen og alle tjenestene starter rent, og viser «Ferdig installert»)
if [ "${GAVE_OMSTART:-1}" = 1 ]; then
  echo
  echo "  Ferdig installert! S1 starter på nytt om 10 sekunder og viser «Ferdig installert – ta ut strømmen nå»."
  echo "  Ta ut strømmen når du ser det. Neste gang den starter, viser den gratulasjonen."
  echo "  (Ctrl+C for å avbryte omstarten.)"
  sleep 10
  sudo reboot
else
  # vis «Ferdig installert» med en gang hvis skjermen allerede kjører
  vist=0
  for _ in $(seq 1 45); do
    if curl -fsS -m 2 -X POST http://127.0.0.1:8766/greeting/ferdig >/dev/null 2>&1; then vist=1; break; fi
    sleep 2
  done
  echo
  if [ "$vist" = 1 ]; then
    echo "  Ferdig installert! Skjermen viser nå «Ferdig installert – ta ut strømmen nå»."
  else
    echo "  Ferdig installert! Skjermen svarte ikke ennå – den viser «Ferdig installert» neste gang den starter."
  fi
  echo "  Ta ut strømmen. Neste gang den starter, viser den gratulasjonen."
fi
