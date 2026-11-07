'use strict';
// Tilbehør (Skjold Røst, Kassett, Hjul): paring via Skjold-verten og capabilities fra /api/rost, /api/nfc og /api/hjul.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const Homey = require('homey');
const App = require('../app');
const RostDevice = require('../drivers/rost/device');
const KassettDevice = require('../drivers/kassett/device');
const HjulDevice = require('../drivers/hjul/device');
const RostDriver = require('../drivers/rost/driver');
const appJson = require('../app.json');

const st = {
  rost: { lyrion: true, minis: [{ id: 'aa:bb', name: 'Skjold Røst bad', connected: true, power: true, playing: true, volume: 40, synced: false }] },
  nfc: { cards: [{ uid: '04A1', navn: 'NRK Jazz' }], active: '', last: { uid: '', t: 0 } },
  spoler: { på: true },
  hjul: { rom: ['Dette rommet', 'Kjøkken'], enheter: { 'hjul-1': { navn: 'Stuehjul', batteri: 77, sist: 100, rom: 'Dette rommet' } } },
};
const posts = [];
let srv; let port;
before(async () => {
  srv = http.createServer((req, res) => {
    let b = ''; req.on('data', (c) => { b += c; });
    req.on('end', () => {
      const body = b ? JSON.parse(b) : {};
      if (req.method === 'POST') posts.push([req.url, body]);
      const send = (o) => { res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(o)); };
      if (req.url === '/api/rost') {
        if (req.method === 'POST' && body.action === 'volume') st.rost.minis[0].volume = body.value;
        if (req.method === 'POST' && body.action === 'sync') st.rost.minis[0].synced = true;
        return send(st.rost);
      }
      if (req.url === '/api/nfc') return send(st.nfc);
      if (req.url === '/api/nfc/spoler') { if (req.method === 'POST') st.spoler.på = body.på; return send(st.spoler); }
      if (req.url === '/api/nfc/scan') { st.nfc.active = body.uid; st.nfc.last = { uid: body.uid, t: 200, known: true, navn: 'NRK Jazz' }; return send({ known: true }); }
      if (req.url === '/api/hjul') return send(st.hjul);
      res.writeHead(404); res.end('{}');
    });
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r)); port = srv.address().port;
});
after(() => srv.close());

const caps = (id) => appJson.drivers.find((d) => d.id === id).capabilities.slice();
const mk = async (Dev, id, acc, homey) => {
  const d = new Dev({ homey, data: { id: `${id}:x:${acc}`, acc }, settings: { host: '127.0.0.1', port }, capabilities: caps(id) });
  d.setCapabilityOptions = async () => {};
  await d.onInit(); d.onDeleted(); return d;
};

test('app.json: tre nye drivere med bilder og ikon', () => {
  for (const id of ['rost', 'kassett', 'hjul']) {
    const d = appJson.drivers.find((x) => x.id === id);
    assert.ok(d, id); assert.equal(d.images.large, `/drivers/${id}/assets/images/large.png`);
  }
});

test('Røst: av/på, volum og synk', async () => {
  const homey = new Homey.HomeyCtx(); await new App({ homey }).onInit();
  const d = await mk(RostDevice, 'rost', 'aa:bb', homey);
  assert.equal(d.getCapabilityValue('onoff'), true); assert.equal(d.getCapabilityValue('volume_set'), 0.4);
  await d.triggerCapability('volume_set', 0.65); assert.equal(d.getCapabilityValue('volume_set'), 0.65);
  await d.triggerCapability('ki_rost_synced', true); assert.equal(d.getCapabilityValue('ki_rost_synced'), true);
  await homey.flow.cards.ki_rost_buttons.run({ device: d, b1: 1, b2: 2, b3: 0, b4: 4 });
  assert.deepEqual(posts.at(-1)[1], { id: 'aa:bb', action: 'presets', value: [1, 2, 0, 4] });
});

test('Kassett: spill fra flyt gir «satt inn»-trigger og viser kassetten', async () => {
  const homey = new Homey.HomeyCtx(); await new App({ homey }).onInit();
  const d = await mk(KassettDevice, 'kassett', 'spiller', homey);
  assert.equal(d.getCapabilityValue('ki_kassett'), 'kassett.none');
  const ac = await homey.flow.cards.ki_kassett_play.autocomplete('jazz', { device: d });
  assert.deepEqual(ac, [{ id: '04A1', name: 'NRK Jazz' }]);
  await homey.flow.cards.ki_kassett_play.run({ device: d, kassett: ac[0] });
  assert.equal(d.getCapabilityValue('ki_kassett'), 'NRK Jazz');
  assert.equal(homey.flow.cards.ki_kassett_inserted.triggered.at(-1).tokens.navn, 'NRK Jazz');
});

test('Hjul: batteri, rom og «brukt»-trigger', async () => {
  const homey = new Homey.HomeyCtx(); await new App({ homey }).onInit();
  const d = await mk(HjulDevice, 'hjul', 'hjul-1', homey);
  assert.equal(d.getCapabilityValue('measure_battery'), 77); assert.equal(d.getCapabilityValue('ki_hjul_room'), 'Dette rommet');
  st.hjul.enheter['hjul-1'].sist = 300; await d.refresh();
  assert.equal(homey.flow.cards.ki_hjul_used.triggered.length, 1);
});

test('paring: tilbehør hentes fra Skjold-verter Homey kjenner', async () => {
  const homey = new Homey.HomeyCtx();
  homey.drivers = { getDriver: (id) => ({ getDevices: () => (id === 's1' ? [{ getSettings: () => ({ host: '127.0.0.1', port }), getName: () => 'Stue' }] : []) }) };
  const drv = new RostDriver({ homey }); drv.getDiscoveryStrategy = () => ({ getDiscoveryResults: () => ({}) });
  const list = await drv.onPairListDevices();
  assert.equal(list.length, 1); assert.equal(list[0].name, 'Skjold Røst bad'); assert.equal(list[0].data.acc, 'aa:bb');
});
