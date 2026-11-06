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

    // --- brukere (bak Access) ---
    if (p === "/api/hjem" || p.startsWith("/api/hjem/")) {
      const epost = await bruker(req, env);
      if (!epost) return feil(401, "ikke innlogget");
      return api(req, env, epost, url);
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
      return json(ut.filter(Boolean));
    }
    if (req.method === "POST") {
      const b = await lesJson(req);
      const navn = String(b.navn || "").trim().slice(0, 60) || "Hjem";
      const id = nyId("st_");
      const r = await intern(stedStub(env, id), "/opprett", { id, navn, eier: epost });
      if (!r.ok) return r;
      await intern(konto, "/legg", { id, navn });
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
  }
  return r;
}

// ---------- Konto: brukerens steder ----------
export class Konto extends DurableObject {
  async fetch(req) {
    const sti = new URL(req.url).pathname;
    const b = await lesJson(req);
    if (sti.startsWith("/i/sync/")) return this.sync(sti.slice(7), b);
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
      this.data = { id: b.id, navn: b.navn, eier: b.eier, medlemmer: [b.eier], enheter: [], hoved: null, reserve: [] };
      await this.lagre();
      return json(this.oversikt(b.eier));
    }
    if (sti === "/oversikt") {
      if (!this.data) return feil(404, "ukjent sted");
      if (!this.data.medlemmer.includes(b.bruker)) return feil(403, "ingen tilgang");
      return json(this.oversikt(b.bruker));
    }
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
    };
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
    await this.lagre();
    // ny nøkkel ⇒ gamle tilkoblinger for samme id kastes
    for (const ws of this.ctx.getWebSockets(b.id)) {
      try {
        ws.close(4003, "ny nøkkel");
      } catch {}
    }
    return json({ sted: d.id, stedNavn: d.navn, noekkel });
  }

  async fjernEnhet(id) {
    const d = this.data;
    if (!d.enheter.some((e) => e.id === id)) return feil(404, "ukjent enhet");
    d.enheter = d.enheter.filter((e) => e.id !== id);
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
