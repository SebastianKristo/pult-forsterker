"""Podme (podme.com) for Skjold: podkastene du følger der, også premium-episoder fra abonnementet ditt.

Podme har ikke et offentlig API. Dette gjør det samme som Podme-appen for Android: logger inn med Schibsted-kontoen
(OAuth med PKCE) og bruker mobil-API-et på api.podme.com. Kartlagt etter det åpne biblioteket podme_api
(github.com/bendikrb/podme_api), og samme flyt som Skjold Klang (server/src/podme.ts). Endrer Podme noe, må dette
oppdateres.

Innloggingen (tilgangs- og fornyelsesnøkkel) lagres på enheten (podme_token.json, bare lesbar for root), så passordet
bare brukes når fornyelsen ikke lenger virker. E-post og passord ligger i innstillingene (podmeEmail/podmePass).

Podkaster fra Podme har id «podme:<tall>», episodene «podme-<tall>» med lydadresse «podme:<tall>» – den byttes mot
den ekte lydfila når episoden spilles (audio_url).
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_BASE = "https://payment.schibsted.no/"
CLIENT_ID = "62557b19f552881812b7431c"
REDIRECT = f"pme.podme.{CLIENT_ID}:/login"
API = "https://api.podme.com/mobile/api/"
AUTH_UA = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"
API_UA = "Podme android app/6.38.5 (Linux;Android 15) AndroidXMedia3/1.5.1"
REFRESH_UA = "AccountSDKAndroidWeb/6.4.0 (Linux; Android 15; API 35; Google; sdk_gphone64_arm64)"
DEVICE = json.dumps({
    "platform": "Android", "userAgent": "Chrome", "userAgentVersion": "128.0.0.0", "hasLiedOs": "0", "hasLiedBrowser": "0",
    "fonts": ["Arial", "Courier", "Courier New", "Georgia", "Helvetica", "Monaco", "Palatino", "Tahoma", "Times", "Times New Roman", "Verdana"],
    "plugins": [],
}, separators=(",", ":"))


class PodmeError(RuntimeError):
    def __init__(self, msg, status=502):
        super().__init__(msg)
        self.status = status


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _secs(v) -> float:
    """«01:02:03», «01:02:03.5» eller sekunder → sekunder."""
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str) or not v:
        return 0.0
    try:
        n = 0.0
        for p in v.split(".")[0].split(":"):
            n = n * 60 + int(p)
        return n
    except ValueError:
        return 0.0


def _dato(v) -> tuple[str, float]:
    """ISO-dato fra Podme → («28.11.2026», unix)."""
    if not v:
        return "", 0.0
    try:
        from datetime import datetime
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d.strftime("%d.%m.%Y"), d.timestamp()
    except ValueError:
        return str(v)[:10], 0.0


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class _Jar:
    """Informasjonskapsler for Schibsted-innloggingen. Følger Domain=, så de blir med på tvers av underdomener."""

    def __init__(self):
        self.c: dict = {}

    def store(self, url: str, headers):
        host = urllib.parse.urlsplit(url).hostname or ""
        for raw in headers.get_all("Set-Cookie") or []:
            pair, *attrs = raw.split(";")
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name, value = name.strip(), value.strip()
            attrs = [a.strip() for a in attrs]
            dom = next((a[7:].lstrip(".").lower() for a in attrs if a.lower().startswith("domain=")), None)
            expired = any(a.lower().startswith("max-age=0") for a in attrs)
            key = (dom or host, name)
            if expired:
                self.c.pop(key, None)
            else:
                self.c[key] = (not dom, value)

    def header(self, url: str):
        host = urllib.parse.urlsplit(url).hostname or ""
        out = [f"{n}={v}" for (d, n), (host_only, v) in self.c.items()
               if (host == d if host_only else host == d or host.endswith("." + d))]
        return "; ".join(out) or None


class Podme:
    def __init__(self, email: str, password: str, token_path: str):
        self.email, self.password, self.token_path = email or "", password or "", token_path
        self.lock = threading.Lock()
        self.failed: tuple[float, PodmeError] | None = None
        self.last_error: str | None = None
        self._stream: dict = {}
        self.tokens = self._load()

    # ---------- lagring ----------
    def _load(self):
        try:
            with open(self.token_path) as f:
                t = json.load(f)
            return t if t.get("access_token") and t.get("email") == self.email else None
        except Exception:
            return None

    def _save(self, t):
        try:
            os.makedirs(os.path.dirname(self.token_path) or ".", exist_ok=True)
            tmp = self.token_path + ".tmp"
            with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
                json.dump({**t, "email": self.email} if t else {}, f)
            os.replace(tmp, self.token_path)
        except OSError:
            pass

    def _keep(self, j: dict, prev=None) -> dict:
        t = {"access_token": j["access_token"], "refresh_token": j.get("refresh_token") or (prev or {}).get("refresh_token"),
             "expiration_time": int(time.time()) + int(j.get("expires_in") or 3600)}
        self.tokens = t
        self._save(t)
        return t

    # ---------- innlogging ----------
    def _login(self) -> dict:
        if not self.email or not self.password:
            raise PodmeError("Podme mangler e-post eller passord", 400)
        jar = _Jar()
        opener = urllib.request.build_opener(_NoRedirect())

        def req(url, form=None, headers=None, method=None):
            h = {"Accept": "text/html", "User-Agent": AUTH_UA, "Referer": "https://podme.com", **(headers or {})}
            ck = jar.header(url)
            if ck:
                h["Cookie"] = ck
            data = None
            if form is not None:
                data = urllib.parse.urlencode(form).encode()
                h["Content-Type"] = "application/x-www-form-urlencoded"
            r = urllib.request.Request(url, data=data, headers=h, method=method or ("POST" if data else "GET"))
            try:
                resp = opener.open(r, timeout=15)
            except urllib.error.HTTPError as e:   # 3xx (ingen automatisk omdirigering) og 4xx kommer hit
                resp = e
            jar.store(url, resp.headers)
            body = resp.read() if hasattr(resp, "read") else b""
            return resp.status if hasattr(resp, "status") else resp.code, resp.headers, body

        def auth(path, params=None):
            return AUTH_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")

        verifier = _b64url(secrets.token_bytes(48))
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        st, hd, _ = req(auth("oauth/authorize", {
            "client_id": CLIENT_ID, "redirect_uri": REDIRECT, "response_type": "code", "scope": "openid offline_access",
            "state": secrets.token_hex(16), "nonce": _b64url(secrets.token_bytes(16)), "code_challenge": challenge,
            "code_challenge_method": "S256", "prompt": "select_account"}))
        loc, base = hd.get("Location"), auth("oauth/authorize")
        if not loc:
            raise PodmeError(f"Podme-innloggingen svarte uventet ({st})")
        for _ in range(10):   # følg kjeden til innloggingssiden, så Schibsted husker hvor vi skal tilbake
            if not loc:
                break
            u = urllib.parse.urljoin(base, loc)
            st, hd, _ = req(u)
            base = u
            loc = hd.get("Location") if 300 <= st < 400 else None

        _, _, body = req(auth("authn/api/settings/csrf", {"client_id": CLIENT_ID}), headers={"Accept": "application/json"})
        try:
            csrf = json.loads(body or b"{}")["data"]["attributes"]["csrfToken"]
        except Exception:
            raise PodmeError("Fikk ikke startet Podme-innloggingen (CSRF)")

        st, _, _ = req(auth("authn/api/identity/login/", {"client_id": CLIENT_ID}), headers={"X-CSRF-Token": csrf, "Accept": "application/json"},
                       form={"username": self.email, "password": self.password, "remember": "true", "deviceData": DEVICE})
        if st in (400, 401, 403):
            raise PodmeError("Podme avviste e-post eller passord", 401)
        if st >= 300:
            raise PodmeError(f"Podme-innloggingen svarte {st}")

        st, hd, _ = req(auth("authn/identity/finish/", {"client_id": CLIENT_ID}),
                        form={"deviceData": DEVICE, "remember": "true", "_csrf": csrf, "redirectToAccountPage": ""})
        nxt, code, last = hd.get("Location"), None, f"finish {st}"
        for _ in range(10):   # omdirigeringer til Schibsted sender oss tilbake til appen med en kode
            if not nxt:
                break
            url = urllib.parse.urljoin(AUTH_BASE, nxt)
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            if url.startswith("pme.podme") or "code" in q:
                code = (q.get("code") or [None])[0]
                if not code:
                    raise PodmeError("Schibsted avbrøt innloggingen (" + ((q.get("error_description") or q.get("error") or ["ukjent feil"])[0]) + ")")
                break
            st, hd, body = req(url)
            last = f"{urllib.parse.urlsplit(url).path} {st}"
            nxt = hd.get("Location")
            if not nxt and st < 300:   # en side i stedet for omdirigering: samtykke, vilkår eller totrinn
                html = body.decode("utf-8", "replace")
                m = re.search(r"<title[^>]*>([^<]*)</title>", html, re.I)
                where = urllib.parse.urlsplit(url).hostname + urllib.parse.urlsplit(url).path + (f" («{m.group(1).strip()}»)" if m else "")
                if re.search(r"two.?factor|totrinn|engangskode|verification code|one-time code", html, re.I):
                    raise PodmeError(f"Schibsted ber om totrinnsbekreftelse ({where}). Det støttes ikke ennå.")
                raise PodmeError(f"Innloggingen stoppet på en side hos Schibsted: {where}. Logg inn i Podme-appen én gang og godta vilkårene.")
        if not code:
            raise PodmeError(f"Fikk ingen innloggingskode fra Podme (stoppet etter {last})")

        st, _, body = req(auth("oauth/token"), headers={"X-OIDC": "v1", "X-Region": "NO", "Accept": "application/json"},
                          form={"client_id": CLIENT_ID, "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "code_verifier": verifier})
        if st >= 300:
            raise PodmeError(f"Podme ga ikke tilgang ({st})")
        return self._keep(json.loads(body))

    def _refresh(self):
        t = self.tokens
        if not t or not t.get("refresh_token"):
            return None
        data = urllib.parse.urlencode({"client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": t["refresh_token"]}).encode()
        r = urllib.request.Request(AUTH_BASE + "oauth/token", data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded", "User-Agent": REFRESH_UA, "X-OIDC": "v1", "X-Region": "NO", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=15) as resp:
                return self._keep(json.loads(resp.read()), t)
        except Exception:
            return None

    def _token(self, force=False) -> str:
        """Gyldig tilgangsnøkkel: lagret → fornyet → ny innlogging. Etter en mislykket innlogging venter vi 10 min,
        så Schibsted ikke låser kontoen."""
        with self.lock:
            t = self.tokens
            if not force and t and t.get("expiration_time", 0) - 60 > time.time():
                return t["access_token"]
            if self.failed and time.time() - self.failed[0] < 600:
                raise self.failed[1]
            try:
                t = self._refresh() or self._login()
                self.failed, self.last_error = None, None
                return t["access_token"]
            except PodmeError as e:
                self.failed, self.last_error = (time.time(), e), str(e)
                raise
            except Exception as e:
                err = PodmeError(f"Fikk ikke kontakt med Podme ({e})")
                self.failed, self.last_error = (time.time(), err), str(err)
                raise err

    # ---------- API ----------
    def _api(self, path, params=None, method="GET", body=None, retry=0):
        q = "?" + urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None}) if params else ""
        h = {"Accept": "application/json", "X-Region": "NO", "User-Agent": API_UA, "Authorization": "Bearer " + self._token(retry > 0)}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        r = urllib.request.Request(API + path + q, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(r, timeout=15) as resp:
                txt = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 401 and retry == 0:
                self.tokens = None
                return self._api(path, params, method, body, 1)
            if e.code == 404:
                raise PodmeError("Fant ikke dette hos Podme", 404)
            raise PodmeError(f"Podme svarte {e.code}")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            raise PodmeError(f"Fikk ikke kontakt med Podme ({e})")
        return json.loads(txt) if txt else True

    def _pages(self, path, params=None, max_pages=4, key=None):
        out = []
        for page in range(max_pages):
            r = self._api(path, {"pageSize": 50, "page": page, **(params or {})})
            items = r if isinstance(r, list) else (r.get(key) if key and isinstance(r, dict) else [])
            if not items:
                break
            out += items
            if len(items) < 50:
                break
        return out

    # ---------- i Skjolds podkastformat (pi/skjold_pod.py) ----------
    @staticmethod
    def show_of(p: dict) -> dict:
        pid = p.get("id") or p.get("podcastId")
        return {"id": f"podme:{pid}", "title": p.get("title") or p.get("podcastTitle") or "Podme", "author": p.get("authorFullName") or "Podme",
                "image": p.get("largeImageUrl") or p.get("mediumImageUrl") or p.get("imageUrl") or "", "src": "podme",
                "genre": ", ".join(c.get("name", "") for c in (p.get("categories") or []) if isinstance(c, dict))[:60],
                "premium": bool(p.get("isPremium")), "description": p.get("description") or ""}

    @staticmethod
    def episode_of(e: dict, show: str = "") -> dict:
        dur = _secs(e.get("length")) or _secs(e.get("audioLength"))
        pos = float(e.get("currentSpotSec") or _secs(e.get("currentSpot")) or 0)
        dato, ts = _dato(e.get("publishDate") or e.get("dateAdded"))
        return {"id": f"podme-{e.get('id')}", "url": f"podme:{e.get('id')}", "title": e.get("title") or "", "date": dato, "ts": ts,
                "duration": dur, "image": e.get("imageUrl") or e.get("podcastImageUrl") or e.get("mediumImageUrl") or "",
                "description": re.sub(r"<[^>]+>", "", e.get("description") or "")[:300], "show": e.get("podcastTitle") or show,
                "pid": f"podme:{e.get('podcastId')}", "pos": dur if e.get("hasCompleted") else pos, "heard": bool(e.get("hasCompleted"))}

    def me(self) -> dict:
        u = self._api("v2/user")
        return {"user": (u or {}).get("email") or (u or {}).get("userName") or (u or {}).get("name") or self.email}

    def my_podcasts(self) -> list:
        return [self.show_of(p) for p in self._pages("v2/podcasts/mypodcasts")]

    def search(self, q: str) -> list:
        return [self.show_of(p) for p in self._pages("v2/podcasts/search", {"searchText": q}, 1, "podcasts")]

    def show(self, podcast_id: int) -> dict:
        info = {}
        try:
            info = self.show_of(self._api(f"v2/podcasts/{podcast_id}"))
        except PodmeError:
            pass
        eps = [self.episode_of(e, info.get("title", "")) for e in self._pages(f"v2/episodes/podcast/{podcast_id}", None, 3)]
        if not info:
            first = eps[0] if eps else {}
            info = {"id": f"podme:{podcast_id}", "title": first.get("show") or "Podme", "author": "Podme", "image": first.get("image", ""), "src": "podme", "description": ""}
        eps.sort(key=lambda e: -(e.get("ts") or 0))
        return {**info, "episodes": eps}

    def feed(self, n=30) -> list:
        return [self.episode_of(e) for e in self._pages("v2/episodes/feed", {"excludeCompleted": "true", "orderBy": 0}, 1)[:n]]

    def follow(self, podcast_id: int, on: bool):
        self._api(f"v2/podcasts/bookmarks/{podcast_id}", method="POST" if on else "DELETE")

    def save_progress(self, episode_id: int, pos: float, completed: bool = False):
        if completed:
            self._api(f"v2/episodes/{episode_id}/completed", method="PATCH")
        else:
            self._api("v3/episodes/player-update", method="POST", body={"episodeId": episode_id, "currentSpotSec": round(pos), "playMode": None, "playAction": None})

    def audio_url(self, episode_id: int) -> str:
        """Selve lydfila. Podme gir enten en direkte fil eller en HLS-spilleliste som peker på én mp4-fil."""
        hit = self._stream.get(episode_id)
        if hit and time.time() - hit[0] < 1800:
            return hit[1]
        e = self._api(f"v2/episodes/{episode_id}")
        if e.get("episodeCanBePlayed") is False:
            raise PodmeError("Episoden krever et Podme-abonnement du ikke har", 403)
        url = e.get("url")
        stream = e.get("streamUrl") or e.get("hlsV4Url") or e.get("hlsV3Url") or e.get("smoothStreamingUrl")
        if not url and stream:
            url = self._hls(stream) if "m3u8" in stream else stream
        if not url:
            raise PodmeError("Fant ingen lyd for episoden")
        self._stream[episode_id] = (time.time(), url)
        return url

    def _hls(self, master: str) -> str:
        def get(u):
            r = urllib.request.Request(u, headers={"User-Agent": API_UA})
            try:
                with urllib.request.urlopen(r, timeout=15) as resp:
                    return resp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                raise PodmeError(f"Podme-strømmen svarte {e.code}")
        txt = get(master)
        line = next((l for l in txt.splitlines() if ".m3u8" in l), None)
        playlist = urllib.parse.urljoin(master, line.strip()) if line else master
        ptxt = get(playlist) if line else txt
        seg = next((l for l in ptxt.splitlines() if l and not l.startswith("#") and "mp4" in l), None)
        if not seg:
            raise PodmeError("Fant ikke lydfila i Podme-strømmen")
        return urllib.parse.urljoin(playlist, seg.strip()).split("?")[0]
