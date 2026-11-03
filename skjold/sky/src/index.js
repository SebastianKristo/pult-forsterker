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
  if (deler[0] !== "steder") return feil(404, "finnes ikke");
  const konto = kontoStub(env, epost);

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
