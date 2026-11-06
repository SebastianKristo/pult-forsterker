#!/usr/bin/env python3
"""Lager docs/api/openapi.yaml (OpenAPI 3.1) fra rutene i pi/*.py.

Alle aiohttp-ruter (web.get/post/…, FEAT_ROUTES og routes()-funksjonene i modulene) plukkes opp statisk, slik at
ingen rute glemmes. Sammendraget tas fra første linje av handlerens docstring. Kjerne-rutene har håndskrevne
skjemaer og eksempler i DETALJ nedenfor. Kjør: python3 docs/api/gen_openapi.py  (test: pi/tests/test_openapi.py)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PI = os.path.join(ROOT, "pi")
UT = os.path.join(ROOT, "docs", "api", "openapi.yaml")
NETT = os.path.join(ROOT, "skjold", "nettside", "utvikler", "openapi.yaml")   # Redoc-siden /utvikler/

R_WEB = re.compile(r'web\.(get|post|put|delete|patch)\(\s*"(/[^"]*)"\s*,\s*([\w.]+)')
R_ROUTE = re.compile(r'web\.route\(\s*"(\w+|\*)"\s*,\s*"(/[^"]*)"\s*,\s*([\w.]+)')
R_FEAT = re.compile(r'\("(GET|POST|PUT|DELETE|\*)"\s*,\s*"(/api[^"]*)"\s*,\s*([\w.]+)\)')
R_DEF = re.compile(r'(?:async )?def (\w+)\([^)]*\):\s*\n\s+(?:r?"""(.*?)""")?', re.S)


def ruter():
    out = {}
    for f in sorted(glob.glob(os.path.join(PI, "*.py"))):
        s = open(f, encoding="utf-8").read()
        docs = {m.group(1): (m.group(2) or "").strip() for m in R_DEF.finditer(s)}
        modul = os.path.basename(f)[:-3]
        for m in R_WEB.finditer(s):
            out.setdefault((m.group(2), m.group(1).lower()), (modul, docs.get(m.group(3).split(".")[-1], "")))
        for rx in (R_ROUTE, R_FEAT):
            for m in rx.finditer(s):
                for met in (["get", "post"] if m.group(1) == "*" else [m.group(1).lower()]):
                    out.setdefault((m.group(2), met), (modul, docs.get(m.group(3).split(".")[-1], "")))
    return {k: v for k, v in out.items() if k[0].startswith("/api/") or k[0] == "/"}


TAGG = [("/api/status", "Status"), ("/api/events", "Status"), ("/api/ws", "Status"), ("/api/power", "Avspilling"), ("/api/toggle", "Avspilling"),
        ("/api/volume", "Avspilling"), ("/api/mute", "Avspilling"), ("/api/input", "Avspilling"), ("/api/preset", "Radio"),
        ("/api/presets", "Radio"), ("/api/play", "Avspilling"), ("/api/transport", "Avspilling"), ("/api/settings", "Innstillinger"),
        ("/api/eq", "Innstillinger"), ("/api/loudness", "Innstillinger"), ("/api/routines", "Rutiner"), ("/api/plugins", "Plugins"),
        ("/api/homekit", "Integrasjoner"), ("/api/matter", "Integrasjoner"), ("/api/cloud", "Skjold Cloud"), ("/api/ma", "Music Assistant"),
        ("/api/nrk", "Radio"), ("/api/radio", "Radio"), ("/api/update", "System"), ("/api/backup", "System"), ("/api/restore", "System"),
        ("/api/health", "System"), ("/api/reboot", "System")]


def tagg(p):
    for pre, t in TAGG:
        if p == pre or p.startswith(pre + "/") or p.startswith(pre + "_"):
            return t
    return "Annet"


STATUS = {"type": "object", "description": "Hele tilstanden. Flere felt kan komme til; ukjente felt skal ignoreres.",
          "properties": {"power": {"type": "boolean"}, "volume": {"type": "integer", "minimum": 0, "maximum": 100},
                         "mute": {"type": "boolean"}, "input": {"type": "string", "examples": ["radio"]},
                         "inputs": {"type": "array", "items": {"type": "string"}}, "preset": {"type": "integer", "description": "Aktiv radiofavoritt (1-basert), 0 = ingen"},
                         "name": {"type": "string"}, "version": {"type": "string"}, "product": {"type": "string", "enum": ["s1", "node", "core", "touch"]},
                         "title": {"type": "string"}, "artist": {"type": "string"}},
          "additionalProperties": True, "required": ["power", "volume", "mute", "input"]}
OK = {"200": {"description": "Ny status", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Status"}}}}}


def body(props, req=None, eks=None):
    sc = {"type": "object", "properties": props}
    if req:
        sc["required"] = req
    c = {"schema": sc}
    if eks is not None:
        c["example"] = eks
    return {"required": True, "content": {"application/json": c}}


DETALJ = {
    ("/api/status", "get"): {"summary": "Hent status", "responses": OK},
    ("/api/events", "get"): {"summary": "Server-Sent Events: status hver gang den endrer seg",
                             "description": "`text/event-stream`. Hver hendelse er `data: <Status-JSON>`. Klienten bør koble til igjen etter `retry`-tiden.",
                             "responses": {"200": {"description": "Strøm", "content": {"text/event-stream": {"schema": {"type": "string"}, "example": "data: {\"power\":true,\"volume\":32,...}\n\n"}}}}},
    ("/api/ws", "get"): {"summary": "WebSocket (Skjold Touch-protokollen)", "description": "Oppgrader til WebSocket. Meldinger: state, input, vol, mute, power, pause, next, set, presets … (se pi/skjold_s1f.py).",
                         "responses": {"101": {"description": "Switching Protocols"}}},
    ("/api/power", "post"): {"summary": "Slå av/på", "requestBody": body({"on": {"type": "boolean"}}, ["on"], {"on": True}), "responses": OK},
    ("/api/toggle", "post"): {"summary": "Veksle av/på", "responses": OK},
    ("/api/volume", "post"): {"summary": "Sett volum (absolutt eller relativt)", "requestBody": body({"volume": {"type": "integer", "minimum": 0, "maximum": 100}, "delta": {"type": "integer"}}, None, {"volume": 35}), "responses": OK},
    ("/api/mute", "post"): {"summary": "Demp", "requestBody": body({"mute": {"type": "boolean"}}, ["mute"], {"mute": True}), "responses": OK},
    ("/api/input", "post"): {"summary": "Velg kilde", "requestBody": body({"input": {"type": "string"}}, ["input"], {"input": "radio"}),
                             "responses": {**OK, "400": {"description": "Ukjent kilde", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Feil"}}}}}},
    ("/api/preset", "post"): {"summary": "Spill (eller lagre) radiofavoritt n", "requestBody": body({"n": {"type": "integer", "minimum": 1}, "save": {"type": "boolean"}}, ["n"], {"n": 1}), "responses": OK},
    ("/api/play", "post"): {"summary": "Spill en URL (strøm eller fil)", "requestBody": body({"url": {"type": "string", "format": "uri"}, "title": {"type": "string"}, "artist": {"type": "string"}, "image": {"type": "string"}, "announce": {"type": "boolean", "description": "Spill oppå det som spiller"}, "volume": {"type": "integer", "minimum": 0, "maximum": 100}}, ["url"], {"url": "https://lyd.nrk.no/nrk_radio_p1_ostlandssendingen_mp3_h"}), "responses": OK},
    ("/api/transport", "post"): {"summary": "Pause/spill/neste/forrige", "requestBody": body({"action": {"type": "string", "enum": ["play", "pause", "playpause", "next", "previous", "stop"]}}, ["action"], {"action": "next"}), "responses": OK},
    ("/api/cloud", "post"): {"summary": "Skjold Cloud: aktiver, gjenopprett, velg deler, synk",
                             "requestBody": body({"aktiver": {"type": "boolean"}, "frase": {"type": "string", "description": "12 ord – gjenopprett på et nytt hjem"},
                                                  "deaktiver": {"type": "boolean"}, "deler": {"type": "array", "items": {"type": "string"}}, "synk": {"type": "boolean"}}, None, {"synk": True})},
    ("/api/matter", "post"): {"summary": "Matter: slå av/på eller glem paringer", "requestBody": body({"enabled": {"type": "boolean"}, "reset": {"type": "boolean"}}, None, {"enabled": True})},
}


def spec():
    paths = {}
    for (p, met), (modul, doc) in sorted(ruter().items()):
        linjer = [x.strip() for x in doc.splitlines() if x.strip()]
        op = {"tags": [tagg(p)], "summary": (linjer[0] if linjer else f"{met.upper()} {p}")[:120],
              "operationId": re.sub(r"[^A-Za-z0-9]+", "_", f"{met}_{p.strip('/')}").strip("_") or "index",
              "x-skjold-modul": modul, "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}}
        if len(linjer) > 1:
            op["description"] = "\n".join(linjer)
        params = re.findall(r"\{(\w+)\}", p)
        if params:
            op["parameters"] = [{"name": n, "in": "path", "required": True, "schema": {"type": "string"}} for n in params]
        if met in ("post", "put", "patch") and (p, met) not in DETALJ:
            op["requestBody"] = {"required": False, "content": {"application/json": {"schema": {"type": "object"}}}}
        op.update(DETALJ.get((p, met), {}))
        paths.setdefault(p, {})[met] = op
    return {
        "openapi": "3.1.0",
        "info": {"title": "Skjold lokalt API", "version": "1.0.0",
                 "description": open(os.path.join(ROOT, "docs", "api", "intro.md"), encoding="utf-8").read(),
                 "license": {"name": "MIT", "identifier": "MIT"}},
        "servers": [{"url": "http://{vert}:8765", "variables": {"vert": {"default": "skjold.local"}}}],
        "tags": [{"name": t} for t in sorted({tagg(p) for p in paths})],
        "paths": paths,
        "components": {"schemas": {"Status": STATUS, "Feil": {"type": "object", "properties": {"error": {"type": "string"}}, "required": ["error"]}}},
    }


def yaml_dump(o):
    import yaml   # PyYAML (bare når spesifikasjonen genereres)
    return yaml.safe_dump(o, allow_unicode=True, sort_keys=False, width=140)


if __name__ == "__main__":
    s = spec()
    tekst = "# Generert av docs/api/gen_openapi.py – ikke rediger for hånd.\n" + yaml_dump(s) + "\n"
    if "--check" in sys.argv:
        sys.exit(0 if os.path.exists(UT) and open(UT, encoding="utf-8").read() == tekst else 1)
    for f in (UT, NETT):
        open(f, "w", encoding="utf-8").write(tekst)
    print(f"{UT}: {len(s['paths'])} stier, {sum(len(v) for v in s['paths'].values())} operasjoner")
