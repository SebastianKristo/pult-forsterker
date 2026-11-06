// Testhjelp: kjører Workeren i Miniflare (workerd) med de samme Durable Object-bindingene som wrangler.toml.
import { Miniflare } from "miniflare";
import { fileURLToPath } from "node:url";

export const SKRIPT = fileURLToPath(new URL("../src/index.js", import.meta.url));

export function lagMiniflare(ekstra = {}) {
  const { bindings, outboundService, ...rest } = ekstra;
  return new Miniflare({
    ...rest,
    modules: true,
    scriptPath: SKRIPT,
    compatibilityDate: "2025-09-01",
    durableObjects: {
      STED: { className: "Sted", useSQLite: true },
      KONTO: { className: "Konto", useSQLite: true },
      KODER: { className: "Koder", useSQLite: true },
      HOYTTALERE: { className: "Hoyttalere", useSQLite: true },
    },
    bindings: { DEV_INSECURE: "1", ...(bindings || {}) },
    ...(outboundService ? { outboundService } : {}),
  });
}

export const B = "http://sky.test";

export async function api(mf, metode, sti, bruker = "eier@test.no", kropp) {
  const h = { "x-skjold-user": bruker };
  if (kropp !== undefined) h["content-type"] = "application/json";
  const r = await mf.dispatchFetch(B + sti, { method: metode, headers: h, body: kropp === undefined ? undefined : JSON.stringify(kropp) });
  const tekst = await r.text();
  let data = null;
  try {
    data = JSON.parse(tekst);
  } catch {
    data = tekst;
  }
  return { status: r.status, data, headers: r.headers };
}

const vent = (ms) => new Promise((r) => setTimeout(r, ms));
export { vent };

/** En falsk Skjold-enhet som snakker enhetsprotokollen over WebSocket. */
export class FalskEnhet {
  constructor(mf, id, { lan = [], svar } = {}) {
    this.mf = mf;
    this.id = id;
    this.lan = lan;
    this.meldinger = [];
    this.rolle = null;
    this.ventere = [];
    this.subs = new Map();
    // svar(req) → {s, h, body}; standard: /api/status svarer med id
    this.svar =
      svar ||
      ((m) => ({ s: 200, h: { "content-type": "application/json" }, body: JSON.stringify({ id: m.til, via: this.id, m: m.m, p: m.p, b: m.b }) }));
  }
  async kobl(sted, eier = "eier@test.no") {
    const k = await api(this.mf, "POST", `/api/hjem/steder/${sted}/kobling`, eier);
    const r = await this.mf.dispatchFetch(B + "/enhet/kobl", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ kode: k.data.kode, id: this.id, navn: "Enhet " + this.id, produkt: "core" }),
    });
    this.koblingssvar = await r.json();
    this.noekkel = this.koblingssvar.noekkel;
    return this.koblingssvar;
  }
  async koblTil() {
    const r = await this.mf.dispatchFetch(B + "/enhet/ws", {
      headers: { upgrade: "websocket", authorization: `Bearer ${this.id}.${this.noekkel}` },
    });
    if (!r.webSocket) throw new Error("WS avvist: " + r.status);
    this.ws = r.webSocket;
    this.ws.accept();
    this.ws.addEventListener("message", (e) => this.motta(JSON.parse(e.data)));
    this.ws.send(JSON.stringify({ t: "hei", id: this.id, navn: "Enhet " + this.id, produkt: "core", versjon: "2.0", lan: this.lan }));
    return this;
  }
  motta(m) {
    this.meldinger.push(m);
    if (m.t === "rolle") this.rolle = m;
    if (m.t === "ping") this.ws.send('{"t":"pong"}');
    if (m.t === "req") {
      const s = this.svar(m);
      this.ws.send(JSON.stringify({ t: "res", rid: m.rid, s: s.s, h: s.h, b: Buffer.from(s.body).toString("base64") }));
    }
    if (m.t === "sub") {
      let n = 0;
      const tid = setInterval(() => {
        try {
          this.ws.send(JSON.stringify({ t: "ev", rid: m.rid, d: JSON.stringify({ n: n++, til: m.til, via: this.id }) }));
        } catch {
          clearInterval(tid);
        }
      }, 20);
      this.subs.set(m.rid, tid);
    }
    if (m.t === "unsub") {
      clearInterval(this.subs.get(m.rid));
      this.subs.delete(m.rid);
    }
    for (const v of [...this.ventere]) if (v.pred(m)) {
      this.ventere.splice(this.ventere.indexOf(v), 1);
      v.resolve(m);
    }
  }
  vent(pred, ms = 3000) {
    const funnet = this.meldinger.find(pred);
    if (funnet) return Promise.resolve(funnet);
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error(`${this.id}: tidsavbrudd`)), ms);
      this.ventere.push({ pred, resolve: (m) => (clearTimeout(t), resolve(m)) });
    });
  }
  /** Vent på at siste rolle-melding peker på `aktiv`. */
  async ventRolle(aktiv, ms = 3000) {
    const slutt = Date.now() + ms;
    while (Date.now() < slutt) {
      if (this.rolle && this.rolle.aktiv === aktiv) return this.rolle;
      await vent(10);
    }
    throw new Error(`${this.id}: ventet rolle aktiv=${aktiv}, fikk ${JSON.stringify(this.rolle)}`);
  }
  lukk() {
    for (const t of this.subs.values()) clearInterval(t);
    this.ws.close(1000, "ha det");
  }
}
