'use strict';
// Kjør: npm test   (NODE_PATH peker på stubben av Homey SDK)
const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const { createMockDaemon } = require('./mock-daemon');
const Homey = require('homey');
const Device = require('../drivers/pultforsterker/device');
const App = require('../app');

const CAPS = ['onoff', 'speaker_prev', 'speaker_playing', 'speaker_next', 'ki_voice', 'ki_preset', 'ki_auto_input', 'ki_mix', 'speaker_track', 'speaker_artist', 'volume_set', 'volume_mute', 'ki_input', 'ki_loudness', 'ki_loudness_level'];
let daemon, port;
before(async () => { daemon = createMockDaemon(); port = await daemon.start(); });
after(async () => { await daemon.stop(); });

function makeDevice(homey) {
  const d = new Device({ homey, settings: { host: '127.0.0.1', port }, capabilities: CAPS });
  return d;
}
beforeEach(() => { Object.assign(daemon.state, { power: true, input: 'airplay', volume: 30, mute: false, loudness: true, loudness_level: 5, playing: false, paused: false, cover: '', voice: true, preset: 0, title: '', artist: '' }); daemon.calls.length = 0; });

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

test('avspillingskontroll: spill/pause, neste, forrige og flytkort', async () => {
  const homey = new Homey.HomeyCtx(); const app = new App({ homey }); await app.onInit();
  const d = makeDevice(homey); await d.onInit(); d.onDeleted();
  await d.triggerCapability('speaker_playing', true);
  assert.deepEqual(daemon.calls.at(-1).body, { action: 'play' }); assert.equal(d.getCapabilityValue('speaker_playing'), true);
  await d.triggerCapability('speaker_playing', false); assert.equal(daemon.state.paused, true);
  await d.triggerCapability('speaker_next', true); assert.equal(daemon.state.title, 'Neste låt');
  await d.triggerCapability('speaker_prev', true); assert.equal(daemon.state.title, 'Forrige låt');
  await homey.flow.cards.ki_transport.run({ device: d, action: 'playpause' }); assert.equal(daemon.calls.at(-1).body.action, 'playpause');
  daemon.state.input = 'aux';
  await assert.rejects(d.triggerCapability('speaker_next', true), /ingen avspilling/);
});

test('eldre enhet uten neste/forrige får capabilities lagt til', async () => {
  const d = new Device({ settings: { host: '127.0.0.1', port }, capabilities: CAPS.filter((c) => !['speaker_prev', 'speaker_next'].includes(c)) });
  await d.onInit(); d.onDeleted();
  assert.ok(d.hasCapability('speaker_next') && d.hasCapability('speaker_prev'));
});

test('albumbilde: oppdateres når cover-ID endrer seg og strømmes fra /api/cover', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  assert.ok(d.albumArt, 'albumbilde satt på enheten');
  const before = d.albumArt.updates;
  daemon.state.cover = 'abc123'; await d.poll(); assert.equal(d.albumArt.updates, before + 1);
  await d.poll(); assert.equal(d.albumArt.updates, before + 1);   // samme bilde – ingen ny henting
  const { PassThrough } = require('stream'); const out = new PassThrough(); const chunks = [];
  out.on('data', (c) => chunks.push(c));
  await d.albumArt.streamFn(out);
  assert.equal(Buffer.concat(chunks).toString('hex'), '89504e470d0a1a0a');
});

test('talemeldinger av/på', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  assert.equal(d.getCapabilityValue('ki_voice'), true);
  await d.triggerCapability('ki_voice', false);
  assert.deepEqual(daemon.calls.at(-1).body, { on: false }); assert.equal(d.getCapabilityValue('ki_voice'), false);
});

test('vises som høyttaler med album, varighet og posisjon', async () => {
  const d = makeDevice(); Object.assign(daemon.state, { playing: true, title: 'Midnight City', artist: 'M83', album: 'Hurry Up, We\'re Dreaming', duration: 243.4, position: 61.7 });
  await d.onInit(); d.onDeleted();
  assert.equal(d.getClass(), 'speaker');
  assert.equal(d.getCapabilityValue('speaker_album'), 'Hurry Up, We\'re Dreaming');
  assert.equal(d.getCapabilityValue('speaker_duration'), 243);
  assert.equal(d.getCapabilityValue('speaker_position'), 62);
});

test('radio: kanal fra picker og flytkort med autocomplete, lagre kanal', async () => {
  const homey = new Homey.HomeyCtx(); const app = new App({ homey }); await app.onInit();
  const d = makeDevice(homey); await d.onInit(); d.onDeleted();
  await d.triggerCapability('ki_preset', '2');
  assert.deepEqual(daemon.calls.at(-1).body, { n: 2 }); assert.equal(d.getCapabilityValue('ki_input'), 'radio'); assert.equal(d.getCapabilityValue('ki_preset'), '2');
  const ac = await homey.flow.cards.ki_play_preset.autocomplete('p1', { device: d });
  assert.deepEqual(ac, [{ id: '1', name: '1. NRK P1' }]);
  await homey.flow.cards.ki_play_preset.run({ device: d, preset: { id: '1' } }); assert.equal(daemon.state.preset, 1);
  await assert.rejects(d.playPreset(4), /ikke lagret/);
  daemon.state.title = 'P13'; await homey.flow.cards.ki_save_preset.run({ device: d, n: '4' });
  assert.equal(daemon.state.presets[3].title, 'P13');
});

test('automatisk kildebytte av/på', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  assert.equal(d.getCapabilityValue('ki_auto_input'), true);
  await d.triggerCapability('ki_auto_input', false);
  assert.deepEqual(daemon.calls.at(-1), { method: 'POST', path: '/api/auto_input', body: { on: false } });
  assert.equal(d.getCapabilityValue('ki_auto_input'), false);
});

test('miks digitale kilder av/på', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  assert.equal(d.getCapabilityValue('ki_mix'), false);
  await d.triggerCapability('ki_mix', true);
  assert.deepEqual(daemon.calls.at(-1), { method: 'POST', path: '/api/mix', body: { on: true } });
  assert.equal(d.getCapabilityValue('ki_mix'), true);
});

test('USB-switch vises bare når den er satt opp, og bytter PC', async () => {
  const d = makeDevice(); await d.onInit(); d.onDeleted();
  assert.equal(d.hasCapability('ki_usb_pc'), false);
  daemon.state.usbsw = true; await d.poll();
  assert.equal(d.hasCapability('ki_usb_pc'), true);
  assert.equal(d.getCapabilityValue('ki_usb_pc'), '1');
  await d.triggerCapability('ki_usb_pc', '2');
  assert.deepEqual(daemon.calls.at(-1), { method: 'POST', path: '/api/usbsw', body: { pc: 2 } });
  assert.equal(d.getCapabilityValue('ki_usb_pc'), '2');
  await d.setUsbPc('toggle'); assert.equal(d.getCapabilityValue('ki_usb_pc'), '1');
  daemon.state.usbsw = false; await d.poll();
  assert.equal(d.hasCapability('ki_usb_pc'), false);
});
