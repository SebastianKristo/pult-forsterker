#!/usr/bin/env bash
# Pultforsterker – norsk tale for talemeldinger («Bluetooth-paring …»). Piper (naturlig stemme) med espeak-ng som reserve.
set -uo pipefail
sudo apt-get -y install --no-install-recommends espeak-ng >/dev/null
if ! command -v piper >/dev/null; then
  sudo pip3 install --break-system-packages -q piper-tts || echo "  piper kunne ikke installeres – bruker espeak-ng"
fi
V=/opt/piper/no_NO-talesyntese-medium.onnx
if [ ! -s "$V" ]; then
  sudo mkdir -p /opt/piper
  U=https://huggingface.co/rhasspy/piper-voices/resolve/main/no/no_NO/talesyntese/medium/no_NO-talesyntese-medium.onnx
  sudo curl -fsSL -o "$V" "$U" && sudo curl -fsSL -o "$V.json" "$U.json" || { sudo rm -f "$V" "$V.json"; echo "  fant ikke Piper-stemmen – bruker espeak-ng"; }
fi
sudo rm -rf /var/cache/ki-amp/tts   # lag lydfilene på nytt med beste tilgjengelige stemme
echo "Tale: $(command -v piper >/dev/null && [ -s "$V" ] && echo 'Piper (norsk)' || echo 'espeak-ng (norsk)')"
