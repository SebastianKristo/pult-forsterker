#!/usr/bin/env bash
# Skjold Node: installer/oppdater skjold-early.service (oppstartsskjerm + LED-jag) og skjold-shutdown.service
# («Slått av – trygt å trekke ut»). Idempotent, kjøres som root. Kalles av installer_node.sh og pi/install.sh.
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" = 0 ] || { echo "Kjør som root (sudo)" >&2; exit 1; }
install -d /opt/skjold/early /var/lib/skjold
install -m 0755 "$HER/skjold_early.py" /opt/skjold/early/skjold_early.py
install -m 0644 "$HER/skjold-early.service" /etc/systemd/system/skjold-early.service
install -m 0644 "$HER/skjold-shutdown.service" /etc/systemd/system/skjold-shutdown.service
systemctl daemon-reload
systemctl enable skjold-early.service skjold-shutdown.service
systemctl start skjold-shutdown.service || true   # så ExecStop kjører ved neste avslåing
echo "skjold-early + skjold-shutdown installert (oppstartstid: cat /var/lib/skjold/boot_time)"
