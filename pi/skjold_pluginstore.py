"""Skjold – plugin-butikk: format, lasting, sandkasse, katalog og installasjon.

Et plugin er en mappe /var/lib/skjold/plugins/<id>/ med plugin.json (se docs/PLUGINS.md). Entry er enten en
Python-modul med register(api) – kjøres alltid i egen prosess med tidsgrense og ressursgrenser – eller deklarative
ferdigheter («skills») direkte i plugin.json / en .json/.yaml-fil. Plugins kan bare be daemonen om handlinger
(vise melding, spille, kunngjøre); daemonen sjekker tillatelsene før noe utføres.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile

from aiohttp import web

ROOT = os.environ.get("SKJOLD_PLUGIN_DIR", "/var/lib/skjold/plugins")
INDEX_URL = "https://raw.githubusercontent.com/SebastianKristo/pult-forsterker/main/plugins/index.json"
RAW_BASE = "https://raw.githubusercontent.com/SebastianKristo/pult-forsterker/main/plugins/"
PERMISSIONS = {"http", "audio", "settings", "schedule"}
CATEGORIES = {"Radio og podkast", "Musikk", "Verktøy", "Hjem", "Moro"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
VER_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
ACTIONS = {"toast": None, "play": "audio", "announce": "audio", "volume": "audio", "navidrome_random": "audio"}
TIMEOUT = 10
MAX_ZIP = 2 * 1024 * 1024


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)


def validate_manifest(m, skjold_version=None):
    """Liste med feil (tom = gyldig)."""
    err = []
    if not isinstance(m, dict):
        return ["plugin.json må være et JSON-objekt"]
    for k in ("id", "navn", "versjon", "forfatter", "beskrivelse", "entry"):
        if not m.get(k):
            err.append(f"mangler «{k}»")
    if m.get("id") and not ID_RE.match(str(m["id"])):
        err.append("id kan bare ha små bokstaver, tall og bindestrek")
    if m.get("versjon") and not VER_RE.match(str(m["versjon"])):
        err.append("versjon må være på formen 1.2.3")
    if m.get("kategori") and m["kategori"] not in CATEGORIES:
        err.append("ukjent kategori")
    bad = set(m.get("tillatelser") or []) - PERMISSIONS
    if bad:
        err.append("ukjente tillatelser: " + ", ".join(sorted(bad)))
    e = str(m.get("entry") or "")
    if e and (e.startswith(("/", ".")) or ".." in e or not re.match(r"^[\w.-]+\.(py|json|ya?ml)$", e)):
        err.append("entry må være en fil i plugin-mappa (.py, .json eller .yaml)")
    if m.get("minSkjold") and skjold_version and vtuple(skjold_version) < vtuple(m["minSkjold"]):
        err.append(f"krever Skjold {m['minSkjold']} eller nyere")
    if not isinstance(m.get("settings", {}), dict):
        err.append("settings må være et objekt (skjema)")
    return err


def settings_defaults(m):
    return {k: (v or {}).get("default") for k, v in (m.get("settings") or {}).items()}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def safe_extract(data, dest):
    """Pakker ut zip uten stier utenfor dest. plugin.json kan ligge i rot eller i én undermappe."""
    if len(data) > MAX_ZIP:
        raise ValueError("pakken er for stor (maks 2 MB)")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        pj = sorted((n for n in names if n.endswith("plugin.json")), key=len)
        if not pj:
            raise ValueError("fant ikke plugin.json i pakken")
        prefix = pj[0][:-len("plugin.json")]
        for n in names:
            if not n.startswith(prefix):
                continue
            rel = n[len(prefix):]
            if rel.startswith("/") or ".." in rel.split("/") or "\\" in rel:
                raise ValueError("ugyldig filsti i pakken: " + n)
            p = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with z.open(n) as src, open(p, "wb") as out:
                out.write(src.read())


RUNNER = r'''
import json, sys, os, resource
d, event, payload, perms = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), set(json.loads(sys.argv[4]))
try:
    resource.setrlimit(resource.RLIMIT_AS, (256 << 20, 256 << 20))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 << 20, 32 << 20))
except Exception:
    pass
os.chdir(d); sys.path.insert(0, d)
import importlib.util, urllib.request
if "http" not in perms:
    def _blocked(*a, **k): raise PermissionError("pluginet har ikke tillatelsen http")
    urllib.request.urlopen = _blocked
    import socket
    socket.socket.connect = lambda *a, **k: _blocked()
class Api:
    def __init__(s):
        s.handlers, s.actions, s.settings = {}, [], payload.get("settings") or {}
    def on(s, ev, fn=None):
        if fn is None: return lambda f: s.on(ev, f) or f
        s.handlers[ev] = fn
    def toast(s, text, sub=""): s.actions.append({"toast": str(text)[:200], "sub": str(sub)[:200]})
    def play(s, url, title=""): s.actions.append({"play": str(url), "title": str(title)[:120]})
    def announce(s, url): s.actions.append({"announce": str(url)})
    def volume(s, v): s.actions.append({"volume": int(v)})
    def http_get(s, url, timeout=6):
        if "http" not in perms: raise PermissionError("pluginet har ikke tillatelsen http")
        req = urllib.request.Request(url, headers={"User-Agent": "skjold-plugin/1"})
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.read().decode("utf-8", "replace")
    def tmpdir(s):
        p = os.path.join(d, ".tmp"); os.makedirs(p, exist_ok=True); return p
api = Api()
spec = importlib.util.spec_from_file_location("plugin_entry", os.path.join(d, sys.argv[5]))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.register(api)
res = None
if event in api.handlers:
    res = api.handlers[event](payload.get("data") or {})
print("\n@@SKJOLD@@" + json.dumps({"actions": api.actions, "result": res, "events": sorted(api.handlers)}, default=str))
'''


def run_python(pdir, entry, event, payload, perms, timeout=TIMEOUT):
    """Kjør pluginets register(api) + handler i egen prosess. Returnerer {"actions", "result", "events"} eller {"error"}."""
    env = {"PATH": "/usr/bin:/bin", "HOME": pdir, "PYTHONIOENCODING": "utf-8", "LANG": "C.UTF-8"}
    for k in ("HTTPS_PROXY", "HTTP_PROXY", "SSL_CERT_FILE"):
        if k in os.environ and "http" in perms:
            env[k] = os.environ[k]
    try:
        p = subprocess.run([sys.executable, "-I", "-c", RUNNER, pdir, event, json.dumps(payload), json.dumps(sorted(perms)), entry],
                           capture_output=True, text=True, timeout=timeout, env=env, cwd=pdir)
    except subprocess.TimeoutExpired:
        return {"error": f"tidsgrense ({timeout} s) overskredet"}
    out = p.stdout.rsplit("@@SKJOLD@@", 1)
    if p.returncode != 0 or len(out) < 2:
        return {"error": (p.stderr.strip().splitlines() or ["ukjent feil"])[-1][:300]}
    try:
        return json.loads(out[1])
    except Exception:
        return {"error": "ugyldig svar fra plugin"}


def allowed_actions(actions, perms):
    """Fjern handlinger pluginet ikke har tillatelse til."""
    out = []
    for a in actions or []:
        key = next((k for k in a if k in ACTIONS), None)
        need = ACTIONS.get(key) if key else "?"
        if key and (need is None or need in perms):
            out.append(a)
    return out


def load_skills(pdir, m):
    e = m.get("entry", "")
    if e.endswith(".py"):
        return []
    if e == "plugin.json":
        return m.get("skills") or []
    with open(os.path.join(pdir, e)) as fh:
        if e.endswith(".json"):
            return json.load(fh).get("skills") or []
        import yaml   # valgfritt
        return (yaml.safe_load(fh) or {}).get("skills") or []


class Store:
    def __init__(self, root=ROOT, version="0", fetch=None, index_url=INDEX_URL, raw_base=RAW_BASE):
        self.root, self.version, self.index_url, self.raw_base = root, version, index_url, raw_base
        self.fetch = fetch or self._fetch
        self.lock = threading.Lock()
        self.errors = {}
        self.fired = set()
        os.makedirs(root, exist_ok=True) if os.access(os.path.dirname(root) or "/", os.W_OK) or os.path.isdir(root) else None

    @staticmethod
    def _fetch(url):
        req = urllib.request.Request(url, headers={"User-Agent": "skjold"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read(MAX_ZIP + 1)

    # --- installerte
    def _cfg_path(self, pid):
        return os.path.join(self.root, pid, ".settings.json")

    def installed(self):
        out = []
        if not os.path.isdir(self.root):
            return out
        for pid in sorted(os.listdir(self.root)):
            pj = os.path.join(self.root, pid, "plugin.json")
            if not os.path.isfile(pj):
                continue
            try:
                m = json.load(open(pj))
            except Exception as e:
                out.append({"id": pid, "error": f"ugyldig plugin.json: {e}"}); continue
            errs = validate_manifest(m, self.version)
            out.append({**m, "enabled": self.get_settings(pid).get("_enabled", True), "settingsValues": self.get_settings(pid),
                        "error": "; ".join(errs) or self.errors.get(pid, "")})
        return out

    def manifest(self, pid):
        if not ID_RE.match(pid):
            raise ValueError("ugyldig id")
        return json.load(open(os.path.join(self.root, pid, "plugin.json")))

    def get_settings(self, pid):
        try:
            return json.load(open(self._cfg_path(pid)))
        except Exception:
            try: return settings_defaults(self.manifest(pid))
            except Exception: return {}

    def set_settings(self, pid, values):
        m = self.manifest(pid)
        cur = self.get_settings(pid)
        schema = m.get("settings") or {}
        for k, v in (values or {}).items():
            if k == "_enabled" or k in schema:
                cur[k] = v
        with open(self._cfg_path(pid), "w") as fh:
            json.dump(cur, fh)
        return cur

    # --- installasjon
    def install_zip(self, data, expect_sha=None):
        if expect_sha and sha256(data) != expect_sha.lower():
            raise ValueError("sha256 stemmer ikke – pakken er endret eller ødelagt")
        tmp = tempfile.mkdtemp(prefix="skjold-plugin-")
        try:
            safe_extract(data, tmp)
            return self._commit(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def install_files(self, pid, files, dir_url):
        """Katalog-installasjon: files = [{"path", "sha256"}], hentet fra dir_url + path."""
        tmp = tempfile.mkdtemp(prefix="skjold-plugin-")
        try:
            for f in files:
                rel = f["path"]
                if rel.startswith("/") or ".." in rel.split("/"):
                    raise ValueError("ugyldig filsti: " + rel)
                b = self.fetch(dir_url + rel)
                if sha256(b) != str(f.get("sha256", "")).lower():
                    raise ValueError(f"sha256 stemmer ikke for {rel}")
                p = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(b)
            return self._commit(tmp, want_id=pid)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _commit(self, tmp, want_id=None):
        m = json.load(open(os.path.join(tmp, "plugin.json")))
        errs = validate_manifest(m, self.version)
        if want_id and m.get("id") != want_id:
            errs.append("id i plugin.json stemmer ikke med katalogen")
        if not errs and not os.path.isfile(os.path.join(tmp, m["entry"])):
            errs.append("entry-fila mangler")
        if errs:
            raise ValueError("; ".join(errs))
        dest = os.path.join(self.root, m["id"])
        with self.lock:
            keep = None
            if os.path.isfile(os.path.join(dest, ".settings.json")):
                keep = open(os.path.join(dest, ".settings.json")).read()
            os.makedirs(self.root, exist_ok=True)
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(tmp, dest)
            if keep:
                open(os.path.join(dest, ".settings.json"), "w").write(keep)
        self.errors.pop(m["id"], None)
        return m

    def install_url(self, url, expect_sha=None):
        if not url.startswith(("https://", "http://")):
            raise ValueError("adressen må starte med https://")
        data = self.fetch(url)
        if url.endswith("plugin.json"):
            m = json.loads(data)
            base = url[: -len("plugin.json")]
            names = ["plugin.json"] + [f for f in (m.get("files") or [m["entry"]]) if f != "plugin.json"]
            files = [{"path": f, "sha256": sha256(self.fetch(base + f))} for f in names]   # ingen sjekksum å sammenligne med
            return self.install_files(m["id"], files, base)
        return self.install_zip(data, expect_sha)

    def remove(self, pid):
        if not ID_RE.match(pid):
            raise ValueError("ugyldig id")
        shutil.rmtree(os.path.join(self.root, pid), ignore_errors=True)

    # --- katalog
    def catalog(self):
        idx = json.loads(self.fetch(self.index_url))
        inst = {m["id"]: m.get("versjon") for m in self.installed() if "id" in m}
        out = []
        for p in idx.get("plugins") or []:
            item = {k: v for k, v in p.items() if k != "files"}
            item["installed"] = inst.get(p["id"])
            item["update"] = bool(inst.get(p["id"]) and vtuple(p.get("versjon")) > vtuple(inst[p["id"]]))
            item["compatible"] = not (p.get("minSkjold") and vtuple(self.version) < vtuple(p["minSkjold"]))
            out.append(item)
        return {"plugins": out, "base": idx.get("base") or self.raw_base}

    def install_from_catalog(self, pid):
        idx = json.loads(self.fetch(self.index_url))
        p = next((x for x in idx.get("plugins") or [] if x.get("id") == pid), None)
        if not p:
            raise ValueError("fant ikke pluginet i katalogen")
        return self.install_files(pid, p.get("files") or [], (idx.get("base") or self.raw_base) + pid + "/")

    # --- kjøring
    def run(self, pid, event, data=None):
        m = self.manifest(pid)
        pdir = os.path.join(self.root, pid)
        perms = set(m.get("tillatelser") or [])
        payload = {"settings": self.get_settings(pid), "data": data or {}}
        if m["entry"].endswith(".py"):
            res = run_python(pdir, m["entry"], event, payload, perms)
        else:
            acts = []
            for s in load_skills(pdir, m):
                if (s.get("when") or {}).get("event") == event:
                    acts.extend(s.get("do") if isinstance(s.get("do"), list) else [s.get("do") or {}])
            res = {"actions": acts}
        if res.get("error"):
            self.errors[pid] = res["error"]
            return res
        res["actions"] = allowed_actions(res.get("actions"), perms)
        return res

    def due_schedules(self, tm):
        """[(pid, event)] for plugins med tillatelsen schedule som har en tid nå ('schedule': [{time, days?, event}])."""
        hm = "%02d:%02d" % (tm.tm_hour, tm.tm_min)
        out = []
        for m in self.installed():
            if m.get("error") or not m.get("enabled", True) or "schedule" not in (m.get("tillatelser") or []):
                continue
            sched = list(m.get("schedule") or [])
            try:
                sched += [{"event": (s.get("when") or {}).get("event", "tick"), **(s.get("when") or {})}
                          for s in load_skills(os.path.join(self.root, m["id"]), m) if (s.get("when") or {}).get("time")]
            except Exception:
                pass
            vals = m.get("settingsValues") or {}
            for s in sched:
                t = vals.get(s["time"][1:]) if str(s.get("time", "")).startswith("$") else s.get("time")
                if t == hm and (not s.get("days") or tm.tm_wday in s["days"]):
                    key = f"{m['id']}|{s.get('event')}|{tm.tm_yday}|{hm}"
                    if key not in self.fired:
                        self.fired.add(key)
                        out.append((m["id"], s.get("event", "tick")))
        return out

    def broadcast(self, event, data=None):
        acts = []
        for m in self.installed():
            if m.get("error") or not m.get("enabled", True):
                continue
            ev = set(m.get("events") or [])
            if event in ev:
                acts += self.run(m["id"], event, data).get("actions") or []
        return acts


def routes(ctx):
    st = Store(ctx.get("root") or ROOT, ctx.get("version", "0"))
    ctx["store"] = st

    def do(actions):
        for a in actions or []:
            try:
                if "toast" in a: ctx["toast"](a["toast"], a.get("sub", ""))
                elif "play" in a: ctx["play_url"](a["play"], a.get("title") or "Plugin")
                elif "announce" in a: ctx["announce"](a["announce"])
                elif "volume" in a: ctx["volume_set"](max(0, min(60, int(a["volume"]))))
                elif "navidrome_random" in a: ctx["nd_random"]()
            except Exception as e:
                print("plugin-handling:", a, e, flush=True)
    ctx["store_event"] = lambda ev, data=None: do(st.broadcast(ev, data))

    def loop():
        while True:
            try:
                for pid, ev in st.due_schedules(time.localtime()):
                    do(st.run(pid, ev).get("actions"))
            except Exception as e:
                print("plugin-planlegger:", e, flush=True)
            time.sleep(20)
    threading.Thread(target=loop, daemon=True).start()

    import asyncio

    async def bg(fn, *a):
        return await asyncio.get_running_loop().run_in_executor(None, fn, *a)

    def mask(m):
        vals = dict(m.get("settingsValues") or {})
        for k, sch in (m.get("settings") or {}).items():
            if (sch or {}).get("type") == "password" and vals.get(k):
                vals[k] = "••••••"
        return {**m, "settingsValues": vals}

    async def h_list(_r):
        return web.json_response({"installed": [mask(m) for m in st.installed()], "dir": st.root})

    async def h_catalog(_r):
        try:
            return web.json_response(await bg(st.catalog))
        except Exception as e:
            return web.json_response({"plugins": [], "error": f"Fikk ikke hentet katalogen: {e}"})

    async def h_post(r):
        ct = r.headers.get("Content-Type", "")
        try:
            if ct.startswith("multipart/"):
                rd = await r.multipart()
                data, sha = b"", ""
                async for part in rd:
                    if part.name == "file":
                        data = await part.read(decode=False)
                    elif part.name == "sha256":
                        sha = (await part.text()).strip()
                m = await bg(st.install_zip, data, sha or None)
                return web.json_response({"ok": True, "installed": m["id"]})
            b = await r.json()
            if b.get("install"):
                m = await bg(st.install_from_catalog, b["install"])
            elif b.get("url"):
                m = await bg(st.install_url, b["url"], b.get("sha256"))
            elif b.get("remove"):
                st.remove(b["remove"]); return web.json_response({"ok": True})
            elif b.get("settings") and b.get("id"):
                v = dict(b["settings"])
                for k in [k for k, x in v.items() if x == "••••••"]:
                    v.pop(k)
                return web.json_response({"ok": True, "settings": st.set_settings(b["id"], v)})
            elif b.get("run") and b.get("id"):
                res = await bg(st.run, b["id"], b["run"])
                do(res.get("actions")); return web.json_response(res)
            else:
                return web.json_response({"error": "ukjent forespørsel"}, status=400)
            return web.json_response({"ok": True, "installed": m["id"], "versjon": m.get("versjon")})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    return [web.get("/api/store", h_list), web.get("/api/store/catalog", h_catalog), web.post("/api/store", h_post)]
