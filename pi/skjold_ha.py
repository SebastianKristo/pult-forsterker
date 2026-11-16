"""Home Assistant for Skjold: finn servere på nettet, logg inn og vis entitetene (kameraer, sensorer, lys …).

Brukes av web-UI-et og appene (Innstillinger → Home Assistant). Adressen og tokenet lagres i dørklokke-oppsettet
(ha_url/ha_token), som Touch, dørklokka og vekkingen allerede leser fra.

Innlogging uten å lime inn token: nettleseren sendes til Home Assistants egen innloggingsside (OAuth/IndieAuth med
Skjold-adressen som client_id). Etter innlogging bytter Skjold koden mot et tilgangstoken og lager et langtidstoken
(«Skjold») over Home Assistants WebSocket-API, så innloggingen ikke går ut etter 30 minutter.
"""
import json
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request

HA_TYPE = "_home-assistant._tcp.local."


def _get(url, token=None, timeout=5.0):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token} if token else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def _norm(url):
    url = str(url or "").strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = "http://" + url
        if url.count(":") == 1:   # bare vertsnavn/IP uten port: Home Assistant svarer som regel på 8123
            url += ":8123"
    return url


def discover(timeout=3.0):
    """Home Assistant-servere på nettet: [{name, url, version}] (mDNS, ellers homeassistant.local)."""
    found = {}

    def add(name, url, version=""):
        url = _norm(url)
        if url and url not in found:
            found[url] = {"name": name or "Home Assistant", "url": url, "version": version}

    try:
        from zeroconf import Zeroconf, ServiceBrowser
        zc = Zeroconf()
        names = []

        class L:
            def add_service(self, z, t, n): names.append(n)
            def update_service(self, z, t, n): pass
            def remove_service(self, z, t, n): pass
        ServiceBrowser(zc, HA_TYPE, L())
        time.sleep(timeout)
        for n in names:
            info = zc.get_service_info(HA_TYPE, n, 2000)
            if not info:
                continue
            p = {k.decode(errors="ignore"): (v.decode(errors="ignore") if isinstance(v, bytes) else v) for k, v in (info.properties or {}).items()}
            url = p.get("internal_url") or p.get("base_url") or ""
            if not url and info.parsed_addresses():
                url = f"http://{info.parsed_addresses()[0]}:{info.port}"
            add(p.get("location_name") or n.split(".")[0], url, p.get("version", ""))
        zc.close()
    except Exception:
        if shutil.which("avahi-browse"):
            try:
                out = subprocess.run(["avahi-browse", "-rtp", "_home-assistant._tcp"], capture_output=True, text=True, timeout=timeout + 4).stdout
                for ln in out.splitlines():
                    f = ln.split(";")
                    if f[0] == "=" and len(f) > 8:
                        add(f[3], f"http://{f[7]}:{f[8]}")
            except Exception:
                pass
    if not found:   # standardnavnet til Home Assistant OS
        try:
            socket.getaddrinfo("homeassistant.local", 8123)
            add("Home Assistant", "http://homeassistant.local:8123")
        except Exception:
            pass
    return list(found.values())


def info(url, token):
    """Sjekk innloggingen: navn og versjon fra /api/config. Feiler med en lesbar melding."""
    url = _norm(url)
    try:
        c = _get(url + "/api/config", token) or {}
    except urllib.error.HTTPError as e:
        raise RuntimeError("Tokenet ble ikke godtatt (" + str(e.code) + ")" if e.code in (401, 403) else "Home Assistant svarte " + str(e.code))
    except Exception as e:
        raise RuntimeError("Får ikke kontakt med " + url + ": " + str(e)[:100])
    return {"name": c.get("location_name") or "Home Assistant", "version": c.get("version", ""), "url": url}


def entities(url, token, domains=None, q=""):
    """Entitetene, gruppert og sortert: [{entity_id, domain, name, state, icon}]. domains: «camera,binary_sensor»."""
    url = _norm(url)
    want = {d.strip() for d in (domains or "").split(",") if d.strip()}
    q = (q or "").strip().lower()
    out = []
    for s in _get(url + "/api/states", token, timeout=8) or []:
        eid = s.get("entity_id", "")
        dom = eid.split(".", 1)[0]
        if want and dom not in want:
            continue
        a = s.get("attributes") or {}
        name = a.get("friendly_name") or eid
        if q and q not in name.lower() and q not in eid.lower():
            continue
        out.append({"entity_id": eid, "domain": dom, "name": name, "state": s.get("state", ""),
                    "device_class": a.get("device_class", ""), "icon": a.get("icon", "")})
    out.sort(key=lambda e: (e["domain"], e["name"].lower()))
    return out


def camera(url, token, entity):
    """Stillbilde fra et kamera i Home Assistant: (bytes, content-type)."""
    req = urllib.request.Request(_norm(url) + "/api/camera_proxy/" + urllib.parse.quote(entity),
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read(), r.headers.get("Content-Type", "image/jpeg")


# ------------------------------------------------------------------ innlogging (OAuth / IndieAuth)
_pending = {}   # state -> {url, client_id, redirect, back, t}
_lock = threading.Lock()


def login_url(ha_url, origin, back=""):
    """Adressen til Home Assistants innloggingsside. origin: Skjold slik nettleseren ser den (http://10.0.0.5:8765)."""
    ha = _norm(ha_url)
    client_id = origin.rstrip("/") + "/"
    redirect = origin.rstrip("/") + "/api/ha/callback"
    state = secrets.token_urlsafe(16)
    with _lock:
        for k in [k for k, v in _pending.items() if time.time() - v["t"] > 900]:
            _pending.pop(k, None)
        _pending[state] = {"url": ha, "client_id": client_id, "redirect": redirect, "back": back or client_id, "t": time.time()}
    return ha + "/auth/authorize?" + urllib.parse.urlencode({"client_id": client_id, "redirect_uri": redirect, "state": state})


def finish_login(state, code, device_name="Skjold"):
    """Bytt koden mot et tilgangstoken og lag et langtidstoken. → (ha_url, langtidstoken, tilbake-adresse)."""
    with _lock:
        p = _pending.pop(state, None)
    if not p:
        raise RuntimeError("Innloggingen er utløpt. Prøv igjen.")
    body = urllib.parse.urlencode({"grant_type": "authorization_code", "code": code, "client_id": p["client_id"]}).encode()
    req = urllib.request.Request(p["url"] + "/auth/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:
        tok = json.loads(r.read())
    access = tok.get("access_token")
    if not access:
        raise RuntimeError("Home Assistant ga ikke noe tilgangstoken")
    llat = long_lived(p["url"], access, device_name)
    return p["url"], llat, p["back"]


def long_lived(ha_url, access_token, name="Skjold"):
    """Langtidstoken (10 år) over WebSocket-API-et. Faller tilbake til tilgangstokenet (gyldig i 30 min) hvis det feiler."""
    try:
        import websocket   # python3-websocket (websocket-client)
    except Exception:
        return access_token
    ws_url = _norm(ha_url).replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
    ws = websocket.create_connection(ws_url, timeout=10)
    try:
        json.loads(ws.recv())                                   # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": access_token}))
        if json.loads(ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("Home Assistant godtok ikke innloggingen")
        navn = f"{name} ({time.strftime('%Y-%m-%d %H:%M')})"   # navnet må være unikt i Home Assistant
        ws.send(json.dumps({"id": 1, "type": "auth/long_lived_access_token", "client_name": navn, "lifespan": 3650}))
        res = json.loads(ws.recv())
        if not res.get("success"):
            raise RuntimeError((res.get("error") or {}).get("message") or "fikk ikke laget langtidstoken")
        return res["result"]
    finally:
        ws.close()
