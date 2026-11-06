"""Radioopptak for Skjold: SMB-lagring, opptak med ICY-metadata, og deling av opptaket i låter.

Rene funksjoner (testes i pi/tests/test_rec.py) + tynne innpakninger rundt ffmpeg/mount.cifs/smbclient.
Opptak er for privat bruk.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy finnes på Skjold
    np = None

SR = 22050          # analyse-samplingsrate
HOP = 0.05          # 50 ms rammer
MAX_TRIM = 15.0     # aldri kutt mer enn 15 s inn i låta
WINDOW = 20.0       # søk ±20 s rundt metadata-endringen

# ---------------------------------------------------------------- tittel

_JUNK = {"", "-", "unknown", "advert", "advertisement", "reklame", "nyheter", "news", "jingle", "promo"}
_NOISE = re.compile(r"\s*[\[(](?:radio edit|edit|explicit|clean|official(?: audio| video)?|hq|hd)[\])]\s*", re.I)


def parse_title(s: str):
    """«Artist - Tittel» (og «–», «—», «:», «Tittel by Artist») → (artist, tittel), ellers None."""
    s = re.sub(r"\s+", " ", str(s or "")).strip().strip("'\"")
    if not s or s.lower() in _JUNK or s.lower().startswith(("http", "www.")):
        return None
    a = t = ""
    m = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", s) or re.match(r"^(.+?)\s*[–—]\s*(.+)$", s)
    if m:
        a, t = m.group(1), m.group(2)
    else:
        m = re.match(r"^(.+?)\s+by\s+(.+)$", s, re.I)
        if m:
            t, a = m.group(1), m.group(2)
        else:
            m = re.match(r"^([^:]{2,60}):\s+(.+)$", s)
            if m:
                a, t = m.group(1), m.group(2)
            else:
                m = re.match(r"^(\S.*?\S)-(\S.*)$", s)   # «Artist-Tittel» uten mellomrom: bare hvis begge sider har bokstaver
                if m and re.search(r"[A-Za-zÆØÅæøå]", m.group(1)) and re.search(r"[A-Za-zÆØÅæøå]", m.group(2)) and " " in s:
                    a, t = m.group(1), m.group(2)
    a, t = a.strip(" -–—:"), _NOISE.sub(" ", t).strip(" -–—:")
    if not a or not t or a.lower() in _JUNK or t.lower() in _JUNK:
        return None
    if a.isupper() and len(a) > 3:
        a = a.title()
    if t.isupper() and len(t) > 3:
        t = t.capitalize()
    return a[:120], t[:160]


def safe_name(s: str, maxlen: int = 80) -> str:
    """Filnavn som tåles av SMB/Windows: fjern / \\ : * ? " < > | og kontrolltegn, ingen avsluttende punktum/mellomrom."""
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", str(s or "")).strip()
    s = re.sub(r"\s+", " ", s).strip(" .")
    if s.upper() in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?i)(com|lpt)\d", s):
        s = "_" + s
    return s[:maxlen].rstrip(" .") or "Ukjent"


def song_relpath(artist: str, title: str, fmt: str = "mp3") -> str:
    ext = {"mp3": "mp3", "flac": "flac", "m4a": "m4a"}.get(fmt, "mp3")
    a = safe_name(artist)
    return os.path.join(a, f"{a} - {safe_name(title, 120)}.{ext}")


# ---------------------------------------------------------------- SMB

SMB_MNT = "/mnt/skjold-opptak"
SMB_CRED = "/etc/skjold/smb-opptak.cred"


def smb_norm_share(share: str) -> str:
    """«nas.local/musikk», «\\\\nas\\musikk», «smb://nas/musikk» → «//nas/musikk»."""
    s = str(share or "").strip().replace("\\", "/")
    s = re.sub(r"^smb:", "", s, flags=re.I)
    s = "//" + s.lstrip("/")
    return s.rstrip("/") if s != "//" else ""


def smb_cred_text(user: str, password: str, domain: str = "") -> str:
    lines = [f"username={user or 'guest'}", f"password={password or ''}"]
    if domain:
        lines.append(f"domain={domain}")
    return "\n".join(lines) + "\n"


def smb_mount_cmd(share: str, vers: str = "3.0", uid: int = 0, gid: int = 0, mnt: str = SMB_MNT, cred: str = SMB_CRED, guest: bool = False):
    opts = [f"vers={vers}", f"uid={uid}", f"gid={gid}", "file_mode=0664", "dir_mode=0775", "iocharset=utf8", "noperm", "nofail"]
    opts.append("guest" if guest else f"credentials={cred}")
    return ["mount", "-t", "cifs", smb_norm_share(share), mnt, "-o", ",".join(opts)]


def smb_versions(vers: str):
    return [vers] if vers and vers != "auto" else ["3.0", "2.1"]


def smb_error(stderr: str, code: int = 0) -> str:
    e = (stderr or "").lower()
    if "permission denied" in e or "(13)" in e or "logon failure" in e or "access denied" in e:
        return "Tilgang nektet – sjekk brukernavn og passord, og at brukeren har skrivetilgang til mappen."
    if "no such file" in e or "(2)" in e or "bad_network_name" in e or "no such device or address" in e:
        return "Fant ikke delt mappe – sjekk server og navnet på mappen (f.eks. //nas.local/musikk)."
    if "operation not supported" in e or "(95)" in e or "protocol" in e:
        return "Serveren støtter ikke SMB-versjonen – prøv en annen versjon (2.1 eller 1.0)."
    if "host is down" in e or "(112)" in e or "unable to find suitable address" in e or "could not resolve" in e:
        return "Finner ikke serveren på nettet – sjekk navnet/IP-adressen."
    if "mount.cifs" in e and "not found" in e or code == 32 and not e:
        return "cifs-utils mangler (kjør pi/update.sh)."
    return (stderr or f"mount feilet ({code})").strip().splitlines()[-1][:200]


def smb_mount(cfg: dict, run=subprocess.run, mnt: str = SMB_MNT, cred: str = SMB_CRED):
    """Monterer SMB-delingen. Returnerer (ok, melding). Prøver 3.0 og så 2.1 når versjon er «auto»."""
    share = smb_norm_share(cfg.get("smb_share", ""))
    if not share:
        return False, "Ingen delt mappe satt"
    if not shutil.which("mount.cifs") and run is subprocess.run:
        return False, "cifs-utils mangler (kjør pi/update.sh)."
    os.makedirs(mnt, exist_ok=True)
    guest = not cfg.get("smb_user")
    if not guest:
        os.makedirs(os.path.dirname(cred), exist_ok=True)
        fd = os.open(cred, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(smb_cred_text(cfg.get("smb_user", ""), cfg.get("smb_password", ""), cfg.get("smb_domain", "")))
        os.chmod(cred, 0o600)
    smb_umount(run=run, mnt=mnt)
    last = ""
    for v in smb_versions(cfg.get("smb_vers", "auto")):
        r = run(smb_mount_cmd(share, v, os.getuid(), os.getgid(), mnt, cred, guest), capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return True, f"Koblet til {share} (SMB {v})"
        last = smb_error((r.stderr or "") + (r.stdout or ""), r.returncode)
        if "Tilgang nektet" in last or "Fant ikke" in last or "Finner ikke serveren" in last:
            break
    return False, last


def smb_umount(run=subprocess.run, mnt: str = SMB_MNT):
    if os.path.ismount(mnt):
        run(["umount", "-l", mnt], capture_output=True, text=True, timeout=20)


def smb_mounted(mnt: str = SMB_MNT) -> bool:
    return os.path.ismount(mnt)


def smb_list_shares(server: str, user: str = "", password: str = "", domain: str = "", run=subprocess.run):
    """smbclient -L → [navn] (bare «Disk»-delinger, uten $-skjulte)."""
    host = smb_norm_share(server).lstrip("/").split("/")[0]
    if not host:
        raise ValueError("skriv inn server først")
    if not shutil.which("smbclient") and run is subprocess.run:
        raise RuntimeError("smbclient mangler (kjør pi/update.sh)")
    cmd = ["smbclient", "-g", "-L", f"//{host}"]
    cmd += ["-U", f"{(domain + '/') if domain else ''}{user}%{password}"] if user else ["-N"]
    r = run(cmd, capture_output=True, text=True, timeout=20)
    out = [ln.split("|")[1] for ln in (r.stdout or "").splitlines() if ln.startswith("Disk|")]
    if not out and r.returncode:
        raise RuntimeError(smb_error(r.stderr or r.stdout, r.returncode))
    return [s for s in out if not s.endswith("$")]


# ---------------------------------------------------------------- lydanalyse

def features(pcm, sr: int = SR, hop: float = HOP):
    """mono float-PCM → dict med rms (dB), fluks og flathet per ramme på hop sekunder."""
    n = max(1, int(sr * hop))
    frames = len(pcm) // n
    x = np.asarray(pcm[: frames * n], dtype=np.float32).reshape(frames, n)
    rms = np.sqrt(np.mean(x * x, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    win = np.hanning(n).astype(np.float32)
    spec = np.abs(np.fft.rfft(x * win, axis=1)) + 1e-9
    norm = spec / spec.sum(axis=1, keepdims=True)
    flux = np.r_[0.0, np.sqrt(np.sum(np.diff(norm, axis=0) ** 2, axis=1))]
    flat = np.exp(np.mean(np.log(spec), axis=1)) / np.mean(spec, axis=1)
    return {"db": db, "flux": flux, "flat": flat, "hop": hop}


def _smooth(v, k):
    k = max(1, int(k))
    return np.convolve(v, np.ones(k) / k, mode="same")


def find_cut(f, t_meta: float, window: float = WINDOW, delay: float = 0.0):
    """Beste kuttpunkt (sekunder) nær t_meta − delay: dypeste energidal (stille/fade) eller tydelig klangskifte,
    vektet mot punktet nærmest forventet tid. Returnerer (t, styrke 0–1)."""
    hop, db = f["hop"], f["db"]
    n = len(db)
    centre = t_meta - delay
    lo, hi = max(0, int((centre - window) / hop)), min(n - 1, int((centre + window) / hop))
    if hi - lo < 4:
        return max(0.0, centre), 0.0
    sdb = _smooth(db, 0.25 / hop)   # 250 ms
    seg = sdb[lo:hi + 1]
    ref = np.percentile(sdb[max(0, lo - int(30 / hop)):min(n, hi + int(30 / hop))], 70)
    dip = np.clip((ref - seg) / 30.0, 0, 1)                       # 30 dB under nivået = full dal
    flux = _smooth(f["flux"], 0.3 / hop)[lo:hi + 1]
    fl = np.clip(flux / (np.percentile(f["flux"], 95) + 1e-9), 0, 1)
    t = (np.arange(lo, hi + 1) * hop)
    near = np.exp(-((t - centre) / (window * 0.6)) ** 2)
    score = (0.75 * dip + 0.25 * fl) * (0.35 + 0.65 * near)
    i = int(np.argmax(score))
    return float(t[i]), float(min(1.0, dip[i] + 0.5 * fl[i]))


def estimate_delay(f, meta_times, window: float = WINDOW):
    """Konstant forsinkelse metadata→lyd for kanalen: median av (metadata-tid − beste kutt) over tydelige overganger."""
    offs = []
    for tm in meta_times:
        t, s = find_cut(f, tm, window, 0.0)
        if s >= 0.5:
            offs.append(tm - t)
    if len(offs) < 2:
        return 0.0
    d = float(np.median(offs))
    return max(-5.0, min(15.0, d))


def is_speechy(f, a: float, b: float) -> bool:
    """Tale/jingle: mange korte pauser (ord og setninger) – energien faller under nivået flere ganger i sekundet.
    Musikk, også fade inn/ut, har få slike skift."""
    hop = f["hop"]
    i, j = int(a / hop), int(b / hop)
    if j - i < 10:
        return False
    db = _smooth(f["db"][i:j], 2)
    if np.max(db) < -60:
        return False
    low = db < np.max(db) - 20
    pauses = float(np.mean(low))
    flips = int(np.count_nonzero(low[1:] != low[:-1]))
    return 0.12 < pauses < 0.75 and flips / ((j - i) * hop) >= 1.2


def trim_speech(f, a: float, b: float, max_trim: float = MAX_TRIM):
    """Fjern tydelig tale/jingle i starten og slutten av [a, b] – aldri mer enn max_trim sekunder per side."""
    step = 2.5
    na, nb = a, b
    while na - a < max_trim and nb - na > 60 and is_speechy(f, na, na + 5):
        na += step
    while b - nb < max_trim and nb - na > 60 and is_speechy(f, nb - 5, nb):
        nb -= step
    return na, nb


def plan_songs(f, events, total: float, min_len: float = 60.0):
    """events: [(t_sek, tekst)] metadata-endringer. → [{start, end, artist, title}] for låter ≥ min_len."""
    evs = []
    for t, txt in sorted(events, key=lambda e: e[0]):
        if evs and evs[-1][1] == txt:
            continue
        evs.append((float(t), txt))
    if not evs:
        return [], 0.0
    delay = estimate_delay(f, [t for t, _ in evs[1:]])
    cuts = [0.0] + [find_cut(f, t, WINDOW, delay)[0] for t, _ in evs[1:]] + [total]
    cuts[0] = max(0.0, evs[0][0] - delay) if evs[0][0] > 1 else 0.0
    out = []
    for k, (_t, txt) in enumerate(evs):
        at = parse_title(txt)
        if not at:
            continue
        a, b = cuts[k], cuts[k + 1]
        if k == 0 and a <= 0.5:   # opptaket startet midt i låta
            continue
        if k == len(evs) - 1 and total - b < 0.5 and b - a < 600:
            pass
        a, b = trim_speech(f, a, b)
        if b - a >= min_len:
            out.append({"start": round(a, 2), "end": round(b, 2), "artist": at[0], "title": at[1]})
    return out, delay


# ---------------------------------------------------------------- ffmpeg

def decode_mono(path: str, sr: int = SR):
    r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg kunne ikke lese opptaket")
    return np.frombuffer(r.stdout, dtype=np.float32)


def encode_args(fmt: str):
    return {"flac": ["-c:a", "flac"], "m4a": ["-c:a", "aac", "-b:a", "256k"]}.get(fmt, ["-c:a", "libmp3lame", "-b:a", "320k"])


def export_song(src: str, song: dict, dest: str, fmt: str, channel: str, when: float, cover: str = ""):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(when + song["start"]))
    meta = {"artist": song["artist"], "title": song["title"], "album": f"{channel} {time.strftime('%Y-%m-%d', time.localtime(when))}",
            "comment": f"Tatt opp fra {channel} {stamp}", "date": time.strftime("%Y", time.localtime(when))}
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{song['start']:.2f}", "-to", f"{song['end']:.2f}", "-i", src]
    if cover and os.path.isfile(cover) and fmt in ("mp3", "flac", "m4a"):
        cmd += ["-i", cover, "-map", "0:a", "-map", "1:v", "-c:v", "mjpeg" if fmt != "m4a" else "copy", "-disposition:v", "attached_pic"]
        if fmt == "mp3":
            cmd += ["-id3v2_version", "3", "-metadata:s:v", "title=Album cover"]
    else:
        cmd += ["-map", "0:a"]
    cmd += encode_args(fmt) + ["-af", "afade=t=in:d=0.3,areverse,afade=t=in:d=0.6,areverse"]
    for k, v in meta.items():
        cmd += ["-metadata", f"{k}={v}"]
    tmp = dest + ".part"
    cmd += ["-f", {"flac": "flac", "m4a": "mp4"}.get(fmt, "mp3"), tmp]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        try: os.remove(tmp)
        except OSError: pass
        raise RuntimeError((r.stderr or "ffmpeg feilet").strip().splitlines()[-1][:200])
    os.replace(tmp, dest)


# ---------------------------------------------------------------- opptak med metadata

class IcyRecorder:
    """Leser strømmen selv (Icy-MetaData: 1), sender lyden til ffmpeg og logger låtbytter med nøyaktig byte-posisjon.
    Strømmer uten ICY (HLS o.l.) tas opp av ffmpeg direkte, og metadata hentes med get_title() hvert 5. s."""

    def __init__(self, url: str, out: str, seconds: int, get_title=None):
        self.url, self.out, self.seconds = url, out, int(seconds)
        self.get_title = get_title
        self.events = []          # [(sek, tekst)]
        self.t0 = time.time()
        self.stop = threading.Event()
        self.proc = None
        self.error = ""
        self.th = threading.Thread(target=self._run, daemon=True)
        self.th.start()

    def alive(self):
        return self.th.is_alive()

    def terminate(self):
        self.stop.set()
        if self.proc and self.proc.poll() is None:
            try: self.proc.terminate()
            except Exception: pass

    def _ffmpeg(self, src):
        return subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-t", str(self.seconds), "-vn",
                                 "-c:a", "libmp3lame", "-b:a", "256k", self.out],
                                stdin=subprocess.PIPE if src == "pipe:0" else subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _log(self, sec, txt):
        if txt and (not self.events or self.events[-1][1] != txt):
            self.events.append((round(sec, 2), txt))

    def _run(self):
        try:
            req = urllib.request.Request(self.url, headers={"Icy-MetaData": "1", "User-Agent": "Skjold/1.0"})
            r = urllib.request.urlopen(req, timeout=10)
            metaint = int(r.headers.get("icy-metaint") or 0)
            br = int(r.headers.get("icy-br") or 0)
        except Exception as e:
            r, metaint, br = None, 0, 0
            self.error = str(e)
        if not r or not metaint:
            if r:
                r.close()
            self._fallback()
            return
        self.proc = self._ffmpeg("pipe:0")
        audio = 0
        try:
            while not self.stop.is_set() and self.proc.poll() is None and time.time() - self.t0 < self.seconds + 5:
                chunk = r.read(metaint)
                if not chunk:
                    break
                self.proc.stdin.write(chunk)
                audio += len(chunk)
                ln = r.read(1)
                if not ln:
                    break
                if ln[0]:
                    meta = r.read(ln[0] * 16).rstrip(b"\0")
                    raw = meta.decode("utf-8", "replace")
                    if "�" in raw:
                        raw = meta.decode("latin-1")
                    m = re.search(r"StreamTitle='(.*?)';", raw, re.S)
                    # tid = lyd lest så langt; med kjent bitrate er byte-posisjonen sikrere enn veggklokka
                    sec = audio * 8 / (br * 1000) if br else time.time() - self.t0
                    self._log(sec, (m.group(1).strip() if m else ""))
        except (BrokenPipeError, OSError):
            pass
        finally:
            try: r.close()
            except Exception: pass
            try: self.proc.stdin.close()
            except Exception: pass
            try: self.proc.wait(timeout=30)
            except Exception: pass

    def _fallback(self):
        self.proc = self._ffmpeg(self.url)
        while not self.stop.is_set() and self.proc.poll() is None:
            if self.get_title:
                try: self._log(time.time() - self.t0, self.get_title() or "")
                except Exception: pass
            self.stop.wait(5)


def save_events(path: str, info: dict):
    with open(path + ".json.tmp", "w") as fh:
        json.dump(info, fh, ensure_ascii=False)
    os.replace(path + ".json.tmp", path + ".json")
