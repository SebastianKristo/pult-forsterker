#!/usr/bin/env bash
# Skjold – installer web-appen som daemonen serverer på http://<pi>:8765/. Brukes av install.sh og update.sh.
#   bash pi/install_webapp.sh
set -uo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
# web-app (PWA) på http://<pi>:8765/ – prioritet: lokal skjold/app/dist (bygd i kildetreet) > skjold-web-*.zip fra
# siste skjold-v*-utgivelse på GitHub > den enkle pi/webapp. Hele mappa serveres på / av daemonen.
WEBAPP=/usr/local/share/ki-amp/webapp; WEB_TMP="$(mktemp -d)"; WEB_OK=0
if [ -f "$SRC/../skjold/app/dist/index.html" ]; then
  cp -r "$SRC/../skjold/app/dist/." "$WEB_TMP/" && WEB_OK=1 && echo "web-app: lokal skjold/app/dist"
else
  WEB_URL="$(curl -fsSL --max-time 20 -H 'Accept: application/vnd.github+json' \
      'https://api.github.com/repos/SebastianKristo/pult-forsterker/releases?per_page=30' 2>/dev/null | python3 -c '
import json, sys
try: rels = json.load(sys.stdin)
except Exception: sys.exit(0)
def ver(t):   # skjold-v0.1.14 -> (0, 1, 14): høyeste versjon vinner, uansett rekkefølgen GitHub lister i
    try: return tuple(int(x) for x in t.split("skjold-v", 1)[1].split("."))
    except Exception: return (0,)
best = None
for r in rels:
    if r.get("draft") or r.get("prerelease") or not str(r.get("tag_name", "")).startswith("skjold-v"): continue
    for a in r.get("assets", []):
        n = a.get("name", "")
        if n.startswith("skjold-web-") and n.endswith(".zip") and a.get("state", "uploaded") == "uploaded":
            if best is None or ver(r["tag_name"]) > best[0]: best = (ver(r["tag_name"]), a["browser_download_url"])
if best: print(best[1])
' 2>/dev/null || true)"
  if [ -n "$WEB_URL" ] && curl -fsSL --max-time 120 -o "$WEB_TMP/web.zip" "$WEB_URL" \
     && unzip -q -o "$WEB_TMP/web.zip" -d "$WEB_TMP/x" && rm -f "$WEB_TMP/web.zip"; then
    W="$WEB_TMP/x"; [ -f "$W/index.html" ] || W="$(dirname "$(find "$WEB_TMP/x" -maxdepth 3 -name index.html | head -n1)" 2>/dev/null)"   # zip med undermappe
    if [ -n "$W" ] && [ -f "$W/index.html" ]; then mv "$W" "$WEB_TMP/app" && WEB_OK=1 && echo "web-app: $WEB_URL"; fi
  fi
  [ "$WEB_OK" = 1 ] && { rm -rf "${WEB_TMP:?}/x"; cp -r "$WEB_TMP/app/." "$WEB_TMP/" && rm -rf "$WEB_TMP/app"; }
fi
if [ "$WEB_OK" != 1 ]; then echo "web-app: ingen utgivelse – bruker pi/webapp"; rm -rf "${WEB_TMP:?}"/*; cp -r "$SRC/webapp/." "$WEB_TMP/"; fi
# versjonen som er installert (vises og sammenlignes i Innstillinger → Oppdatering)
WEB_TAG="$(printf '%s' "${WEB_URL:-}" | sed -n 's#.*/download/\(skjold-v[0-9.]*\)/.*#\1#p')"
[ "$WEB_OK" = 1 ] && [ -z "$WEB_TAG" ] && WEB_TAG="lokal"
sudo mkdir -p /usr/local/share/ki-amp && printf '%s\n' "${WEB_TAG:-}" | sudo tee /usr/local/share/ki-amp/release >/dev/null
sudo rm -rf "$WEBAPP" && sudo mkdir -p "$WEBAPP" && sudo cp -r "$WEB_TMP/." "$WEBAPP/" \
  && sudo find "$WEBAPP" -type d -exec chmod 755 {} + && sudo find "$WEBAPP" -type f -exec chmod 644 {} +
rm -rf "$WEB_TMP"
