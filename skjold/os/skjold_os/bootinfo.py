"""Oppstartstid og overlevering fra skjold-early.service (skjold/node/early/skjold_early.py).

  /run/skjold/os-display   Skjold OS har tatt skjermen (skjold-early slutter å tegne)
  /run/skjold/os-ready     Skjold OS har kontakt med daemonen (skjold-early slipper LED-ene, daemonen slutter LED-jaget)
  /var/lib/skjold/boot_time  {"avg": s, "last": s, "n": antall} – sekunder fra kjernen startet til os-ready (glidende snitt)
"""
import json, os, time

RUN = os.environ.get("SKJOLD_RUN_DIR", "/run/skjold")
BOOT_TIME = os.environ.get("SKJOLD_BOOT_TIME", "/var/lib/skjold/boot_time")
DEFAULT_S = 45.0
ALPHA = 0.4          # vekt på siste måling i snittet


def uptime():
    try:
        with open("/proc/uptime") as f: return float(f.read().split()[0])
    except (OSError, ValueError): return 0.0


def read():
    try:
        with open(BOOT_TIME) as f: v = json.load(f)
        return v if isinstance(v, dict) else {"avg": float(v), "last": float(v), "n": 1}
    except (OSError, ValueError, TypeError):
        return None


def estimate():
    v = read()
    try: return max(5.0, min(600.0, float(v["avg"])))
    except (TypeError, KeyError, ValueError): return DEFAULT_S


def _touch(name):
    try:
        os.makedirs(RUN, exist_ok=True); open(os.path.join(RUN, name), "w").close()
    except OSError:
        pass


def mark_display(): _touch("os-display")


def mark_ready():
    """Kalles én gang når daemonen svarer. Måler oppstarten bare første gang etter en omstart (oppetid < 10 min)."""
    first = not os.path.exists(os.path.join(RUN, "os-ready"))
    _touch("os-ready")
    up = uptime()
    if not first or not (3 < up < 600): return None
    old = read() or {}
    try: avg = float(old["avg"]) * (1 - ALPHA) + up * ALPHA if old.get("n") else up
    except (TypeError, ValueError, KeyError): avg = up
    rec = {"avg": round(avg, 1), "last": round(up, 1), "n": int(old.get("n") or 0) + 1, "t": int(time.time())}
    try:
        os.makedirs(os.path.dirname(BOOT_TIME), exist_ok=True)
        with open(BOOT_TIME + ".tmp", "w") as f: json.dump(rec, f)
        os.replace(BOOT_TIME + ".tmp", BOOT_TIME)
    except OSError:
        pass
    print("Oppstart: %.1f s (snitt %.1f s)" % (up, avg), flush=True)
    return rec
