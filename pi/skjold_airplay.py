"""AirPlay 2 til flere rom: hver Skjold er et eget AirPlay 2-mål (shairport-sync + nqptp).

iPhone/Mac kan velge flere AirPlay 2-høyttalere samtidig og holder dem synkrone selv. For at det skal virke må hvert
mål ha en unik AirPlay-ID. shairport-sync lager den fra nettverkskortets MAC-adresse, men klonede maskiner
(Proxmox-LXC fra samme mal, SD-kort kopiert til flere Pi-er) kan få samme MAC/ID – da ser iPhone bare én av dem.
Skjold setter derfor «airplay_device_id» fra en stabil hash av /etc/machine-id + MAC + vertsnavn.

Navnet er enhetens navn i Skjold (f.eks. «Stue», «Kjøkken»), satt av daemonen (apply_name). Volumet fra iPhone
følger Skjold-volumet (ignore_volume_control = "yes" + pvol → /api/volume i daemonen).
"""
import hashlib
import re


def device_id(machine_id: str, mac: str = "", host: str = "") -> str:
    """48-bit ID som 0x-heks (samme format som shairport-sync bruker). Lokalt administrert, unicast."""
    h = hashlib.sha256(f"skjold-airplay|{machine_id.strip()}|{mac.strip().lower()}|{host.strip()}".encode()).digest()
    b = bytearray(h[:6])
    b[0] = (b[0] | 0x02) & 0xFE          # «locally administered», ikke multicast
    return "0x" + b.hex().upper()


def ensure_id(conf: str, dev_id: str) -> str:
    """Sett/oppdater airplay_device_id i general-blokken. Rører ikke resten av fila."""
    line = f'  airplay_device_id = {dev_id}L;   // Skjold: unik per enhet (pi/skjold_airplay.py)'
    if re.search(r"^\s*airplay_device_id\s*=", conf, flags=re.M):
        return re.sub(r"^\s*airplay_device_id\s*=.*$", line, conf, count=1, flags=re.M)
    m = re.search(r"^general\s*=\s*\n?\s*\{\s*\n", conf, flags=re.M)
    if not m:
        return conf
    return conf[:m.end()] + line + "\n" + conf[m.end():]


def current_id(conf: str):
    m = re.search(r"^\s*airplay_device_id\s*=\s*(0x[0-9A-Fa-f]+)L?\s*;", conf, flags=re.M)
    return m.group(1).upper().replace("0X", "0x") if m else None


def read_machine_id():
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            return open(p).read().strip()
        except OSError:
            continue
    return ""


def read_mac():
    import glob
    for p in sorted(glob.glob("/sys/class/net/*/address")):
        if "/lo/" in p:
            continue
        try:
            mac = open(p).read().strip()
            if mac and mac != "00:00:00:00:00:00":
                return mac
        except OSError:
            continue
    return ""
