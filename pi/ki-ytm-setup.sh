#!/bin/bash
# YouTube Music innebygd (skjold_ytm.py): ytmusicapi (bibliotek/søk) og yt-dlp (lyden), oppdatert hver gang –
# YouTube endrer seg ofte, og en gammel yt-dlp slutter å finne lyden. yt-dlp trenger en JavaScript-motor (deno).
# Feiler aldri oppdateringen: uten dette er YouTube Music bare av.
set +e
sudo pip3 install --break-system-packages -q -U ytmusicapi "yt-dlp[default]" >/dev/null 2>&1 \
  && echo "  ytmusicapi og yt-dlp er oppdatert" || echo "  ADVARSEL: ytmusicapi/yt-dlp ble ikke installert – YouTube Music er av" >&2
if ! command -v deno >/dev/null; then
  case "$(uname -m)" in
    aarch64|arm64) T=aarch64-unknown-linux-gnu ;;
    x86_64) T=x86_64-unknown-linux-gnu ;;
    *) T="" ;;
  esac
  if [ -n "$T" ]; then
    command -v unzip >/dev/null || sudo apt-get -y install --no-install-recommends unzip >/dev/null 2>&1
    D=$(mktemp -d)
    if curl -fsSL -o "$D/deno.zip" "https://github.com/denoland/deno/releases/latest/download/deno-$T.zip" && unzip -q -o "$D/deno.zip" -d "$D"; then
      sudo install -m 755 "$D/deno" /usr/local/bin/deno && echo "  deno installert ($(deno --version | head -1))"
    else
      echo "  ADVARSEL: fant ikke deno – YouTube Music kan mangle lyd for noen låter" >&2
    fi
    rm -rf "$D"
  else
    echo "  deno finnes ikke for $(uname -m) (32-bit Pi OS) – yt-dlp prøver node/quickjs" >&2
  fi
fi
exit 0
