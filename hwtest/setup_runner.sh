#!/usr/bin/env bash
# Gjør en Skjold-Pi til GitHub Actions-runner for maskinvaretester (se setup_runner.md).
# Bruk:  sudo bash hwtest/setup_runner.sh <REG_TOKEN> [eier/repo] [opptakskort, f.eks. plughw:CODEC]
#   REG_TOKEN: Settings → Actions → Runners → New self-hosted runner (gyldig i 1 time).
set -euo pipefail
TOKEN="${1:?registreringstoken mangler}"
REPO="${2:-sebastiankristo/pult-forsterker}"
CAPTURE="${3:-}"
VER="${RUNNER_VERSION:-2.321.0}"
USR=skjoldci
DIR=/opt/actions-runner

[ "$(id -u)" = 0 ] || { echo "Kjør med sudo"; exit 1; }
[ "$(uname -m)" = aarch64 ] || echo "Advarsel: ikke aarch64 – runneren under er for linux-arm64."

apt-get update -qq
apt-get install -y -qq python3-numpy python3-pytest python3-matplotlib alsa-utils avahi-utils curl git jq

id "$USR" >/dev/null 2>&1 || useradd -m -s /bin/bash -G audio "$USR"
usermod -aG audio "$USR"
cat > /etc/sudoers.d/skjoldci <<SUD
# Kun det maskinvaretestene trenger: installere en commit og styre tjenester.
$USR ALL=(root) NOPASSWD: /usr/bin/bash $DIR/_work/*/pi/update.sh*, /bin/bash $DIR/_work/*/pi/update.sh*, /usr/bin/systemctl restart *, /usr/bin/systemctl is-active *, /bin/systemctl restart *
SUD
chmod 440 /etc/sudoers.d/skjoldci
visudo -cf /etc/sudoers.d/skjoldci

mkdir -p "$DIR"; chown "$USR:$USR" "$DIR"
if [ ! -x "$DIR/config.sh" ]; then
  sudo -u "$USR" bash -c "cd $DIR && curl -fsSL -o r.tgz https://github.com/actions/runner/releases/download/v$VER/actions-runner-linux-arm64-$VER.tar.gz && tar xzf r.tgz && rm r.tgz"
fi
sudo -u "$USR" bash -c "cd $DIR && ./config.sh --unattended --replace --url https://github.com/$REPO --token $TOKEN --name skjold-hw-$(hostname) --labels skjold-hw"
[ -n "$CAPTURE" ] && echo "HWTEST_CAPTURE=$CAPTURE" >> "$DIR/.env"
cd "$DIR" && ./svc.sh install "$USR" && ./svc.sh start
echo "Ferdig. Runneren skal nå vises som «Idle» under Settings → Actions → Runners."
