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

test("Valhalla finner hjem som ble laget før registeret (via kontoene)", async () => {
  // et hjem laget rett i Sted/Konto uten registeret (som før oppdateringen)
  const r = await api(mf, "POST", "/api/hjem/steder", "gammel@test.no", { navn: "Gammelt hjem" });
  await mf.getDurableObjectNamespace("REGISTER").then(async (ns) => {
    const stub = ns.get(ns.idFromName("register"));
    await stub.fetch("https://do/i/sted-slett", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: r.data.id }) });
  });
  const l = await api(mf, "GET", "/api/valhalla/steder?synk=1", "sjef@skjold.no");
  assert.ok(l.data.some((x) => x.id === r.data.id && x.eier === "gammel@test.no"));
});

import { createHmac } from "node:crypto";
function totp(h32, steg = Math.floor(Date.now() / 30000)) {
  const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = 0, v = 0; const b = [];
  for (const c of h32) { v = (v << 5) | A.indexOf(c); bits += 5; if (bits >= 8) { b.push((v >>> (bits - 8)) & 255); bits -= 8; } }
  const buf = Buffer.alloc(8); buf.writeBigUInt64BE(BigInt(steg));
  const h = createHmac("sha1", Buffer.from(b)).update(buf).digest(); const o = h[19] & 15;
  return String((((h[o] & 127) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3]) % 1000000).padStart(6, "0");
}
async function medCookie(metode, sti, bruker, kropp, ck) {
  const h = { "x-skjold-user": bruker }; if (kropp) h["content-type"] = "application/json"; if (ck) h.cookie = ck;
  const r = await mf.dispatchFetch("http://sky.test" + sti, { method: metode, headers: h, body: kropp ? JSON.stringify(kropp) : undefined });
  return { status: r.status, data: await r.json(), ck: (r.headers.get("set-cookie") || "").split(";")[0] };
}

test("Skjold-konto: profil, totrinnsbekreftelse med kodeapp og reservekoder, Valhalla kan tilbakestille", async () => {
  const u = "tofa@test.no";
  const k = await api(mf, "GET", "/api/hjem/konto", u);
  assert.equal(k.status, 200); assert.equal(k.data.tofa.aktiv, false); assert.equal(k.data.epost, u);
  assert.equal((await api(mf, "PATCH", "/api/hjem/konto", u, { navn: "Tora" })).data.navn, "Tora");
  const st = await api(mf, "POST", "/api/hjem/konto/2fa/start", u, {});
  assert.match(st.data.uri, /^otpauth:\/\/totp\/Skjold\?secret=[A-Z2-7]{26}&issuer=Skjold$/);
  assert.ok(st.data.uri.length <= 78);   // passer i QR-versjon 4 (lib/qr.ts)
  assert.equal((await api(mf, "POST", "/api/hjem/konto/2fa/aktiver", u, { kode: "000000" })).status, 401);
  const ak = await medCookie("POST", "/api/hjem/konto/2fa/aktiver", u, { kode: totp(st.data.hemmelighet) });
  assert.equal(ak.status, 200); assert.equal(ak.data.reservekoder.length, 10); assert.match(ak.ck, /^skjold_2fa=/);
  // uten økt-cookie: alt annet enn /meg og /2fa/bekreft avvises
  const uten = await api(mf, "GET", "/api/hjem/steder", u);
  assert.equal(uten.status, 401); assert.equal(uten.data.error, "2fa");
  const meg = await api(mf, "GET", "/api/hjem/meg", u);
  assert.equal(meg.data.tofa, true); assert.equal(meg.data.tofaOk, false);
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, ak.ck)).status, 200);
  // ny enhet: bekreft med en reservekode (kan bare brukes én gang)
  const b1 = await medCookie("POST", "/api/hjem/konto/2fa/bekreft", u, { kode: ak.data.reservekoder[0] });
  assert.equal(b1.status, 200); assert.equal((await medCookie("GET", "/api/hjem/konto", u, null, b1.ck)).data.tofa.reservekoderIgjen, 9);
  assert.equal((await api(mf, "POST", "/api/hjem/konto/2fa/bekreft", u, { kode: ak.data.reservekoder[0] })).status, 401);
  // logg ut overalt: gamle økter slutter å virke
  await medCookie("POST", "/api/hjem/konto/logg-ut-overalt", u, {}, b1.ck);
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, b1.ck)).status, 401);
  // Valhalla tilbakestiller (mistet telefonen)
  assert.equal((await api(mf, "POST", "/api/valhalla/kontoer/tofa%40test.no", "sjef@skjold.no", { tofaAv: true })).status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/steder", u)).status, 200);
});

test("Skjold-konto: kan ikke slettes mens du eier et hjem", async () => {
  const u = "slett@test.no";
  const s = (await api(mf, "POST", "/api/hjem/steder", u, { navn: "Mitt" })).data;
  assert.equal((await api(mf, "DELETE", "/api/hjem/konto", u)).status, 409);
  await api(mf, "DELETE", "/api/hjem/steder/" + s.id, u);
  assert.equal((await api(mf, "DELETE", "/api/hjem/konto", u)).status, 200);
});
