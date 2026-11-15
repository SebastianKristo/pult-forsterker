#!/usr/bin/env python3
"""Kopier musikkinnlogginger og radiofavoritter fra en annen Skjold-enhet til denne.
Hver Skjold-enhet (S1, Touch, Node) har egne innstillinger; dette henter Navidrome, YouTube Music, Plex og
radiofavorittene fra f.eks. S1-en, så Touch viser det samme.
  python3 pi/tools/kopier_fra.py pultamp.local        (eller IP-adressen til den andre enheten)
"""
import json
import sys
import urllib.request

NOKLER = ["ndEn", "ndUrl", "ndUser", "ndPass", "ytmEn", "ytmUser", "ytmCookie", "plexEn", "plexUrl", "plexToken"]


def hent(url):
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.load(r)


def send(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    kilde = sys.argv[1].rstrip("/")
    if not kilde.startswith("http"):
        kilde = "http://" + kilde + ("" if ":" in kilde else ":8765")
    her = "http://127.0.0.1:8765"
    s = hent(kilde + "/api/settings"); s = s.get("settings", s)
    body = {k: s[k] for k in NOKLER if s.get(k) not in (None, "")}
    if body:
        send(her + "/api/settings", body)
    print("Innlogginger kopiert:", ", ".join(sorted(body)) or "ingen (kilden har ingen)")
    p = hent(kilde + "/api/presets")
    fav = [{"title": x["title"], "url": x["url"], "genre": x.get("genre", ""), "icon": x.get("icon", "")} for x in p.get("items") or [] if x and x.get("url")]
    if fav:
        send(her + "/api/presets", {"presets": fav})
    print("Radiofavoritter kopiert:", len(fav))


if __name__ == "__main__":
    main()
