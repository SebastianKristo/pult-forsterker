// Skjold-hjem – sky-relé for Skjold-enheter (Cloudflare Worker + Durable Objects).
// Kontrakt: docs/SKJOLD_HJEM.md. Ingen byggesteg: ren JavaScript (ES-moduler).
//
//  Worker (fetch)        – ruting, brukerinnlogging (Cloudflare Access), web-UI (statiske filer)
//  Sted   (DO per sted)  – stedets data, enhetsnøkler, koblingskoder, WebSocket til enhetene, relé, aktiv hovedenhet
//  Konto  (DO per e-post) – brukerens liste over steder
//  Koder  (DO «koder»)   – liten indeks kode → sted, så /enhet/kobl finner stedet fra koden
import { DurableObject } from "cloudflare:workers";

const KODE_TEGN = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // uten I, O, 0, 1
const KODE_TTL_MS = 10 * 60 * 1000;
// Automatisk innmelding av nye enheter på LAN-et: første forsøk straks, deretter dobles pausen opp til et døgn
const INVITER_PAUSE_MS = KODE_TTL_MS;
const INVITER_MAKS_PAUSE_MS = 24 * 60 * 60 * 1000;
const INVITER_PER_RUNDE = 3;
const RELE_TIMEOUT_MS = 25 * 1000;
const STALE_MS = 45 * 1000;
const ALARM_MS = 30 * 1000;
const PING = '{"t":"ping"}';
const PONG = '{"t":"pong"}';

// ---------- små hjelpere ----------
const json = (data, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers },
  });
const feil = (status, melding) => json({ feil: melding }, status);

function tilfeldig(n, alfabet) {
  const b = crypto.getRandomValues(new Uint8Array(n));
  let s = "";
  for (const x of b) s += alfabet[x % alfabet.length]; // 256 % 32 == 0 ⇒ ingen skjevhet for 32-tegns alfabet
  return s;
}
const hex = (buf) => [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, "0")).join("");
async function sha256hex(s) {
  return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)));
}
function likTid(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function tilB64(buf) {
  const u = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
  return btoa(s);
}
function fraB64(s) {
  const bin = atob(s);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}
function b64urlTilBytes(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return fraB64(s);
}
const nyId = (prefiks) => prefiks + tilfeldig(10, "abcdefghijklmnopqrstuvwxyz234567");

// ---------- brukerinnlogging ----------
let certsCache = { url: "", t: 0, keys: [] };

function teamUrl(team) {
  let t = String(team).trim().replace(/^https?:\/\//, "").replace(/\/+$/, "");
  if (!t.includes(".")) t += ".cloudflareaccess.com";
  return "https://" + t;
}

async function hentCerts(url, tving = false) {
  if (!tving && certsCache.url === url && Date.now() - certsCache.t < 10 * 60 * 1000) return certsCache.keys;
  const r = await fetch(url);
  if (!r.ok) throw new Error("certs " + r.status);
  const keys = (await r.json()).keys || [];
  certsCache = { url, t: Date.now(), keys };
  return keys;
}

function cookie(req, navn) {
  for (const del of (req.headers.get("cookie") || "").split(";")) {
    const [k, ...v] = del.trim().split("=");
    if (k === navn) return v.join("=");
  }
  return "";
}

/** Verifiser Cloudflare Access-JWT (RS256) mot teamets nøkler. Gir e-post eller null. */
export async function verifiserAccess(req, env) {
  const tok = req.headers.get("cf-access-jwt-assertion") || cookie(req, "CF_Authorization");
  if (!tok) return null;
  const deler = tok.split(".");
  if (deler.length !== 3) return null;
  let hode, last;
  try {
    hode = JSON.parse(new TextDecoder().decode(b64urlTilBytes(deler[0])));
    last = JSON.parse(new TextDecoder().decode(b64urlTilBytes(deler[1])));
  } catch {
    return null;
  }
  if (hode.alg !== "RS256") return null;
  const team = teamUrl(env.ACCESS_TEAM_DOMAIN);
  const url = team + "/cdn-cgi/access/certs";
  let keys = await hentCerts(url);
  let jwk = keys.find((k) => k.kid === hode.kid);
  if (!jwk) {
    keys = await hentCerts(url, true); // nøkkelrotasjon
    jwk = keys.find((k) => k.kid === hode.kid);
  }
  if (!jwk) return null;
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    key,
    b64urlTilBytes(deler[2]),
    new TextEncoder().encode(deler[0] + "." + deler[1]),
  );
  if (!ok) return null;
  const aud = Array.isArray(last.aud) ? last.aud : [last.aud];
  if (!aud.includes(env.ACCESS_AUD)) return null;
  const naa = Math.floor(Date.now() / 1000);
  if (typeof last.exp !== "number" || last.exp < naa) return null;
  if (typeof last.nbf === "number" && last.nbf > naa + 60) return null;
  if (last.iss && last.iss !== team) return null;
  const epost = String(last.email || "").toLowerCase();
  return epost || null;
}

/** Hvem er brukeren? Access-JWT når ACCESS_TEAM_DOMAIN + ACCESS_AUD er satt; ellers bare med DEV_INSECURE=1. */
async function bruker(req, env) {
  if (env.ACCESS_TEAM_DOMAIN && env.ACCESS_AUD) {
    try {
      return await verifiserAccess(req, env);
    } catch (e) {
      console.log("Access-verifisering feilet", String(e));
      return null;
    }
  }
  if (String(env.DEV_INSECURE || "") === "1") {
    const e = req.headers.get("x-skjold-user") || req.headers.get("cf-access-authenticated-user-email");
    return e ? e.trim().toLowerCase() : null;
  }
  return null;
}

// ---------- Worker ----------
const stedStub = (env, id) => env.STED.get(env.STED.idFromName(id));
const kontoStub = (env, epost) => env.KONTO.get(env.KONTO.idFromName(epost));
const koderStub = (env) => env.KODER.get(env.KODER.idFromName("koder"));
const hoyttalerStub = (env) => env.HOYTTALERE.get(env.HOYTTALERE.idFromName("hoyttalere"));
const delingStub = (env) => env.DELINGER.get(env.DELINGER.idFromName("delinger"));
const registerStub = (env) => env.REGISTER.get(env.REGISTER.idFromName("register"));
const intern = (stub, sti, data) =>
  stub.fetch("https://do/i" + sti, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data ?? {}) });

async function lesJson(req) {
  try {
    return await req.json();
  } catch {
    return {};
  }
}

const LANDING = `<!doctype html><html lang="nb"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Skjold-hjem</title><body style="font-family:system-ui;margin:2rem;max-width:40rem">
<h1>Skjold-hjem</h1><p>Sky-reléet kjører, men web-UI-et er ikke lagt ut ennå (bygg <code>skjold/app</code> før <code>wrangler deploy</code>).</p>
<p>API: <a href="/api/hjem/steder">/api/hjem/steder</a></p></body></html>`;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const p = url.pathname;

    // --- enheter (utenom Access, egen nøkkel) ---
    if (p === "/enhet/kobl" && req.method === "POST") {
      const b = await lesJson(req);
      const kode = String(b.kode || "").trim().toUpperCase().replace(/[\s-]/g, "");
      const id = String(b.id || "").trim();
      if (!/^[A-Z0-9]{6}$/.test(kode) || !id || id.length > 64) return feil(400, "kode og id må oppgis");
      const r = await intern(koderStub(env), "/los", { kode });
      if (!r.ok) return feil(404, "ukjent eller utløpt kode");
      const { sted } = await r.json();
      return intern(stedStub(env, sted), "/kobl", { kode, id, navn: b.navn, produkt: b.produkt });
    }
    if (p === "/enhet/sync") {
      // Skjold Cloud: ende-til-ende-krypterte blobs (favoritter, rutiner, innstillinger …) per konto (stedets eier).
      // Skyen ser aldri innholdet – bare navn på delen, versjon, størrelse og tidspunkt.
      const auth = req.headers.get("authorization") || "";
      const m = /^Bearer\s+(.+)$/i.exec(auth);
      const t = m ? /^(.+)\.(st_[a-z2-7]+)\.([0-9a-f]{64})$/.exec(m[1].trim()) : null;
      if (!t) return feil(401, "ugyldig enhetsnøkkel");
      const v = await stedStub(env, t[2]).fetch(new Request("https://do/i/eier", {
        method: "POST",
        headers: { "x-skjold-enhet": t[1], "x-skjold-noekkel": t[2] + "." + t[3] },
      }));
      if (!v.ok) return v;
      const { eier } = await v.json();
      const konto = kontoStub(env, eier);
      if (req.method === "GET") return intern(konto, "/sync/hent", { del: url.searchParams.get("del") || "" });
      if (req.method === "PUT") {
        const b = await lesJson(req);
        return intern(konto, "/sync/lagre", { ...b, enhet: t[1] });
      }
      return feil(405, "metode ikke støttet");
    }
    if (p === "/enhet/ws") {
      if ((req.headers.get("upgrade") || "").toLowerCase() !== "websocket") return feil(426, "krever WebSocket");
      const auth = req.headers.get("authorization") || "";
      const m = /^Bearer\s+(.+)$/i.exec(auth);
      // noekkel = "<sted>.<64 hex>"; token = "<id>.<noekkel>"
      const t = m ? /^(.+)\.(st_[a-z2-7]+)\.([0-9a-f]{64})$/.exec(m[1].trim()) : null;
      if (!t) return feil(401, "ugyldig enhetsnøkkel");
      const h = new Headers(req.headers);
      h.set("x-skjold-enhet", t[1]);
      h.set("x-skjold-noekkel", t[2] + "." + t[3]);
      return stedStub(env, t[2]).fetch(new Request("https://do/i/ws", { headers: h }));
    }

    // --- Skjold Sertifisert: åpen, anonym database over høyttalerprofiler (se docs/HOYTTALERPROFILER.md) ---
    if (p.startsWith("/hoyttaler/")) {
      if (!env.HOYTTALERE) return feil(503, "profildatabasen er ikke satt opp");
      const ip = req.headers.get("cf-connecting-ip") || "lokal";
      const h = new Headers({ "content-type": "application/json", "x-ip": await sha256hex("skjold-ip:" + ip) });
      const auth = /^Bearer\s+(.+)$/i.exec(req.headers.get("authorization") || "");
      if (auth && env.MOD_TOKEN && likTid(auth[1].trim(), env.MOD_TOKEN)) h.set("x-mod", "1");
      return hoyttalerStub(env).fetch(new Request("https://do" + p + url.search, {
        method: req.method, headers: h, body: req.method === "GET" ? undefined : await req.text(),
      }));
    }

    // --- Del en kassett: anonym postkasse for krypterte kassettlister (nøkkelen står bare i delingskoden) ---
    if (p === "/del" || p.startsWith("/del/")) {
      if (!env.DELINGER) return feil(503, "deling er ikke satt opp");
      const ip = req.headers.get("cf-connecting-ip") || "lokal";
      return delingStub(env).fetch(new Request("https://do" + p, {
        method: req.method,
        headers: { "content-type": "application/json", "x-ip": await sha256hex("skjold-ip:" + ip) },
        body: req.method === "POST" ? await req.text() : undefined,
      }));
    }

    // --- vedlikehold: offentlig, så appen og enhetene kan vise nedtellingen også uten innlogging ---
    if (p === "/api/vedlikehold") {
      const vh = await vedlikehold(env);
      return json(vh.aktiv ? vh : { aktiv: false }, 200, { "access-control-allow-origin": "*" });
    }

    // --- brukere (bak Access) ---
    if (p === "/api/hjem" || p.startsWith("/api/hjem/") || p === "/api/valhalla" || p.startsWith("/api/valhalla/")) {
      const epost = await bruker(req, env);
      if (!epost) return feil(401, "ikke innlogget");
      const rolle = await kontoRolle(env, epost);
      if (rolle.sperret) return feil(403, "kontoen er sperret – kontakt Skjold Lab");
      // Vedlikehold (Valhalla): alle unntatt administratorene får 503 med nedtelling – enhetene virker lokalt som før
      const vh = await vedlikehold(env);
      if (vh.aktiv && !rolle.valhalla && p !== "/api/hjem/meg") return json({ error: "vedlikehold", vedlikehold: vh }, 503);
      // Økt (cookie per nettleser/telefon): ny økt lages ved første besøk. Med totrinnsbekreftelse må økten bekreftes
      // (kode, passkey/sikkerhetsnøkkel eller godkjenning fra appen) før noe annet enn bekreftelsen virker.
      const okt = await hentOkt(req, env, epost, rolle);
      const medOkt = (r) => { if (!okt.cookie) return r; const ny = new Response(r.body, r); ny.headers.append("set-cookie", okt.cookie); return ny; };
      if (p === "/api/hjem/meg") return medOkt(json({ epost, valhalla: rolle.valhalla && okt.bekreftet, eier: rolle.eier, tofa: rolle.tofa, tofaOk: okt.bekreftet, vedlikehold: vh.aktiv ? vh : null }));
      const BEKREFT = ["/api/hjem/konto/2fa/bekreft", "/api/hjem/konto/passkey/login-start", "/api/hjem/konto/passkey/login", "/api/hjem/konto/godkjenn/start", "/api/hjem/konto/godkjenn/status"];
      if (BEKREFT.includes(p)) return medOkt(await bekreftApi(req, env, epost, url, okt));
      if (!okt.bekreftet) return medOkt(json({ error: "2fa", tofa: true, melding: "Bekreft at det er deg" }, 401));
      if (p === "/api/hjem/konto" || p.startsWith("/api/hjem/konto/")) return medOkt(await kontoApi(req, env, epost, url, okt));
      if (p.startsWith("/api/valhalla")) {
        if (!rolle.valhalla) return feil(403, "bare for Skjold Lab Valhalla-administratorer");
        return medOkt(await valhalla(req, env, epost, rolle, url));
      }
      return medOkt(await api(req, env, epost, url));
    }

    if (p.startsWith("/api/") || p.startsWith("/enhet/")) return feil(404, "finnes ikke");

    // --- web-UI (statiske filer fra skjold/app/dist; wrangler.toml [assets]) ---
    if (env.ASSETS) {
      const r = await env.ASSETS.fetch(req);
      if (r.status !== 404) return r;
      // SPA-fallback
      return env.ASSETS.fetch(new Request(new URL("/index.html", url), req));
    }
    if (p === "/" || p === "/index.html") return new Response(LANDING, { headers: { "content-type": "text/html; charset=utf-8" } });
    return feil(404, "finnes ikke");
  },
};

// ---------- Konto-roller, deling og Valhalla (tjenesteadministrasjon) ----------
const ROLLE_CACHE = new Map(); // epost → { t, rolle } – sperring slår inn innen ett minutt på alle isolater
const eierListe = (env) => String(env.OWNER_EMAILS || "").split(/[,\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean);

async function kontoRolle(env, epost) {
  const c = ROLLE_CACHE.get(epost);
  if (c && Date.now() - c.t < 60000) return c.rolle;
  let r = { sperret: false, admin: false };
  try { r = await (await intern(registerStub(env), "/bruker", { epost })).json(); } catch {}
  const eier = eierListe(env).includes(epost);
  const rolle = { sperret: !!r.sperret && !eier, eier, valhalla: eier || !!r.admin, tofa: !!r.tofa };
  ROLLE_CACHE.set(epost, { t: Date.now(), rolle });
  return rolle;
}

async function synkMedlemmer(env, stedId, svar) {
  for (const m of svar.lagtTil || []) await intern(kontoStub(env, m), "/legg", { id: stedId, navn: svar.navn });
  for (const m of svar.fjernet || []) await intern(kontoStub(env, m), "/fjern", { id: stedId });
  await intern(registerStub(env), "/steder", { steder: [{ id: stedId, navn: svar.navn, eier: svar.eier, medlemmer: svar.medlemmer }] });
}

// ---------- Skjold-konto: profil, totrinnsbekreftelse (TOTP) og økter ----------
const B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
function b32(bytes) {
  let bits = 0, v = 0, ut = "";
  for (const b of bytes) { v = (v << 8) | b; bits += 8; while (bits >= 5) { ut += B32[(v >>> (bits - 5)) & 31]; bits -= 5; } }
  if (bits > 0) ut += B32[(v << (5 - bits)) & 31];
  return ut;
}
function fraB32(s) {
  let bits = 0, v = 0; const ut = [];
  for (const c of String(s).toUpperCase().replace(/[^A-Z2-7]/g, "")) { v = (v << 5) | B32.indexOf(c); bits += 5; if (bits >= 8) { ut.push((v >>> (bits - 8)) & 255); bits -= 8; } }
  return new Uint8Array(ut);
}
export async function totpKode(hemmelighet, steg) {
  const key = await crypto.subtle.importKey("raw", fraB32(hemmelighet), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const buf = new ArrayBuffer(8); const dv = new DataView(buf); dv.setUint32(0, Math.floor(steg / 2 ** 32)); dv.setUint32(4, steg >>> 0);
  const h = new Uint8Array(await crypto.subtle.sign("HMAC", key, buf));
  const o = h[19] & 15;
  const n = ((h[o] & 127) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3];
  return String(n % 1000000).padStart(6, "0");
}
/** Riktig 6-sifret kode for nå (±30 s). Gir steget som ble brukt (så samme kode ikke kan brukes to ganger), ellers -1. */
async function totpSjekk(hemmelighet, kode, brukt = -1) {
  const k = String(kode || "").replace(/\D/g, "");
  if (k.length !== 6) return -1;
  const naa = Math.floor(Date.now() / 30000);
  for (const d of [0, -1, 1]) if (naa + d > brukt && likTid(await totpKode(hemmelighet, naa + d), k)) return naa + d;
  return -1;
}
let OKT_NOEKKEL = null;
async function oktNoekkel(env) {
  if (!OKT_NOEKKEL) {
    const h = env.SESSION_SECRET || (await (await intern(registerStub(env), "/hemmelighet", {})).json()).h;
    OKT_NOEKKEL = await crypto.subtle.importKey("raw", new TextEncoder().encode(h), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  }
  return OKT_NOEKKEL;
}
async function oktSign(env, tekst) { return tilB64(await crypto.subtle.sign("HMAC", await oktNoekkel(env), new TextEncoder().encode(tekst))).replace(/=+$/, ""); }
// Økter utløper ikke av seg selv: cookien fornyes (glidende) så lenge enheten brukes. Totrinnsbekreftelse kreves bare
// når en ny enhet logger inn, eller etter «logg ut». 400 dager er det lengste nettleserne godtar for en cookie.
const OKT_DAGER = 400;
async function oktCookie(env, epost, sid) {
  const exp = Math.floor(Date.now() / 1000) + OKT_DAGER * 86400;
  return `skjold_okt=${sid}.${exp}.${await oktSign(env, epost + "|" + sid + "|" + exp)}; Path=/; Max-Age=${OKT_DAGER * 86400}; HttpOnly; Secure; SameSite=None`;
}
const OKT_CACHE = new Map(); // epost|sid → { t, bekreftet } – en utlogget økt slutter å virke innen ett minutt
function enhetsnavn(req) {
  const ua = req.headers.get("user-agent") || "";
  const os = /iPhone/.test(ua) ? "iPhone" : /iPad/.test(ua) ? "iPad" : /Android/.test(ua) ? "Android" : /Mac OS X/.test(ua) ? "Mac" : /Windows/.test(ua) ? "Windows" : /Linux/.test(ua) ? "Linux" : "Ukjent enhet";
  const app = /SkjoldApp|Capacitor/i.test(ua) ? "Skjold-appen" : /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : "nettleser";
  const land = (req.cf && req.cf.city ? req.cf.city + ", " : "") + ((req.cf && req.cf.country) || "");
  return { navn: app + " på " + os, sted: land };
}
/** Økten for denne nettleseren/telefonen. Lager en ny (med Set-Cookie) hvis cookien mangler, er ugyldig eller logget ut. */
async function hentOkt(req, env, epost, rolle) {
  const c = cookie(req, "skjold_okt");
  if (c) {
    const [sid, exp, sig] = c.split(".");
    if (sig && Number(exp) > Date.now() / 1000 && likTid(sig, await oktSign(env, epost + "|" + sid + "|" + exp))) {
      const n = epost + "|" + sid, hit = OKT_CACHE.get(n);
      // mer enn 30 dager siden cookien ble laget: forny den, så økten aldri går ut mens den er i bruk
      const forny = Number(exp) - Date.now() / 1000 < (OKT_DAGER - 30) * 86400 ? await oktCookie(env, epost, sid) : undefined;
      if (hit && Date.now() - hit.t < 60000) return { sid, bekreftet: hit.bekreftet || !rolle.tofa, cookie: forny };
      const r = await (await intern(kontoStub(env, epost), "/okt/sjekk", { sid })).json();
      if (r.finnes) { OKT_CACHE.set(n, { t: Date.now(), bekreftet: r.bekreftet }); return { sid, bekreftet: r.bekreftet || !rolle.tofa, cookie: forny }; }
    }
  }
  const e = enhetsnavn(req);
  const { sid } = await (await intern(kontoStub(env, epost), "/okt/ny", { ...e, bekreftet: !rolle.tofa })).json();
  const cookieV = await oktCookie(env, epost, sid);
  return { sid, bekreftet: !rolle.tofa, cookie: cookieV, ny: true };
}
async function oktBekreftet(env, epost, okt, metode) {
  await intern(kontoStub(env, epost), "/okt/bekreft", { sid: okt.sid, metode });
  OKT_CACHE.delete(epost + "|" + okt.sid);
}
const rpId = (url) => url.hostname;
const opphav = (url) => url.origin;

/** Bekreftelse av en ny økt: kode (TOTP/reserve), passkey/sikkerhetsnøkkel, eller godkjenning fra en innlogget enhet. */
async function bekreftApi(req, env, epost, url, okt) {
  const k = kontoStub(env, epost), p = url.pathname.slice("/api/hjem/konto".length), b = req.method === "POST" ? await lesJson(req) : {};
  if (p === "/2fa/bekreft") {
    const r = await intern(k, "/konto/2fa/sjekk", { kode: b.kode });
    if (!r.ok) return r;
    await oktBekreftet(env, epost, okt, "kode");
    return json({ ok: true });
  }
  if (p === "/passkey/login-start") return intern(k, "/konto/passkey/login-start", { rpId: rpId(url) });
  if (p === "/passkey/login") {
    const r = await intern(k, "/konto/passkey/login", { ...b, rpId: rpId(url), opphav: opphav(url) });
    if (!r.ok) return r;
    await oktBekreftet(env, epost, okt, "passkey");
    return json({ ok: true });
  }
  if (p === "/godkjenn/start") return intern(k, "/konto/godkjenn/start", { sid: okt.sid, ...enhetsnavn(req) });
  if (p === "/godkjenn/status") {
    const r = await (await intern(k, "/konto/godkjenn/status", { rid: url.searchParams.get("rid"), sid: okt.sid })).json();
    if (r.status === "godkjent") OKT_CACHE.delete(epost + "|" + okt.sid);
    return json(r);
  }
  return feil(404, "finnes ikke");
}

async function kontoApi(req, env, epost, url, okt) {
  const del = url.pathname.slice("/api/hjem/konto".length) || "/";
  const k = kontoStub(env, epost), m = req.method, reg = registerStub(env);
  const b = m === "GET" || m === "DELETE" ? {} : await lesJson(req);
  const tofaFlagg = async (svar) => { await intern(reg, "/bruker-sett", { epost, tofa: !!svar.tofaAktiv }); ROLLE_CACHE.delete(epost); };
  if (del === "/" && m === "GET") {
    const info = await (await intern(k, "/konto/info", { epost })).json();
    const { steder } = await (await intern(k, "/liste")).json();
    const sync = await (await intern(k, "/sync/oversikt", {})).json();
    return json({ ...info, epost, steder, sync: sync.deler || [] });
  }
  if (del === "/" && m === "PATCH") {
    if (b.bilde !== undefined && b.bilde !== "" && !/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(String(b.bilde))) return feil(400, "ugyldig bilde");
    if (String(b.bilde || "").length > 90000) return feil(413, "bildet er for stort (maks ca. 60 kB)");
    const r = await intern(k, "/konto/profil", b);
    if (r.ok && b.bilde !== undefined) await intern(reg, "/bruker-sett", { epost, bilde: String(b.bilde || "") });
    return r;
  }
  if (del === "/2fa/start" && m === "POST") return intern(k, "/konto/2fa/start", { epost });
  if ((del === "/2fa/aktiver" || del === "/2fa/av" || del === "/2fa/nye-koder") && m === "POST") {
    const r = await intern(k, "/konto" + del, b);
    if (!r.ok) return r;
    const svar = await r.json();
    await tofaFlagg(svar);
    await oktBekreftet(env, epost, okt, "kode");
    return json(svar);
  }
  // passkeys og sikkerhetsnøkler (WebAuthn)
  if (del === "/passkey/start" && m === "POST") return intern(k, "/konto/passkey/start", { epost, rpId: rpId(url), type: b.type });
  if (del === "/passkey/registrer" && m === "POST") {
    const r = await intern(k, "/konto/passkey/registrer", { ...b, rpId: rpId(url), opphav: opphav(url) });
    if (!r.ok) return r;
    const svar = await r.json(); await tofaFlagg(svar);
    return json(svar);
  }
  if (del.startsWith("/passkey/") && m === "DELETE") {
    const r = await intern(k, "/konto/passkey/slett", { id: decodeURIComponent(del.slice(9)) });
    if (!r.ok) return r;
    const svar = await r.json(); await tofaFlagg(svar);
    return json(svar);
  }
  // godkjenn innlogging på en annen enhet
  if (del === "/godkjenn/ventende" && m === "GET") return intern(k, "/konto/godkjenn/ventende", { sid: okt.sid });
  if (del.startsWith("/godkjenn/") && m === "POST") {
    const r = await intern(k, "/konto/godkjenn/svar", { rid: decodeURIComponent(del.slice(10)), svar: b.svar, av: okt.sid });
    if (r.ok) { const j = await r.clone().json(); if (j.sid) OKT_CACHE.delete(epost + "|" + j.sid); }
    return r;
  }
  // økter (påloggede enheter)
  if (del === "/okter" && m === "GET") return json((await (await intern(k, "/okt/liste", {})).json()).map((x) => ({ ...x, denne: x.sid === okt.sid })));
  if (del.startsWith("/okter/") && m === "DELETE") {
    const sid = decodeURIComponent(del.slice(7));
    await intern(k, "/okt/slett", { sid }); OKT_CACHE.delete(epost + "|" + sid);
    return json({ ok: true });
  }
  if (del === "/logg-ut-overalt" && m === "POST") {
    const l = await (await intern(k, "/okt/liste", {})).json();
    await intern(k, "/okt/slett-alle", {});
    for (const x of l) OKT_CACHE.delete(epost + "|" + x.sid);
    return json({ ok: true, antall: l.length });
  }
  if (del === "/" && m === "DELETE") {
    const { steder } = await (await intern(k, "/liste")).json();
    for (const s of steder) {
      const o = await intern(stedStub(env, s.id), "/admin", {});
      if (o.ok && (await o.json()).eier === epost) return feil(409, "du eier fortsatt «" + s.navn + "» – overfør eierskapet eller slett hjemmet først");
    }
    for (const s of steder) {
      const r = await intern(stedStub(env, s.id), "/admin-endre", { fjern: epost });
      if (r.ok) await synkMedlemmer(env, s.id, await r.json());
    }
    await intern(k, "/konto/slett", {});
    await intern(reg, "/bruker-slett", { epost });
    ROLLE_CACHE.delete(epost);
    return json({ ok: true });
  }
  return feil(404, "finnes ikke");
}

// ---------- Vedlikehold (service mode) – settes i Valhalla, mellomlagres 15 s per isolat ----------
let VH = { t: 0, v: { aktiv: false } };
async function vedlikehold(env) {
  if (Date.now() - VH.t < 15000) return VH.v;
  try { VH = { t: Date.now(), v: await (await intern(registerStub(env), "/vedlikehold", {})).json() }; } catch {}
  if (VH.v.aktiv && VH.v.til && VH.v.til * 1000 < Date.now() - 6 * 3600 * 1000) VH.v = { aktiv: false };   // glemt i over 6 t etter slutt
  return VH.v;
}

// ---------- WebAuthn (passkeys og sikkerhetsnøkler) ----------
function b64url(bytes) { return tilB64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
function fraB64url(s) { return b64urlTilBytes(String(s || "")); }
/** Minimal CBOR-leser (det WebAuthn bruker: tall, byte, tekst, lister, kart, true/false/null). */
export function cbor(bytes) {
  let i = 0;
  const les = () => {
    const b0 = bytes[i++], mt = b0 >> 5, ai = b0 & 31;
    let n = ai;
    if (ai === 24) n = bytes[i++];
    else if (ai === 25) { n = (bytes[i] << 8) | bytes[i + 1]; i += 2; }
    else if (ai === 26) { n = ((bytes[i] << 24) >>> 0) + (bytes[i + 1] << 16) + (bytes[i + 2] << 8) + bytes[i + 3]; i += 4; }
    else if (ai > 26 && mt !== 7) throw new Error("CBOR: ikke støttet lengde");
    if (mt === 0) return n;
    if (mt === 1) return -1 - n;
    if (mt === 2) { const v = bytes.slice(i, i + n); i += n; return v; }
    if (mt === 3) { const v = new TextDecoder().decode(bytes.slice(i, i + n)); i += n; return v; }
    if (mt === 4) { const a = []; for (let k = 0; k < n; k++) a.push(les()); return a; }
    if (mt === 5) { const m = new Map(); for (let k = 0; k < n; k++) { const kk = les(); m.set(kk, les()); } return m; }
    if (mt === 7) return ai === 20 ? false : ai === 21 ? true : null;
    throw new Error("CBOR: ukjent type");
  };
  const v = les();
  return { v, slutt: i };
}
/** authenticatorData → rpIdHash, flagg, teller og (ved registrering) credential-id og offentlig nøkkel (COSE). */
export function lesAuthData(ad) {
  const flagg = ad[32], teller = ((ad[33] << 24) >>> 0) + (ad[34] << 16) + (ad[35] << 8) + ad[36];
  const ut = { rpIdHash: ad.slice(0, 32), up: !!(flagg & 1), uv: !!(flagg & 4), teller };
  if (flagg & 64) {
    const len = (ad[53] << 8) | ad[54];
    ut.credId = ad.slice(55, 55 + len);
    const c = cbor(ad.slice(55 + len));
    ut.cose = c.v;
  }
  return ut;
}
function coseTilJwk(cose) {
  const kty = cose.get(1), alg = cose.get(3);
  if (kty === 2 && alg === -7) return { alg: -7, jwk: { kty: "EC", crv: "P-256", x: b64url(cose.get(-2)), y: b64url(cose.get(-3)), ext: true } };
  if (kty === 3 && alg === -257) return { alg: -257, jwk: { kty: "RSA", n: b64url(cose.get(-1)), e: b64url(cose.get(-2)), alg: "RS256", ext: true } };
  throw new Error("nøkkeltypen støttes ikke (bare ES256 og RS256)");
}
/** ECDSA-signaturen fra WebAuthn er DER; WebCrypto vil ha r||s (64 byte). */
function derTilRaa(der) {
  let i = 2; if (der[1] & 0x80) i += der[1] & 0x7f;
  const del = () => { i++; const len = der[i++]; let v = der.slice(i, i + len); i += len; while (v.length > 32 && v[0] === 0) v = v.slice(1); const ut = new Uint8Array(32); ut.set(v, 32 - v.length); return ut; };
  const r = del(), s = del(); const ut = new Uint8Array(64); ut.set(r); ut.set(s, 32); return ut;
}
async function sha256(bytes) { return new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)); }
const likeBytes = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
/** Sjekk clientDataJSON: type, utfordring og opphav. */
function sjekkKlient(cdj, type, utfordring, opphavet) {
  const c = JSON.parse(new TextDecoder().decode(cdj));
  if (c.type !== type) throw new Error("feil type");
  if (c.challenge !== utfordring) throw new Error("feil utfordring");
  if (c.origin !== opphavet) throw new Error("feil opphav: " + c.origin);
}

const gyldigEpost = (e) => /^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,}$/i.test(String(e || ""));

/** Hjem som ble laget før registeret fantes: let gjennom kontoene registeret kjenner (og den som ser på), og meld inn
 *  hjemmene deres. Høyst hvert 5. minutt per isolat, så Valhalla er rask å bla i. */
let SIST_FUNNET = 0;
async function finnHjem(env, epost, tving = false) {
  if (!tving && Date.now() - SIST_FUNNET < 300000) return;
  SIST_FUNNET = Date.now();
  const reg = registerStub(env);
  const kontoer = (await (await intern(reg, "/kontoer", {})).json()).map((k) => k.epost);
  const kjente = new Set((await (await intern(reg, "/steder-liste", {})).json()).steder.map((x) => x.id));
  const nye = new Map();
  for (const e of [...new Set([epost, ...kontoer])].slice(0, 500)) {
    try {
      const { steder } = await (await intern(kontoStub(env, e), "/liste")).json();
      for (const x of steder || []) if (!kjente.has(x.id)) nye.set(x.id, x);
    } catch {}
  }
  const ut = [];
  for (const id of [...nye.keys()].slice(0, 300)) {
    const r = await intern(stedStub(env, id), "/admin", {});
    if (r.ok) { const d = await r.json(); ut.push({ id, navn: d.navn, eier: d.eier, medlemmer: d.medlemmer }); }
  }
  if (ut.length) await intern(reg, "/steder", { steder: ut });
}

async function valhalla(req, env, epost, rolle, url) {
  const deler = url.pathname.split("/").filter(Boolean).slice(2); // etter api/valhalla
  const reg = registerStub(env);
  const m = req.method;
  if (m === "GET" && (deler.length === 0 || deler[0] === "oversikt" || deler[0] === "steder")) await finnHjem(env, epost, url.searchParams.has("synk"));
  if (deler.length === 0 || deler[0] === "oversikt") {
    const o = await (await intern(reg, "/oversikt", {})).json();
    return json({ ...o, meg: epost, eier: rolle.eier, tjenesteeiere: eierListe(env), access: !!(env.ACCESS_TEAM_DOMAIN && env.ACCESS_AUD), vedlikehold: await (await intern(reg, "/vedlikehold", {})).json() });
  }
  if (deler[0] === "vedlikehold" && m === "POST") {
    const b = await lesJson(req);
    const r = await intern(reg, "/vedlikehold-sett", { ...b, av: epost });
    VH = { t: 0, v: { aktiv: false } };
    return r;
  }
  if (deler[0] === "kontoer" && deler.length === 1 && m === "GET") return intern(reg, "/kontoer", {});
  if (deler[0] === "kontoer" && deler.length === 2 && m === "POST") {
    const mål = decodeURIComponent(deler[1]).toLowerCase(), b = await lesJson(req);
    if ("admin" in b && !rolle.eier) return feil(403, "bare tjenesteeieren kan gi eller ta Valhalla-tilgang");
    if (eierListe(env).includes(mål) && b.sperret) return feil(400, "tjenesteeieren kan ikke sperres");
    if (b.tofaAv) {   // brukeren har mistet telefonen og reservekodene: slå av totrinnsbekreftelsen
      await intern(kontoStub(env, mål), "/konto/2fa/tilbakestill", {});
      await intern(reg, "/bruker-sett", { epost: mål, tofa: false });
      ROLLE_CACHE.delete(mål);
      return json({ epost: mål, tofa: false });
    }
    const r = await intern(reg, "/bruker-sett", { epost: mål, ...("sperret" in b ? { sperret: !!b.sperret } : {}), ...("admin" in b ? { admin: !!b.admin } : {}) });
    ROLLE_CACHE.delete(mål);
    return r;
  }
  if (deler[0] === "steder" && deler.length === 1 && m === "GET") {
    const { steder } = await (await intern(reg, "/steder-liste", {})).json();
    const ut = await Promise.all(steder.slice(0, 300).map(async (x) => {
      const r = await intern(stedStub(env, x.id), "/admin", {});
      if (r.status === 404) { await intern(reg, "/sted-slett", { id: x.id }); return null; }
      return r.ok ? { ...x, ...(await r.json()) } : { ...x, feil: true };
    }));
    return json(ut.filter(Boolean));
  }
  if (deler[0] === "steder" && deler.length === 2) {
    const id = deler[1];
    if (!/^st_[a-z2-7]+$/.test(id)) return feil(404, "ukjent sted");
    if (m === "DELETE") {
      const r = await intern(stedStub(env, id), "/admin-slett", {});
      if (!r.ok) return r;
      const svar = await r.json();
      for (const x of svar.medlemmer || []) await intern(kontoStub(env, x), "/fjern", { id });
      await intern(reg, "/sted-slett", { id });
      return json({ ok: true });
    }
    if (m === "POST") {
      const b = await lesJson(req);
      if (b.leggTil && !gyldigEpost(b.leggTil)) return feil(400, "ugyldig e-postadresse");
      const r = await intern(stedStub(env, id), "/admin-endre", b);
      if (!r.ok) return r;
      const svar = await r.json();
      await synkMedlemmer(env, id, svar);
      return json(svar);
    }
  }
  return feil(404, "finnes ikke");
}

async function api(req, env, epost, url) {
  const deler = url.pathname.split("/").filter(Boolean).slice(2); // etter api/hjem
  const konto = kontoStub(env, epost);
  if (deler[0] === "sync" && deler.length === 1) {
    if (req.method === "GET") return intern(konto, "/sync/oversikt", {});
    if (req.method === "DELETE") return intern(konto, "/sync/slett", {});
    return feil(405, "metode ikke støttet");
  }
  if (deler[0] !== "steder") return feil(404, "finnes ikke");

  if (deler.length === 1) {
    if (req.method === "GET") {
      const { steder } = await (await intern(konto, "/liste")).json();
      const ut = await Promise.all(
        steder.map(async (s) => {
          const r = await intern(stedStub(env, s.id), "/oversikt", { bruker: epost });
          if (r.status === 404 || r.status === 403) {
            await intern(konto, "/fjern", { id: s.id }); // stedet er slettet / tilgang fjernet
            return null;
          }
          return r.ok ? r.json() : { ...s, rolle: "medlem", enheter: 0, online: 0 };
        }),
      );
      const liste = ut.filter(Boolean);
      // registeret (Valhalla) holder oversikt over hjemmene – fyll inn hjem som ble laget før registeret fantes
      await intern(registerStub(env), "/steder", { steder: liste.filter((x) => x.rolle === "eier").map((x) => ({ id: x.id, navn: x.navn, eier: epost, medlemmer: x.medlemmer })) });
      return json(liste);
    }
    if (req.method === "POST") {
      const b = await lesJson(req);
      const navn = String(b.navn || "").trim().slice(0, 60) || "Hjem";
      const id = nyId("st_");
      const r = await intern(stedStub(env, id), "/opprett", { id, navn, eier: epost });
      if (!r.ok) return r;
      await intern(konto, "/legg", { id, navn });
      await intern(registerStub(env), "/steder", { steder: [{ id, navn, eier: epost, medlemmer: [epost], ny: true }] });
      return json(await r.json(), 201);
    }
    return feil(405, "metode ikke støttet");
  }

  const stedId = deler[1];
  if (!/^st_[a-z2-7]+$/.test(stedId)) return feil(404, "ukjent sted");
  const rest = "/" + deler.slice(2).join("/");
  const h = new Headers(req.headers);
  h.set("x-skjold-bruker", epost);
  const r = await stedStub(env, stedId).fetch(
    new Request("https://do/u" + (rest === "/" ? "" : rest) + url.search, {
      method: req.method,
      headers: h,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body,
    }),
  );
  // hold kontoene i takt etter navneendring / sletting
  if (deler.length === 2 && r.ok && (req.method === "PATCH" || req.method === "DELETE")) {
    const svar = await r.clone().json();
    for (const m of svar.medlemmer || [epost]) {
      if (req.method === "DELETE") await intern(kontoStub(env, m), "/fjern", { id: stedId });
      else await intern(kontoStub(env, m), "/navn", { id: stedId, navn: svar.navn });
    }
    if (req.method === "DELETE") await intern(registerStub(env), "/sted-slett", { id: stedId });
    else await intern(registerStub(env), "/steder", { steder: [{ id: stedId, navn: svar.navn, eier: svar.eier, medlemmer: svar.medlemmer }] });
  }
  // deling: den som ble lagt til / fjernet får hjemmet i / ut av kontoen sin
  if ((deler[2] === "medlemmer" || deler[2] === "eier") && r.ok) await synkMedlemmer(env, stedId, await r.clone().json());
  return r;
}

// ---------- Konto: brukerens steder ----------
export class Konto extends DurableObject {
  async fetch(req) {
    const sti = new URL(req.url).pathname;
    const b = await lesJson(req);
    if (sti.startsWith("/i/sync/")) return this.sync(sti.slice(7), b);
    if (sti.startsWith("/i/konto/")) return this.konto(sti.slice(8), b);
    if (sti.startsWith("/i/okt/")) return this.okt(sti.slice(6), b);
    let steder = (await this.ctx.storage.get("steder")) || [];
    if (sti === "/i/liste") return json({ steder });
    if (sti === "/i/legg") {
      if (!steder.some((s) => s.id === b.id)) steder.push({ id: b.id, navn: b.navn });
    } else if (sti === "/i/fjern") steder = steder.filter((s) => s.id !== b.id);
    else if (sti === "/i/navn") steder = steder.map((s) => (s.id === b.id ? { ...s, navn: b.navn } : s));
    else return feil(404, "finnes ikke");
    await this.ctx.storage.put("steder", steder);
    return json({ steder });
  }
}

// Profil og totrinnsbekreftelse for kontoen (hemmeligheten forlater aldri kontoen; reservekodene lagres som SHA-256).
const BACKUP_ALFABET = "abcdefghjkmnpqrstuvwxyz23456789";
Konto.prototype.konto = async function (sti, b) {
  const st = this.ctx.storage, naa = Math.floor(Date.now() / 1000);
  const profil = (await st.get("profil")) || { navn: "", opprettet: naa };
  const t = (await st.get("tofa")) || { aktiv: false, ver: 0, backup: [], brukt: -1 };
  const nokler = (await st.get("passkeys")) || [];
  const lagreT = () => st.put("tofa", t);
  const tofaAktiv = () => !!t.aktiv || nokler.length > 0;   // kodeapp eller passkey/sikkerhetsnøkkel = totrinnsbekreftelse
  const nyeKoder = async () => {
    const koder = Array.from({ length: 10 }, () => tilfeldig(4, BACKUP_ALFABET) + "-" + tilfeldig(4, BACKUP_ALFABET));
    t.backup = await Promise.all(koder.map((k) => sha256hex(k)));
    return koder;
  };
  /** TOTP-kode eller ubrukt reservekode. Låses i 15 min etter 8 feil. */
  const sjekk = async (kode, hemmelighet = t.hemmelighet) => {
    const feilet = (await st.get("feil")) || { n: 0, t: 0 };
    if (feilet.n >= 8 && naa - feilet.t < 900) return "låst";
    if (hemmelighet) {
      const steg = await totpSjekk(hemmelighet, kode, t.brukt);
      if (steg >= 0) { t.brukt = steg; await st.delete("feil"); return "ok"; }
    }
    const h = await sha256hex(String(kode || "").trim().toLowerCase());
    const i = (t.backup || []).indexOf(h);
    if (i >= 0 && hemmelighet === t.hemmelighet) { t.backup.splice(i, 1); await st.delete("feil"); return "ok"; }
    await st.put("feil", { n: (naa - feilet.t < 900 ? feilet.n : 0) + 1, t: naa });
    return "feil";
  };
  const svarFeil = (r) => (r === "låst" ? feil(429, "for mange feil koder – prøv igjen om 15 minutter") : feil(401, "feil kode"));
  const nokkelListe = () => nokler.map((n) => ({ id: n.id, navn: n.navn, type: n.type, opprettet: n.opprettet, sist: n.sist || null }));
  if (sti === "/info") {
    if (!(await st.get("profil"))) await st.put("profil", profil);
    return json({ navn: profil.navn, bilde: profil.bilde || "", opprettet: profil.opprettet,
      tofa: { aktiv: tofaAktiv(), kodeapp: !!t.aktiv, reservekoderIgjen: (t.backup || []).length, passkeys: nokkelListe() } });
  }
  if (sti === "/profil") {
    if (b.navn !== undefined) profil.navn = String(b.navn).trim().slice(0, 60);
    if (b.bilde !== undefined) profil.bilde = String(b.bilde || "");
    await st.put("profil", profil);
    return json({ navn: profil.navn, bilde: profil.bilde || "" });
  }
  if (sti === "/2fa/start") {
    if (t.aktiv) return feil(409, "kodeappen er allerede satt opp");
    const h = b32(crypto.getRandomValues(new Uint8Array(16)));
    t.ventende = h; await lagreT();
    return json({ hemmelighet: h, uri: `otpauth://totp/Skjold?secret=${h}&issuer=Skjold` });
  }
  if (sti === "/2fa/aktiver") {
    if (!t.ventende) return feil(400, "start oppsettet først");
    const r = await sjekk(b.kode, t.ventende);
    if (r !== "ok") return svarFeil(r);
    t.hemmelighet = t.ventende; delete t.ventende; t.aktiv = true; t.ver = (t.ver || 0) + 1;
    const koder = await nyeKoder(); await lagreT();
    return json({ aktiv: true, tofaAktiv: true, reservekoder: koder });
  }
  if (sti === "/2fa/sjekk") {
    if (!tofaAktiv()) return json({ ok: true });
    if (!t.aktiv && !(t.backup || []).length) return feil(400, "bruk passkeyen eller godkjenn fra en innlogget enhet");
    const r = await sjekk(b.kode); await lagreT();
    return r === "ok" ? json({ ok: true }) : svarFeil(r);
  }
  if (sti === "/2fa/av" || sti === "/2fa/nye-koder") {
    if (!t.aktiv) return feil(400, "kodeappen er ikke satt opp");
    const r = await sjekk(b.kode);
    if (r !== "ok") { await lagreT(); return svarFeil(r); }
    if (sti === "/2fa/av") { t.aktiv = false; delete t.hemmelighet; t.backup = []; await lagreT(); return json({ aktiv: false, tofaAktiv: tofaAktiv() }); }
    const koder = await nyeKoder(); await lagreT();
    return json({ aktiv: true, tofaAktiv: true, reservekoder: koder });
  }
  if (sti === "/2fa/tilbakestill") {   // Valhalla: mistet telefon, nøkler og reservekoder
    t.aktiv = false; delete t.hemmelighet; t.backup = []; await lagreT(); await st.delete("passkeys");
    return json({ aktiv: false, tofaAktiv: false });
  }
  // --- passkeys / sikkerhetsnøkler (WebAuthn)
  if (sti === "/passkey/start") {
    const utf = b64url(crypto.getRandomValues(new Uint8Array(32)));
    await st.put("webauthn", { utf, t: naa, type: b.type === "nokkel" ? "nokkel" : "passkey" });
    const brukerId = b64url((await sha256(new TextEncoder().encode(String(b.epost)))).slice(0, 16));
    return json({ challenge: utf, rp: { name: "Skjold", id: b.rpId }, user: { id: brukerId, name: b.epost, displayName: profil.navn || b.epost },
      pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }], timeout: 60000, attestation: "none",
      excludeCredentials: nokler.map((n) => ({ type: "public-key", id: n.id })),
      authenticatorSelection: b.type === "nokkel" ? { authenticatorAttachment: "cross-platform", residentKey: "discouraged", userVerification: "discouraged" }
        : { residentKey: "preferred", userVerification: "preferred" } });
  }
  if (sti === "/passkey/registrer") {
    const w = await st.get("webauthn");
    if (!w || naa - w.t > 300) return feil(400, "utfordringen er utløpt – prøv igjen");
    await st.delete("webauthn");
    try {
      const cdj = fraB64url(b.clientDataJSON);
      sjekkKlient(cdj, "webauthn.create", w.utf, b.opphav);
      const att = cbor(fraB64url(b.attestationObject)).v;
      const ad = lesAuthData(att.get("authData"));
      if (!likeBytes(ad.rpIdHash, await sha256(new TextEncoder().encode(b.rpId)))) throw new Error("feil rpId");
      if (!ad.up || !ad.credId) throw new Error("mangler brukerbekreftelse");
      const n = coseTilJwk(ad.cose);
      if (nokler.length >= 10) throw new Error("høyst 10 nøkler");
      nokler.push({ id: b64url(ad.credId), ...n, teller: ad.teller, navn: String(b.navn || (w.type === "nokkel" ? "Sikkerhetsnøkkel" : "Passkey")).slice(0, 40), type: w.type, opprettet: naa });
      await st.put("passkeys", nokler);
      return json({ ok: true, tofaAktiv: true, passkeys: nokkelListe() });
    } catch (e) { return feil(400, "kunne ikke registrere nøkkelen: " + e.message); }
  }
  if (sti === "/passkey/login-start") {
    if (!nokler.length) return feil(400, "ingen passkey eller sikkerhetsnøkkel er registrert");
    const utf = b64url(crypto.getRandomValues(new Uint8Array(32)));
    await st.put("webauthn-inn", { utf, t: naa });
    return json({ challenge: utf, rpId: b.rpId, timeout: 60000, userVerification: "preferred", allowCredentials: nokler.map((n) => ({ type: "public-key", id: n.id })) });
  }
  if (sti === "/passkey/login") {
    const w = await st.get("webauthn-inn");
    if (!w || naa - w.t > 300) return feil(400, "utfordringen er utløpt – prøv igjen");
    await st.delete("webauthn-inn");
    const n = nokler.find((x) => x.id === b.id);
    if (!n) return feil(401, "ukjent nøkkel");
    try {
      const cdj = fraB64url(b.clientDataJSON), adB = fraB64url(b.authenticatorData), sig = fraB64url(b.signature);
      sjekkKlient(cdj, "webauthn.get", w.utf, b.opphav);
      const ad = lesAuthData(adB);
      if (!likeBytes(ad.rpIdHash, await sha256(new TextEncoder().encode(b.rpId)))) throw new Error("feil rpId");
      if (!ad.up) throw new Error("mangler brukerbekreftelse");
      const data = new Uint8Array([...adB, ...(await sha256(cdj))]);
      const ok = n.alg === -7
        ? await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, await crypto.subtle.importKey("jwk", n.jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]), derTilRaa(sig), data)
        : await crypto.subtle.verify({ name: "RSASSA-PKCS1-v1_5" }, await crypto.subtle.importKey("jwk", n.jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]), sig, data);
      if (!ok) throw new Error("ugyldig signatur");
      if (ad.teller && n.teller && ad.teller <= n.teller) throw new Error("telleren gikk ikke opp – mulig kopiert nøkkel");
      n.teller = ad.teller; n.sist = naa;
      await st.put("passkeys", nokler);
      return json({ ok: true });
    } catch (e) { return feil(401, "nøkkelen ble ikke godtatt: " + e.message); }
  }
  if (sti === "/passkey/slett") {
    const før = nokler.length;
    const rest = nokler.filter((x) => x.id !== b.id);
    if (rest.length === før) return feil(404, "ukjent nøkkel");
    await st.put("passkeys", rest);
    return json({ ok: true, tofaAktiv: !!t.aktiv || rest.length > 0, passkeys: rest.map((n) => ({ id: n.id, navn: n.navn, type: n.type, opprettet: n.opprettet, sist: n.sist || null })) });
  }
  // --- godkjenn innlogging fra en annen enhet («Er det deg?» med tre tall)
  const foresp = (await st.get("foresp")) || {};
  for (const [rid, f] of Object.entries(foresp)) if (naa - f.t > 180) delete foresp[rid];
  if (sti === "/godkjenn/start") {
    const rid = tilfeldig(12, "abcdefghijklmnopqrstuvwxyz0123456789");
    const tall = 10 + Math.floor(Math.random() * 90);
    const valg = new Set([tall]); while (valg.size < 3) valg.add(10 + Math.floor(Math.random() * 90));
    for (const [r, f] of Object.entries(foresp)) if (f.sid === b.sid) delete foresp[r];
    foresp[rid] = { sid: b.sid, navn: String(b.navn || "").slice(0, 60), sted: String(b.sted || "").slice(0, 60), t: naa, tall, valg: [...valg].sort(() => Math.random() - 0.5), status: "venter" };
    await st.put("foresp", foresp);
    return json({ rid, tall, utloper: naa + 180 });
  }
  if (sti === "/godkjenn/status") {
    const f = foresp[b.rid];
    if (!f || f.sid !== b.sid) return json({ status: "utlopt" });
    return json({ status: f.status });
  }
  if (sti === "/godkjenn/ventende") return json(Object.entries(foresp).filter(([, f]) => f.status === "venter" && f.sid !== b.sid).map(([rid, f]) => ({ rid, navn: f.navn, sted: f.sted, t: f.t, valg: f.valg })));
  if (sti === "/godkjenn/svar") {
    const f = foresp[b.rid];
    if (!f || f.status !== "venter") return feil(404, "forespørselen er utløpt");
    if (f.sid === b.av) return feil(400, "en enhet kan ikke godkjenne seg selv");
    if (b.svar === "avvis") f.status = "avvist";
    else if (Number(b.svar) === f.tall) {
      f.status = "godkjent";
      const okter = (await st.get("okter")) || {};
      if (okter[f.sid]) { okter[f.sid].bekreftet = true; okter[f.sid].metode = "godkjent fra en annen enhet"; await st.put("okter", okter); }
    } else f.status = "avvist";   // feil tall: avvis (noen prøver å lure deg)
    await st.put("foresp", foresp);
    return json({ status: f.status, sid: f.status === "godkjent" ? f.sid : undefined });
  }
  if (sti === "/slett") { await st.deleteAll(); return json({ ok: true }); }
  return feil(404, "finnes ikke");
};

// Økter, passkeys og godkjenning fra en annen enhet (lagres per konto)
Konto.prototype.okt = async function (sti, b) {
  const st = this.ctx.storage, naa = Math.floor(Date.now() / 1000);
  const okter = (await st.get("okter")) || {};
  const lagre = () => st.put("okter", okter);
  if (sti === "/ny") {
    const sid = tilfeldig(16, "abcdefghijklmnopqrstuvwxyz0123456789");
    okter[sid] = { navn: String(b.navn || "").slice(0, 60), sted: String(b.sted || "").slice(0, 60), opprettet: naa, sist: naa, bekreftet: !!b.bekreftet, metode: b.bekreftet ? "" : null };
    // aldri gjenbrukte økter (f.eks. klienter uten cookies) forsvinner først, så de eldste
    const ids = Object.keys(okter).sort((x, y) => ((okter[y].sist > okter[y].opprettet) - (okter[x].sist > okter[x].opprettet)) || okter[x].sist - okter[y].sist);
    while (ids.length > 30) delete okter[ids.shift()];   // høyst 30 økter: de eldste forsvinner
    await lagre();
    return json({ sid });
  }
  if (sti === "/sjekk") {
    const o = okter[b.sid];
    if (!o) return json({ finnes: false });
    if (naa - o.sist > 300) { o.sist = naa; await lagre(); }
    return json({ finnes: true, bekreftet: !!o.bekreftet });
  }
  if (sti === "/bekreft") { if (okter[b.sid]) { okter[b.sid].bekreftet = true; okter[b.sid].metode = String(b.metode || ""); await lagre(); } return json({ ok: true }); }
  if (sti === "/liste") return json(Object.entries(okter).map(([sid, o]) => ({ sid, ...o })).sort((a, b) => b.sist - a.sist));
  if (sti === "/slett") { delete okter[b.sid]; await lagre(); return json({ ok: true }); }
  if (sti === "/slett-alle") { await st.delete("okter"); return json({ ok: true }); }
  return feil(404, "finnes ikke");
};

const SYNC_DELER = ["favoritter", "rutiner", "innstillinger", "eq", "wrapped", "historikk", "kassetter", "plugins"];
const SYNC_MAKS = 512 * 1024; // per del, base64 av kryptert innhold

Konto.prototype.sync = async function (sti, b) {
  const st = this.ctx.storage;
  if (sti === "/oversikt") {
    const ut = [];
    for (const del of SYNC_DELER) {
      const x = await st.get("sync:" + del);
      if (x) ut.push({ del, versjon: x.versjon, storrelse: x.blob.length, endret: x.endret, enhet: x.enhet });
    }
    return json({ deler: ut });
  }
  if (sti === "/slett") {
    for (const del of SYNC_DELER) await st.delete("sync:" + del);
    return json({ ok: true });
  }
  const del = String(b.del || "");
  if (sti === "/hent") {
    if (!del) return this.sync("/oversikt", {});
    if (!SYNC_DELER.includes(del)) return feil(400, "ukjent del");
    const x = await st.get("sync:" + del);
    return x ? json({ del, ...x }) : json({ del, versjon: 0, blob: null });
  }
  if (sti === "/lagre") {
    if (!SYNC_DELER.includes(del)) return feil(400, "ukjent del");
    const blob = String(b.blob || "");
    if (!blob || blob.length > SYNC_MAKS || !/^[A-Za-z0-9+/=_-]+$/.test(blob)) return feil(413, "ugyldig eller for stor blob");
    const naa = await st.get("sync:" + del);
    const versjon = naa ? naa.versjon : 0;
    if (Number(b.base ?? -1) !== versjon) {
      // noen andre har lagret i mellomtiden: klienten må hente, flette og prøve igjen
      return json({ konflikt: true, del, versjon, blob: naa ? naa.blob : null, endret: naa ? naa.endret : null }, 409);
    }
    const ny = { versjon: versjon + 1, blob, endret: Math.floor(Date.now() / 1000), enhet: String(b.enhet || "").slice(0, 64) };
    await st.put("sync:" + del, ny);
    return json({ del, versjon: ny.versjon, endret: ny.endret });
  }
  return feil(404, "finnes ikke");
};

// ---------- Koder: kode → sted ----------
export class Koder extends DurableObject {
  async fetch(req) {
    const sti = new URL(req.url).pathname;
    const b = await lesJson(req);
    const naa = Date.now();
    if (sti === "/i/sett") {
      const finnes = await this.ctx.storage.get("k:" + b.kode);
      if (finnes && finnes.utloper > naa) return feil(409, "kode i bruk");
      await this.ctx.storage.put("k:" + b.kode, { sted: b.sted, utloper: b.utloper });
      return json({ ok: true });
    }
    if (sti === "/i/los") {
      const v = await this.ctx.storage.get("k:" + b.kode);
      await this.ctx.storage.delete("k:" + b.kode); // engangs
      if (!v || v.utloper < naa) return feil(404, "ukjent kode");
      return json({ sted: v.sted });
    }
    if (sti === "/i/slett") {
      await this.ctx.storage.delete((b.koder || []).map((k) => "k:" + k));
      return json({ ok: true });
    }
    return feil(404, "finnes ikke");
  }
}

// ---------- Sted ----------
export class Sted extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.data = null; // { id, navn, eier, medlemmer, enheter, hoved, reserve }
    this.ventende = new Map(); // rid → { resolve, enhet, timer }
    this.strommer = new Map(); // rid → { writer, enhet }
    ctx.blockConcurrencyWhile(async () => {
      this.data = (await ctx.storage.get("sted")) || null;
    });
    try {
      ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair(PING, PONG)); // svarer uten å vekke objektet
    } catch {}
  }

  async lagre() {
    await this.ctx.storage.put("sted", this.data);
  }

  // --- tilkoblede enheter ---
  sokler(ekskluder) {
    return this.ctx.getWebSockets().filter((ws) => ws !== ekskluder && ws.readyState === 1 && ws.deserializeAttachment());
  }
  tilkoblet(ekskluder) {
    const m = new Map();
    for (const ws of this.sokler(ekskluder)) m.set(ws.deserializeAttachment().id, ws);
    return m;
  }
  velgAktiv(tilk) {
    const d = this.data;
    if (!d) return null;
    if (d.hoved && tilk.has(d.hoved)) return d.hoved;
    for (const id of d.reserve || []) if (tilk.has(id)) return id;
    for (const e of d.enheter) if (tilk.has(e.id)) return e.id;
    return null;
  }
  /** Regn ut aktiv hovedenhet; send «rolle» til alle ved endring (eller alltid til `ny`). */
  async valg(ekskluder, ny, tving = false) {
    const tilk = this.tilkoblet(ekskluder);
    const aktiv = this.velgAktiv(tilk);
    const forrige = (await this.ctx.storage.get("aktiv")) ?? null;
    const msg = JSON.stringify({ t: "rolle", aktiv, hoved: this.data?.hoved ?? null });
    if (aktiv !== forrige || tving) {
      if (aktiv !== forrige) await this.ctx.storage.put("aktiv", aktiv);
      for (const ws of tilk.values()) this.send(ws, msg);
    } else if (ny) this.send(ny, msg);
    return aktiv;
  }
  send(ws, msg) {
    try {
      ws.send(typeof msg === "string" ? msg : JSON.stringify(msg));
      return true;
    } catch {
      return false;
    }
  }
  lanKart(tilk) {
    // id → { ip, port, via } fra enhetenes «hei»-lister
    const m = new Map();
    for (const ws of tilk.values()) {
      const a = ws.deserializeAttachment();
      for (const l of a.lan || []) if (l && l.id && !m.has(l.id)) m.set(l.id, { ip: l.ip, port: l.port, navn: l.navn, produkt: l.produkt, via: a.id });
    }
    return m;
  }
  async sikreAlarm() {
    if ((await this.ctx.storage.getAlarm()) == null) await this.ctx.storage.setAlarm(Date.now() + ALARM_MS);
  }

  // --- HTTP ---
  async fetch(req) {
    const url = new URL(req.url);
    const sti = url.pathname;
    if (sti.startsWith("/i/")) return this.intern(req, sti.slice(2));
    if (!sti.startsWith("/u")) return feil(404, "finnes ikke");
    const d = this.data;
    const epost = req.headers.get("x-skjold-bruker");
    if (!d) return feil(404, "ukjent sted");
    if (!d.medlemmer.includes(epost)) return feil(403, "ingen tilgang til stedet");
    const deler = sti.slice(2).split("/").filter(Boolean);
    const m = req.method;

    if (deler.length === 0) {
      if (m === "GET") return json(this.oversikt(epost));
      if (m === "PATCH") return this.endre(await lesJson(req), epost);
      if (m === "DELETE") {
        if (d.eier !== epost) return feil(403, "bare eieren kan slette stedet");
        return this.slett();
      }
    }
    if (deler[0] === "medlemmer" && deler.length === 1 && m === "GET") return json(this.medlemsliste());
    if (deler[0] === "medlemmer" && deler.length === 1 && m === "POST") {
      if (d.eier !== epost) return feil(403, "bare eieren kan dele hjemmet");
      const ny = String((await lesJson(req)).epost || "").trim().toLowerCase();
      if (!/^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,}$/i.test(ny)) return feil(400, "ugyldig e-postadresse");
      if (d.medlemmer.length >= 20) return feil(400, "et hjem kan ha høyst 20 medlemmer");
      return this.medlemEndring({ leggTil: ny }, epost);
    }
    if (deler[0] === "medlemmer" && deler.length === 2 && m === "DELETE") {
      const hvem = decodeURIComponent(deler[1]).toLowerCase();
      if (hvem === d.eier) return feil(400, "eieren kan ikke fjernes – overfør eierskapet eller slett hjemmet");
      if (d.eier !== epost && hvem !== epost) return feil(403, "bare eieren kan fjerne andre");
      return this.medlemEndring({ fjern: hvem }, epost);
    }
    if (deler[0] === "eier" && deler.length === 1 && m === "POST") {
      if (d.eier !== epost) return feil(403, "bare eieren kan overføre eierskapet");
      return this.medlemEndring({ eier: String((await lesJson(req)).epost || "").trim().toLowerCase() }, epost);
    }
    if (deler[0] === "enheter" && deler.length === 1 && m === "GET") return json(this.enhetsliste());
    if (deler[0] === "kobling" && deler.length === 1 && m === "POST") return this.nyKode();
    if (deler[0] === "enheter" && deler.length === 2 && m === "DELETE") return this.fjernEnhet(decodeURIComponent(deler[1]));
    if (deler[0] === "enheter" && deler.length >= 3 && deler[2] === "api") {
      const id = decodeURIComponent(deler[1]);
      const p = "/" + deler.slice(2).join("/") + url.search;
      if (m === "GET" && deler.length === 4 && deler[3] === "events") return this.sse(id, p);
      return this.rele(req, id, p);
    }
    return feil(404, "finnes ikke");
  }

  async intern(req, sti) {
    if (sti === "/ws") return this.koblWs(req);
    const b = await lesJson(req);
    if (sti === "/opprett") {
      if (this.data) return feil(409, "finnes");
      this.data = { id: b.id, navn: b.navn, eier: b.eier, medlemmer: [b.eier], enheter: [], hoved: null, reserve: [], opprettet: Math.floor(Date.now() / 1000) };
      await this.lagre();
      return json(this.oversikt(b.eier));
    }
    if (sti === "/oversikt") {
      if (!this.data) return feil(404, "ukjent sted");
      if (!this.data.medlemmer.includes(b.bruker)) return feil(403, "ingen tilgang");
      return json(this.oversikt(b.bruker));
    }
    if (sti === "/admin") {
      if (!this.data) return feil(404, "ukjent sted");
      const d = this.data, tilk = this.tilkoblet();
      return json({ id: d.id, navn: d.navn, eier: d.eier, medlemmer: d.medlemmer, opprettet: d.opprettet || null,
        enheter: d.enheter.map((e) => ({ id: e.id, navn: e.navn, produkt: e.produkt, online: tilk.has(e.id), versjon: e.versjon || null, sist: e.sist || null })) });
    }
    if (sti === "/admin-slett") { if (!this.data) return feil(404, "ukjent sted"); return this.slett(); }
    if (sti === "/admin-endre") { if (!this.data) return feil(404, "ukjent sted"); return this.medlemEndring(b, null); }
    if (sti === "/kobl") return this.kobl(b);
    if (sti === "/eier") {
      const d = this.data;
      const id = req.headers.get("x-skjold-enhet");
      const e = d && d.enheter.find((x) => x.id === id);
      if (!e || !likTid(await sha256hex(req.headers.get("x-skjold-noekkel") || ""), e.noekkelHash)) return feil(401, "ugyldig enhetsnøkkel");
      return json({ eier: d.eier, sted: d.id });
    }
    return feil(404, "finnes ikke");
  }

  oversikt(epost) {
    const d = this.data;
    const tilk = this.tilkoblet();
    return {
      id: d.id,
      navn: d.navn,
      rolle: d.eier === epost ? "eier" : "medlem",
      enheter: d.enheter.length,
      online: d.enheter.filter((e) => tilk.has(e.id)).length,
      hoved: d.hoved,
      reserve: d.reserve,
      aktiv: this.velgAktiv(tilk),
      medlemmer: d.medlemmer,
      autoLegg: d.autoLegg !== false,
    };
  }

  medlemsliste() {
    const d = this.data;
    return { eier: d.eier, medlemmer: d.medlemmer.map((e) => ({ epost: e, rolle: e === d.eier ? "eier" : "medlem" })) };
  }

  /** leggTil / fjern / eier (overfør til et medlem; legges til hvis det ikke er medlem). epost = den som gjør det (null = Valhalla). */
  async medlemEndring(b, epost) {
    const d = this.data, lagtTil = [], fjernet = [];
    const add = (e) => { if (e && !d.medlemmer.includes(e)) { d.medlemmer.push(e); lagtTil.push(e); } };
    if (b.leggTil) add(String(b.leggTil).toLowerCase());
    if (b.fjern) {
      const f = String(b.fjern).toLowerCase();
      if (f === d.eier) return feil(400, "eieren kan ikke fjernes");
      if (d.medlemmer.includes(f)) { d.medlemmer = d.medlemmer.filter((x) => x !== f); fjernet.push(f); }
    }
    if (b.eier) {
      const ny = String(b.eier).toLowerCase();
      if (!/^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,}$/i.test(ny)) return feil(400, "ugyldig e-postadresse");
      add(ny);
      d.eier = ny;
    }
    await this.lagre();
    return json({ id: d.id, navn: d.navn, eier: d.eier, medlemmer: d.medlemmer, lagtTil, fjernet, liste: this.medlemsliste().medlemmer,
      rolle: epost ? (d.eier === epost ? "eier" : d.medlemmer.includes(epost) ? "medlem" : "ingen") : "valhalla" });
  }

  enhetsliste() {
    const d = this.data;
    const tilk = this.tilkoblet();
    const lan = this.lanKart(tilk);
    const aktiv = this.velgAktiv(tilk);
    const naa = Math.floor(Date.now() / 1000);
    return d.enheter.map((e) => {
      const ws = tilk.get(e.id);
      const a = ws ? ws.deserializeAttachment() : null;
      const l = lan.get(e.id);
      const ri = (d.reserve || []).indexOf(e.id);
      return {
        id: e.id,
        navn: (a && a.navn) || e.navn,
        produkt: (a && a.produkt) || e.produkt,
        rom: e.rom || "",
        online: !!ws,
        aktivHoved: aktiv === e.id,
        hoved: d.hoved === e.id,
        reserveNr: ri >= 0 ? ri + 1 : null,
        lan: l ? { ip: l.ip, port: l.port, via: l.via } : null,
        sist: ws ? naa : e.sist || null,
        versjon: (a && a.versjon) || e.versjon || null,
      };
    });
  }

  async endre(b, epost) {
    const d = this.data;
    const ids = new Set(d.enheter.map((e) => e.id));
    if (typeof b.navn === "string" && b.navn.trim()) d.navn = b.navn.trim().slice(0, 60);
    if ("hoved" in b) {
      if (b.hoved !== null && !ids.has(b.hoved)) return feil(400, "ukjent hovedenhet");
      d.hoved = b.hoved;
    }
    if ("reserve" in b) {
      if (!Array.isArray(b.reserve) || b.reserve.some((x) => !ids.has(x))) return feil(400, "ukjent enhet i reserve");
      d.reserve = [...new Set(b.reserve)];
    }
    if (typeof b.autoLegg === "boolean") d.autoLegg = b.autoLegg;
    d.reserve = d.reserve.filter((x) => x !== d.hoved);
    await this.lagre();
    await this.valg(null, null, true); // «hoved» kan ha endret seg uten at aktiv gjorde det – send til alle
    return json(this.oversikt(epost));
  }

  async slett() {
    const d = this.data;
    for (const ws of this.ctx.getWebSockets()) {
      try {
        ws.close(4002, "sted slettet");
      } catch {}
    }
    const koder = Object.keys((await this.ctx.storage.get("koder")) || {});
    if (koder.length) await intern(koderStub(this.env), "/slett", { koder });
    await this.ctx.storage.deleteAlarm();
    await this.ctx.storage.deleteAll();
    this.data = null;
    return json({ ok: true, id: d.id, medlemmer: d.medlemmer });
  }

  async nyKode() {
    const naa = Date.now();
    const koder = (await this.ctx.storage.get("koder")) || {};
    for (const [k, t] of Object.entries(koder)) if (t < naa) delete koder[k];
    const utloper = naa + KODE_TTL_MS;
    for (let forsok = 0; forsok < 5; forsok++) {
      const kode = tilfeldig(6, KODE_TEGN);
      const r = await intern(koderStub(this.env), "/sett", { kode, sted: this.data.id, utloper });
      if (!r.ok) continue;
      koder[kode] = utloper;
      await this.ctx.storage.put("koder", koder);
      return json({ kode, utloper: new Date(utloper).toISOString() }, 201);
    }
    return feil(503, "fant ingen ledig kode");
  }

  async kobl(b) {
    const d = this.data;
    const koder = (await this.ctx.storage.get("koder")) || {};
    const t = koder[b.kode];
    delete koder[b.kode];
    await this.ctx.storage.put("koder", koder);
    if (!d || !t || t < Date.now()) return feil(404, "ukjent eller utløpt kode");
    const noekkel = d.id + "." + hex(crypto.getRandomValues(new Uint8Array(32)));
    const noekkelHash = await sha256hex(noekkel);
    const navn = String(b.navn || b.id).slice(0, 60);
    const produkt = String(b.produkt || "").slice(0, 20);
    const e = d.enheter.find((x) => x.id === b.id);
    if (e) Object.assign(e, { navn, produkt, noekkelHash });
    else d.enheter.push({ id: b.id, navn, produkt, rom: "", noekkelHash, lagtTil: Math.floor(Date.now() / 1000) });
    if (!d.hoved) d.hoved = b.id; // første enhet blir hovedenhet
    if (d.utelatt) d.utelatt = d.utelatt.filter((x) => x !== b.id);
    await this.lagre();
    await this.glemInvitasjon(b.id);
    // ny nøkkel ⇒ gamle tilkoblinger for samme id kastes
    for (const ws of this.ctx.getWebSockets(b.id)) {
      try {
        ws.close(4003, "ny nøkkel");
      } catch {}
    }
    return json({ sted: d.id, stedNavn: d.navn, noekkel });
  }

  // --- automatisk innmelding: enheter den aktive hovedenheten ser på LAN-et, men som ikke er med i stedet ---
  // Skyen lager en vanlig koblingskode og ber hovedenheten levere den til enheten på LAN-et («inviter»). Enheten
  // melder seg så inn selv med /enhet/kobl og får egen nøkkel og egen forbindelse. Enheter brukeren har fjernet
  // («utelatt») inviteres ikke, og en enhet som ikke svarer får stadig lengre pause mellom forsøkene.
  async inviterNye(ws, a) {
    const d = this.data;
    if (!d || d.autoLegg === false || !Array.isArray(a.lan) || !a.lan.length) return;
    if (this.velgAktiv(this.tilkoblet()) !== a.id) return; // bare én enhet inviterer, ellers får hver nabo flere koder
    const kjent = new Set(d.enheter.map((e) => e.id));
    const utelatt = new Set(d.utelatt || []);
    const logg = (await this.ctx.storage.get("invitert")) || {};
    const naa = Date.now();
    let sendt = 0;
    let endret = false;
    for (const id of Object.keys(logg)) {
      if (kjent.has(id) || naa - logg[id].t > 2 * INVITER_MAKS_PAUSE_MS) {
        delete logg[id];
        endret = true;
      }
    }
    for (const p of a.lan) {
      const id = String(p?.id || "");
      if (!id || id.length > 64 || kjent.has(id) || utelatt.has(id)) continue;
      const f = logg[id];
      if (f && naa - f.t < Math.min(INVITER_MAKS_PAUSE_MS, INVITER_PAUSE_MS * 2 ** (f.n - 1))) continue;
      if (sendt >= INVITER_PER_RUNDE) break;
      const r = await this.nyKode();
      if (r.status !== 201) break;
      const { kode } = await r.json();
      logg[id] = { t: naa, n: Math.min(20, (f?.n || 0) + 1) };
      endret = true;
      sendt++;
      this.send(ws, { t: "inviter", til: id, kode });
    }
    if (endret) await this.ctx.storage.put("invitert", logg);
  }

  async inviterFraAktiv() {
    const d = this.data;
    if (!d || d.autoLegg === false) return;
    const aktiv = this.velgAktiv(this.tilkoblet());
    if (!aktiv) return;
    const ws = this.ctx.getWebSockets(aktiv)[0];
    const a = ws && ws.deserializeAttachment();
    if (a) await this.inviterNye(ws, a);
  }

  async glemInvitasjon(id) {
    const logg = await this.ctx.storage.get("invitert");
    if (logg && logg[id]) {
      delete logg[id];
      await this.ctx.storage.put("invitert", logg);
    }
  }

  async fjernEnhet(id) {
    const d = this.data;
    if (!d.enheter.some((e) => e.id === id)) return feil(404, "ukjent enhet");
    d.enheter = d.enheter.filter((e) => e.id !== id);
    d.utelatt = [...new Set([...(d.utelatt || []), id])].slice(-100); // fjernet av brukeren ⇒ meldes ikke inn automatisk igjen
    if (d.hoved === id) d.hoved = d.enheter[0]?.id ?? null;
    d.reserve = d.reserve.filter((x) => x !== id && x !== d.hoved);
    await this.lagre();
    let lukket = null;
    for (const ws of this.ctx.getWebSockets(id)) {
      lukket = ws;
      try {
        ws.close(4001, "fjernet fra stedet");
      } catch {}
    }
    this.avbrytFor(id);
    await this.valg(lukket, null);
    return json({ ok: true });
  }

  // --- WebSocket fra enheter ---
  async koblWs(req) {
    const d = this.data;
    const id = req.headers.get("x-skjold-enhet");
    const e = d && d.enheter.find((x) => x.id === id);
    if (!e || !likTid(await sha256hex(req.headers.get("x-skjold-noekkel") || ""), e.noekkelHash)) return feil(401, "ugyldig enhetsnøkkel");
    const gamle = this.ctx.getWebSockets(id);
    for (const ws of gamle) {
      try {
        ws.close(4004, "ny tilkobling");
      } catch {}
    }
    const par = new WebSocketPair();
    const [klient, server] = Object.values(par);
    this.ctx.acceptWebSocket(server, [id]);
    server.serializeAttachment({ id, sist: Date.now(), navn: e.navn, produkt: e.produkt, lan: [] });
    e.sist = Math.floor(Date.now() / 1000);
    await this.lagre();
    await this.sikreAlarm();
    await this.valg(gamle[0] || null, server);
    return new Response(null, { status: 101, webSocket: klient });
  }

  async webSocketMessage(ws, raw) {
    let m;
    try {
      m = JSON.parse(typeof raw === "string" ? raw : new TextDecoder().decode(raw));
    } catch {
      return;
    }
    const a = ws.deserializeAttachment();
    if (!a) return;
    a.sist = Date.now();
    if (m.t === "ping") {
      this.send(ws, PONG);
    } else if (m.t === "hei") {
      a.navn = String(m.navn || a.navn || "").slice(0, 60);
      a.produkt = String(m.produkt || a.produkt || "").slice(0, 20);
      a.versjon = String(m.versjon || "").slice(0, 20);
      a.lan = Array.isArray(m.lan) ? m.lan.slice(0, 50) : [];
      const e = this.data?.enheter.find((x) => x.id === a.id);
      if (e && (e.navn !== a.navn || e.produkt !== a.produkt || e.versjon !== a.versjon)) {
        Object.assign(e, { navn: a.navn || e.navn, produkt: a.produkt || e.produkt, versjon: a.versjon });
        await this.lagre();
      }
      ws.serializeAttachment(a);
      if (!this.iRegister && this.data) {   // Valhalla: hjemmet blir synlig så snart en enhet i det er på nett
        this.iRegister = true;
        const d = this.data;
        try { await intern(registerStub(this.env), "/steder", { steder: [{ id: d.id, navn: d.navn, eier: d.eier, medlemmer: d.medlemmer }] }); } catch {}
      }
      await this.inviterNye(ws, a);
    } else if (m.t === "res") {
      const v = this.ventende.get(m.rid);
      if (v) {
        this.ventende.delete(m.rid);
        clearTimeout(v.timer);
        v.resolve(m);
      } else if (this.strommer.has(m.rid)) this.lukkStrom(m.rid, false); // enheten avsluttet SSE
    } else if (m.t === "ev") {
      const s = this.strommer.get(m.rid);
      if (s) {
        this.skrivStrom(m.rid, "data: " + String(m.d ?? "") + "\n\n");
      } else this.send(ws, { t: "unsub", rid: m.rid });
    }
    ws.serializeAttachment(a);
  }

  async webSocketClose(ws, code, reason) {
    await this.frakoblet(ws);
    try {
      ws.close(code === 1005 || code === 1006 ? 1000 : code, reason);
    } catch {}
  }
  async webSocketError(ws) {
    await this.frakoblet(ws);
  }
  async frakoblet(ws) {
    const a = ws.deserializeAttachment();
    if (!a) return;
    ws.serializeAttachment(null);
    const e = this.data?.enheter.find((x) => x.id === a.id);
    if (e) {
      e.sist = Math.floor(Date.now() / 1000);
      await this.lagre();
    }
    if (!this.tilkoblet(ws).has(a.id)) this.avbrytFor(a.id);
    await this.valg(ws, null);
  }

  async alarm() {
    const naa = Date.now();
    let endret = false;
    for (const ws of this.ctx.getWebSockets()) {
      const a = ws.deserializeAttachment();
      if (!a) continue;
      let sist = a.sist || 0;
      try {
        const t = this.ctx.getWebSocketAutoResponseTimestamp(ws);
        if (t) sist = Math.max(sist, t.getTime());
      } catch {}
      if (naa - sist > STALE_MS) {
        try {
          ws.close(4000, "ingen ping");
        } catch {}
        await this.frakoblet(ws);
        endret = true;
      } else this.send(ws, PING);
    }
    // SSE: hold-i-live-kommentar; avdekker klienter som har gått
    for (const [rid, s] of this.strommer) {
      // ingen skriving har gått gjennom siden forrige alarm ⇒ klienten leser ikke lenger
      if (s.ventende > 0 && naa - s.sistLest > ALARM_MS) this.lukkStrom(rid, true);
      else this.skrivStrom(rid, ": ka\n\n");
    }
    if (!endret) await this.valg(null, null);
    await this.inviterFraAktiv();
    if (this.sokler().length || this.strommer.size) await this.ctx.storage.setAlarm(Date.now() + ALARM_MS);
  }

  // --- relé ---
  /** Hvilken WebSocket skal få forespørselen til `id`? Direkte, ellers via aktiv hovedenhet. */
  rute(id) {
    const tilk = this.tilkoblet();
    if (tilk.has(id)) return { ws: tilk.get(id), via: id };
    const kjent = this.data.enheter.some((e) => e.id === id) || this.lanKart(tilk).has(id);
    if (!kjent) return { feil: feil(404, "ukjent enhet") };
    const aktiv = this.velgAktiv(tilk);
    if (!aktiv) return { feil: feil(503, "ingen enheter på stedet er tilkoblet") };
    return { ws: tilk.get(aktiv), via: aktiv };
  }

  avbrytFor(enhet) {
    for (const [rid, v] of this.ventende)
      if (v.via === enhet) {
        this.ventende.delete(rid);
        clearTimeout(v.timer);
        v.resolve({ s: 502, h: { "content-type": "application/json" }, b: tilB64(new TextEncoder().encode('{"feil":"enheten koblet fra"}')) });
      }
    for (const [rid, s] of this.strommer) if (s.via === enhet) this.lukkStrom(rid, false);
  }

  async rele(req, id, p) {
    const r = this.rute(id);
    if (r.feil) return r.feil;
    const rid = crypto.randomUUID();
    const h = {};
    for (const k of ["content-type", "accept", "if-none-match", "range"]) {
      const v = req.headers.get(k);
      if (v) h[k] = v;
    }
    let b = null;
    if (req.method !== "GET" && req.method !== "HEAD") {
      const buf = await req.arrayBuffer();
      if (buf.byteLength > 512 * 1024) return feil(413, "for stor forespørsel");
      if (buf.byteLength) b = tilB64(buf);
    }
    const svar = new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.ventende.delete(rid);
        resolve(null);
      }, RELE_TIMEOUT_MS);
      this.ventende.set(rid, { resolve, timer, via: r.via });
    });
    if (!this.send(r.ws, { t: "req", rid, m: req.method, p, h, b, til: id })) {
      const v = this.ventende.get(rid);
      clearTimeout(v?.timer);
      this.ventende.delete(rid);
      return feil(502, "kunne ikke sende til enheten");
    }
    const m = await svar;
    if (!m) return feil(504, "enheten svarte ikke");
    const ut = new Headers();
    for (const [k, v] of Object.entries(m.h || {})) {
      if (!/^(content-length|transfer-encoding|connection|set-cookie|access-control-.*)$/i.test(k)) ut.set(k, String(v));
    }
    ut.set("x-skjold-via", r.via);
    if (!ut.has("cache-control")) ut.set("cache-control", "no-store");
    const s = Number(m.s) || 502;
    const kropp = m.b && s !== 204 && s !== 304 ? fraB64(m.b) : null;
    return new Response(kropp, { status: s, headers: ut });
  }

  async sse(id, p) {
    const r = this.rute(id);
    if (r.feil) return r.feil;
    const rid = crypto.randomUUID();
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    this.strommer.set(rid, { writer, via: r.via, ws: r.ws, ventende: 0, sistLest: Date.now() });
    writer.closed.catch(() => this.lukkStrom(rid, true)); // klienten gikk (lesesiden avbrutt)
    if (!this.send(r.ws, { t: "sub", rid, p, til: id })) {
      this.strommer.delete(rid);
      return feil(502, "kunne ikke sende til enheten");
    }
    this.skrivStrom(rid, "retry: 2000\n\n");
    await this.sikreAlarm();
    return new Response(readable, {
      headers: { "content-type": "text/event-stream", "cache-control": "no-cache", "x-accel-buffering": "no", "x-skjold-via": r.via },
    });
  }

  /** Skriv til SSE-strømmen. Skrivinger som henger (klienten leser ikke / har gått) teller; for mange ⇒ unsub. */
  skrivStrom(rid, tekst) {
    const s = this.strommer.get(rid);
    if (!s) return;
    if (s.ventende > 32) return this.lukkStrom(rid, true);
    s.ventende++;
    s.writer.write(new TextEncoder().encode(tekst)).then(
      () => {
        s.ventende--;
        s.sistLest = Date.now();
      },
      () => this.lukkStrom(rid, true),
    );
  }

  lukkStrom(rid, sendUnsub) {
    const s = this.strommer.get(rid);
    if (!s) return;
    this.strommer.delete(rid);
    if (sendUnsub) this.send(s.ws, { t: "unsub", rid });
    s.writer.abort("lukket").catch(() => {}); // close() ville ventet på ulest data
  }
}


// ---------- Hoyttalere: delte høyttalerprofiler («Skjold Sertifisert») ----------
// Lagrer bare målekurver (1/12-oktav, normalisert), score, gyldig område og en anonym kilde (hash fra enheten).
// Profilen som vises er medianen av innsendingene; EQ-filtrene regnes ut lokalt på Skjold.
// Sertifisert: ≥ 3 ulike kilder innen 2 dB RMS (100 Hz–10 kHz) av medianen, og snittscore ≥ 70 (samme regel som
// pi/skjold_speakerprofiles.py certify()). 3 flagg fra ulike kilder skjuler profilen til en moderator ser på den.
const H_MAKS_PER_DOGN = 20;
const H_MAKS_INNS = 50;
const H_FLAGG_SKJUL = 3;

export function slug(merke, modell) {
  return (String(merke) + " " + String(modell)).toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/æ/g, "ae").replace(/ø/g, "o").replace(/å/g, "a").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64);
}

function interpLog(fra, til) {
  // fra: [{f,db}] → db-verdier på frekvensene i til
  const lf = fra.map((c) => Math.log10(c.f));
  return til.map((t) => {
    const x = Math.log10(t);
    if (x <= lf[0]) return fra[0].db;
    if (x >= lf[lf.length - 1]) return fra[fra.length - 1].db;
    let i = 1;
    while (lf[i] < x) i++;
    const w = (x - lf[i - 1]) / (lf[i] - lf[i - 1]);
    return fra[i - 1].db * (1 - w) + fra[i].db * w;
  });
}

const median = (a) => {
  const s = [...a].sort((x, y) => x - y);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

function normaliser(fr, db) {
  const idx = fr.map((f, i) => (f >= 300 && f <= 3000 ? i : -1)).filter((i) => i >= 0);
  const snitt = idx.length ? idx.reduce((a, i) => a + db[i], 0) / idx.length : 0;
  return db.map((d) => d - snitt);
}

function rmsAvvik(fr, a, b) {
  const na = normaliser(fr, a), nb = normaliser(fr, b);
  let s = 0, n = 0;
  fr.forEach((f, i) => { if (f >= 100 && f <= 10000) { s += (na[i] - nb[i]) ** 2; n++; } });
  return n ? Math.sqrt(s / n) : 99;
}

export function sammenstill(p) {
  const inns = p.inns || [];
  if (!inns.length) return null;
  const fr = inns[0].kurve.map((c) => c.f);
  const kurver = inns.map((x) => normaliser(fr, x.kurve.map((c) => c.db)));
  const med = fr.map((_, i) => median(kurver.map((k) => k[i])));
  const enige = inns.filter((x, j) => rmsAvvik(fr, kurver[j], med) <= 2);
  const kilder = new Set(enige.map((x) => x.kilde));
  const score = enige.length ? Math.round(enige.reduce((a, x) => a + (x.score || 0), 0) / enige.length) : 0;
  const tall = (k) => { const v = inns.map((x) => x[k]).filter((v) => typeof v === "number"); return v.length ? median(v) : null; };
  return {
    id: p.id, merke: p.merke, modell: p.modell, antall: inns.length, enige: kilder.size, score,
    sertifisert: kilder.size >= 3 && score >= 70, skjult: !!p.skjult, flagg: (p.flagg || []).length,
    kurve: fr.map((f, i) => ({ f, db: Math.round(med[i] * 100) / 100 })),
    gyldig: [Math.round(median(inns.map((x) => x.gyldig[0]))), Math.round(median(inns.map((x) => x.gyldig[1])))],
    folsomhet: tall("folsomhet"), impedans: tall("impedans"), oppdatert: Math.max(...inns.map((x) => x.t)),
  };
}

function sjekkInnsending(b) {
  const merke = String(b.merke || "").trim().slice(0, 60), modell = String(b.modell || "").trim().slice(0, 80);
  if (!merke || !modell) return [null, "merke og modell må oppgis"];
  const k = Array.isArray(b.kurve) ? b.kurve : [];
  if (k.length < 30 || k.length > 400) return [null, "kurven må ha 30–400 punkter"];
  let forrige = 0;
  for (const c of k) {
    if (!c || typeof c.f !== "number" || typeof c.db !== "number" || !(c.f > forrige) || c.f > 24000 || Math.abs(c.db) > 60) return [null, "ugyldig kurve"];
    forrige = c.f;
  }
  const kilde = String(b.kilde || "").slice(0, 32);
  if (!/^[0-9a-f]{8,32}$/.test(kilde)) return [null, "kilde mangler"];
  const g = Array.isArray(b.gyldig) && b.gyldig.length === 2 ? b.gyldig.map(Number) : [100, 20000];
  const tall = (v, lo, hi) => (typeof v === "number" && v >= lo && v <= hi ? v : null);
  return [{ merke, modell, kurve: k.map((c) => ({ f: c.f, db: c.db })), kilde, score: Math.max(0, Math.min(100, Math.round(Number(b.score) || 0))),
    gyldig: [Math.max(20, g[0] || 20), Math.min(20000, g[1] || 20000)], folsomhet: tall(b.folsomhet, 70, 110), impedans: tall(b.impedans, 1, 32) }, null];
}

export class Hoyttalere extends DurableObject {
  async fetch(req) {
    const url = new URL(req.url);
    const sti = url.pathname.replace(/^\/hoyttaler/, "");
    const ip = req.headers.get("x-ip") || "";
    const mod = req.headers.get("x-mod") === "1";
    const st = this.ctx.storage;

    if (sti === "/sok" && req.method === "GET") {
      const q = (url.searchParams.get("q") || "").toLowerCase().trim();
      const alle = await st.list({ prefix: "p:" });
      const treff = [];
      for (const p of alle.values()) {
        if (p.skjult && !mod) continue;
        if (q && !(p.merke + " " + p.modell).toLowerCase().includes(q) && !p.id.includes(slug(q, ""))) continue;
        const s = sammenstill(p);
        if (s) treff.push({ id: s.id, merke: s.merke, modell: s.modell, antall: s.antall, sertifisert: s.sertifisert, score: s.score, skjult: s.skjult });
      }
      treff.sort((a, b) => (b.sertifisert - a.sertifisert) || (b.antall - a.antall) || a.modell.localeCompare(b.modell));
      return json({ treff: treff.slice(0, 50) }, 200, { "cache-control": "public, max-age=60" });
    }
    const m = /^\/profil\/([a-z0-9-]{1,64})$/.exec(sti);
    if (m && req.method === "GET") {
      const p = await st.get("p:" + m[1]);
      if (!p || (p.skjult && !mod)) return feil(404, "ukjent profil");
      return json(sammenstill(p));
    }
    if (sti === "/send" && req.method === "POST") {
      const [x, f] = sjekkInnsending(await lesJson(req));
      if (f) return feil(400, f);
      const dag = new Date().toISOString().slice(0, 10);
      const rk = "r:" + ip + ":" + dag;
      const n = (await st.get(rk)) || 0;
      if (n >= H_MAKS_PER_DOGN) return feil(429, "for mange innsendinger i dag");
      await st.put(rk, n + 1);
      const id = slug(x.merke, x.modell);
      const p = (await st.get("p:" + id)) || { id, merke: x.merke, modell: x.modell, inns: [], flagg: [] };
      const fr = p.inns.length ? p.inns[0].kurve.map((c) => c.f) : null;
      const kurve = fr ? interpLog(x.kurve, fr).map((db, i) => ({ f: fr[i], db })) : x.kurve;
      // én innsending per kilde og modell (ny måling erstatter den gamle)
      p.inns = p.inns.filter((y) => y.kilde !== x.kilde);
      p.inns.push({ kurve, kilde: x.kilde, score: x.score, gyldig: x.gyldig, folsomhet: x.folsomhet, impedans: x.impedans, t: Date.now() });
      p.inns = p.inns.slice(-H_MAKS_INNS);
      await st.put("p:" + id, p);
      const s = sammenstill(p);
      return json({ id, antall: s.antall, sertifisert: s.sertifisert, score: s.score }, 201);
    }
    if (sti === "/flagg" && req.method === "POST") {
      const b = await lesJson(req);
      const p = await st.get("p:" + String(b.id || ""));
      if (!p) return feil(404, "ukjent profil");
      p.flagg = (p.flagg || []).filter((y) => y.ip !== ip);
      p.flagg.push({ ip, grunn: String(b.grunn || "").slice(0, 200), t: Date.now() });
      if (p.flagg.length >= H_FLAGG_SKJUL) p.skjult = true;
      await st.put("p:" + p.id, p);
      return json({ ok: true, skjult: !!p.skjult });
    }
    if (sti === "/moder" && req.method === "POST") {
      if (!mod) return feil(403, "krever moderatornøkkel");
      const b = await lesJson(req);
      const p = await st.get("p:" + String(b.id || ""));
      if (!p) return feil(404, "ukjent profil");
      if (b.handling === "slett") { await st.delete("p:" + p.id); return json({ ok: true, slettet: true }); }
      if (b.handling === "vis") { p.skjult = false; p.flagg = []; }
      else if (b.handling === "skjul") p.skjult = true;
      else if (b.handling === "fjern_kilde") p.inns = p.inns.filter((y) => y.kilde !== b.kilde);
      else return feil(400, "ukjent handling");
      await st.put("p:" + p.id, p);
      return json({ ok: true, profil: sammenstill(p) });
    }
    return feil(404, "finnes ikke");
  }
}


// ---------- Del en kassett ----------
// Skyen lagrer bare en kryptert blob (AES-GCM, nøkkelen genereres på Skjold-enheten og står bare i delingskoden
// «S<id>.<nøkkel>» som sendes til vennen). Ingen konto, ingen innsyn. Blobben slettes etter 14 dager.
const D_TTL_MS = 14 * 24 * 3600 * 1000;
const D_MAKS_BYTES = 48 * 1024;
const D_MAKS_PER_DOGN = 50;
const D_ALFABET = "abcdefghijkmnpqrstuvwxyz23456789";

function nyDelId() {
  const b = crypto.getRandomValues(new Uint8Array(10));
  return Array.from(b, (x) => D_ALFABET[x % D_ALFABET.length]).join("");
}

export class Delinger extends DurableObject {
  async fetch(req) {
    const url = new URL(req.url);
    const st = this.ctx.storage;
    const ip = req.headers.get("x-ip") || "";
    const naa = Date.now();
    if (url.pathname === "/del" && req.method === "POST") {
      const b = await lesJson(req);
      const blob = typeof b.blob === "string" ? b.blob : "";
      if (!blob || blob.length > D_MAKS_BYTES || !/^[A-Za-z0-9+/=]+$/.test(blob)) return feil(400, "ugyldig deling");
      const dag = new Date(naa).toISOString().slice(0, 10);
      const rk = "r:" + ip + ":" + dag;
      const n = (await st.get(rk)) || 0;
      if (n >= D_MAKS_PER_DOGN) return feil(429, "for mange delinger i dag");
      await st.put(rk, n + 1);
      let id = nyDelId();
      while (await st.get("d:" + id)) id = nyDelId();
      const utloper = naa + D_TTL_MS;
      await st.put("d:" + id, { blob, utloper });
      // rydd utløpte (billig: maks 50 per innsending)
      const gamle = await st.list({ prefix: "d:", limit: 50 });
      for (const [k, v] of gamle) if (v && v.utloper < naa) await st.delete(k);
      return json({ id, utloper }, 201);
    }
    const m = /^\/del\/([a-z0-9]{8,16})$/.exec(url.pathname);
    if (m && req.method === "GET") {
      const d = await st.get("d:" + m[1]);
      if (!d || d.utloper < naa) {
        if (d) await st.delete("d:" + m[1]);
        return feil(404, "delingen finnes ikke eller er utløpt");
      }
      return json({ blob: d.blob, utloper: d.utloper }, 200, { "cache-control": "no-store" });
    }
    return feil(404, "finnes ikke");
  }
}

// ---------- Register: oversikt over kontoer og hjem for Skjold Lab Valhalla (tjenesteadministrasjon) ----------
// Én instans («register»). Kontoer: første og siste innlogging, sperret, Valhalla-admin. Hjem: navn, eier, medlemmer.
export class Register extends DurableObject {
  async fetch(req) {
    const sti = new URL(req.url).pathname.slice(2);
    const b = await lesJson(req);
    const st = this.ctx.storage, naa = Math.floor(Date.now() / 1000);
    if (sti === "/bruker") {
      const e = String(b.epost || "").toLowerCase();
      const k = (await st.get("k:" + e)) || { forst: naa, sist: 0, sperret: false, admin: false };
      if (naa - (k.sist || 0) > 300) { k.sist = naa; await st.put("k:" + e, k); }   // «sist sett», høyst hvert 5. minutt
      return json(k);
    }
    if (sti === "/hemmelighet") {
      let h = await st.get("hemmelighet");
      if (!h) { h = [...crypto.getRandomValues(new Uint8Array(32))].map((x) => x.toString(16).padStart(2, "0")).join(""); await st.put("hemmelighet", h); }
      return json({ h });
    }
    if (sti === "/vedlikehold") return json((await st.get("vedlikehold")) || { aktiv: false });
    if (sti === "/vedlikehold-sett") {
      const v = { aktiv: !!b.aktiv, melding: String(b.melding || "").slice(0, 300), til: Number(b.til) || 0, fra: naa, av: String(b.av || "") };
      await st.put("vedlikehold", v);
      return json(v);
    }
    if (sti === "/bruker-slett") { await st.delete("k:" + String(b.epost || "").toLowerCase()); return json({ ok: true }); }
    if (sti === "/bruker-sett") {
      const e = String(b.epost || "").toLowerCase();
      const k = (await st.get("k:" + e)) || { forst: naa, sist: 0, sperret: false, admin: false };
      if ("sperret" in b) k.sperret = !!b.sperret;
      if ("admin" in b) k.admin = !!b.admin;
      if ("tofa" in b) k.tofa = !!b.tofa;
      if ("bilde" in b) k.bilde = String(b.bilde || "");
      await st.put("k:" + e, k);
      return json({ epost: e, ...k });
    }
    if (sti === "/steder") {
      for (const x of b.steder || []) {
        if (!x || !x.id) continue;
        const gml = (await st.get("s:" + x.id)) || { opprettet: naa };
        await st.put("s:" + x.id, { ...gml, navn: x.navn ?? gml.navn, eier: x.eier ?? gml.eier, medlemmer: x.medlemmer ?? gml.medlemmer ?? [x.eier] });
        for (const m of x.medlemmer || [x.eier]) if (m && !(await st.get("k:" + m))) await st.put("k:" + m, { forst: naa, sist: 0, sperret: false, admin: false });
      }
      return json({ ok: true });
    }
    if (sti === "/sted-slett") { await st.delete("s:" + b.id); return json({ ok: true }); }
    const kontoer = async () => [...(await st.list({ prefix: "k:" })).entries()].map(([k, v]) => ({ epost: k.slice(2), ...v }));
    const steder = async () => [...(await st.list({ prefix: "s:" })).entries()].map(([k, v]) => ({ id: k.slice(2), ...v }));
    if (sti === "/steder-liste") return json({ steder: await steder() });
    if (sti === "/kontoer") {
      const s = await steder();
      return json((await kontoer()).map((k) => ({ ...k, eierAv: s.filter((x) => x.eier === k.epost).map((x) => ({ id: x.id, navn: x.navn })),
        medlemAv: s.filter((x) => x.eier !== k.epost && (x.medlemmer || []).includes(k.epost)).map((x) => ({ id: x.id, navn: x.navn })) }))
        .sort((a, b) => (b.sist || 0) - (a.sist || 0)));
    }
    if (sti === "/oversikt") {
      const k = await kontoer(), s = await steder(), uke = naa - 7 * 86400;
      return json({ kontoer: k.length, aktive7d: k.filter((x) => (x.sist || 0) > uke).length, nye7d: k.filter((x) => (x.forst || 0) > uke).length,
        sperrede: k.filter((x) => x.sperret).length, admins: k.filter((x) => x.admin).map((x) => x.epost), steder: s.length,
        delte: s.filter((x) => (x.medlemmer || []).length > 1).length, nyeSteder7d: s.filter((x) => (x.opprettet || 0) > uke).length });
    }
    return feil(404, "finnes ikke");
  }
}
