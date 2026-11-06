"""Skjold – ekstra plugins: Roon-endepunkt (RoonBridge), Plexamp headless, backup/gjenoppretting, automatisk standby og
«Skjold Wrapped» (årsoppsummering). Ingen tunge installasjoner ved import – alt starter når brukeren ber om det.

Modulen er fri for daemon-globaler; daemonen sender inn det den trenger (status, callbacks)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import subprocess
import threading
import time

# ---------------------------------------------------------------- jobber (installasjon i bakgrunnen)
_jobs: dict = {}   # navn → {"busy", "ok", "log", "t"}


def job(name):
    return _jobs.setdefault(name, {"busy": False, "ok": None, "log": "", "t": 0.0})


def run_job(name, argv, env=None, stdin_text=None, timeout=1800):
    """Kjører en kommando i bakgrunnen og samler loggen (siste 6000 tegn)."""
    j = job(name)
    if j["busy"]:
        return False
    j.update(busy=True, ok=None, log="", t=time.time())

    def go():
        try:
            p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE if stdin_text else None,
                                 text=True, env={**os.environ, **(env or {})})
            if stdin_text:
                try:
                    p.stdin.write(stdin_text); p.stdin.flush(); p.stdin.close()
                except Exception:
                    pass
            t0 = time.time()
            for line in p.stdout:
                j["log"] = (j["log"] + line)[-6000:]
                if time.time() - t0 > timeout:
                    p.kill(); j["log"] += "\nAvbrutt: tok for lang tid\n"; break
            j["ok"] = p.wait() == 0
        except Exception as e:
            j["log"] += f"\nFeil: {e}\n"; j["ok"] = False
        finally:
            j["busy"] = False
    threading.Thread(target=go, daemon=True).start()
    return True


def service_state(unit):
    try:
        r = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "ukjent"
    except Exception:
        return "ukjent"


def service_ctl(unit, action):
    if action not in ("start", "stop", "restart", "enable", "disable"):
        raise ValueError("ukjent handling")
    subprocess.run(["systemctl", action, unit], capture_output=True, timeout=30)


def arch():
    m = platform.machine().lower()
    if m in ("aarch64", "arm64"):
        return "armv8"
    if m in ("x86_64", "amd64"):
        return "x64"
    if m.startswith("armv7"):
        return "armv7hf"
    return m


# ---------------------------------------------------------------- Roon (RoonBridge)
ROON_DIR = "/opt/RoonBridge"
ROON_UNIT = "roonbridge"
ROON_ALSA = "skjold_roon"


def roon_installer_url(a=None):
    a = a or arch()
    if a not in ("armv8", "x64", "armv7hf"):
        raise ValueError(f"RoonBridge finnes ikke for {a}")
    return f"https://download.roonlabs.net/builds/roonbridge-installer-linux{a}.sh"


def roon_install_cmd(a=None):
    """Offisielt installasjonsskript fra Roon Labs. «yes» svarer ja på spørsmålene."""
    url = roon_installer_url(a)
    return ["bash", "-c", f"set -e; f=$(mktemp); curl -fsSL -o \"$f\" {url}; chmod +x \"$f\"; yes | \"$f\"; rm -f \"$f\""]


def roon_installed(base=ROON_DIR):
    return os.path.isdir(base)


def roon_status():
    inst = roon_installed()
    return {"installed": inst, "service": service_state(ROON_UNIT) if inst else "mangler", "alsa": ROON_ALSA,
            "job": dict(job("roon")), "hint": f"Velg «{ROON_ALSA}» under Roon → Innstillinger → Lyd, og slå den på."}


def pcm_open_by(names, proc="/proc"):
    """Har en prosess med et av navnene en ALSA-avspillingsenhet (/dev/snd/pcmC*p) åpen?"""
    try:
        pids = [p for p in os.listdir(proc) if p.isdigit()]
    except Exception:
        return False
    for pid in pids:
        try:
            with open(os.path.join(proc, pid, "comm")) as fh:
                comm = fh.read().strip()
        except Exception:
            continue
        if comm not in names:
            continue
        fd = os.path.join(proc, pid, "fd")
        try:
            for f in os.listdir(fd):
                try:
                    t = os.readlink(os.path.join(fd, f))
                except Exception:
                    continue
                if re.match(r"/dev/snd/pcmC\d+D\d+p$", t):
                    return True
        except Exception:
            continue
    return False


def roon_playing():
    return roon_installed() and pcm_open_by({"RAATServer", "RoonBridge", "RoonBridgeHelp"})


# ---------------------------------------------------------------- Plexamp headless
PLEX_HOME = "/var/lib/ki-plex"
PLEX_UNIT = "ki-plex"


def plex_install_cmd(script, user="pi"):
    """pi/install_plex.sh uten interaktiv innlogging (den gjøres med claim-koden fra web-UI-et)."""
    return ["sudo", "-u", user, "env", "KI_PLEX_SKIP_LOGIN=1", "bash", script]


def plex_claim_cmd(home=PLEX_HOME):
    return ["sudo", "-u", "ki-plex", "-H", "bash", "-c", f"cd {home}/plexamp && exec timeout 90 /usr/bin/node js/index.js"]


def plex_claim_input(code, name):
    code = re.sub(r"[^A-Za-z0-9-]", "", str(code or ""))
    if not code.startswith("claim-") or len(code) < 10:
        raise ValueError("claim-koden starter med «claim-» (hent den på plex.tv/claim)")
    return f"{code}\n{str(name or 'Skjold')[:40]}\n"


def plex_installed(home=PLEX_HOME):
    return os.path.isdir(os.path.join(home, "plexamp")) or os.path.isdir(os.path.join(home, "caldera-music"))


def plex_signed_in(home=PLEX_HOME):
    d = os.path.join(home, ".local", "share", "Plexamp")
    for root, _dirs, files in os.walk(d):
        if any("token" in f.lower() for f in files):
            return True
    return False


def plex_status():
    inst = plex_installed()
    return {"installed": inst, "signed_in": inst and plex_signed_in(), "service": service_state(PLEX_UNIT) if inst else "mangler",
            "job": dict(job("plex")), "claim": dict(job("plex_claim")), "web": "https://listen.plex.tv"}


# ---------------------------------------------------------------- Backup og gjenoppretting
SECRET_KEYS = {"password", "smb_password", "token", "secret", "session", "key", "pin", "ndPass", "ytmCookie", "plexToken"}
BACKUP_VERSION = 1


def _ks(key, n):
    """Nøkkelstrøm: SHA-256 i tellermodus (bare standardbiblioteket)."""
    out = b""
    i = 0
    while len(out) < n:
        out += hashlib.sha256(key + i.to_bytes(8, "big")).digest(); i += 1
    return out[:n]


def encrypt(obj, passphrase):
    salt = secrets.token_bytes(16)
    k = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 200_000, 64)
    ek, mk = k[:32], k[32:]
    nonce = secrets.token_bytes(16)
    data = json.dumps(obj).encode()
    ct = bytes(a ^ b for a, b in zip(data, _ks(ek + nonce, len(data))))
    tag = hmac.new(mk, nonce + ct, hashlib.sha256).digest()
    return {"alg": "pbkdf2-sha256-ctr-hmac", "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode(),
            "data": base64.b64encode(ct).decode(), "tag": base64.b64encode(tag).decode()}


def decrypt(blob, passphrase):
    salt, nonce = base64.b64decode(blob["salt"]), base64.b64decode(blob["nonce"])
    ct, tag = base64.b64decode(blob["data"]), base64.b64decode(blob["tag"])
    k = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 200_000, 64)
    ek, mk = k[:32], k[32:]
    if not hmac.compare_digest(tag, hmac.new(mk, nonce + ct, hashlib.sha256).digest()):
        raise ValueError("feil passfrase, eller filen er endret")
    return json.loads(bytes(a ^ b for a, b in zip(ct, _ks(ek + nonce, len(ct)))))


def split_secrets(obj, path=()):
    """Tar hemmeligheter ut av en innstillingsstruktur. Gir (renset kopi, {sti: verdi})."""
    found = {}

    def walk(o, p):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k in SECRET_KEYS and isinstance(v, str) and v:
                    found[".".join(p + (k,))] = v
                    out[k] = ""
                else:
                    out[k] = walk(v, p + (k,))
            return out
        if isinstance(o, list):
            return [walk(v, p + (str(i),)) for i, v in enumerate(o)]
        return o
    return walk(obj, tuple(path)), found


def put_secrets(obj, found):
    for path, v in found.items():
        cur = obj
        parts = path.split(".")
        try:
            for p in parts[:-1]:
                cur = cur[int(p)] if isinstance(cur, list) else cur[p]
            cur[parts[-1]] = v
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return obj


def make_backup(state, device, extra_files=None, secrets_mode="exclude", passphrase=""):
    """state: daemonens state-dict. secrets_mode: exclude | encrypt. extra_files: {navn: sti} (f.eks. HomeKit-paringer)."""
    keep = {k: state[k] for k in ("settings", "presets", "preset", "levels", "loudness", "loudness_level", "voice", "voice_profile",
                                  "auto_input", "mix", "hp_automute", "volume") if k in state}
    clean, found = split_secrets(keep)
    out = {"skjold_backup": BACKUP_VERSION, "created": int(time.time()), "device": device, "state": clean, "secrets": None, "files": {}}
    if found:
        if secrets_mode == "encrypt":
            if len(passphrase) < 6:
                raise ValueError("passfrasen må være minst 6 tegn")
            out["secrets"] = encrypt(found, passphrase)
        else:
            out["secrets_omitted"] = sorted(found)
    for name, path in (extra_files or {}).items():
        try:
            with open(path, "rb") as fh:
                out["files"][name] = base64.b64encode(fh.read()).decode()
        except OSError:
            pass
    return out


def preview_restore(current, backup, mode="settings"):
    """Hva som endres: liste over toppnivå-nøkler og innstillinger som er forskjellige."""
    if not isinstance(backup, dict) or backup.get("skjold_backup") != BACKUP_VERSION:
        raise ValueError("ikke en Skjold-backup (eller ukjent versjon)")
    b = backup.get("state") or {}
    ch = []
    cs, bs = current.get("settings") or {}, b.get("settings") or {}
    for k in sorted(set(cs) | set(bs)):
        if k == "plugins" and mode != "all":
            continue
        if cs.get(k) != bs.get(k) and k in bs:
            ch.append("innstilling: " + k)
    if mode == "all":
        for pid in sorted(set((bs.get("plugins") or {})) | set((cs.get("plugins") or {}))):
            if (bs.get("plugins") or {}).get(pid) != (cs.get("plugins") or {}).get(pid) and pid in (bs.get("plugins") or {}):
                ch.append("plugin: " + pid)
        for f in sorted(backup.get("files") or {}):
            ch.append("fil: " + f)
    for k in ("presets", "levels", "volume", "loudness", "loudness_level"):
        if k in b and current.get(k) != b.get(k):
            ch.append(k)
    return {"changes": ch, "device": backup.get("device"), "created": backup.get("created"),
            "has_secrets": bool(backup.get("secrets")), "secrets_omitted": backup.get("secrets_omitted") or []}


def apply_restore(state, backup, mode="settings", passphrase="", file_paths=None):
    """Skriver backupen inn i state (kaller må lagre og ta i bruk). mode: settings | all. Gir liste over filer som ble skrevet."""
    preview_restore(state, backup, mode)
    b = json.loads(json.dumps(backup.get("state") or {}))
    if backup.get("secrets"):
        if not passphrase:
            raise ValueError("backupen har krypterte passord – skriv inn passfrasen")
        put_secrets(b, decrypt(backup["secrets"], passphrase))
    cur_settings = state.setdefault("settings", {})
    bs = b.get("settings") or {}
    for k, v in bs.items():
        if k == "plugins" and mode != "all":
            continue
        if k == "plugins":
            merged = {}
            for pid, cfg in v.items():
                old = (cur_settings.get("plugins") or {}).get(pid) or {}
                # tomme hemmeligheter (utelatt i backupen) skal ikke slette dem som finnes
                merged[pid] = {kk: (old.get(kk, vv) if kk in SECRET_KEYS and vv == "" else vv) for kk, vv in cfg.items()}
            cur_settings["plugins"] = {**(cur_settings.get("plugins") or {}), **merged}
        elif k in SECRET_KEYS and v == "":
            continue
        else:
            cur_settings[k] = v
    for k in ("presets", "preset", "levels", "loudness", "loudness_level", "voice", "voice_profile", "auto_input", "mix", "hp_automute", "volume"):
        if k in b:
            state[k] = b[k]
    written = []
    if mode == "all":
        for name, data in (backup.get("files") or {}).items():
            path = (file_paths or {}).get(name)
            if not path:
                continue
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + ".tmp", "wb") as fh:
                    fh.write(base64.b64decode(data))
                os.replace(path + ".tmp", path); written.append(name)
            except OSError:
                pass
    return written


def backup_filename(device_name, t=None):
    t = time.localtime(t or time.time())
    safe = re.sub(r"[^A-Za-z0-9æøåÆØÅ_-]+", "-", device_name or "skjold").strip("-") or "skjold"
    return "skjold-backup-%s-%04d%02d%02d-%02d%02d.json" % (safe, t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)


def rotate_backups(folder, keep=14):
    try:
        fs = sorted(f for f in os.listdir(folder) if f.startswith("skjold-backup-") and f.endswith(".json"))
    except OSError:
        return []
    gone = fs[:-keep] if len(fs) > keep else []
    for f in gone:
        try:
            os.remove(os.path.join(folder, f))
        except OSError:
            pass
    return gone


# ---------------------------------------------------------------- Automatisk standby
class AutoStandby:
    """Teller tid uten lyd. idle_s nullstilles når noe spiller (eller er satt på pause, hvis pause ikke teller)."""

    def __init__(self):
        self.idle_s = 0.0
        self.last = None

    def tick(self, now, minutes, power, playing, paused=False, pause_counts=True):
        """Gir True når enheten skal i standby nå."""
        dt = 0.0 if self.last is None else max(0.0, min(30.0, now - self.last))
        self.last = now
        if not power or not minutes:
            self.idle_s = 0.0
            return False
        if playing or (paused and not pause_counts):
            self.idle_s = 0.0
            return False
        self.idle_s += dt
        return self.idle_s >= minutes * 60

    def left(self, minutes):
        return max(0, int(round(minutes * 60 - self.idle_s))) if minutes else 0


# ---------------------------------------------------------------- Skjold Wrapped
class Wrapped:
    """Årlige tellere i egen fil, så årsoppsummeringen ikke er begrenset av de siste 500 i historikken."""

    def __init__(self, path):
        self.path = path
        self.data = None
        self.lock = threading.Lock()
        self.session = {"start": 0.0, "last": 0.0}
        self._dirty = 0.0

    def _load(self):
        if self.data is None:
            try:
                with open(self.path) as fh:
                    self.data = json.load(fh)
            except Exception:
                self.data = {}
        return self.data

    def _year(self, t):
        y = str(time.localtime(t).tm_year)
        d = self._load()
        return d.setdefault(y, {"minutes": 0.0, "by_input": {}, "artists": {}, "tracks": {}, "stations": {}, "days": {}, "hours": {},
                                "longest": 0.0, "plays": 0, "rooms": []})

    def listen(self, t, dt, inp, room=""):
        """Kalles jevnlig mens noe spiller: dt sekunder lytting."""
        if dt <= 0:
            return
        with self.lock:
            y = self._year(t)
            m = dt / 60.0
            y["minutes"] += m
            y["by_input"][inp or "ukjent"] = y["by_input"].get(inp or "ukjent", 0.0) + m
            lt = time.localtime(t)
            day = "%04d-%02d-%02d" % (lt.tm_year, lt.tm_mon, lt.tm_mday)
            y["days"][day] = y["days"].get(day, 0.0) + m
            y["hours"][str(lt.tm_hour)] = y["hours"].get(str(lt.tm_hour), 0.0) + m
            if room and room not in y["rooms"]:
                y["rooms"].append(room)
            s = self.session
            if not s["start"] or t - s["last"] > 300:
                s["start"] = t
            s["last"] = t
            y["longest"] = max(y["longest"], (t - s["start"]) / 60.0)
            self._dirty += dt
        if self._dirty >= 60:
            self.save()

    def track(self, t, artist, title, station=""):
        with self.lock:
            y = self._year(t)
            y["plays"] += 1
            if artist:
                y["artists"][artist] = y["artists"].get(artist, 0) + 1
            if artist and title:
                k = f"{artist} – {title}"
                y["tracks"][k] = y["tracks"].get(k, 0) + 1
            if station:
                y["stations"][station] = y["stations"].get(station, 0) + 1
        self.save()

    def save(self):
        with self.lock:
            self._dirty = 0.0
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path + ".tmp", "w") as fh:
                    json.dump(self._load(), fh)
                os.replace(self.path + ".tmp", self.path)
            except OSError:
                pass

    def summary(self, year):
        with self.lock:
            y = (self._load().get(str(year)) or {})
        if not y:
            return {"year": int(year), "empty": True}

        def top(d, n=5):
            return [{"name": k, "count": round(v, 1) if isinstance(v, float) else v} for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n]]
        days = y.get("days") or {}
        hours = y.get("hours") or {}
        bd = max(days.items(), key=lambda kv: kv[1]) if days else (None, 0)
        bh = max(hours.items(), key=lambda kv: kv[1]) if hours else (None, 0)
        return {"year": int(year), "empty": False, "minutes": int(round(y.get("minutes", 0))), "plays": y.get("plays", 0),
                "by_input": top(y.get("by_input") or {}, 8), "artists": top(y.get("artists") or {}), "tracks": top(y.get("tracks") or {}),
                "stations": top(y.get("stations") or {}), "busiest_day": {"date": bd[0], "minutes": int(round(bd[1]))},
                "busiest_hour": {"hour": int(bh[0]) if bh[0] is not None else None, "minutes": int(round(bh[1]))},
                "longest_session": int(round(y.get("longest", 0))), "rooms": len(y.get("rooms") or []), "days_listened": len(days)}

    def years(self):
        with self.lock:
            return sorted((int(k) for k in self._load()), reverse=True)
