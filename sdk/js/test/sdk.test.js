import { test } from "node:test";
import assert from "node:assert/strict";
import { Skjold, SkjoldFeil } from "../index.js";

// Falsk fetch – testene trenger verken nett eller simulator.
function falsk() {
  const kall = [];
  const s = { power: false, volume: 20, mute: false, input: "radio" };
  const f = async (url, init = {}) => {
    const sti = new URL(url).pathname, b = init.body ? JSON.parse(init.body) : {};
    kall.push([init.method || "GET", sti, b]);
    if (sti === "/api/events") {
      const enc = new TextEncoder();
      return { ok: true, body: (async function* () { yield enc.encode("retry: 2000\n\ndata: {\"volume\":5"); yield enc.encode("}\n\ndata: {\"volume\":6}\n\n"); })() };
    }
    if (sti === "/api/input" && b.input === "x") return { ok: false, status: 400, statusText: "Bad", text: async () => '{"error":"ukjent"}' };
    if (sti === "/api/volume") s.volume = b.delta !== undefined ? s.volume + b.delta : b.volume;
    if (sti === "/api/power") s.power = b.on;
    return { ok: true, status: 200, text: async () => JSON.stringify(s) };
  };
  return { f, kall };
}

test("kommandoer sender riktig JSON", async () => {
  const { f, kall } = falsk();
  const s = new Skjold("x", { fetch: f });
  assert.equal(s.base, "http://x:8765");
  assert.equal((await s.power(true)).power, true);
  assert.equal((await s.volume(30)).volume, 30);
  assert.equal((await s.volume(undefined, { delta: -5 })).volume, 25);
  await s.preset(2); await s.transport("next");
  assert.deepEqual(kall.slice(-2), [["POST", "/api/preset", { n: 2 }], ["POST", "/api/transport", { action: "next" }]]);
});

test("feil gir SkjoldFeil med status", async () => {
  const s = new Skjold("x", { fetch: falsk().f });
  await assert.rejects(s.input("x"), (e) => e instanceof SkjoldFeil && e.status === 400 && /ukjent/.test(e.message));
});

test("events tåler oppdelte biter", async () => {
  const s = new Skjold("x", { fetch: falsk().f });
  const sett = [];
  for await (const st of s.events()) sett.push(st.volume);
  assert.deepEqual(sett, [5, 6]);
});
