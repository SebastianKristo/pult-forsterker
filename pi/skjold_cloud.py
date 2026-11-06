"""Skjold Cloud – valgfri ende-til-ende-kryptert synk mellom hjem (favoritter, rutiner, EQ/innstillinger, Wrapped).

* Nøkkelen avledes fra en gjenopprettingsfrase på 12 ord (vises én gang). scrypt(frase) → 256-bit nøkkel → AES-GCM.
  Skyen («skjold-hjem»-workeren, /enhet/sync) ser bare delnavn, versjon, størrelse og tidspunkt – aldri innholdet.
* Hver del er en mappe nøkkel → verdi. Vi holder et tidsstempel per element lokalt; ved synk flettes per element
  (sist endret vinner). Begge sider endret samme element siden forrige synk med ulik verdi ⇒ konflikt logges.
* Passord og hemmeligheter synkes aldri: broen (bridge) bestemmer innholdet, og `rens()` fjerner kjente nøkkelnavn.
"""
import base64
import hashlib
import json
import os
import secrets
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DELER = ["favoritter", "rutiner", "innstillinger", "eq", "wrapped", "historikk", "kassetter", "plugins"]
STANDARD = ["favoritter", "rutiner", "innstillinger", "eq"]
SALT = b"skjold-cloud-v1"
HEMMELIG = ("pass", "password", "passord", "token", "secret", "noekkel", "key", "pin", "pwd")

# 256 uttalbare ord (16 forlyd × 16 rim) ⇒ 12 ord = 96 bit.
_FOR = ["b", "d", "f", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "sk", "st"]
_RIM = ["ake", "ane", "are", "eke", "ele", "ene", "ide", "ine", "ise", "oke", "ole", "ore", "ude", "une", "yre", "ase"]
ORD = [f + r for f in _FOR for r in _RIM]
_ORDIX = {w: i for i, w in enumerate(ORD)}


def ny_frase():
    return " ".join(ORD[b] for b in secrets.token_bytes(12))


def normaliser_frase(frase):
    ordene = (frase or "").lower().split()
    if len(ordene) != 12 or any(w not in _ORDIX for w in ordene):
        raise ValueError("Frasen må være 12 gyldige ord")
    return " ".join(ordene)


def nokkel(frase):
    return hashlib.scrypt(normaliser_frase(frase).encode(), salt=SALT, n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def krypter(key, obj, del_=""):
    nonce = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, json.dumps(obj, separators=(",", ":")).encode(), del_.encode())
    return base64.b64encode(b"\x01" + nonce + ct).decode()


def dekrypter(key, blob, del_=""):
    raw = base64.b64decode(blob)
    if raw[:1] != b"\x01":
        raise ValueError("ukjent format")
    return json.loads(AESGCM(key).decrypt(raw[1:13], raw[13:], del_.encode()))


def rens(v):
    """Fjern alt som ser ut som passord/nøkler (rekursivt)."""
    if isinstance(v, dict):
        return {k: rens(x) for k, x in v.items() if not any(h in str(k).lower() for h in HEMMELIG)}
    if isinstance(v, list):
        return [rens(x) for x in v]
    return v


def _h(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def flett(lokal, fjern, sist_synk):
    """lokal/fjern: {nøkkel: {"v":…, "t":…, "s": slettet?}}; sist_synk: {nøkkel: hash ved forrige synk}.
    → (flettet, konflikter)."""
    ut, konflikter = {}, []
    for k in set(lokal) | set(fjern):
        a, b = lokal.get(k), fjern.get(k)
        if a is None or b is None:
            ut[k] = a or b
            continue
        if _h(a.get("v")) == _h(b.get("v")) and bool(a.get("s")) == bool(b.get("s")):
            ut[k] = a if a["t"] >= b["t"] else b
            continue
        vinner = a if a["t"] >= b["t"] else b
        base = sist_synk.get(k)
        if base is not None and _h(a.get("v")) != base and _h(b.get("v")) != base:
            konflikter.append({"nokkel": k, "vant": "lokal" if vinner is a else "fjern", "t": int(time.time())})
        ut[k] = vinner
    return ut, konflikter


class SkjoldCloud:
    """bridge: {"hent": del → {nøkkel: verdi}, "sett": (del, {nøkkel: verdi}) → None, "sky": () → sky.json-dict}
    http: async (metode, url, headers, json) → (status, dict). Injiseres så testene slipper nettverk."""

    def __init__(self, bridge, path, http=None):
        self.b, self.path, self.http = bridge, path, http
        self.s = self._les()
        self._key = None

    def _les(self):
        try:
            with open(self.path) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {"enabled": False, "deler": list(STANDARD), "frase": None, "elementer": {}, "sist": {},
                    "versjon": {}, "konflikter": [], "sist_synk": 0, "feil": ""}

    def _lagre(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump(self.s, fh)
        os.replace(tmp, self.path)

    def key(self):
        if self._key is None and self.s.get("frase"):
            self._key = nokkel(self.s["frase"])
        return self._key

    # --- API ---
    def status(self):
        sky = self.b["sky"]() or {}
        return {"enabled": bool(self.s.get("enabled")), "har_frase": bool(self.s.get("frase")), "deler": self.s.get("deler", []),
                "alle_deler": DELER, "sist_synk": self.s.get("sist_synk", 0), "feil": self.s.get("feil", ""),
                "konflikter": self.s.get("konflikter", [])[-20:], "sky_koblet": bool(sky.get("id"))}

    def aktiver(self, frase=None):
        """Uten frase: lag ny og returner den (vises én gang). Med frase: gjenopprett på et nytt hjem."""
        ny = frase is None
        frase = ny_frase() if ny else normaliser_frase(frase)
        self.s.update(enabled=True, frase=frase, elementer={}, sist={}, versjon={}, feil="")
        self._key = None
        self._lagre()
        return {"frase": frase} if ny else {}

    def deaktiver(self):
        self.s.update(enabled=False, frase=None, elementer={}, sist={}, versjon={})
        self._key = None
        self._lagre()

    def velg(self, deler):
        self.s["deler"] = [d for d in deler if d in DELER]
        self._lagre()

    def _oppdater_lokalt(self, del_):
        """Les delen fra daemonen og gi nytt tidsstempel til elementer som er endret siden sist."""
        now = time.time()
        gml = self.s["elementer"].setdefault(del_, {})
        nå = {str(k): rens(v) for k, v in (self.b["hent"](del_) or {}).items()}
        for k, v in nå.items():
            if k not in gml or gml[k].get("s") or _h(gml[k]["v"]) != _h(v):
                gml[k] = {"v": v, "t": now}
        for k in list(gml):
            if k not in nå and not gml[k].get("s"):
                gml[k] = {"v": None, "t": now, "s": True}
        return gml

    async def synk(self):
        if not self.s.get("enabled") or not self.key():
            return {"ok": False, "feil": "ikke aktivert"}
        sky = self.b["sky"]() or {}
        if not sky.get("id"):
            self.s["feil"] = "Hjemmet er ikke koblet til Skjold-skyen"
            return {"ok": False, "feil": self.s["feil"]}
        url, hdr = sky["url"].rstrip("/") + "/enhet/sync", {"Authorization": f"Bearer {sky['id']}.{sky['noekkel']}"}
        endret = []
        try:
            for d in self.s.get("deler", []):
                lok = self._oppdater_lokalt(d)
                st, r = await self.http("GET", f"{url}?del={d}", hdr, None)
                if st != 200:
                    raise RuntimeError(f"hent {d}: {st}")
                for _ in range(3):
                    fjern = dekrypter(self.key(), r["blob"], d) if r.get("blob") else {}
                    flettet, konf = flett(lok, fjern, self.s["sist"].get(d, {}))
                    self.s["konflikter"] = (self.s.get("konflikter", []) + [{**c, "del": d} for c in konf])[-100:]
                    if flettet != fjern:
                        st, r2 = await self.http("PUT", url, hdr, {"del": d, "base": r.get("versjon", 0), "blob": krypter(self.key(), flettet, d)})
                        if st == 409:
                            r = r2
                            continue
                        if st != 200:
                            raise RuntimeError(f"lagre {d}: {st}")
                    break
                if flettet != lok:
                    self.b["sett"](d, {k: e["v"] for k, e in flettet.items() if not e.get("s")})
                    endret.append(d)
                self.s["elementer"][d] = flettet
                self.s["sist"][d] = {k: _h(e["v"]) for k, e in flettet.items()}
            self.s.update(sist_synk=int(time.time()), feil="")
        except Exception as e:
            self.s["feil"] = str(e)
            self._lagre()
            return {"ok": False, "feil": str(e)}
        self._lagre()
        return {"ok": True, "endret": endret}
