import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, createSign } from "node:crypto";
import { lagMiniflare, api, FalskEnhet, B, vent } from "./hjelp.mjs";

let mf;
before(() => {
  mf = lagMiniflare();
});
after(async () => {
  await mf.dispose();
});

async function nyttSted(navn = "Hytta", bruker = "eier@test.no") {
  const r = await api(mf, "POST", "/api/hjem/steder", bruker, { navn });
  assert.equal(r.status, 201);
  return r.data.id;
}

test("innlogging kreves (uten bruker → 401)", async () => {
  const r = await mf.dispatchFetch(B + "/api/hjem/steder");
  assert.equal(r.status, 401);
  await r.arrayBuffer();
});

test("lag sted, list steder, endre navn, andre brukere får 403", async () => {
  const id = await nyttSted("Hytta");
  assert.match(id, /^st_[a-z2-7]+$/);
  const l = await api(mf, "GET", "/api/hjem/steder");
  const s = l.data.find((x) => x.id === id);
  assert.deepEqual([s.navn, s.rolle, s.enheter, s.online], ["Hytta", "eier", 0, 0]);
  const p = await api(mf, "PATCH", `/api/hjem/steder/${id}`, "eier@test.no", { navn: "Hytta 2" });
  assert.equal(p.status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/steder")).data.find((x) => x.id === id).navn, "Hytta 2");
  assert.equal((await api(mf, "GET", `/api/hjem/steder/${id}/enheter`, "fremmed@test.no")).status, 403);
  assert.equal((await api(mf, "DELETE", `/api/hjem/steder/${id}`, "fremmed@test.no")).status, 403);
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "fremmed@test.no")).data.length, 0);
});

test("koblingskode: format, engangs, enhetsnøkkel lagres bare som hash", async () => {
  const sted = await nyttSted();
  const k = await api(mf, "POST", `/api/hjem/steder/${sted}/kobling`);
  assert.equal(k.status, 201);
  assert.match(k.data.kode, /^[A-HJ-NP-Z2-9]{6}$/);
  assert.ok(Date.parse(k.data.utloper) > Date.now() + 9 * 60 * 1000);
  const kobl = (kode) =>
    mf.dispatchFetch(B + "/enhet/kobl", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ kode, id: "pi-a", navn: "Stue", produkt: "core" }),
    });
  const r1 = await kobl(k.data.kode.toLowerCase());
  assert.equal(r1.status, 200);
  const d = await r1.json();
  assert.equal(d.sted, sted);
  assert.match(d.noekkel, new RegExp(`^${sted}\\.[0-9a-f]{64}$`));
  const r2 = await kobl(k.data.kode);
  assert.equal(r2.status, 404, "koden kan bare brukes én gang");
  await r2.arrayBuffer();
  const e = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter`);
  assert.equal(e.data.length, 1);
  assert.equal(e.data[0].id, "pi-a");
  assert.equal(e.data[0].hoved, true);
  assert.equal(JSON.stringify(e.data).includes(d.noekkel.split(".")[1]), false);
  assert.equal("noekkelHash" in e.data[0], false);
  // feil nøkkel avvises
  const ws = await mf.dispatchFetch(B + "/enhet/ws", {
    headers: { upgrade: "websocket", authorization: `Bearer pi-a.${sted}.${"0".repeat(64)}` },
  });
  assert.equal(ws.status, 401);
  await ws.arrayBuffer();
});

test("WS-tilkobling + relé GET /api/status og POST med kropp", async () => {
  const sted = await nyttSted();
  const a = new FalskEnhet(mf, "pi-relay");
  await a.kobl(sted);
  await a.koblTil();
  await a.ventRolle("pi-relay");
  const r = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter/pi-relay/api/status`);
  assert.equal(r.status, 200);
  assert.deepEqual([r.data.id, r.data.via, r.data.m, r.data.p], ["pi-relay", "pi-relay", "GET", "/api/status"]);
  assert.equal(r.headers.get("x-skjold-via"), "pi-relay");
  const p = await api(mf, "POST", `/api/hjem/steder/${sted}/enheter/pi-relay/api/volume?x=1`, "eier@test.no", { volume: 30 });
  assert.equal(p.data.p, "/api/volume?x=1");
  assert.deepEqual(JSON.parse(Buffer.from(p.data.b, "base64").toString()), { volume: 30 });
  const l = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter`);
  assert.equal(l.data[0].online, true);
  assert.equal(l.data[0].aktivHoved, true);
  const st = (await api(mf, "GET", "/api/hjem/steder")).data.find((x) => x.id === sted);
  assert.equal(st.online, 1);
  a.lukk();
});

test("ping besvares med pong", async () => {
  const sted = await nyttSted();
  const a = new FalskEnhet(mf, "pi-ping");
  await a.kobl(sted);
  await a.koblTil();
  a.ws.send('{"t":"ping"}');
  await a.vent((m) => m.t === "pong");
  a.lukk();
});

test("aktiv hovedenhet: hoved/reserve, failover og tilbakefall", async () => {
  const sted = await nyttSted();
  const h = new FalskEnhet(mf, "hoved");
  const r1 = new FalskEnhet(mf, "res1");
  const r2 = new FalskEnhet(mf, "res2");
  for (const e of [h, r1, r2]) await e.kobl(sted);
  const p = await api(mf, "PATCH", `/api/hjem/steder/${sted}`, "eier@test.no", { hoved: "hoved", reserve: ["res2", "res1"] });
  assert.equal(p.status, 200);
  await r1.koblTil();
  await r1.ventRolle("res1"); // bare res1 tilkoblet
  await r2.koblTil();
  await r1.ventRolle("res2"); // res2 er reserve 1
  await r2.ventRolle("res2");
  await h.koblTil();
  for (const e of [h, r1, r2]) await e.ventRolle("hoved");
  assert.equal(h.rolle.hoved, "hoved");
  let l = (await api(mf, "GET", `/api/hjem/steder/${sted}/enheter`)).data;
  const finn = (id) => l.find((x) => x.id === id);
  assert.deepEqual([finn("hoved").aktivHoved, finn("hoved").hoved, finn("res2").reserveNr, finn("res1").reserveNr], [true, true, 1, 2]);

  // hovedenheten faller ut → reserve 1 tar over
  h.lukk();
  await r1.ventRolle("res2");
  await r2.ventRolle("res2");
  l = (await api(mf, "GET", `/api/hjem/steder/${sted}/enheter`)).data;
  assert.equal(finn("hoved").online, false);
  assert.equal(finn("res2").aktivHoved, true);

  // hovedenheten kommer tilbake → tilbakefall
  const h2 = new FalskEnhet(mf, "hoved");
  h2.noekkel = h.noekkel;
  await h2.koblTil();
  await h2.ventRolle("hoved");
  await r1.ventRolle("hoved");
  await r2.ventRolle("hoved");
  h2.lukk();
  r1.lukk();
  r2.lukk();
});

test("relé via aktiv hovedenhet til LAN-enhet som ikke er tilkoblet (til)", async () => {
  const sted = await nyttSted();
  const hub = new FalskEnhet(mf, "hub", { lan: [{ id: "lan-node", navn: "Kjøkken", ip: "192.168.1.50", port: 8765, produkt: "node" }] });
  const borte = new FalskEnhet(mf, "registrert-borte");
  await hub.kobl(sted);
  await borte.kobl(sted); // registrert, men aldri tilkoblet
  await hub.koblTil();
  await hub.ventRolle("hub");
  await hub.vent((m) => m.t === "rolle");
  await vent(50); // la «hei» nå frem
  const r = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter/lan-node/api/status`);
  assert.equal(r.status, 200);
  assert.deepEqual([r.data.id, r.data.via], ["lan-node", "hub"]);
  const req = hub.meldinger.find((m) => m.t === "req" && m.til === "lan-node");
  assert.ok(req);
  const r2 = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter/registrert-borte/api/status`);
  assert.deepEqual([r2.data.id, r2.data.via], ["registrert-borte", "hub"]);
  const ukjent = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter/finnes-ikke/api/status`);
  assert.equal(ukjent.status, 404);
  hub.lukk();
});

test("relé uten tilkoblede enheter → 503; enhet som ikke svarer → 504 (25 s)", { timeout: 40000 }, async () => {
  const sted = await nyttSted();
  const a = new FalskEnhet(mf, "treg", { svar: () => null });
  await a.kobl(sted);
  assert.equal((await api(mf, "GET", `/api/hjem/steder/${sted}/enheter/treg/api/status`)).status, 503);
  a.motta = (m) => a.meldinger.push(m); // svarer aldri
  await a.koblTil();
  const t0 = Date.now();
  const r = await api(mf, "GET", `/api/hjem/steder/${sted}/enheter/treg/api/status`);
  assert.equal(r.status, 504);
  assert.ok(Date.now() - t0 >= 24000);
  a.lukk();
});

test("SSE-relé (sub/ev/unsub) via TransformStream", async () => {
  const sted = await nyttSted();
  const hub = new FalskEnhet(mf, "sse-hub", { lan: [{ id: "sse-lan", navn: "x", ip: "10.0.0.2", port: 8765, produkt: "node" }] });
  await hub.kobl(sted);
  await hub.koblTil();
  await hub.ventRolle("sse-hub");
  await vent(50);
  for (const mål of ["sse-hub", "sse-lan"]) {
    const r = await mf.dispatchFetch(B + `/api/hjem/steder/${sted}/enheter/${mål}/api/events`, { headers: { "x-skjold-user": "eier@test.no" } });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("content-type"), "text/event-stream");
    const leser = r.body.getReader();
    let tekst = "";
    while ((tekst.match(/^data: /gm) || []).length < 3) tekst += new TextDecoder().decode((await leser.read()).value);
    const data = tekst.split("\n").filter((l) => l.startsWith("data: ")).map((l) => JSON.parse(l.slice(6)));
    assert.deepEqual([data[0].n, data[1].n, data[0].til, data[0].via], [0, 1, mål, "sse-hub"]);
    const sub = hub.meldinger.find((m) => m.t === "sub" && m.til === mål);
    assert.equal(sub.p, "/api/events");
    await leser.cancel();
    await hub.vent((m) => m.t === "unsub" && m.rid === sub.rid, 10000);
  }
  hub.lukk();
});

test("fjern enhet lukker WebSocket; slett sted fjerner det fra kontoen", async () => {
  const sted = await nyttSted("Slettes");
  const a = new FalskEnhet(mf, "pi-fjern");
  await a.kobl(sted);
  await a.koblTil();
  await a.ventRolle("pi-fjern");
  const lukket = new Promise((r) => a.ws.addEventListener("close", (e) => r(e.code)));
  assert.equal((await api(mf, "DELETE", `/api/hjem/steder/${sted}/enheter/pi-fjern`)).status, 200);
  assert.equal(await lukket, 4001);
  assert.equal((await api(mf, "GET", `/api/hjem/steder/${sted}/enheter`)).data.length, 0);
  assert.equal((await api(mf, "DELETE", `/api/hjem/steder/${sted}`)).status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/steder")).data.some((x) => x.id === sted), false);
  assert.equal((await api(mf, "GET", `/api/hjem/steder/${sted}/enheter`)).status, 404);
});

test("web-UI: landingsside uten ASSETS; ukjent sti 404", async () => {
  const r = await mf.dispatchFetch(B + "/");
  assert.equal(r.status, 200);
  assert.match(await r.text(), /Skjold-hjem/);
  const n = await mf.dispatchFetch(B + "/finnes/ikke");
  assert.equal(n.status, 404);
  await n.arrayBuffer();
});

test("Cloudflare Access: JWT verifiseres mot teamets nøkler; X-Skjold-User ignoreres", async () => {
  const { publicKey, privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwk = { ...publicKey.export({ format: "jwk" }), kid: "k1", alg: "RS256", use: "sig" };
  const team = "https://lag.cloudflareaccess.com";
  const aud = "aud-123";
  const m2 = lagMiniflare({
    bindings: { DEV_INSECURE: "1", ACCESS_TEAM_DOMAIN: "lag", ACCESS_AUD: aud },
    outboundService: async (req) => {
      if (req.url === team + "/cdn-cgi/access/certs") return new Response(JSON.stringify({ keys: [jwk] }), { headers: { "content-type": "application/json" } });
      return new Response("nei", { status: 404 });
    },
  });
  const b64u = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
  const jwt = (payload, kid = "k1") => {
    const hode = b64u({ alg: "RS256", kid, typ: "JWT" }) + "." + b64u(payload);
    const sig = createSign("RSA-SHA256").update(hode).sign(privateKey).toString("base64url");
    return hode + "." + sig;
  };
  const naa = Math.floor(Date.now() / 1000);
  const god = { aud: [aud], email: "Ola@Test.no", exp: naa + 600, iat: naa, iss: team };
  const kall = (h) => m2.dispatchFetch(B + "/api/hjem/steder", { headers: h }).then(async (r) => [r.status, await r.text()]);
  try {
    assert.equal((await kall({ "x-skjold-user": "eier@test.no" }))[0], 401);
    assert.equal((await kall({ "cf-access-authenticated-user-email": "eier@test.no" }))[0], 401);
    const [s, t] = await kall({ "cf-access-jwt-assertion": jwt(god) });
    assert.equal(s, 200, t);
    assert.equal((await kall({ cookie: "CF_Authorization=" + jwt(god) }))[0], 200);
    assert.equal((await kall({ "cf-access-jwt-assertion": jwt({ ...god, aud: ["annen"] }) }))[0], 401);
    assert.equal((await kall({ "cf-access-jwt-assertion": jwt({ ...god, exp: naa - 10 }) }))[0], 401);
    const t2 = jwt(god).split(".");
    t2[1] = b64u({ ...god, email: "angriper@test.no" });
    assert.equal((await kall({ "cf-access-jwt-assertion": t2.join(".") }))[0], 401);
  } finally {
    await m2.dispose();
  }
});

test("uten Access-oppsett og uten DEV_INSECURE avvises alt", async () => {
  const m3 = lagMiniflare({ bindings: { DEV_INSECURE: "" } });
  try {
    const r = await m3.dispatchFetch(B + "/api/hjem/steder", { headers: { "x-skjold-user": "eier@test.no", "cf-access-authenticated-user-email": "eier@test.no" } });
    assert.equal(r.status, 401);
    await r.arrayBuffer();
  } finally {
    await m3.dispose();
  }
});
