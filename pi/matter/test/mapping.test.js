import { test } from "node:test";
import assert from "node:assert/strict";
import * as m from "../mapping.js";

test("volum ↔ nivå", () => {
  assert.equal(m.volumTilNivaa(0), 0);
  assert.equal(m.volumTilNivaa(100), 254);
  assert.equal(m.volumTilNivaa(50), 127);
  assert.equal(m.volumTilNivaa(150), 254);
  assert.equal(m.volumTilNivaa(-3), 0);
  assert.equal(m.nivaaTilVolum(254), 100);
  assert.equal(m.nivaaTilVolum(0), 0);
  for (let v = 0; v <= 100; v++) assert.equal(m.nivaaTilVolum(m.volumTilNivaa(v)), v, `rundtur ${v}`);
});

test("kilder som ModeSelect", () => {
  const inp = ["airplay", "bt", "radio", "usb"];
  assert.deepEqual(m.kildeModuser(inp, { bt: "Blåtann" })[1], { label: "Blåtann", mode: 1, semanticTags: [] });
  assert.equal(m.kildeTilModus(inp, "radio"), 2);
  assert.equal(m.kildeTilModus(inp, "ukjent"), 0);
  assert.equal(m.modusTilKilde(inp, 3), "usb");
  assert.equal(m.modusTilKilde(inp, 9), null);
});

test("status → Matter", () => {
  const t = m.statusTilMatter({ power: true, volume: 40, mute: true, preset: 3, input: "radio", inputs: ["airplay", "radio"] });
  assert.deepEqual(t.hoyttaler, { onOff: true, level: 102 });
  assert.equal(t.demp, true);
  assert.deepEqual(t.favoritter, [false, false, true, false, false, false]);
  assert.equal(t.kilde, 1);
  assert.deepEqual(m.statusTilMatter({ power: false, preset: 3 }).favoritter, Array(6).fill(false));
});

test("Matter → daemon-kall", () => {
  assert.deepEqual(m.hendelseTilKall("onOff", false), { sti: "/api/power", body: { on: false } });
  assert.deepEqual(m.hendelseTilKall("level", 254), { sti: "/api/volume", body: { volume: 100 } });
  assert.deepEqual(m.hendelseTilKall("demp", true), { sti: "/api/mute", body: { mute: true } });
  assert.deepEqual(m.hendelseTilKall("favoritt", { n: 2, on: true }), { sti: "/api/preset", body: { n: 2 } });
  assert.deepEqual(m.hendelseTilKall("favoritt", { n: 2, on: false }), { sti: "/api/power", body: { on: false } });
  assert.deepEqual(m.hendelseTilKall("kilde", 1, ["airplay", "bt"]), { sti: "/api/input", body: { input: "bt" } });
  assert.equal(m.hendelseTilKall("kilde", 5, ["airplay"]), null);
  assert.equal(m.hendelseTilKall("tull", 1), null);
});

test("Volum-lampe: nivå = volum, av = dempet", () => {
  const t = m.statusTilMatter({ power: true, volume: 50, mute: false, inputs: [] });
  assert.equal(t.volum.onOff, true);
  assert.equal(t.volum.level, 127);
  assert.equal(m.statusTilMatter({ mute: true, volume: 10, inputs: [] }).volum.onOff, false);
  assert.deepEqual(m.hendelseTilKall("volumPa", false, []), { sti: "/api/mute", body: { mute: true } });
  assert.deepEqual(m.hendelseTilKall("volumNivaa", 254, []), { sti: "/api/volume", body: { volume: 100 } });
});
