#!/bin/bash
# Avinstallerer Skjold Matter-pluginen: stopper tjenesten, fjerner matter.js og (hvis Skjold installerte den) Node.js.
# Paringsdata slettes også, så en ny installasjon får ny paringskode.
set -e
systemctl disable --now skjold-matter.service 2>/dev/null || true
rm -f /etc/systemd/system/skjold-matter.service /var/lib/ki-amp/matter.on
systemctl daemon-reload
rm -rf /opt/skjold-matter
if [ -f /var/lib/ki-amp/matter/.node-by-skjold ]; then
  apt-get purge -y -q nodejs >/dev/null 2>&1 || true
  rm -f /etc/apt/sources.list.d/nodesource.list
fi
rm -rf /var/lib/ki-amp/matter
echo "Skjold Matter avinstallert."
