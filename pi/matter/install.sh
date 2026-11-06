#!/bin/bash
# Installerer Skjold Matter (pluginen «Matter»): Node 20+, matter.js (låst i package-lock.json) og skjold-matter.service.
# Kjøres av daemonen når Matter slås på, og av update.sh når den alt er på. Idempotent.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST=/opt/skjold-matter
need_node() { ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; }
if need_node; then
  apt-get install -y -q ca-certificates curl gnupg >/dev/null
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
  apt-get install -y -q nodejs >/dev/null
  mkdir -p /var/lib/ki-amp/matter && touch /var/lib/ki-amp/matter/.node-by-skjold   # avinstallering fjerner Node igjen
fi
mkdir -p "$DEST" /var/lib/ki-amp/matter
install -m 644 "$SRC/package.json" "$SRC/package-lock.json" "$SRC/index.js" "$SRC/mapping.js" "$DEST/"
if ! cmp -s "$SRC/package-lock.json" "$DEST/.installed-lock" || [ ! -d "$DEST/node_modules" ]; then
  (cd "$DEST" && npm ci --omit=dev --no-audit --no-fund --loglevel=error)
  cp "$SRC/package-lock.json" "$DEST/.installed-lock"
fi
install -m 644 "$SRC/skjold-matter.service" /etc/systemd/system/skjold-matter.service
systemctl daemon-reload
systemctl enable --now skjold-matter.service
systemctl restart skjold-matter.service
echo "Skjold Matter installert (node $(node -v))."
