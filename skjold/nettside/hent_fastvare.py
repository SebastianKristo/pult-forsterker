#!/usr/bin/env python3
"""Henter fastvaren til nettleserflashingen fra nyeste skjold-v*-utgivelse (kjøres av nettside.yml).

For hvert produkt: manifestet (skjold-<produkt>-manifest.json → flasher/<mappe>/<navn>) og alle .bin-filene manifestet
peker på. Røst og Kassett har én fil, Sensor og IR har én per brikke (ESP32/ESP32-C3 og D1 mini), Dokk ligger hos IR.
Miljø: GH_TOKEN, REPO (owner/repo)."""
import json
import os
import sys
import urllib.request

HER = os.path.dirname(os.path.abspath(__file__))
# (mappe under flasher/, manifest-asset, filnavn på nettsiden)
PRODUKTER = [("rost", "skjold-rost-manifest.json", "manifest.json"), ("kassett", "skjold-kassett-manifest.json", "manifest.json"),
             ("sensor", "skjold-sensor-manifest.json", "manifest.json"), ("bryter", "skjold-bryter-manifest.json", "manifest.json"),
             ("ir", "skjold-ir-manifest.json", "manifest.json"),
             ("ir", "skjold-dokk-manifest.json", "dokk-manifest.json")]


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ.get("GH_TOKEN", ""), "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read() if raw else json.loads(r.read())


def v(t):
    try:
        return tuple(int(x) for x in t.split("skjold-v", 1)[1].split("."))
    except Exception:
        return (0,)


def main():
    rel = [r for r in get(f"https://api.github.com/repos/{os.environ['REPO']}/releases?per_page=30")
           if not r.get("draft") and not r.get("prerelease") and str(r.get("tag_name", "")).startswith("skjold-v")]
    rel.sort(key=lambda r: v(r["tag_name"]), reverse=True)
    for mappe, asset, navn in PRODUKTER:
        r = next((r for r in rel if any(a["name"] == asset for a in r.get("assets", []))), None)
        if not r:
            print(f"::warning::{asset} finnes ikke på noen utgivelse ennå"); continue
        a = {x["name"]: x["browser_download_url"] for x in r["assets"]}
        d = os.path.join(HER, "flasher", mappe); os.makedirs(d, exist_ok=True)
        m = json.loads(get(a[asset], raw=True))
        ok = True
        for b in m.get("builds", []):
            for fil in [p["path"] for p in b.get("parts", [])] + ([b["ota"]["path"]] if b.get("ota") else []):   # OTA: «Fastvare»
                if fil not in a:
                    print(f"::warning::{fil} mangler på {r['tag_name']}"); ok = False; continue
                open(os.path.join(d, fil), "wb").write(get(a[fil], raw=True))
                print(f"{mappe}/{fil}: {r['tag_name']}")
        if ok:
            json.dump(m, open(os.path.join(d, navn), "w"), ensure_ascii=False, indent=2)
            print(f"{mappe}/{navn}: {r['tag_name']}")


if __name__ == "__main__":
    sys.exit(main())
