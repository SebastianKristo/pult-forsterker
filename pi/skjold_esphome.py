"""Skjold-tilbehør på ESPHome (Kassett …): finn dem på nettet og gi dem adressen til Skjold, så ingen IP må tastes inn.

Kassettspilleren har en «Skjold adresse»-tekst (esphome/skjold-kassett.yaml) som den sender kassettene til. En Skjold
som finner spilleren (mDNS _esphomelib._tcp), sjekker adressen der. Er den tom eller svarer den ikke (Skjold har fått
ny IP, eller spilleren er ny), skriver Skjold sin egen adresse inn via spillerens web_server (REST). Kassettene er
felles for hele systemet, så det spiller ingen rolle hvilken Skjold som svarer.
"""
import json
import shutil
import subprocess
import time
import urllib.parse
import urllib.request

ESPHOME_TYPE = "_esphomelib._tcp.local."
TEKST_IDER = ("skjold_adresse", "Skjold%20adresse")   # web_server v2 (object_id) og v3 (navn)


def discover(prefix="skjold-kassett", timeout=3.0):
    """ESPHome-enheter med navn som starter med prefix: [{"navn", "ip"}]."""
    funnet = {}
    try:
        from zeroconf import ServiceBrowser, Zeroconf
        zc = Zeroconf()
        navn = []

        class L:
            def add_service(self, z, t, n): navn.append(n)
            def update_service(self, z, t, n): pass
            def remove_service(self, z, t, n): pass
        ServiceBrowser(zc, ESPHOME_TYPE, L())
        time.sleep(timeout)
        for n in navn:
            kort = n.split(".")[0]
            if not kort.startswith(prefix):
                continue
            info = zc.get_service_info(ESPHOME_TYPE, n, 2000)
            if info and info.parsed_addresses():
                funnet[kort] = info.parsed_addresses()[0]
        zc.close()
    except Exception:
        if shutil.which("avahi-browse"):
            try:
                ut = subprocess.run(["avahi-browse", "-rtp", "_esphomelib._tcp"], capture_output=True, text=True,
                                    timeout=timeout + 5).stdout
                for ln in ut.splitlines():
                    f = ln.split(";")
                    if f[0] == "=" and len(f) > 7 and f[3].startswith(prefix) and "." in f[7]:
                        funnet[f[3]] = f[7]
            except Exception:
                pass
    return [{"navn": k, "ip": v} for k, v in sorted(funnet.items())]


def _get(url, timeout=3.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def get_host(ip, opener=_get):
    """Adressen spilleren sender til nå ("" = ingen), eller None hvis spilleren ikke har feltet (eldre fastvare)."""
    for tid in TEKST_IDER:
        try:
            d = json.loads(opener(f"http://{ip}/text/{tid}") or b"{}")
            return str(d.get("value", d.get("state", "")) or "")
        except Exception:
            continue
    return None


def set_host(ip, verdi, opener=None):
    """Skriv Skjold-adressen inn i spilleren. True hvis det gikk."""
    q = urllib.parse.quote(verdi, safe="")
    for tid in TEKST_IDER:
        try:
            req = urllib.request.Request(f"http://{ip}/text/{tid}/set?value={q}", data=b"", method="POST")
            (opener or (lambda r: urllib.request.urlopen(r, timeout=3).read()))(req)
            return True
        except Exception:
            continue
    return False


def skjold_svarer(host, port=8765, timeout=2.0):
    if not host:
        return False
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/status", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def pass_paa(min_ip, finn=discover, hent=get_host, sett=set_host, svarer=skjold_svarer, logg=print):
    """Én runde: gi spillere uten fungerende Skjold-adresse adressen til denne Skjold-en. Returnerer endringene."""
    endret = []
    if not min_ip:
        return endret
    for sp in finn():
        naa = hent(sp["ip"])
        if naa is None or naa == min_ip:
            continue   # eldre fastvare uten feltet, eller allerede riktig
        if naa and svarer(naa):
            continue   # sender til en annen Skjold som svarer – kassettene er felles, så det er greit
        if sett(sp["ip"], min_ip):
            endret.append({**sp, "fra": naa, "til": min_ip})
            logg(f"{sp['navn']} ({sp['ip']}): Skjold-adressen satt til {min_ip}" + (f" (var {naa}, svarte ikke)" if naa else ""))
    return endret
