import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { lagMiniflare, B } from "./hjelp.mjs";

let mf;
before(() => { mf = lagMiniflare({ bindings: { MOD_TOKEN: "hemmelig-mod" } }); });
after(async () => { await mf.dispose(); });

async function kall(metode, sti, kropp, { ip = "1.1.1.1", mod } = {}) {
  const h = { "cf-connecting-ip": ip };
  if (kropp) h["content-type"] = "application/json";
  if (mod) h.authorization = "Bearer " + mod;
  const r = await mf.dispatchFetch(B + sti, { method: metode, headers: h, body: kropp ? JSON.stringify(kropp) : undefined });
  return { status: r.status, data: await r.json() };
}

const fr = Array.from({ length: 120 }, (_, i) => 20 * 2 ** (i / 12));
const kurve = (fn) => fr.map((f) => ({ f, db: fn(f) }));
const inns = (kilde, fn = () => 0, ekstra = {}) => ({ merke: "Dali", modell: "Oberon 3", kurve: kurve(fn), kilde, score: 80, gyldig: [200, 20000], ...ekstra });

test("høyttalerprofiler: send, søk, median, sertifisering", async () => {
  assert.equal((await kall("POST", "/hoyttaler/send", { ...inns("aaaaaaaa"), kurve: [] })).status, 400);
  const a = await kall("POST", "/hoyttaler/send", inns("aaaaaaaa", (f) => (f > 2000 ? 3 : 0), { impedans: 4 }));
  assert.equal(a.status, 201); assert.equal(a.data.id, "dali-oberon-3"); assert.equal(a.data.sertifisert, false);
  await kall("POST", "/hoyttaler/send", inns("bbbbbbbb", (f) => (f > 2000 ? 3.5 : 0)));
  // samme kilde erstatter sin forrige innsending
  await kall("POST", "/hoyttaler/send", inns("bbbbbbbb", (f) => (f > 2000 ? 3 : 0)));
  let p = (await kall("GET", "/hoyttaler/profil/dali-oberon-3")).data;
  assert.equal(p.antall, 2); assert.equal(p.sertifisert, false);
  await kall("POST", "/hoyttaler/send", inns("cccccccc", (f) => (f > 2000 ? 2.8 : 0)));
  await kall("POST", "/hoyttaler/send", inns("dddddddd", (f) => (f > 1000 && f < 5000 ? 12 : 0)));   // avviker
  p = (await kall("GET", "/hoyttaler/profil/dali-oberon-3")).data;
  assert.equal(p.antall, 4); assert.equal(p.enige, 3); assert.equal(p.sertifisert, true); assert.equal(p.impedans, 4);
  const s = (await kall("GET", "/hoyttaler/sok?q=oberon")).data.treff;
  assert.equal(s.length, 1); assert.equal(s[0].sertifisert, true);
  assert.equal((await kall("GET", "/hoyttaler/sok?q=kef")).data.treff.length, 0);
});

test("høyttalerprofiler: flagging skjuler, moderator viser igjen; grense per døgn", async () => {
  await kall("POST", "/hoyttaler/send", { ...inns("eeeeeeee"), merke: "KEF", modell: "LS50" });
  for (const ip of ["9.9.9.1", "9.9.9.1", "9.9.9.2"]) await kall("POST", "/hoyttaler/flagg", { id: "kef-ls50", grunn: "tull" }, { ip });
  assert.equal((await kall("GET", "/hoyttaler/profil/kef-ls50")).status, 200);   // samme ip teller én gang
  await kall("POST", "/hoyttaler/flagg", { id: "kef-ls50" }, { ip: "9.9.9.3" });
  assert.equal((await kall("GET", "/hoyttaler/profil/kef-ls50")).status, 404);
  assert.equal((await kall("POST", "/hoyttaler/moder", { id: "kef-ls50", handling: "vis" })).status, 403);
  assert.equal((await kall("POST", "/hoyttaler/moder", { id: "kef-ls50", handling: "vis" }, { mod: "hemmelig-mod" })).status, 200);
  assert.equal((await kall("GET", "/hoyttaler/profil/kef-ls50")).status, 200);
  let siste;
  for (let i = 0; i < 21; i++) siste = await kall("POST", "/hoyttaler/send", { ...inns("ffffffff"), modell: "Spam " + i }, { ip: "7.7.7.7" });
  assert.equal(siste.status, 429);
});
