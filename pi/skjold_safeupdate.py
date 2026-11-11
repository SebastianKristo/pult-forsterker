#!/usr/bin/env python3
"""Trygg oppdatering: øyeblikksbilde før oppdatering, helsesjekk etterpå og automatisk tilbakerulling.

  skjold_safeupdate.py snapshot <kildetre>   → lager /var/lib/skjold/rollback/<tid>/ og skriver «pending»
  skjold_safeupdate.py check                  → venter inntil 120 s på at Skjold svarer; ruller tilbake hvis ikke
  skjold_safeupdate.py rollback [grunn]       → legger tilbake forrige øyeblikksbilde og starter tjenestene på nytt

Helsesjekken kjøres av skjold-healthcheck.service (etter oppdatering og ved oppstart).
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.environ.get("SKJOLD_ROLLBACK_DIR", "/var/lib/skjold/rollback")
PENDING = os.path.join(ROOT, "pending.json")
UPD_LOG = os.environ.get("SKJOLD_UPD_LOG", "/var/log/skjold-update.log")
KEEP = 3
FILES = ["/usr/local/bin/ki_amp_daemon.py", "/usr/local/bin/skjold_*.py", "/usr/local/bin/oled_*.py", "/usr/local/bin/tft_screen.py",
         "/etc/systemd/system/ki-amp.service", "/etc/systemd/system/skjold-*.service", "/etc/ki-amp.env",
         "/usr/local/share/ki-amp/release", "/usr/local/share/ki-amp/src"]
DIRS = ["/usr/local/share/ki-amp/webapp"]
SERVICES = ["ki-amp"]
OPTIONAL_SERVICES = ["skjold-ui"]


def _log(msg: str) -> None:
    print(msg, flush=True)
    try:
        with open(UPD_LOG, "a") as fh:
            fh.write(msg + "\n")
    except OSError:
        pass


def _git(src: str, *args: str) -> str:
    r = subprocess.run(["git", "-c", "safe.directory=*", "-C", src, *args], capture_output=True, text=True, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def snapshot(src: str, root: str = ROOT, files=FILES, dirs=DIRS) -> str:
    d = os.path.join(root, time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.join(d, "files"), exist_ok=True)
    saved = []
    for pat in files:
        for f in glob.glob(pat):
            if os.path.isfile(f):
                dst = os.path.join(d, "files", f.lstrip("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(f, dst); saved.append(f)
    for dd in dirs:
        if os.path.isdir(dd):
            shutil.copytree(dd, os.path.join(d, "files", dd.lstrip("/")), dirs_exist_ok=True); saved.append(dd + "/")
    meta = {"t": time.time(), "src": src, "rev": _git(src, "rev-parse", "HEAD") if src else "",
            "branch": _git(src, "rev-parse", "--abbrev-ref", "HEAD") if src else "", "files": saved}
    with open(os.path.join(d, "meta.json"), "w") as fh:
        json.dump(meta, fh)
    with open(os.path.join(root, "pending.json"), "w") as fh:
        json.dump({"snapshot": d, "t": time.time()}, fh)
    for old in sorted(glob.glob(os.path.join(root, "2*")))[:-KEEP]:
        shutil.rmtree(old, ignore_errors=True)
    return d


def latest(root: str = ROOT) -> str | None:
    snaps = sorted(glob.glob(os.path.join(root, "2*")))
    return snaps[-1] if snaps else None


def restore(d: str, run=subprocess.run) -> dict:
    with open(os.path.join(d, "meta.json")) as fh:
        meta = json.load(fh)
    base = os.path.join(d, "files")
    for dirpath, _dirs, names in os.walk(base):
        for n in names:
            srcf = os.path.join(dirpath, n)
            dst = "/" + os.path.relpath(srcf, base)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(srcf, dst)
    if meta.get("src") and meta.get("rev"):
        br = meta.get("branch") or "main"
        if br == "HEAD":
            run(["git", "-c", "safe.directory=*", "-C", meta["src"], "checkout", "-q", "--detach", meta["rev"]], check=False)
        else:
            run(["git", "-c", "safe.directory=*", "-C", meta["src"], "checkout", "-q", "-B", br, meta["rev"]], check=False)
    if meta.get("src") and os.path.isdir(meta["src"]):   # checkout som root: gi filene tilbake til eieren av kildetreet
        st = os.stat(meta["src"])
        run(["chown", "-R", f"{st.st_uid}:{st.st_gid}", meta["src"]], check=False)
    run(["systemctl", "daemon-reload"], check=False)
    for s in SERVICES + OPTIONAL_SERVICES:
        # skjold-ui finnes bare på S1 rev F – ikke prøv å starte tjenester som ikke er installert
        if s in OPTIONAL_SERVICES and not os.path.exists(f"/etc/systemd/system/{s}.service"):
            continue
        run(["systemctl", "try-restart", s], check=False)
    return meta


def healthy(url: str = "http://127.0.0.1:8765/api/status", is_active=None) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            d = json.loads(r.read())
            if not isinstance(d, dict) or "volume" not in d:
                return False, "status-svaret mangler felter"
    except Exception as e:
        return False, f"svarer ikke på /api/status ({e.__class__.__name__})"
    act = is_active or (lambda s: subprocess.run(["systemctl", "is-active", "--quiet", s], check=False).returncode == 0)
    for s in SERVICES:
        if not act(s):
            return False, f"tjenesten {s} kjører ikke"
    return True, ""


def check(timeout: float = 120.0, root: str = ROOT, probe=healthy, do_restore=restore, sleep=time.sleep) -> str:
    """Kjøres etter oppdatering/oppstart. «ok», «ingen» (ingenting å sjekke) eller «rullet tilbake: <grunn>»."""
    pend = os.path.join(root, "pending.json")
    if not os.path.exists(pend):
        return "ingen"
    with open(pend) as fh:
        snap = json.load(fh).get("snapshot")
    end, why = time.time() + timeout, ""
    while time.time() < end:
        ok, why = probe()
        if ok:
            os.unlink(pend)
            _log("== Helsesjekk etter oppdatering: OK")
            return "ok"
        sleep(5)
    _log(f"== Helsesjekk feilet: {why} – ruller tilbake")
    if snap and os.path.isdir(snap):
        do_restore(snap)
    try:
        os.unlink(pend)
    except OSError:
        pass
    res = f"rullet tilbake: {why}"
    _log("SKJOLD-RESULTAT: " + res)
    return res


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "check"
    os.makedirs(ROOT, exist_ok=True)
    if cmd == "snapshot":
        print(snapshot(argv[2] if len(argv) > 2 else ""))
    elif cmd == "check":
        print(check())
    elif cmd == "rollback":
        d = latest()
        if not d:
            print("ingen øyeblikksbilder"); return 1
        restore(d)
        _log("SKJOLD-RESULTAT: rullet tilbake: " + (" ".join(argv[2:]) or "manuelt"))
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
