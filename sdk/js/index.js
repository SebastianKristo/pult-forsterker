// Skjold – JS-klient (ESM, fetch) for det lokale API-et. Node 18+ og nettlesere.
//   import { Skjold } from "skjold";
//   const s = new Skjold("skjold.local"); await s.volume(30);
//   for await (const st of s.events()) console.log(st.volume);
export class SkjoldFeil extends Error {
  constructor(status, message) { super(`${status}: ${message}`); this.status = status; }
}

export class Skjold {
  constructor(vert = "skjold.local", { port = 8765, base, fetch: f } = {}) {
    this.base = (base || `http://${vert}:${port}`).replace(/\/$/, "");
    this.fetch = f || globalThis.fetch.bind(globalThis);
  }

  async request(metode, sti, body) {
    const r = await this.fetch(this.base + sti, {
      method: metode,
      headers: body !== undefined ? { "content-type": "application/json" } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const tekst = await r.text();
    let data = {};
    try { data = tekst ? JSON.parse(tekst) : {}; } catch { if (r.ok) throw new SkjoldFeil(r.status, "ugyldig JSON"); }
    if (!r.ok) throw new SkjoldFeil(r.status, data.error || r.statusText);
    return data;
  }
  get(sti) { return this.request("GET", sti); }
  post(sti, body = {}) { return this.request("POST", sti, body); }

  status() { return this.get("/api/status"); }
  power(on = true) { return this.post("/api/power", { on: !!on }); }
  toggle() { return this.post("/api/toggle"); }
  volume(volume, { delta } = {}) { return this.post("/api/volume", delta !== undefined ? { delta } : { volume }); }
  mute(mute = true) { return this.post("/api/mute", { mute: !!mute }); }
  input(input) { return this.post("/api/input", { input }); }
  preset(n) { return this.post("/api/preset", { n }); }
  play(url, ekstra = {}) { return this.post("/api/play", { url, ...ekstra }); }
  transport(action) { return this.post("/api/transport", { action }); }

  /** Asynkron iterator over status-oppdateringer (Server-Sent Events). */
  async *events({ signal } = {}) {
    const r = await this.fetch(this.base + "/api/events", { headers: { accept: "text/event-stream" }, signal });
    const dec = new TextDecoder();
    let buf = "";
    for await (const chunk of r.body) {
      buf += dec.decode(chunk, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const blokk = buf.slice(0, i); buf = buf.slice(i + 2);
        const data = blokk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
        if (data) { try { yield JSON.parse(data); } catch { /* ikke JSON */ } }
      }
    }
  }
}
export default Skjold;
