'use strict';
// Driverne per produkt (Skjold S1 / Node / Core): capabilities, paring via mDNS (filtrert på TXT product) og manuell IP.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { createMockDaemon } = require('./mock-daemon');
const Homey = require('homey');
const App = require('../app');
const S1Device = require('../drivers/s1/device');
const NodeDevice = require('../drivers/node/device');
const CoreDevice = require('../drivers/core/device');
const S1Driver = require('../drivers/s1/driver');
const NodeDriver = require('../drivers/node/driver');
const CoreDriver = require('../drivers/core/driver');
const LegacyDriver = require('../drivers/pultforsterker/driver');
const appJson = require('../app.json');

const daemons = {};
const ports = {};
const PRODUCT_STATE = {
  s1: { product: 's1', board: 'main', name: 'Skjold S1', id: 'skjold-s1', inputs: ['radio', 'airplay', 'bt', 'aux', 'aux2', 'usb', 'spotify'], headphones: false },
  node: { product: 'node', board: 'node', name: 'Skjold Node', id: 'skjold-node', inputs: ['radio', 'airplay', 'bt', 'spotify'], settings: { bright: 0 } },
  core: { product: 'core', board: 'node', name: 'Skjold Core', id: 'skjold-core', inputs: ['radio', 'airplay', 'bt', 'spotify', 'plex'], settings: {} },
};
before(async () => {
  for (const p of Object.keys(PRODUCT_STATE)) {
    daemons[p] = createMockDaemon(); Object.assign(daemons[p].state, PRODUCT_STATE[p], { presets_api: true });
    daemons[p].state.presets = Array.from({ length: 8 }, (_, i) => ({ n: i + 1, title: `Kanal ${i + 1}` }));
    ports[p] = await daemons[p].start();
  }
  daemons.old = createMockDaemon(); ports.old = await daemons.old.start();   // eldre daemon: uten product/board
});
after(async () => { for (const d of Object.values(daemons)) await d.stop(); });

function driverCaps(id) { return appJson.drivers.find((d) => d.id === id).capabilities.slice(); }

const DEV = { s1: S1Device, node: NodeDevice, core: CoreDevice };
for (const p of ['s1', 'node', 'core']) {
  test(`${p}: capabilities fra app.json + status, favoritter fra /api/presets`, async () => {
    const homey = new Homey.HomeyCtx(); const app = new App({ homey }); await app.onInit();
    const d = new DEV[p]({ homey, settings: { host: '127.0.0.1', port: ports[p] }, capabilities: driverCaps(p) });
    const opts = {}; d.setCapabilityOptions = async (c, o) => { opts[c] = o; };
    await d.onInit(); d.onDeleted();
    const has = (c) => d.hasCapability(c);
    assert.equal(has('ki_hp_automute'), p === 's1');
    assert.equal(has('ki_headphones'), p === 's1');
    assert.equal(has('ki_bright'), p !== 'core');
    assert.equal(has('ki_led_level'), p === 'node'); assert.equal(has('ki_led_mode'), p === 'node');
    assert.deepEqual(opts.ki_input.values.map((v) => v.id), PRODUCT_STATE[p].inputs);
    assert.equal(opts.ki_preset.values.length, 8); assert.equal(opts.ki_preset.values[7].title.en, '8. Kanal 8');
    const ac = await homey.flow.cards.ki_play_preset.autocomplete('kanal 8', { device: d });
    assert.deepEqual(ac, [{ id: '8', name: '8. Kanal 8' }]);
    await d.triggerCapability('ki_preset', '8'); assert.equal(daemons[p].state.preset, 8); assert.equal(d.getCapabilityValue('ki_preset'), '8');
    if (p === 'node') {
      assert.equal(d.getCapabilityValue('ki_led_level'), 100); assert.equal(d.getCapabilityValue('ki_led_mode'), 'press');
      await d.triggerCapability('ki_led_level', 42); assert.equal(daemons.node.state.settings.ledLevel, 42); assert.equal(d.getCapabilityValue('ki_led_level'), 42);
      await d.triggerCapability('ki_led_mode', 'always'); assert.equal(d.getCapabilityValue('ki_led_mode'), 'always');
      await homey.flow.cards.ki_set_led.run({ device: d, level: 10, mode: 'off' });
      assert.deepEqual(daemons.node.calls.at(-1).body, { ledLevel: 10, ledMode: 'off' }); assert.equal(d.getCapabilityValue('ki_led_mode'), 'off');
    }
  });
}

test('gammel driver: produktet følger status (eldre daemon → S1-oppsett)', async () => {
  const Legacy = require('../drivers/pultforsterker/device');
  const d = new Legacy({ settings: { host: '127.0.0.1', port: ports.core }, capabilities: driverCaps('pultforsterker').concat('ki_hp_automute') });
  await d.onInit(); d.onDeleted();
  assert.equal(d.hasCapability('ki_hp_automute'), false); assert.equal(d.hasCapability('ki_bright'), false);
});

function fakeDriver(Cls, results) {
  const drv = new Cls({});
  drv.getDiscoveryStrategy = () => ({ getDiscoveryResults: () => results });
  return drv;
}
function fakeSession() {
  const h = {}; return { setHandler(ev, fn) { h[ev] = fn; }, emit: (ev, data) => h[ev](data) };
}

test('paring: mDNS filtreres på TXT product, eldre daemon uten product spørres om /api/status', async () => {
  const results = {
    a: { id: 'a', address: '127.0.0.1', port: ports.s1, txt: { id: 'skjold-s1', name: 'Stue', product: 's1' } },
    b: { id: 'b', address: '127.0.0.1', port: ports.node, txt: { id: 'skjold-node', name: 'Kjøkken', product: 'node' } },
    c: { id: 'c', address: '127.0.0.1', port: ports.core, txt: { id: 'skjold-core' } },   // uten product
  };
  for (const [Cls, want] of [[S1Driver, ['skjold-s1']], [NodeDriver, ['skjold-node']], [CoreDriver, ['skjold-core']], [LegacyDriver, ['skjold-core', 'skjold-node', 'skjold-s1']]]) {
    const s = fakeSession(); await fakeDriver(Cls, results).onPair(s);
    const list = await s.emit('list_devices');
    assert.deepEqual(list.map((x) => x.data.id).sort(), want, Cls.name);
  }
  const s = fakeSession(); await fakeDriver(NodeDriver, results).onPair(s);
  const [dev] = await s.emit('list_devices');
  assert.deepEqual(dev, { name: 'Kjøkken', data: { id: 'skjold-node' }, settings: { host: '127.0.0.1', port: ports.node }, store: { product: 'node' } });
});

test('paring: manuell IP validerer /api/status og produktet', async () => {
  const s = fakeSession(); await fakeDriver(CoreDriver, {}).onPair(s);
  const dev = await s.emit('manual', { host: ' 127.0.0.1 ', port: String(ports.core) });
  assert.deepEqual(dev, { name: 'Skjold Core', data: { id: 'skjold-core' }, settings: { host: '127.0.0.1', port: ports.core }, store: { product: 'core' } });
  assert.equal((await s.emit('manual', { host: `http://127.0.0.1:${ports.core}/` })).settings.port, ports.core);
  await assert.rejects(s.emit('manual', { host: '127.0.0.1', port: ports.s1 }), /Skjold S1/);
  await assert.rejects(s.emit('manual', { host: '127.0.0.1', port: 1 }), /127\.0\.0\.1:1/);
  await assert.rejects(s.emit('manual', { host: '' }));
  const s1 = fakeSession(); await fakeDriver(S1Driver, {}).onPair(s1);
  assert.equal((await s1.emit('manual', { host: '127.0.0.1', port: ports.old })).store.product, 's1');   // eldre daemon = S1
});

test('app.json: tre produktdrivere med egen paring, gammel driver deprecated, flytkort filtrert', () => {
  const ids = appJson.drivers.map((d) => d.id);
  assert.deepEqual(ids, ['s1', 'node', 'core', 'pultforsterker']);
  assert.equal(appJson.drivers.find((d) => d.id === 'pultforsterker').deprecated, true);
  for (const id of ['s1', 'node', 'core']) {
    const d = appJson.drivers.find((x) => x.id === id);
    assert.deepEqual(d.pair.map((v) => v.id), ['start', 'list_devices', 'add_devices']);
    assert.ok(require('fs').existsSync(`${__dirname}/../drivers/${id}/pair/start.html`));
    for (const k of ['small', 'large', 'xlarge']) assert.ok(require('fs').existsSync(`${__dirname}/..${d.images[k]}`), d.images[k]);
    for (const c of d.capabilities) assert.ok(c.startsWith('ki_') ? appJson.capabilities[c] : true, c);
  }
  const card = (id) => Object.values(appJson.flow).flat().find((c) => c.id === id).args[0].filter;
  assert.equal(card('ki_set_led'), 'driver_id=pultforsterker|node');
  assert.equal(card('ki_usb_pc'), 'driver_id=pultforsterker|s1');
  assert.equal(card('ki_toggle'), 'driver_id=pultforsterker|s1|node|core');
});
