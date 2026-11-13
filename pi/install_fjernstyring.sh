#!/usr/bin/env bash
# Skjold – fjernstyring via Cloudflare Tunnel (f.eks. https://styring.skjold-lab.com)
#   sudo bash pi/install_fjernstyring.sh <TUNNEL-TOKEN>
# Tokenet får du når du lager tunnelen i Cloudflare Zero Trust (se docs/FJERNSTYRING.md). Ingen porter åpnes i ruteren:
# cloudflared kobler seg UT til Cloudflare, og Cloudflare sender trafikken for vertsnavnet inn til http://localhost:8765.
# VIKTIG: beskytt vertsnavnet med Cloudflare Access (innlogging med e-post) – ellers kan hvem som helst styre Skjold.
set -euo pipefail
TOKEN="${1:-${CF_TUNNEL_TOKEN:-}}"
if [ -z "$TOKEN" ]; then echo "Bruk: sudo bash $0 <TUNNEL-TOKEN>   (se docs/FJERNSTYRING.md)"; exit 1; fi
if ! command -v cloudflared >/dev/null; then
  echo "== Installerer cloudflared"
  mkdir -p --mode=0755 /usr/share/keyrings
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" > /etc/apt/sources.list.d/cloudflared.list
  apt-get update -qq && apt-get install -y -qq cloudflared
fi
cloudflared service uninstall >/dev/null 2>&1 || true
cloudflared service install "$TOKEN"
systemctl enable --now cloudflared
sleep 3
systemctl is-active --quiet cloudflared && echo "Fjernstyring klar: åpne vertsnavnet du satte opp i Cloudflare (f.eks. https://styring.skjold-lab.com)" \
  || { echo "cloudflared startet ikke – se: journalctl -u cloudflared -n 50"; exit 1; }
