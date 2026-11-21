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
  assert.equal(ak.status, 200); assert.equal(ak.data.reservekoder.length, 10); assert.match(ak.ck, /^skjold_okt=/);
  // uten økt-cookie: alt annet enn /meg og /2fa/bekreft avvises
  const uten = await api(mf, "GET", "/api/hjem/steder", u);
  assert.equal(uten.status, 401); assert.equal(uten.data.error, "2fa");
  const meg = await api(mf, "GET", "/api/hjem/meg", u);
  assert.equal(meg.data.tofa, true); assert.equal(meg.data.tofaOk, false);
  assert.equal((await api(mf, "GET", "/api/hjem/konto/okter", u)).status, 401);
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

test("Økter: liste, logg ut én enhet, godkjenn ny innlogging fra en annen enhet", async () => {
  const u = "okt@test.no";
  const st = await api(mf, "POST", "/api/hjem/konto/2fa/start", u, {});
  const a = await medCookie("POST", "/api/hjem/konto/2fa/aktiver", u, { kode: totp(st.data.hemmelighet) });
  const tlf = a.ck;   // «telefonen» er logget inn og bekreftet
  // ny nettleser ber om godkjenning
  const ny = await medCookie("POST", "/api/hjem/konto/godkjenn/start", u, {});
  assert.equal(ny.status, 200); assert.ok(ny.data.tall >= 10 && ny.data.tall < 100);
  const pc = ny.ck;
  assert.equal((await medCookie("GET", "/api/hjem/konto/godkjenn/status?rid=" + ny.data.rid, u, null, pc)).data.status, "venter");
  // den nye økten kan ikke godkjenne seg selv (er ikke bekreftet)
  assert.equal((await medCookie("GET", "/api/hjem/konto/godkjenn/ventende", u, null, pc)).status, 401);
  const v = await medCookie("GET", "/api/hjem/konto/godkjenn/ventende", u, null, tlf);
  assert.equal(v.data.length, 1); assert.equal(v.data[0].valg.length, 3); assert.ok(v.data[0].valg.includes(ny.data.tall));
  const svar = await medCookie("POST", "/api/hjem/konto/godkjenn/" + v.data[0].rid, u, { svar: ny.data.tall }, tlf);
  assert.equal(svar.data.status, "godkjent");
  assert.equal((await medCookie("GET", "/api/hjem/konto/godkjenn/status?rid=" + ny.data.rid, u, null, pc)).data.status, "godkjent");
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, pc)).status, 200);
  // feil tall avviser
  const ny2 = await medCookie("POST", "/api/hjem/konto/godkjenn/start", u, {});
  const v2 = (await medCookie("GET", "/api/hjem/konto/godkjenn/ventende", u, null, tlf)).data[0];
  const feilTall = v2.valg.find((x) => x !== ny2.data.tall);
  assert.equal((await medCookie("POST", "/api/hjem/konto/godkjenn/" + v2.rid, u, { svar: feilTall }, tlf)).data.status, "avvist");
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, ny2.ck)).status, 401);
  // øktlisten viser enhetene, og «denne» er markert
  const l = await medCookie("GET", "/api/hjem/konto/okter", u, null, tlf);
  assert.ok(l.data.length >= 3); assert.equal(l.data.filter((x) => x.denne).length, 1);
  const pcSid = pc.split("=")[1].split(".")[0];
  assert.ok(l.data.some((x) => x.sid === pcSid && x.bekreftet && x.metode === "godkjent fra en annen enhet"));
  // logg ut PC-en fra telefonen
  assert.equal((await medCookie("DELETE", "/api/hjem/konto/okter/" + pcSid, u, null, tlf)).status, 200);
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, pc)).status, 401);
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, tlf)).status, 200);
});

import { generateKeyPairSync, sign as nodeSign, createHash } from "node:crypto";
const b64u = (b) => Buffer.from(b).toString("base64url");
function cborEnc(v) {   // akkurat nok CBOR for en attestasjon
  const hode = (maj, n) => n < 24 ? [maj << 5 | n] : n < 256 ? [maj << 5 | 24, n] : [maj << 5 | 25, n >> 8, n & 255];
  if (typeof v === "number") return Buffer.from(v >= 0 ? hode(0, v) : hode(1, -1 - v));
  if (typeof v === "string") { const b = Buffer.from(v); return Buffer.concat([Buffer.from(hode(3, b.length)), b]); }
  if (Buffer.isBuffer(v)) return Buffer.concat([Buffer.from(hode(2, v.length)), v]);
  if (v instanceof Map) return Buffer.concat([Buffer.from(hode(5, v.size)), ...[...v].flatMap(([k, x]) => [cborEnc(k), cborEnc(x)])]);
  throw new Error("cbor");
}
test("Passkey: registrer og logg inn med en ES256-nøkkel (WebAuthn)", async () => {
  const u = "nokkel@test.no", rp = "sky.test", opp = "http://sky.test";
  const { publicKey, privateKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });
  const jwk = publicKey.export({ format: "jwk" });
  const credId = Buffer.from("nokkel-id-1234567890");
  const rpHash = createHash("sha256").update(rp).digest();
  const start = await medCookie("POST", "/api/hjem/konto/passkey/start", u, { type: "passkey" });
  assert.equal(start.status, 200); assert.equal(start.data.rp.id, rp);
  const ck = start.ck;
  const cose = cborEnc(new Map([[1, 2], [3, -7], [-1, 1], [-2, Buffer.from(jwk.x, "base64url")], [-3, Buffer.from(jwk.y, "base64url")]]));
  const len = Buffer.alloc(2); len.writeUInt16BE(credId.length);
  const authData = Buffer.concat([rpHash, Buffer.from([0x45]), Buffer.from([0, 0, 0, 1]), Buffer.alloc(16), len, credId, cose]);
  const cdj = Buffer.from(JSON.stringify({ type: "webauthn.create", challenge: start.data.challenge, origin: opp }));
  const att = cborEnc(new Map([["fmt", "none"], ["attStmt", new Map()], ["authData", authData]]));
  const reg = await medCookie("POST", "/api/hjem/konto/passkey/registrer", u, { clientDataJSON: b64u(cdj), attestationObject: b64u(att), navn: "Testnøkkel" }, ck);
  assert.equal(reg.status, 200, JSON.stringify(reg.data)); assert.equal(reg.data.tofaAktiv, true);
  // en ny enhet må nå bekrefte – med passkeyen
  assert.equal((await api(mf, "GET", "/api/hjem/steder", u)).status, 401);
  const ls = await medCookie("POST", "/api/hjem/konto/passkey/login-start", u, {});
  assert.equal(ls.data.allowCredentials[0].id, b64u(credId));
  const lagSvar = (utf, teller) => {
    const ad = Buffer.concat([rpHash, Buffer.from([0x05]), Buffer.from([0, 0, 0, teller])]);
    const c = Buffer.from(JSON.stringify({ type: "webauthn.get", challenge: utf, origin: opp }));
    const sig = nodeSign("sha256", Buffer.concat([ad, createHash("sha256").update(c).digest()]), privateKey);   // DER, som nettleseren
    return { id: b64u(credId), clientDataJSON: b64u(c), authenticatorData: b64u(ad), signature: b64u(sig) };
  };
  const inn = await medCookie("POST", "/api/hjem/konto/passkey/login", u, lagSvar(ls.data.challenge, 2), ls.ck);
  assert.equal(inn.status, 200, JSON.stringify(inn.data));
  assert.equal((await medCookie("GET", "/api/hjem/steder", u, null, ls.ck)).status, 200);
  // samme teller igjen (kopiert nøkkel) avvises
  const ls2 = await medCookie("POST", "/api/hjem/konto/passkey/login-start", u, {});
  assert.equal((await medCookie("POST", "/api/hjem/konto/passkey/login", u, lagSvar(ls2.data.challenge, 2), ls2.ck)).status, 401);
  // feil utfordring avvises
  const ls3 = await medCookie("POST", "/api/hjem/konto/passkey/login-start", u, {});
  assert.equal((await medCookie("POST", "/api/hjem/konto/passkey/login", u, lagSvar("feil", 3), ls3.ck)).status, 401);
  // fjern nøkkelen → totrinn av igjen
  const info = await medCookie("GET", "/api/hjem/konto", u, null, ls.ck);
  assert.equal(info.data.tofa.passkeys.length, 1);
  const d = await medCookie("DELETE", "/api/hjem/konto/passkey/" + encodeURIComponent(info.data.tofa.passkeys[0].id), u, null, ls.ck);
  assert.equal(d.data.tofaAktiv, false);
  assert.equal((await api(mf, "GET", "/api/hjem/steder", u)).status, 200);
});

test("Profilbilde: lagres på kontoen og vises i Valhalla", async () => {
  const u = "bilde@test.no", bilde = "data:image/jpeg;base64," + Buffer.from("liksom-jpeg").toString("base64");
  assert.equal((await api(mf, "PATCH", "/api/hjem/konto", u, { bilde: "javascript:alert(1)" })).status, 400);
  assert.equal((await api(mf, "PATCH", "/api/hjem/konto", u, { bilde })).status, 200);
  assert.equal((await api(mf, "GET", "/api/hjem/konto", u)).data.bilde, bilde);
  const k = await api(mf, "GET", "/api/valhalla/kontoer", "sjef@skjold.no");
  assert.equal(k.data.find((x) => x.epost === u).bilde, bilde);
});

test("Vedlikehold: brukere får 503 med nedtelling, Valhalla og /meg virker", async () => {
  const til = Math.floor(Date.now() / 1000) + 3600;
  assert.equal((await api(mf, "POST", "/api/valhalla/vedlikehold", "vanlig@test.no", { aktiv: true })).status, 403);
  const s = await api(mf, "POST", "/api/valhalla/vedlikehold", "sjef@skjold.no", { aktiv: true, melding: "Ny database", til });
  assert.equal(s.status, 200); assert.equal(s.data.aktiv, true);
  const r = await api(mf, "GET", "/api/hjem/steder", "vanlig@test.no");
  assert.equal(r.status, 503); assert.equal(r.data.error, "vedlikehold"); assert.equal(r.data.vedlikehold.til, til);
  assert.equal((await api(mf, "GET", "/api/hjem/meg", "vanlig@test.no")).data.vedlikehold.melding, "Ny database");
  const off = await mf.dispatchFetch("http://sky.test/api/vedlikehold");
  assert.equal(off.headers.get("access-control-allow-origin"), "*"); assert.equal((await off.json()).aktiv, true);
  assert.equal((await api(mf, "GET", "/api/valhalla/oversikt", "sjef@skjold.no")).data.vedlikehold.aktiv, true);
  await api(mf, "POST", "/api/valhalla/vedlikehold", "sjef@skjold.no", { aktiv: false });
  assert.equal((await api(mf, "GET", "/api/hjem/steder", "vanlig@test.no")).status, 200);
});

test("Kontrollsenter: hendelseslogg, statistikk, kontodetaljer og alle enheter", async () => {
  const u = "logg@test.no";
  const s = (await api(mf, "POST", "/api/hjem/steder", u, { navn: "Hytta" })).data;
  await api(mf, "PATCH", "/api/hjem/konto", u, { navn: "Loggy" });
  const l = await api(mf, "GET", "/api/valhalla/logg?epost=" + encodeURIComponent(u), "sjef@skjold.no");
  const typer = l.data.hendelser.map((h) => h.type);
  assert.ok(typer.includes("innlogging") && typer.includes("hjem_nytt") && typer.includes("profil"), typer.join(","));
  assert.equal((await api(mf, "GET", "/api/valhalla/logg", "vanlig@test.no")).status, 403);
  assert.ok((await api(mf, "GET", "/api/valhalla/logg?type=hjem_nytt&limit=1", "sjef@skjold.no")).data.hendelser.every((h) => h.type === "hjem_nytt"));
  const st = await api(mf, "GET", "/api/valhalla/statistikk", "sjef@skjold.no");
  assert.ok(st.data.hendelser24t > 0 && st.data.perTime.length === 24 && st.data.perType.innlogging > 0);
  const d = await api(mf, "GET", "/api/valhalla/kontoer/" + encodeURIComponent(u), "sjef@skjold.no");
  assert.equal(d.status, 200); assert.equal(d.data.profil.navn, "Loggy"); assert.ok(d.data.okter.length >= 1);
  assert.equal(d.data.steder[0].navn, "Hytta"); assert.ok(d.data.hendelser.length >= 3);
  // admin: endre hjemnavn, logg ut kontoen, se hjemdetalj og alle enheter
  assert.equal((await api(mf, "POST", "/api/valhalla/steder/" + s.id, "sjef@skjold.no", { navn: "Fjellhytta" })).data.navn, "Fjellhytta");
  assert.equal((await api(mf, "GET", "/api/hjem/steder", u)).data[0].navn, "Fjellhytta");
  const sd = await api(mf, "GET", "/api/valhalla/steder/" + s.id, "sjef@skjold.no");
  assert.ok(sd.data.hendelser.some((h) => h.type === "admin_hjem_navn" && h.av === "sjef@skjold.no"));
  assert.ok(Array.isArray((await api(mf, "GET", "/api/valhalla/enheter", "sjef@skjold.no")).data));
  assert.equal((await api(mf, "POST", "/api/valhalla/kontoer/" + encodeURIComponent(u), "sjef@skjold.no", { loggUt: true })).status, 200);
  assert.equal((await api(mf, "GET", "/api/valhalla/kontoer/" + encodeURIComponent(u), "sjef@skjold.no")).data.okter.length, 0);
  // brukeren ser sin egen aktivitet, og at Skjold Lab har gjort noe
  const akt = await api(mf, "GET", "/api/hjem/konto/aktivitet", u);
  assert.ok(akt.data.some((h) => h.type === "admin_hjem_navn" && h.skjoldLab));
});

test("Logg inn som: bare tjenesteeieren, sikkerhet sperret, alt loggføres", async () => {
  const u = "kunde@test.no";
  await api(mf, "POST", "/api/hjem/steder", u, { navn: "Kundens hjem" });
  assert.equal((await api(mf, "POST", "/api/valhalla/som", "vanlig@test.no", { epost: u })).status, 403);
  // en admin (ikke tjenesteeier) får ikke lov
  await api(mf, "POST", "/api/valhalla/kontoer/" + encodeURIComponent("hjelper@test.no"), "sjef@skjold.no", { admin: true });
  await api(mf, "GET", "/api/hjem/meg", "hjelper@test.no");
  assert.equal((await api(mf, "POST", "/api/valhalla/som", "hjelper@test.no", { epost: u })).status, 403);
  const start = await medCookie("POST", "/api/valhalla/som", "sjef@skjold.no", { epost: u });
  assert.equal(start.status, 200); assert.match(start.ck, /^skjold_som=/);
  const meg = await medCookie("GET", "/api/hjem/meg", "sjef@skjold.no", null, start.ck);
  assert.equal(meg.data.epost, u); assert.equal(meg.data.som.admin, "sjef@skjold.no");
  const steder = await medCookie("GET", "/api/hjem/steder", "sjef@skjold.no", null, start.ck);
  assert.equal(steder.data[0].navn, "Kundens hjem");
  assert.equal((await medCookie("POST", "/api/hjem/konto/2fa/start", "sjef@skjold.no", {}, start.ck)).status, 403);
  assert.equal((await medCookie("POST", "/api/hjem/konto/logg-ut-overalt", "sjef@skjold.no", {}, start.ck)).status, 403);
  assert.equal((await medCookie("PATCH", "/api/hjem/konto", "sjef@skjold.no", { navn: "Endret av støtte" }, start.ck)).status, 200);
  // cookien virker ikke for en annen bruker
  assert.equal((await medCookie("GET", "/api/hjem/meg", "hjelper@test.no", null, start.ck)).data.epost, "hjelper@test.no");
  const akt = await api(mf, "GET", "/api/hjem/konto/aktivitet", u);
  assert.ok(akt.data.some((h) => h.type === "som_start" && h.skjoldLab) && akt.data.some((h) => h.type === "som_handling"));
  const slutt = await medCookie("DELETE", "/api/valhalla/som", "sjef@skjold.no", null, start.ck);
  assert.match(slutt.ck, /^skjold_som=$/);
  assert.equal((await api(mf, "GET", "/api/hjem/meg", "sjef@skjold.no")).data.epost, "sjef@skjold.no");
  assert.equal((await api(mf, "POST", "/api/valhalla/som", "sjef@skjold.no", { epost: "ukjent@test.no" })).status, 404);
});
