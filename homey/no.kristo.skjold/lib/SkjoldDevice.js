'use strict';

const Homey = require('homey');
const http = require('http');

const POLL_MS = 5000;
// Kildene i standardrekkefølge (nøkkel → navn). Eldre daemoner uten "inputs" i status har FALLBACK_INPUTS.
const SOURCE_LABELS = { radio: 'Radio', airplay: 'AirPlay', bt: 'Bluetooth', spotify: 'Spotify', plex: 'Plex', aux: 'AUX 1', aux2: 'AUX 2', usb: 'USB' };
const FALLBACK_INPUTS = ['radio', 'airplay', 'bt', 'aux', 'aux2', 'usb'];
const LEVEL_SOURCES = ['airplay', 'bt', 'usb', 'radio', 'aux', 'aux2', 'spotify', 'plex'];
const NODE_BOARDS = ['node'];   // Skjold Node/Core: ingen AUX/USB, hodetelefonjack, overtemperatur eller USB-switch
const PRODUCTS = ['s1', 'node', 'core', 'touch'];
const LED_MODES = ['press', 'always', 'off'];
// Hvilke produktspesifikke capabilities hvert produkt har (resten er felles eller styres av status, f.eks. usbsw/levels).
const PRODUCT_CAPS = {
  s1: { ki_hp_automute: true, ki_bright: true, ki_led_level: false, ki_led_mode: false },
  node: { ki_hp_automute: false, ki_bright: true, ki_led_level: true, ki_led_mode: true },
  core: { ki_hp_automute: false, ki_bright: false, ki_led_level: false, ki_led_mode: false },
  touch: { ki_hp_automute: false, ki_bright: true, ki_led_level: false, ki_led_mode: false },
};

function statusInputs(st) {
  return Array.isArray(st && st.inputs) && st.inputs.length ? st.inputs.map(String) : FALLBACK_INPUTS.slice();
}
/** s1 | node | core – fra status["product"]; eldre daemoner: board=node → node, ellers s1. */
function productOf(st) {
  if (st && PRODUCTS.includes(st.product)) return st.product;
  return st && NODE_BOARDS.includes(st.board) ? 'node' : 's1';
}
function isNode(st) { return productOf(st) !== 's1'; }
function setting(st, key, def) {
  const v = st && st.settings && typeof st.settings === 'object' ? st.settings[key] : undefined;   // bare endrede nøkler
  return v === undefined || v === null ? def : v;
}

class SkjoldDevice extends Homey.Device {
  /** Produktet driveren er laget for (s1/node/core). null = gammel «pultforsterker»-driver: følg status. */
  static get PRODUCT() { return null; }

  product(st) { return this.constructor.PRODUCT || productOf(st); }

  async onInit() {
    if (this.getClass() !== 'speaker') await this.setClass('speaker').catch(this.error);   // gir «spiller nå»-visning med albumbilde
    for (const cap of ['speaker_prev', 'speaker_next', 'speaker_album', 'speaker_duration', 'speaker_position', 'ki_voice', 'ki_preset', 'ki_auto_input', 'ki_mix', 'ki_voice_profile']) {   // eldre enheter: legg til nye capabilities
      if (!this.hasCapability(cap)) await this.addCapability(cap).catch(this.error);
    }
    this.registerCapabilityListener('onoff', (on) => this.setPower(on));
    this.registerCapabilityListener('volume_set', (v) => this.setVolume(Math.round(v * 100)));
    this.registerCapabilityListener('volume_mute', (m) => this.setMute(m));
    this.registerCapabilityListener('ki_input', (i) => this.setInput(i));
    this.registerCapabilityListener('ki_loudness', (on) => this.setLoudness(on, undefined));
    this.registerCapabilityListener('speaker_playing', (play) => this.transport(play ? 'play' : 'pause'));
    this.registerCapabilityListener('ki_voice', (on) => this.request('POST', '/voice', { on: !!on }).then((st) => this.apply(st)));
    this.registerCapabilityListener('ki_auto_input', (on) => this.request('POST', '/auto_input', { on: !!on }).then((st) => this.apply(st)));
    this.registerCapabilityListener('ki_mix', (on) => this.request('POST', '/mix', { on: !!on }).then((st) => this.apply(st)));
    this.registerCapabilityListener('ki_hp_automute', (on) => this.request('POST', '/hp_automute', { on: !!on }).then((st) => this.apply(st)));
    this.registerCapabilityListener('ki_preset', (n) => this.playPreset(Number(n)));
    this.registerCapabilityListener('ki_usb_pc', (pc) => this.setUsbPc(pc));
    for (const src of LEVEL_SOURCES) {
      this.registerCapabilityListener(`ki_level_${src}`, (v) => this.setLevel(src, Math.round(v)));
    }
    this.registerCapabilityListener('ki_bright', (b) => this.setBright(Number(b)));
    this.registerCapabilityListener('ki_voice_profile', (p) => this.request('POST', '/voice', { profile: p }).then((st) => this.apply(st)));
    this.registerCapabilityListener('speaker_next', () => this.transport('next'));
    this.registerCapabilityListener('speaker_prev', () => this.transport('previous'));
    this.registerCapabilityListener('ki_loudness_level', (lvl) => this.setLoudness(undefined, Math.round(lvl)));
    this.registerCapabilityListener('ki_led_level', (v) => this.setLed(Math.round(v), undefined));
    this.registerCapabilityListener('ki_led_mode', (m) => this.setLed(undefined, m));

    // Følg IP-endringer fra mDNS
    try {
      const result = this.driver.getDiscoveryStrategy().getDiscoveryResult(this.getData().id);
      if (result) {
        this.onDiscoveryAvailable(result);
        result.on('addressChanged', (r) => this.onDiscoveryAddressChanged(r));
      }
    } catch (e) { /* manuell IP i settings brukes */ }

    // Albumbilde (AirPlay) – hentes fra Pi-en når cover-ID endrer seg
    this._cover = null;
    try {
      this._image = await this.homey.images.createImage();
      this._image.setStream(async (stream) => {
        const { host, port } = this.base();
        await new Promise((resolve, reject) => {
          http.get({ host, port, path: '/api/cover', timeout: 4000 }, (res) => {
            if (res.statusCode !== 200) { res.resume(); return reject(new Error('Ingen albumbilde')); }
            res.pipe(stream); res.on('end', resolve);
          }).on('error', reject);
        });
      });
      await this.setAlbumArtImage(this._image);
    } catch (e) { this.error('Albumbilde', e); }

    this._wasPlaying = null;
    this._lastInput = null;
    await this.poll();
    this._timer = this.homey.setInterval(() => this.poll().catch((e) => this.error(e)), POLL_MS);
  }

  onDiscoveryAvailable(result) { this.setSettings({ host: result.address }).catch(() => {}); }
  onDiscoveryAddressChanged(result) { this.setSettings({ host: result.address }).catch(() => {}); }

  onDeleted() { if (this._timer) this.homey.clearInterval(this._timer); }

  base() {
    const { host, port } = this.getSettings();
    return { host, port: port || 8765 };
  }

  request(method, path, body) {
    const { host, port } = this.base();
    return new Promise((resolve, reject) => {
      const data = body ? JSON.stringify(body) : null;
      const req = http.request({ host, port, path: `/api${path}`, method, timeout: 4000,
        headers: data ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {} },
      (res) => {
        let buf = '';
        res.on('data', (c) => { buf += c; });
        res.on('end', () => {
          let json; try { json = JSON.parse(buf); } catch (e) { return reject(new Error(`Ugyldig svar: ${buf}`)); }
          if (res.statusCode >= 400) return reject(new Error(json.error || `HTTP ${res.statusCode}`));
          resolve(json);
        });
      });
      req.on('error', reject);
      req.on('timeout', () => req.destroy(new Error('Tidsavbrudd')));
      if (data) req.write(data);
      req.end();
    });
  }

  async poll() {
    let st;
    try {
      st = await this.request('GET', '/status');
    } catch (e) {
      if (this.getAvailable()) await this.setUnavailable(this.homey.__('unavailable') || 'Ingen kontakt');
      return;
    }
    if (!this.getAvailable()) await this.setAvailable();
    await this.apply(st);
  }

  async setLevel(source, level) {
    return this.apply(await this.request('POST', '/level', { source, level }));
  }

  async setUsbPc(pc) {
    const body = pc === 'toggle' ? { toggle: true } : { pc: Number(pc) };
    return this.apply(await this.request('POST', '/usbsw', body));
  }

  /** Tilpass capabilities til kortet (board/inputs) – kjøres når de endrer seg. */
  async syncBoard(st) {
    const inputs = statusInputs(st);
    const product = this.product(st);
    const key = `${product}|${st.board || ''}|${inputs.join(',')}`;
    if (key === this._boardKey) return;
    this._boardKey = key;
    this._inputs = inputs;
    const node = product !== 's1';
    const want = PRODUCT_CAPS[product] || PRODUCT_CAPS.s1;
    for (const [cap, on] of Object.entries(want)) {
      if (on && !this.hasCapability(cap)) await this.addCapability(cap).catch(this.error);
      if (!on && this.hasCapability(cap)) await this.removeCapability(cap).catch(this.error);
    }
    if (node && this.hasCapability('ki_headphones')) await this.removeCapability('ki_headphones').catch(this.error);
    // Kildevelgeren viser bare kildene kortet har
    if (typeof this.setCapabilityOptions === 'function') {
      const values = inputs.map((id) => ({ id, title: { en: SOURCE_LABELS[id] || id, no: SOURCE_LABELS[id] || id } }));
      await this.setCapabilityOptions('ki_input', { values }).catch(this.error);
    }
  }

  inputList() { return (this._inputs || FALLBACK_INPUTS).map((id) => ({ id, name: SOURCE_LABELS[id] || id })); }

  /** Radiofavoritter (inntil 50): hentes fra /api/presets når lista i status endrer seg, og blir verdiene i ki_preset. */
  async syncPresets(st) {
    const slots = Array.isArray(st.presets) ? st.presets : [];
    const sig = slots.map((p) => `${p && p.n}:${(p && p.title) || ''}`).join('|');
    if (sig === this._presetSig) return;
    this._presetSig = sig;
    let items = slots.filter((p) => p && p.title);
    try {
      const res = await this.request('GET', '/presets');
      const got = Array.isArray(res.items) ? res.items : (res.presets || []).filter(Boolean);
      items = got.filter((p) => p && p.n && p.title);
    } catch (e) { /* eldre daemon uten /api/presets: plassene i status */ }
    this._presets = items.map((p) => ({ n: Number(p.n), title: String(p.title), genre: p.genre || '' }));
    if (this.hasCapability('ki_preset') && typeof this.setCapabilityOptions === 'function' && this._presets.length) {
      const values = this._presets.map((p) => ({ id: String(p.n), title: { en: `${p.n}. ${p.title}`, no: `${p.n}. ${p.title}` } }));
      await this.setCapabilityOptions('ki_preset', { values }).catch(this.error);
    }
  }

  async apply(st) {
    if (!st || typeof st !== 'object') return;
    this._last = st;
    await this.syncBoard(st);
    await this.syncPresets(st);
    const node = this.product(st) !== 's1';
    await this.setCapabilityValue('onoff', !!st.power).catch(this.error);
    await this.setCapabilityValue('speaker_playing', !!st.playing).catch(this.error);
    await this.setCapabilityValue('speaker_track', st.title || '').catch(this.error);
    await this.setCapabilityValue('speaker_artist', st.artist || '').catch(this.error);
    if (this.hasCapability('speaker_album')) await this.setCapabilityValue('speaker_album', st.album || '').catch(this.error);
    if (this.hasCapability('speaker_duration')) await this.setCapabilityValue('speaker_duration', Math.round(st.duration || 0)).catch(this.error);
    if (this.hasCapability('speaker_position')) await this.setCapabilityValue('speaker_position', Math.round(st.position || 0)).catch(this.error);
    await this.setCapabilityValue('volume_set', (st.volume || 0) / 100).catch(this.error);
    await this.setCapabilityValue('volume_mute', !!st.mute).catch(this.error);
    await this.setCapabilityValue('ki_input', st.input || 'airplay').catch(this.error);
    const presetNow = st.preset || (st.radio_now && st.radio_now.n) || 0;
    if (this.hasCapability('ki_preset') && presetNow) await this.setCapabilityValue('ki_preset', String(presetNow)).catch(this.error);
    if (this.hasCapability('ki_auto_input')) await this.setCapabilityValue('ki_auto_input', st.auto_input !== false).catch(this.error);
    if (this.hasCapability('ki_mix')) await this.setCapabilityValue('ki_mix', !!st.mix).catch(this.error);
    if (this.hasCapability('ki_hp_automute')) await this.setCapabilityValue('ki_hp_automute', st.hp_automute !== false).catch(this.error);
    // Hodetelefonjack (hovedkortet): vises bare når daemonen rapporterer den
    if (!node && 'headphones' in st && !this.hasCapability('ki_headphones')) await this.addCapability('ki_headphones').catch(this.error);
    if (!node && this.hasCapability('ki_headphones') && 'headphones' in st) {
      const was = this.getCapabilityValue('ki_headphones');
      await this.setCapabilityValue('ki_headphones', !!st.headphones).catch(this.error);
      if (was !== null && was !== !!st.headphones) {
        await this.homey.flow.getDeviceTriggerCard('ki_headphones_changed').trigger(this, { connected: !!st.headphones }).catch(this.error);
      }
    }
    // USB-switch: vises bare når den er satt opp på Pi-en (KI_AMP_USBSW_PULSE)
    if (st.usbsw && !this.hasCapability('ki_usb_pc')) await this.addCapability('ki_usb_pc').catch(this.error);
    if (!st.usbsw && this.hasCapability('ki_usb_pc')) await this.removeCapability('ki_usb_pc').catch(this.error);
    if (st.usbsw && this.hasCapability('ki_usb_pc')) await this.setCapabilityValue('ki_usb_pc', String(st.usb_pc || 1)).catch(this.error);
    if (this.hasCapability('ki_voice')) await this.setCapabilityValue('ki_voice', st.voice !== false).catch(this.error);
    if (this.hasCapability('ki_voice_profile')) await this.setCapabilityValue('ki_voice_profile', st.voice_profile || 'en').catch(this.error);
    // Nivå per kilde – vises bare når daemonen har miks med nivåer (hovedkortet)
    const inputs = statusInputs(st);
    for (const src of LEVEL_SOURCES) {
      const cap = `ki_level_${src}`; const has = inputs.includes(src) && st.levels && typeof st.levels === 'object' && src in st.levels;
      if (has && !this.hasCapability(cap)) await this.addCapability(cap).catch(this.error);
      if (!has && this.hasCapability(cap)) await this.removeCapability(cap).catch(this.error);
      if (has && this.hasCapability(cap)) await this.setCapabilityValue(cap, Number(st.levels[src])).catch(this.error);
    }
    const bright = st.settings && typeof st.settings === 'object' ? (st.settings.bright ?? 0) : undefined;   // bare endrede nøkler; standard 0 = auto
    if (this.hasCapability('ki_bright') && Number.isInteger(bright)) await this.setCapabilityValue('ki_bright', String(bright)).catch(this.error);
    if (this.hasCapability('ki_led_level')) await this.setCapabilityValue('ki_led_level', Number(setting(st, 'ledLevel', 100))).catch(this.error);
    if (this.hasCapability('ki_led_mode')) {
      let m = setting(st, 'ledMode', 'press'); if (Number.isInteger(m)) m = LED_MODES[m];
      if (LED_MODES.includes(m)) await this.setCapabilityValue('ki_led_mode', m).catch(this.error);
    }
    if (this.hasCapability('ki_loudness')) await this.setCapabilityValue('ki_loudness', !!st.loudness).catch(this.error);
    if (this.hasCapability('ki_loudness_level')) await this.setCapabilityValue('ki_loudness_level', Number(st.loudness_level ?? 0)).catch(this.error);

    if (this._image && (st.cover || '') !== this._cover) {
      this._cover = st.cover || '';
      await this._image.update().catch(() => {});
    }

    if (this._lastInput !== null && this._lastInput !== st.input) {
      await this.homey.flow.getDeviceTriggerCard('ki_input_changed').trigger(this, { input: st.input }).catch(this.error);
    }
    this._lastInput = st.input;

    if (this._wasPlaying !== null && this._wasPlaying !== !!st.playing) {
      const card = this.homey.flow.getDeviceTriggerCard(st.playing ? 'ki_started_playing' : 'ki_stopped_playing');
      await card.trigger(this, st.playing ? { title: st.title || '', artist: st.artist || '' } : {}).catch(this.error);
    }
    this._wasPlaying = !!st.playing;

    // Skjold S1: nattmodus og dobbelttrykk på power
    if ('night' in st) {
      const nightOn = st.night && typeof st.night === 'object' ? !!st.night.on : !!st.night;
      if (!this.hasCapability('night_mode') && this.product(st) === 's1') {
        await this.addCapability('night_mode').catch(this.error);
        this.registerCapabilityListener('night_mode', (on) => this.setNight(on));
      }
      if (this.hasCapability('night_mode')) await this.setCapabilityValue('night_mode', nightOn).catch(this.error);
      if (this._lastNight !== null && this._lastNight !== nightOn) {
        const src = (st.night && st.night.src) || '';
        await this.homey.flow.getDeviceTriggerCard('ki_night_changed').trigger(this, { on: nightOn, src }, { on: nightOn }).catch(this.error);
      }
      this._lastNight = nightOn;
    }
    const ev = st.last_event;
    if (ev && ev.seq !== undefined) {
      if (this._lastEventSeq !== null && ev.seq !== this._lastEventSeq && ev.name === 'power_double_press') {
        await this.homey.flow.getDeviceTriggerCard('ki_power_double').trigger(this, {}).catch(this.error);
      }
      this._lastEventSeq = ev.seq;
    }
  }

  async setPower(on) {
    const st = await this.request('POST', '/power', { on: !!on });
    await this.apply(st);
  }

  async setVolume(v) { await this.apply(await this.request('POST', '/volume', { volume: v })); }
  async setMute(m) { await this.apply(await this.request('POST', '/mute', { mute: !!m })); }
  async playUrl(url, announce = false) {
    const u = String(url || '').trim();
    if (!/^https?:\/\//.test(u)) throw new Error('Adressen må starte med http:// eller https://');
    const r = await this.request('POST', '/play', { url: u, announce: !!announce });
    if (!announce) await this.apply(r);
  }

  async btPair() { await this.apply(await this.request('POST', '/bt', { pairing: true })); }
  async setLoudness(on, level) {
    const body = {}; if (on !== undefined) body.on = !!on; if (level !== undefined) body.level = level;
    await this.apply(await this.request('POST', '/loudness', body));
  }
  async transport(action) { await this.apply(await this.request('POST', '/transport', { action })); }
  async playPreset(n) { await this.apply(await this.request('POST', '/preset', { n })); }
  async savePreset(n) { await this.apply(await this.request('POST', '/preset', { n, save: true })); }
  presetList() { return (this._presets || []).filter((p) => p.title); }

  /** Albumbildet som data-URL (for widgets: dashbordet kjører på https og kan ikke hente http-bilder fra Pi-en). */
  /** Henter et bilde (http/https) og gir det som data-URL, eller '' ved feil. Følger én omdirigering. */
  _fetchImage(url, hop = 0) {
    return new Promise((resolve) => {
      let mod = http; try { if (new URL(url).protocol === 'https:') mod = require('https'); } catch (e) { return resolve(''); }
      const req = mod.get(url, { timeout: 5000 }, (res) => {
        if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location && hop < 2) {
          res.resume(); return resolve(this._fetchImage(new URL(res.headers.location, url).toString(), hop + 1));
        }
        const type = String(res.headers['content-type'] || '');
        if (res.statusCode !== 200 || !type.startsWith('image/')) { res.resume(); return resolve(''); }
        const chunks = []; let n = 0;
        res.on('data', (c) => { n += c.length; if (n > 3e6) { req.destroy(); resolve(''); } else chunks.push(c); });
        res.on('end', () => resolve(`data:${type.split(';')[0]};base64,${Buffer.concat(chunks).toString('base64')}`));
      });
      req.on('error', () => resolve('')); req.on('timeout', () => { req.destroy(); resolve(''); });
    });
  }

  /** Albumbilde/kanallogo som data-URL (dashbordet kjører på https og kan ikke hente http-bilder fra Pi-en selv).
   *  Prøver i rekkefølge: status.cover_url (relativ → Pi-en, full URL → direkte), /api/cover, radio_now.image. */
  async coverDataUrl() {
    const st = this._last || {};
    const rn = st.radio_now || {};
    const key = [st.cover, st.cover_url, rn.image, st.title].join('|');
    if (this._coverCache && this._coverCache.key === key) return this._coverCache.url;
    const { host, port } = this.base();
    const dev = (p) => `http://${host}:${port}${p}`;
    const cands = [];
    if (st.cover_url) cands.push(/^https?:\/\//.test(st.cover_url) ? st.cover_url : dev(st.cover_url.startsWith('/') ? st.cover_url : '/' + st.cover_url));
    if (st.cover) cands.push(dev('/api/cover?v=' + encodeURIComponent(st.cover)));
    if (rn.image && /^https?:\/\//.test(rn.image)) cands.push(rn.image);
    let url = '';
    for (const c of cands) { url = await this._fetchImage(c); if (url) break; }
    this._coverCache = { key, url };
    return url;
  }

  /** Det widgetene trenger, i én pakke. */
  async widgetState() {
    const st = this._last || {};
    const rn = st.radio_now || {};
    return {
      name: this.getName(), product: this.product(st), online: this.getAvailable(),
      power: !!st.power, playing: !!st.playing, input: st.input || '', inputLabel: SOURCE_LABELS[st.input] || st.input || '',
      title: st.title || rn.name || st.station || '', artist: st.artist || rn.now || '', album: st.album || '',
      volume: Number(st.volume || 0), mute: !!st.mute, cover: await this.coverDataUrl(), image: /^https:/.test(rn.image || '') ? rn.image : '',
      inputs: statusInputs(st).map((i) => ({ id: i, label: SOURCE_LABELS[i] || i })),
      preset: st.preset || rn.n || 0, presets: this.presetList().map((p) => ({ n: p.n, title: p.title, genre: p.genre || '', image: p.image || p.icon || '' })),
    };
  }

  /** Handling fra en widget. */
  async widgetAction(a) {
    switch (a && a.type) {
      case 'toggle': return this.transport(this._last && this._last.playing ? 'pause' : 'play');
      case 'next': return this.transport('next');
      case 'prev': return this.transport('previous');
      case 'volume': return this.setVolume(Math.max(0, Math.min(100, Math.round(Number(a.value) || 0))));
      case 'mute': return this.setMute(!(this._last && this._last.mute));
      case 'power': return this.togglePower();
      case 'preset': return this.playPreset(Number(a.n));
      case 'input': return this.setInput(String(a.input));
      default: throw new Error('Ukjent handling');
    }
  }

  /** LED-ringene (Skjold Node): lysstyrke 0–100 og/eller modus press|always|off. */
  async setLed(level, mode) {
    const patch = {}; if (level !== undefined) patch.ledLevel = level; if (mode !== undefined) patch.ledMode = mode;
    const res = await this.request('POST', '/settings', patch);
    if (res && res.settings) await this.apply({ ...(this._last || {}), settings: res.settings });
  }
  async setInput(i) { await this.apply(await this.request('POST', '/input', { input: i })); }

  async setBright(b) {
    const res = await this.request('POST', '/settings', { bright: b });
    if (this.hasCapability('ki_bright') && res.settings) await this.setCapabilityValue('ki_bright', String(res.settings.bright)).catch(this.error);
  }

  /** Start Pi-en på nytt (eller slå den av). Daemonen svarer med status (rebooting=true) før den går ned. */
  async reboot(poweroff = false) { await this.apply(await this.request('POST', '/reboot', { poweroff: !!poweroff })); }

  async togglePower() {
    const st = await this.request('POST', '/toggle');
    await this.apply(st);
  }
}

SkjoldDevice.productOf = productOf;
SkjoldDevice.PRODUCT_CAPS = PRODUCT_CAPS;
module.exports = SkjoldDevice;
