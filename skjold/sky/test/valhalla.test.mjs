import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { lagMiniflare, api } from "./hjelp.mjs";

let mf;
before(() => { mf = lagMiniflare({ bindings: { OWNER_EMAILS: "sjef@skjold.no" } }); });
after(async () => { await mf.dispose(); });

test("deling: eieren inviterer, medlemmet ser hjemmet, kan forlate det; eierskap kan overføres", async () => {
  const s = (await api(mf, "POST", "/api/hjem/steder", "eier@test.no", { navn: "Hytta" })).data;
  assert.equal((await api(mf, "POST", `/api/hjem/steder/${s.id}/medlemmer`, "eier@test.no", { epost: "ikke-epost" })).status, 400);
  const r = await api(mf, "POST", `/api/hjem/steder/${s.id}/medlemmer`, "eier@test.no", { epost: "Kari@Test.no" });
  assert.equal(r.status, 200);
  assert.deepEqual(r.data.medlemmer, ["eier@test.no", "kari@test.no"]);
  const kari = await api(mf, "GET", "/api/hjem/steder", "kari@test.no");
  assert.equal(kari.data.length, 1); assert.equal(kari.data[0].rolle, "medlem");
  // medlemmet kan ikke dele videre eller fjerne andre
  assert.equal((await api(mf, "POST", `/api/hjem/steder/${s.id}/medlemmer`, "kari@test.no", { epost: "ola@test.no" })).status, 403);
  assert.equal((await api(mf, "DELETE", `/api/hjem/steder/${s.id}/medlemmer/eier%40test.no`, "kari@test.no")).status, 400);
  // overfør eierskapet til Kari
  const o = await api(mf, "POST", `/api/hjem/steder/${s.id}/eier`, "eier@test.no", { epost: "kari@test.no" });
  assert.equal(o.data.eier, "kari@test.no");
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "eier@test.no")).data[0].rolle, "medlem");
  // den gamle eieren forlater hjemmet
  assert.equal((await api(mf, "DELETE", `/api/hjem/steder/${s.id}/medlemmer/eier%40test.no`, "eier@test.no")).status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "eier@test.no")).data.length, 0);
  const m = await api(mf, "GET", `/api/hjem/steder/${s.id}/medlemmer`, "kari@test.no");
  assert.deepEqual(m.data.medlemmer, [{ epost: "kari@test.no", rolle: "eier" }]);
});

test("Valhalla: bare tjenesteeieren og admins; oversikt, kontoer, hjem, sperring og eierskap", async () => {
  assert.equal((await api(mf, "GET", "/api/valhalla/oversikt", "eier@test.no")).status, 403);
  const meg = await api(mf, "GET", "/api/hjem/meg", "sjef@skjold.no");
  assert.equal(meg.data.valhalla, true); assert.equal(meg.data.eier, true);
  const s = (await api(mf, "POST", "/api/hjem/steder", "per@test.no", { navn: "Byen" })).data;
  const o = await api(mf, "GET", "/api/valhalla/oversikt", "sjef@skjold.no");
  assert.ok(o.data.kontoer >= 1 && o.data.steder >= 1);
  const steder = await api(mf, "GET", "/api/valhalla/steder", "sjef@skjold.no");
  const byen = steder.data.find((x) => x.id === s.id);
  assert.equal(byen.eier, "per@test.no"); assert.deepEqual(byen.enheter, []);
  // Valhalla legger til et medlem og overfører eierskapet
  const e = await api(mf, "POST", `/api/valhalla/steder/${s.id}`, "sjef@skjold.no", { leggTil: "ola@test.no", eier: "ola@test.no" });
  assert.equal(e.data.eier, "ola@test.no");
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "ola@test.no")).data[0].rolle, "eier");
  // sperr Per: avvises på /api/hjem (rolle-mellomlageret tømmes for den som endres)
  assert.equal((await api(mf, "POST", "/api/valhalla/kontoer/per%40test.no", "sjef@skjold.no", { sperret: true })).status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "per@test.no")).status, 403);
  const k = await api(mf, "GET", "/api/valhalla/kontoer", "sjef@skjold.no");
  assert.equal(k.data.find((x) => x.epost === "per@test.no").sperret, true);
  // gi Ola Valhalla-tilgang (bare tjenesteeieren), Ola kan ikke gi videre
  await api(mf, "POST", "/api/valhalla/kontoer/ola%40test.no", "sjef@skjold.no", { admin: true });
  assert.equal((await api(mf, "GET", "/api/valhalla/oversikt", "ola@test.no")).status, 200);
  assert.equal((await api(mf, "POST", "/api/valhalla/kontoer/kari%40test.no", "ola@test.no", { admin: true })).status, 403);
  assert.equal((await api(mf, "POST", "/api/valhalla/kontoer/sjef%40skjold.no", "ola@test.no", { sperret: true })).status, 400);
  // slett hjemmet fra Valhalla: borte for medlemmene
  assert.equal((await api(mf, "DELETE", `/api/valhalla/steder/${s.id}`, "sjef@skjold.no")).status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "ola@test.no")).data.length, 0);
});
