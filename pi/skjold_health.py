"""Skjold – helsesjekk og feilrapport.

GET /api/health samler maskin- og tjenestestatus, og gir hver post et nivå (ok / advarsel / feil) med forklaring på
norsk. GET /api/health/report gir en anonymisert rapport (passord, tokens og IP-adresser maskert) som kan lastes ned,
kopieres eller legges i en GitHub-sak.
"""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse

from aiohttp import web

SERVICES = ["ki-amp", "camilladsp", "shairport-sync", "squeezelite", "lyrion", "nqptp", "skjold-ui", "raspotify"]
ISSUE_URL = "https://github.com/SebastianKristo/pult-forsterker/issues/new"
RANK = {"ok": 0, "advarsel": 1, "feil": 2}


def sh(cmd, timeout=5):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:
        return ""


def read(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except Exception:
        return ""


# ---------------------------------------------------------------- vurdering (rene funksjoner)
def item(key, navn, verdi, niva, forklaring):
    return {"key": key, "navn": navn, "verdi": verdi, "niva": niva, "forklaring": forklaring}


def assess_temp(c):
    if c is None:
        return item("cpu_temp", "CPU-temperatur", None, "ok", "Temperaturen er ikke tilgjengelig på denne maskinen.")
    if c >= 80:
        return item("cpu_temp", "CPU-temperatur", c, "feil", f"{c:.0f} °C er for varmt – Pi-en struper ytelsen. Sjekk kjøling og lufting.")
    if c >= 70:
        return item("cpu_temp", "CPU-temperatur", c, "advarsel", f"{c:.0f} °C er varmt. Sørg for luft rundt kabinettet.")
    return item("cpu_temp", "CPU-temperatur", c, "ok", f"{c:.0f} °C – fin temperatur.")


THROTTLE_BITS = {0: "for lav spenning nå", 1: "frekvens begrenset nå", 2: "strupet nå", 3: "temperaturgrense nå",
                 16: "for lav spenning tidligere", 17: "frekvens begrenset tidligere", 18: "strupet tidligere", 19: "temperaturgrense tidligere"}


def assess_throttle(hexval):
    if hexval is None:
        return item("throttling", "Strøm og struping", None, "ok", "vcgencmd finnes ikke – kan ikke sjekkes.")
    v = int(hexval, 16)
    now = [t for b, t in THROTTLE_BITS.items() if b < 16 and v & (1 << b)]
    past = [t for b, t in THROTTLE_BITS.items() if b >= 16 and v & (1 << b)]
    if now:
        return item("throttling", "Strøm og struping", hexval, "feil", "Problem nå: " + ", ".join(now) + ". Bruk en kraftigere strømforsyning (5 V / 3–5 A).")
    if past:
        return item("throttling", "Strøm og struping", hexval, "advarsel", "Har skjedd siden oppstart: " + ", ".join(past) + ". Følg med på strømforsyningen.")
    return item("throttling", "Strøm og struping", hexval, "ok", "Ingen spenningsfall eller struping.")


def assess_load(load1, cpus):
    r = load1 / max(1, cpus)
    if r >= 2:
        return item("load", "Belastning", round(load1, 2), "feil", f"Svært høy belastning ({load1:.1f} på {cpus} kjerner). Noe henger kanskje.")
    if r >= 1:
        return item("load", "Belastning", round(load1, 2), "advarsel", f"Høy belastning ({load1:.1f} på {cpus} kjerner).")
    return item("load", "Belastning", round(load1, 2), "ok", f"{load1:.1f} på {cpus} kjerner – normalt.")


def assess_pct(key, navn, used_pct, warn, err, hva):
    if used_pct is None:
        return item(key, navn, None, "ok", "Ikke tilgjengelig.")
    if used_pct >= err:
        return item(key, navn, used_pct, "feil", f"{hva} er {used_pct:.0f} % full. Frigjør plass nå.")
    if used_pct >= warn:
        return item(key, navn, used_pct, "advarsel", f"{hva} er {used_pct:.0f} % full.")
    return item(key, navn, used_pct, "ok", f"{used_pct:.0f} % brukt.")


def assess_service(name, st):
    if st == "active":
        return item("svc:" + name, name, st, "ok", "Kjører.")
    if st in ("", "unknown", "inactive") and name in ("raspotify", "lyrion", "skjold-ui"):
        return item("svc:" + name, name, st or "ikke installert", "ok", "Ikke i bruk på denne enheten.")
    if st == "failed":
        return item("svc:" + name, name, st, "feil", f"Tjenesten har krasjet. Se loggen: journalctl -u {name}")
    if st in ("activating", "reloading"):
        return item("svc:" + name, name, st, "advarsel", "Starter …")
    return item("svc:" + name, name, st or "ukjent", "advarsel", "Kjører ikke.")


def assess_wifi(signal_dbm, online):
    if not online:
        return item("network", "Nettverk", None, "feil", "Ingen nettverkstilkobling.")
    if signal_dbm is None:
        return item("network", "Nettverk", "kablet", "ok", "Tilkoblet.")
    if signal_dbm <= -75:
        return item("network", "Nettverk", signal_dbm, "advarsel", f"Svakt WiFi-signal ({signal_dbm} dBm). Kan gi hakking i strømmer.")
    return item("network", "Nettverk", signal_dbm, "ok", f"WiFi {signal_dbm} dBm – godt signal.")


def overall(items):
    worst = max((RANK[i["niva"]] for i in items), default=0)
    return [k for k, v in RANK.items() if v == worst][0]


# ---------------------------------------------------------------- maskering
SECRET_KEYS = re.compile(r"(pass(word)?|pwd|token|secret|api[_-]?key|session|auth|pin|psk|passphrase)", re.I)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6 = re.compile(r"\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b", re.I)
MAC = re.compile(r"\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", re.I)
KV = re.compile(r"""(?P<k>["']?[\w-]*(?:pass(?:word)?|pwd|token|secret|api[_-]?key|auth|psk|passphrase)[\w-]*["']?\s*[:=]\s*)(?P<v>"[^"]*"|'[^']*'|[^\s,&}]+)""", re.I)
BEARER = re.compile(r"(Bearer\s+)[\w.\-~+/]+=*", re.I)
URLCRED = re.compile(r"(://)[^/\s:@]+:[^/\s@]+@")
QS = re.compile(r"([?&](?:u|p|t|s|token|api_key|apikey|password)=)[^&\s]+", re.I)


def mask_text(s):
    s = BEARER.sub(r"\1•••", s)
    s = URLCRED.sub(r"\1•••:•••@", s)
    s = QS.sub(r"\1•••", s)
    s = KV.sub(lambda m: m.group("k") + ('"•••"' if m.group("v").startswith('"') else "•••"), s)
    s = IPV4.sub(lambda m: m.group(0) if m.group(0).startswith(("127.", "0.")) else "x.x.x." + m.group(0).rsplit(".", 1)[1], s)
    s = IPV6.sub("x:x:x:x", s)
    s = MAC.sub("xx:xx:xx:xx:xx:xx", s)
    return s


def mask_obj(o, key=""):
    if isinstance(o, dict):
        return {k: ("•••" if SECRET_KEYS.search(str(k)) and v not in ("", None, False) and not isinstance(v, (dict, list)) else mask_obj(v, k))
                for k, v in o.items()}
    if isinstance(o, list):
        return [mask_obj(x, key) for x in o]
    if isinstance(o, str):
        return mask_text(o)
    return o


def report_text(health, extra=None):
    h = mask_obj(health)
    lines = [f"# Skjold feilrapport", "", f"Versjon: {h.get('version', '?')}  ·  Tid: {time.strftime('%Y-%m-%d %H:%M')}",
             f"Samlet: {h.get('niva')}", "", "## Sjekker"]
    for i in h.get("items", []):
        lines.append(f"- [{i['niva']}] {i['navn']}: {i['forklaring']}")
    if h.get("aplay"):
        lines += ["", "## Lydkort (aplay -l)", "```", h["aplay"], "```"]
    if h.get("errors"):
        lines += ["", "## Siste feil i journalen", "```", *h["errors"][-50:], "```"]
    if extra:
        lines += ["", "## Annet", "```", mask_text(json.dumps(mask_obj(extra), ensure_ascii=False, indent=1)), "```"]
    return "\n".join(lines) + "\n"


def issue_link(text, title="Feilrapport fra Skjold"):
    body = text if len(text) < 6000 else text[:6000] + "\n… (forkortet – last ned hele rapporten og legg den ved)"
    return ISSUE_URL + "?" + urllib.parse.urlencode({"title": title, "body": body})


# ---------------------------------------------------------------- innsamling
def collect(ctx):
    items = []
    t = read("/sys/class/thermal/thermal_zone0/temp")
    items.append(assess_temp(int(t) / 1000 if t.isdigit() else None))
    thr = sh(["vcgencmd", "get_throttled"]) if shutil.which("vcgencmd") else ""
    items.append(assess_throttle(thr.split("=", 1)[1] if "=" in thr else None))
    try:
        l1 = os.getloadavg()[0]
    except Exception:
        l1 = 0.0
    items.append(assess_load(l1, os.cpu_count() or 1))
    mem = {}
    for ln in read("/proc/meminfo").splitlines():
        k, _, v = ln.partition(":")
        mem[k] = int((v.split() or ["0"])[0])
    mp = (100 - 100 * mem.get("MemAvailable", 0) / mem["MemTotal"]) if mem.get("MemTotal") else None
    items.append(assess_pct("memory", "Minne", round(mp, 1) if mp is not None else None, 85, 95, "Minnet"))
    try:
        du = shutil.disk_usage("/")
        items.append(assess_pct("disk", "Lagring", round(100 * du.used / du.total, 1), 85, 95, "Minnekortet"))
    except Exception:
        items.append(assess_pct("disk", "Lagring", None, 85, 95, "Minnekortet"))
    up = read("/proc/uptime").split()
    uptime = int(float(up[0])) if up else 0
    sig = None
    wl = read("/proc/net/wireless").splitlines()
    if len(wl) > 2:
        try: sig = int(float(wl[2].split()[3]))
        except Exception: pass
    online = bool(sh(["ip", "route", "show", "default"])) if shutil.which("ip") else True
    items.append(assess_wifi(sig, online))
    for s in SERVICES:
        st = sh(["systemctl", "is-active", s + ".service"]) if shutil.which("systemctl") else ""
        if not st and shutil.which("systemctl"):
            try:
                st = subprocess.run(["systemctl", "is-active", s + ".service"], capture_output=True, text=True, timeout=5).stdout.strip()
            except Exception:
                st = ""
        items.append(assess_service(s, st))
    aplay = sh(["aplay", "-l"]) if shutil.which("aplay") else ""
    if shutil.which("aplay"):
        items.append(item("aplay", "Lydkort", aplay.count("card "), "ok" if "card " in aplay else "feil",
                          "Lydkort funnet." if "card " in aplay else "Fant ingen lydkort. Sjekk DAC-en og config.txt."))
    for key, navn, fn in (("camilladsp", "CamillaDSP", ctx.get("camilla")), ("lyrion", "Lyrion", ctx.get("lyrion"))):
        if not fn:
            continue
        try:
            ok, txt = fn()
        except Exception as e:
            ok, txt = False, str(e)
        items.append(item(key, navn, txt, "ok" if ok else "advarsel", txt if ok else f"Svarer ikke: {txt}"))
    errors = []
    if shutil.which("journalctl"):
        errors = sh(["journalctl", "-p", "3", "-n", "50", "--no-pager", "-o", "short-iso", "-b"], timeout=8).splitlines()[-50:]
    if len(errors) >= 20:
        items.append(item("journal", "Feil i loggen", len(errors), "advarsel", f"{len(errors)} feilmeldinger siden oppstart. Se listen under."))
    upd = {}
    try:
        upd = ctx["update"]() if ctx.get("update") else {}
    except Exception:
        pass
    if upd.get("available"):
        items.append(item("update", "Programvare", upd.get("latest"), "advarsel", f"Ny versjon {upd.get('latest')} er klar. Oppdater under Innstillinger → System."))
    return {"niva": overall(items), "items": items, "uptime": uptime, "load": os.getloadavg() if hasattr(os, "getloadavg") else None,
            "aplay": aplay, "errors": errors, "version": ctx.get("version", "?"),
            "update": {k: upd.get(k) for k in ("current", "latest", "available", "can_rollback", "rollback") if k in upd},
            "time": time.time()}


# ---------------------------------------------------------------- ytelse (for Home Assistant, Homey og web)
PERF_SERVICES = ["ki-amp", "camilladsp", "ki-squeezelite", "squeezelite", "shairport-sync", "skjold-matter", "lyrion", "raspotify"]
_perf_prev = {"cpu": None, "svc": {}}


def parse_proc_stat(text):
    """(total, idle) jiffies fra første linje i /proc/stat."""
    for ln in text.splitlines():
        if ln.startswith("cpu "):
            v = [int(x) for x in ln.split()[1:]]
            idle = v[3] + (v[4] if len(v) > 4 else 0)
            return sum(v), idle
    return None


def cpu_pct(prev, cur):
    if not prev or not cur or cur[0] <= prev[0]:
        return None
    dt, di = cur[0] - prev[0], cur[1] - prev[1]
    return round(max(0.0, min(100.0, 100.0 * (dt - di) / dt)), 1)


def parse_throttled(hexval):
    """vcgencmd get_throttled → flagg. None når det ikke finnes (ikke Pi)."""
    if not hexval:
        return None
    try:
        v = int(hexval, 16)
    except ValueError:
        return None
    return {"raw": hexval, "under_voltage": bool(v & 1), "freq_capped": bool(v & 2), "throttled": bool(v & 4),
            "soft_temp_limit": bool(v & 8), "under_voltage_occurred": bool(v & 0x10000), "freq_capped_occurred": bool(v & 0x20000),
            "throttled_occurred": bool(v & 0x40000), "soft_temp_limit_occurred": bool(v & 0x80000),
            "power_problem": bool(v & 0x1 or v & 0x10000)}


def parse_meminfo(text):
    m = {}
    for ln in text.splitlines():
        k, _, v = ln.partition(":")
        try:
            m[k] = int((v.split() or ["0"])[0])
        except ValueError:
            pass
    tot, av = m.get("MemTotal", 0), m.get("MemAvailable", 0)
    if not tot:
        return None
    return {"total_mb": round(tot / 1024), "used_mb": round((tot - av) / 1024), "pct": round(100 - 100 * av / tot, 1)}


def service_usage(name, now, prev):
    """CPU % og minne for en systemd-tjeneste (CPUUsageNSec/MemoryCurrent); None hvis den ikke kjører."""
    if not shutil.which("systemctl"):
        return None
    out = sh(["systemctl", "show", name + ".service", "-p", "ActiveState", "-p", "CPUUsageNSec", "-p", "MemoryCurrent"])
    kv = dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)
    if kv.get("ActiveState") != "active":
        return None
    def num(k):
        try:
            return int(kv.get(k, ""))
        except ValueError:
            return None
    ns, mem = num("CPUUsageNSec"), num("MemoryCurrent")
    pct = None
    p = prev.get(name)
    if ns is not None and p and now > p[0] and ns >= p[1]:
        pct = round(100.0 * (ns - p[1]) / ((now - p[0]) * 1e9) / (os.cpu_count() or 1), 1)
    if ns is not None:
        prev[name] = (now, ns)
    return {"cpu_pct": pct, "mem_mb": round(mem / 1048576, 1) if mem and mem < 1 << 60 else None}


def collect_perf():
    """Rask ytelsesmåling (ingen journal/nettsjekk) – kalles ofte av Home Assistant og Homey."""
    now = time.time()
    cur = parse_proc_stat(read("/proc/stat"))
    pct = cpu_pct(_perf_prev["cpu"], cur)
    if pct is None and cur:   # første kall: mål kort selv
        time.sleep(0.25)
        cur2 = parse_proc_stat(read("/proc/stat"))
        pct, cur = cpu_pct(cur, cur2), cur2
    _perf_prev["cpu"] = cur
    t = read("/sys/class/thermal/thermal_zone0/temp")
    thr = sh(["vcgencmd", "get_throttled"]) if shutil.which("vcgencmd") else ""
    try:
        load = [round(x, 2) for x in os.getloadavg()]
    except Exception:
        load = None
    try:
        du = shutil.disk_usage("/")
        disk = {"free_gb": round(du.free / 1e9, 1), "total_gb": round(du.total / 1e9, 1), "pct": round(100 * du.used / du.total, 1)}
    except Exception:
        disk = None
    up = read("/proc/uptime").split()
    model = read("/proc/device-tree/model").replace("\x00", "").strip("\x00 ") or None
    svc = {}
    for s in PERF_SERVICES:
        u = service_usage(s, now, _perf_prev["svc"])
        if u:
            svc[s] = u
    return {"cpu_pct": pct, "cpus": os.cpu_count() or 1, "load": load,
            "temp_c": round(int(t) / 1000, 1) if t.lstrip("-").isdigit() else None,
            "throttle": parse_throttled(thr.split("=", 1)[1] if "=" in thr else None),
            "memory": parse_meminfo(read("/proc/meminfo")), "disk": disk,
            "uptime_s": int(float(up[0])) if up else None, "model": model, "services": svc, "time": now}


def routes(ctx):
    import asyncio

    async def h_health(_r):
        return web.json_response(await asyncio.get_running_loop().run_in_executor(None, collect, ctx))

    async def h_report(r):
        h = await asyncio.get_running_loop().run_in_executor(None, collect, ctx)
        extra = None
        try:
            extra = ctx["extra"]() if ctx.get("extra") else None
        except Exception:
            pass
        txt = report_text(h, extra)
        if r.query.get("format") == "json":
            return web.json_response({"text": txt, "issue": issue_link(txt)})
        return web.Response(text=txt, content_type="text/markdown",
                            headers={"Content-Disposition": 'attachment; filename="skjold-feilrapport.md"'})

    async def h_perf(_r):
        return web.json_response(await asyncio.get_running_loop().run_in_executor(None, collect_perf))

    return [web.get("/api/health", h_health), web.get("/api/health/report", h_report), web.get("/api/health/perf", h_perf)]
