// Skjold som Matter-enhet (matter.js). Startes av skjold-matter.service når pluginen «Matter» er på.
//
// Endepunkter (det kontrollerne viser):
//   1  Høyttaler (Speaker 0x0022)  – OnOff = av/på (strøm), LevelControl = volum 0–100 ↔ 0–254
//   2  «Volum» (Dimmable Light)     – nivå = volum, av = dempet (glidebryter i Apple Hjem, som ikke viser Speaker)
//   3  «Demp» (On/Off Plug-in Unit) – på = dempet
//   3–8 «Favoritt 1–6» (On/Off Plug-in Unit) – på = spill radiofavoritten, av = slå av
//   9  «Kilde» (Mode Select)        – én modus per inngang
// Status hentes fra daemonen (SSE /api/events, REST som reserve) på 127.0.0.1:8765.
// Lokal status-API for daemonen/web-UI: http://127.0.0.1:8767/status · POST /reset (glem paringer).
import fs from "node:fs";
import http from "node:http";
import crypto from "node:crypto";
import { Endpoint, Environment, ServerNode, StorageService, VendorId } from "@matter/main";
import { DescriptorServer } from "@matter/main/behaviors";
import { DimmableLightDevice, ModeSelectDevice, OnOffPlugInUnitDevice, SpeakerDevice } from "@matter/main/devices";
import { FAVORITTER, hendelseTilKall, kildeModuser, statusTilMatter } from "./mapping.js";

const DAEMON = process.env.SKJOLD_DAEMON || "http://127.0.0.1:8765";
const STATUS_PORT = Number(process.env.SKJOLD_MATTER_STATUS_PORT || 8767);
const MATTER_PORT = Number(process.env.SKJOLD_MATTER_PORT || 5540);
const env = Environment.default;
const DIR = process.env.SKJOLD_MATTER_DIR || "/var/lib/ki-amp/matter";
env.vars.set("storage.path", DIR);

// Tilfeldig paringskode per enhet (lagres; slettes ved «Glem paringer»). Matter forbyr enkelte koder.
const UGYLDIG = new Set([0, 11111111, 22222222, 33333333, 44444444, 55555555, 66666666, 77777777, 88888888, 99999999, 12345678, 87654321]);
function paring() {
  const f = `${DIR}/paring.json`;
  try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { /* ny */ }
  let passcode;
  do passcode = crypto.randomInt(1, 99999999); while (UGYLDIG.has(passcode));
  const p = { passcode, discriminator: crypto.randomInt(0, 4096) };
  fs.mkdirSync(DIR, { recursive: true });
  fs.writeFileSync(f, JSON.stringify(p), { mode: 0o600 });
  return p;
}

const post = (sti, body) => fetch(DAEMON + sti, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) })
  .catch((e) => console.error("daemon:", e.message));
const hent = async (sti) => (await fetch(DAEMON + sti)).json();

let status = { power: false, volume: 30, mute: false, preset: 0, input: "", inputs: [] };
try { status = await hent("/api/status"); } catch (e) { console.error("daemon ikke klar:", e.message); }
const inputs = status.inputs?.length ? status.inputs : ["airplay", "bt", "radio"];
const t0 = statusTilMatter({ ...status, inputs });
const navn = String(status.name || process.env.SKJOLD_NAME || "Skjold").slice(0, 32);
const uid = String(status.id || "skjold").replace(/[^a-z0-9-]/gi, "").slice(0, 32) || "skjold";

const node = await ServerNode.create({
  id: "skjold",
  network: { port: MATTER_PORT },
  commissioning: paring(),
  productDescription: { name: navn, deviceType: SpeakerDevice.deviceType },
  basicInformation: {
    vendorName: "Skjold", vendorId: VendorId(0xfff1), nodeLabel: navn, productName: "Skjold høyttaler",
    productLabel: "Høyttaler", productId: 0x8000, serialNumber: uid,
    uniqueId: crypto.createHash("sha256").update("skjold-matter:" + uid).digest("hex").slice(0, 32),
    softwareVersion: 1, softwareVersionString: String(status.version || "1").slice(0, 64), hardwareVersion: 1, hardwareVersionString: "1",
  },
});

const hoyttaler = new Endpoint(SpeakerDevice, {
  id: "hoyttaler",
  onOff: { onOff: t0.hoyttaler.onOff },
  levelControl: { currentLevel: t0.hoyttaler.level, minLevel: 0, maxLevel: 254, onLevel: null },
});
// Flere like bryter-endepunkter må skilles med TagList (Common Number-navnerommet 0x07) – label vises i noen apper.
const Bryter = OnOffPlugInUnitDevice.with(DescriptorServer.with("TagList"));
const tag = (n, label) => ({ tagList: [{ mfgCode: null, namespaceId: 0x07, tag: n, label }] });
const demp = new Endpoint(Bryter, { id: "demp", descriptor: tag(0, "Demp"), onOff: { onOff: t0.demp } });
const fav = Array.from({ length: FAVORITTER }, (_, i) => new Endpoint(Bryter, { id: `favoritt${i + 1}`, descriptor: tag(i + 1, `Favoritt ${i + 1}`), onOff: { onOff: t0.favoritter[i] } }));
// Apple Hjem (og noen andre) støtter ikke Matter-enhetstypen Speaker. En dimbar lampe «Volum» gir glidebryter overalt:
// nivå = volum, av = dempet.
const volum = new Endpoint(DimmableLightDevice.with(DescriptorServer.with("TagList")), {
  id: "volum", descriptor: tag(7, "Volum"),
  onOff: { onOff: t0.volum.onOff },
  levelControl: { currentLevel: Math.max(1, t0.volum.level), minLevel: 1, maxLevel: 254, onLevel: null },
});
const kilde = new Endpoint(ModeSelectDevice, {
  id: "kilde",
  modeSelect: { description: "Kilde", standardNamespace: null, supportedModes: kildeModuser(inputs, status.input_names || {}), currentMode: t0.kilde },
});
for (const e of [hoyttaler, volum, demp, ...fav, kilde]) await node.add(e);

// Matter → daemon. «fraSkjold» stopper ekko når vi selv oppdaterer attributtene.
let fraSkjold = false;
const send = (type, verdi) => { if (fraSkjold) return; const k = hendelseTilKall(type, verdi, inputs); if (k) post(k.sti, k.body); };
hoyttaler.events.onOff.onOff$Changed.on((v) => send("onOff", v));
hoyttaler.events.levelControl.currentLevel$Changed.on((v) => v != null && send("level", v));
demp.events.onOff.onOff$Changed.on((v) => send("demp", v));
volum.events.onOff.onOff$Changed.on((v) => send("volumPa", v));
volum.events.levelControl.currentLevel$Changed.on((v) => v != null && send("volumNivaa", v));
fav.forEach((e, i) => e.events.onOff.onOff$Changed.on((v) => send("favoritt", { n: i + 1, on: v })));
kilde.events.modeSelect.currentMode$Changed.on((v) => send("kilde", v));

// Daemon → Matter
async function oppdater(s) {
  status = s;
  const t = statusTilMatter({ ...s, inputs });
  fraSkjold = true;
  try {
    await hoyttaler.set({ onOff: { onOff: t.hoyttaler.onOff }, levelControl: { currentLevel: t.hoyttaler.level } });
    await demp.set({ onOff: { onOff: t.demp } });
    await volum.set({ onOff: { onOff: t.volum.onOff }, levelControl: { currentLevel: Math.max(1, t.volum.level) } });
    for (let i = 0; i < FAVORITTER; i++) await fav[i].set({ onOff: { onOff: t.favoritter[i] } });
    await kilde.set({ modeSelect: { currentMode: t.kilde } });
  } catch (e) { console.error("oppdater:", e.message); } finally { fraSkjold = false; }
}

async function lytt() {
  for (;;) {
    try {
      const r = await fetch(DAEMON + "/api/events");
      const dec = new TextDecoder();
      let buf = "";
      for await (const chunk of r.body) {
        buf += dec.decode(chunk, { stream: true });
        let i;
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const blokk = buf.slice(0, i); buf = buf.slice(i + 2);
          const data = blokk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5)).join("");
          if (data) { try { await oppdater(JSON.parse(data)); } catch { /* ikke JSON */ } }
        }
      }
    } catch (e) { console.error("SSE:", e.message); }
    await new Promise((r) => setTimeout(r, 3000));
  }
}

function info() {
  const c = node.state.commissioning;
  const fabrics = Object.values(node.state.operationalCredentials?.fabrics || {}).map((f) => ({ label: f.label || "", vendor: f.vendorId }));
  return {
    running: true, commissioned: !!c.commissioned, fabrics,
    qr: c.pairingCodes.qrPairingCode, manual: c.pairingCodes.manualPairingCode,
    tilstand: { pa: hoyttaler.state.onOff.onOff, niva: hoyttaler.state.levelControl.currentLevel, demp: demp.state.onOff.onOff,
      favoritter: fav.map((e) => e.state.onOff.onOff), kilde: kilde.state.modeSelect.currentMode },
    endpoints: ["Høyttaler", "Volum", "Demp", ...fav.map((_, i) => `Favoritt ${i + 1}`), "Kilde"],
  };
}

http.createServer(async (req, res) => {
  const svar = (o, s = 200) => { res.writeHead(s, { "content-type": "application/json" }); res.end(JSON.stringify(o)); };
  try {
    if (req.url === "/status") return svar(info());
    if (req.url === "/reset" && req.method === "POST") {
      svar({ ok: true, restart: true });
      try { fs.unlinkSync(`${DIR}/paring.json`); } catch { /* finnes ikke */ }
      await node.erase();          // glemmer alle paringer; systemd starter tjenesten på nytt med ny paringstilstand
      process.exit(0);
    }
    svar({ error: "ukjent" }, 404);
  } catch (e) { svar({ error: e.message }, 500); }
}).listen(process.env.SKJOLD_MATTER_DRYRUN ? 0 : STATUS_PORT, "127.0.0.1");

if (process.env.SKJOLD_MATTER_DRYRUN) { console.log(JSON.stringify(info())); process.exit(0); }   // test uten nettverk
await node.start();
const i0 = info();
console.log(`Matter klar. Manuell kode ${i0.manual} · QR ${i0.qr} · paret: ${i0.commissioned}`);
lytt();
