import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { lagMiniflare, B } from "./hjelp.mjs";

let mf;
before(() => { mf = lagMiniflare(); });
after(async () => { await mf.dispose(); });

async function kall(metode, sti, kropp, ip = "2.2.2.2") {
  const h = { "cf-connecting-ip": ip };
  if (kropp) h["content-type"] = "application/json";
  const r = await mf.dispatchFetch(B + sti, { method: metode, headers: h, body: kropp ? JSON.stringify(kropp) : undefined });
  return { status: r.status, data: await r.json() };
}

test("kassettdeling: lagre kryptert blob, hente den med id, avvise ugyldig og ukjent", async () => {
  assert.equal((await kall("POST", "/del", { blob: "" })).status, 400);
  assert.equal((await kall("POST", "/del", { blob: "ikke base64!" })).status, 400);
  assert.equal((await kall("POST", "/del", { blob: "A".repeat(50 * 1024) })).status, 400);
  const r = await kall("POST", "/del", { blob: "AQIDBAUGBwgJ" });
  assert.equal(r.status, 201);
  assert.match(r.data.id, /^[a-z0-9]{10}$/);
  assert.ok(r.data.utloper > Date.now());
  const g = await kall("GET", "/del/" + r.data.id);
  assert.equal(g.status, 200); assert.equal(g.data.blob, "AQIDBAUGBwgJ");
  assert.equal((await kall("GET", "/del/finnesikke1")).status, 404);
});

test("kassettdeling: grense per døgn per avsender", async () => {
  let siste;
  for (let i = 0; i < 51; i++) siste = await kall("POST", "/del", { blob: "AQID" }, "9.9.9.9");
  assert.equal(siste.status, 429);
  assert.equal((await kall("POST", "/del", { blob: "AQID" }, "8.8.8.8")).status, 201);
});
