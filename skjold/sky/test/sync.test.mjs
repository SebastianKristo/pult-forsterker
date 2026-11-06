import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { lagMiniflare, api, FalskEnhet, B } from "./hjelp.mjs";

let mf;
before(() => { mf = lagMiniflare(); });
after(async () => { await mf.dispose(); });

async function sync(e, metode, kropp, del) {
  const r = await mf.dispatchFetch(B + "/enhet/sync" + (del ? "?del=" + del : ""), {
    method: metode,
    headers: { authorization: `Bearer ${e.id}.${e.noekkel}`, "content-type": "application/json" },
    body: kropp ? JSON.stringify(kropp) : undefined,
  });
  return { status: r.status, data: await r.json() };
}

test("Skjold Cloud: krypterte blobs deles mellom hjem til samme eier, med konfliktsjekk", async () => {
  const hjem = (await api(mf, "POST", "/api/hjem/steder", "eier@test.no", { navn: "Hjem" })).data.id;
  const hytta = (await api(mf, "POST", "/api/hjem/steder", "eier@test.no", { navn: "Hytta" })).data.id;
  const a = new FalskEnhet(mf, "sync-a"); await a.kobl(hjem);
  const b = new FalskEnhet(mf, "sync-b"); await b.kobl(hytta);

  assert.equal((await sync(a, "GET", null, "favoritter")).data.versjon, 0);
  const l1 = await sync(a, "PUT", { del: "favoritter", base: 0, blob: "QUJD" });
  assert.equal(l1.status, 200); assert.equal(l1.data.versjon, 1);
  // samme konto fra et annet sted ser den nye versjonen
  const h = await sync(b, "GET", null, "favoritter");
  assert.deepEqual([h.data.versjon, h.data.blob, h.data.enhet], [1, "QUJD", "sync-a"]);
  // utdatert base → 409 med gjeldende innhold
  const k = await sync(b, "PUT", { del: "favoritter", base: 0, blob: "REVG" });
  assert.equal(k.status, 409); assert.equal(k.data.blob, "QUJD");
  assert.equal((await sync(b, "PUT", { del: "favoritter", base: 1, blob: "REVG" })).data.versjon, 2);
  // ukjent del, for stor blob og feil nøkkel avvises
  assert.equal((await sync(a, "PUT", { del: "hemmelig", base: 0, blob: "QQ" })).status, 400);
  assert.equal((await sync(a, "PUT", { del: "eq", base: 0, blob: "A".repeat(600 * 1024) })).status, 413);
  const feil = await mf.dispatchFetch(B + "/enhet/sync?del=eq", { headers: { authorization: `Bearer sync-a.${hjem}.${"0".repeat(64)}` } });
  assert.equal(feil.status, 401); await feil.arrayBuffer();
  // brukeren ser bare metadata, og kan slette alt
  const o = await api(mf, "GET", "/api/hjem/sync");
  assert.deepEqual(o.data.deler.map((x) => [x.del, x.versjon]), [["favoritter", 2]]);
  assert.equal("blob" in o.data.deler[0], false);
  assert.equal((await api(mf, "GET", "/api/hjem/sync", "fremmed@test.no")).data.deler.length, 0);
  await api(mf, "DELETE", "/api/hjem/sync");
  assert.equal((await sync(a, "GET", null, "favoritter")).data.versjon, 0);
});
