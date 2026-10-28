'use strict';
// Kjør: npm test   (NODE_PATH peker på stubben av Homey SDK)
const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const { createMockDaemon } = require('./mock-daemon');
const Homey = require('homey');
const Device = require('../drivers/pultforsterker/device');
const App = require('../app');

const CAPS = ['onoff', 'speaker_playing', 'speaker_track', 'speaker_artist', 'volume_set', 'volume_mute', 'ki_input', 'ki_loudness', 'ki_loudness_level'];
let daemon, port;
before(async () => { daemon = createMockDaemon(); port = await daemon.start(); });
after(async () => { await daemon.stop(); });

function makeDevice(homey) {
  const d = new Device({ homey, settings: { host: '127.0.0.1', port }, capabilities: CAPS });
  return d;
}
beforeEach(() => { Object.assign(daemon.state, { power: true, input: 'airplay', volume: 30, mute: false, loudness: true, loudness_level: 5, playing: false, title: '', artist: '' }); daemon.calls.length = 0; });

test('onInit henter status og setter capabilities', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  assert.equal(d.getCapabilityValue('onoff'), true);
  assert.equal(d.getCapabilityValue('volume_set'), 0.3);
  assert.equal(d.getCapabilityValue('ki_input'), 'airplay');
  assert.equal(d.getCapabilityValue('ki_loudness'), true);
  assert.equal(d.getCapabilityValue('ki_loudness_level'), 5);
  assert.equal(d.getAvailable(), true);
});

test('volum fra Homey (0–1) blir 0–100 mot API-et', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  await d.triggerCapability('volume_set', 0.42);
  assert.deepEqual(daemon.calls.at(-1), { method: 'POST', path: '/api/volume', body: { volume: 42 } });
  assert.equal(daemon.state.volume, 42);
  assert.equal(d.getCapabilityValue('volume_set'), 0.42);
});

test('av/på, mute, kilde og loudness', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  await d.triggerCapability('onoff', false); assert.equal(daemon.state.power, false); assert.equal(d.getCapabilityValue('onoff'), false);
  await d.triggerCapability('volume_mute', true); assert.equal(daemon.state.mute, true);
  await d.triggerCapability('ki_input', 'usb'); assert.equal(daemon.state.input, 'usb'); assert.equal(d.getCapabilityValue('ki_input'), 'usb');
  await d.triggerCapability('ki_loudness', false); assert.equal(daemon.state.loudness, false);
  await d.triggerCapability('ki_loudness_level', 7.6); assert.equal(daemon.state.loudness_level, 8);
});

test('ugyldig kilde gir feil fra API-et', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  await assert.rejects(d.triggerCapability('ki_input', 'tape'));
});

test('flytkort: trigger ved kildebytte og avspilling start/stopp', async () => {
  const homey = new Homey.HomeyCtx(); const d = makeDevice(homey); await d.onInit(); d.onDeleted();
  daemon.state.input = 'bt'; await d.poll();
  assert.deepEqual(homey.flow.cards.ki_input_changed.triggered[0].tokens, { input: 'bt' });
  daemon.state.playing = true; daemon.state.title = 'Teardrop'; daemon.state.artist = 'Massive Attack'; await d.poll();
  assert.deepEqual(homey.flow.cards.ki_started_playing.triggered[0].tokens, { title: 'Teardrop', artist: 'Massive Attack' });
  assert.equal(d.getCapabilityValue('speaker_track'), 'Teardrop');
  daemon.state.playing = false; await d.poll();
  assert.equal(homey.flow.cards.ki_stopped_playing.triggered.length, 1);
  await d.poll(); // ingen endring → ingen nye triggere
  assert.equal(homey.flow.cards.ki_stopped_playing.triggered.length, 1);
});

test('app.js: betingelser og handlinger', async () => {
  const homey = new Homey.HomeyCtx(); const app = new App({ homey }); await app.onInit();
  const d = makeDevice(homey); await d.onInit(); d.onDeleted();
  assert.equal(await homey.flow.cards.ki_is_playing.run({ device: d }), false);
  assert.equal(await homey.flow.cards.ki_input_is.run({ device: d, input: 'airplay' }), true);
  await homey.flow.cards.ki_set_input.run({ device: d, input: 'aux' }); assert.equal(daemon.state.input, 'aux');
  await homey.flow.cards.ki_toggle.run({ device: d }); assert.equal(daemon.state.power, false);
  await homey.flow.cards.ki_bt_pair.run({ device: d }); assert.equal(daemon.state.bt_pairing, true);
  await homey.flow.cards.ki_set_loudness.run({ device: d, on: 'on', level: 3 }); assert.equal(daemon.state.loudness_level, 3);
});

test('mister kontakt → utilgjengelig, får kontakt → tilgjengelig', async () => {
  const d = new Device({ settings: { host: '127.0.0.1', port: 1 }, capabilities: CAPS }); // ingen lytter på port 1
  await d.onInit(); d.onDeleted();
  assert.equal(d.getAvailable(), false);
  d._settings.port = port; await d.poll();
  assert.equal(d.getAvailable(), true);
});

test('mDNS-oppdagelse oppdaterer host i settings', async () => {
  const result = Object.assign(new (require('events').EventEmitter)(), { address: '10.69.1.50' });
  const driver = { getDiscoveryStrategy() { return { getDiscoveryResult() { return result; } }; } };
  const d = new Device({ driver, settings: { host: '127.0.0.1', port }, capabilities: CAPS });
  d.request = async () => daemon.state; // ikke kall 10.69.1.50
  await d.onInit(); d.onDeleted();
  assert.equal(d.getSettings().host, '10.69.1.50');
  result.emit('addressChanged', { address: '10.69.1.51' });
  await new Promise((r) => setImmediate(r));
  assert.equal(d.getSettings().host, '10.69.1.51');
});
