'use strict';

const Homey = require('homey');
const http = require('http');

const POLL_MS = 5000;

class PultforsterkerDevice extends Homey.Device {
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
    this.registerCapabilityListener('ki_preset', (n) => this.playPreset(Number(n)));
    this.registerCapabilityListener('ki_usb_pc', (pc) => this.setUsbPc(pc));
    this.registerCapabilityListener('ki_voice_profile', (p) => this.request('POST', '/voice', { profile: p }).then((st) => this.apply(st)));
    this.registerCapabilityListener('speaker_next', () => this.transport('next'));
    this.registerCapabilityListener('speaker_prev', () => this.transport('previous'));
    this.registerCapabilityListener('ki_loudness_level', (lvl) => this.setLoudness(undefined, Math.round(lvl)));

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

  async setUsbPc(pc) {
    const body = pc === 'toggle' ? { toggle: true } : { pc: Number(pc) };
    return this.apply(await this.request('POST', '/usbsw', body));
  }

  async apply(st) {
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
    if (this.hasCapability('ki_preset') && st.preset) await this.setCapabilityValue('ki_preset', String(st.preset)).catch(this.error);
    this._presets = st.presets || [];
    if (this.hasCapability('ki_auto_input')) await this.setCapabilityValue('ki_auto_input', st.auto_input !== false).catch(this.error);
    if (this.hasCapability('ki_mix')) await this.setCapabilityValue('ki_mix', !!st.mix).catch(this.error);
    // USB-switch: vises bare når den er satt opp på Pi-en (KI_AMP_USBSW_PULSE)
    if (st.usbsw && !this.hasCapability('ki_usb_pc')) await this.addCapability('ki_usb_pc').catch(this.error);
    if (!st.usbsw && this.hasCapability('ki_usb_pc')) await this.removeCapability('ki_usb_pc').catch(this.error);
    if (st.usbsw && this.hasCapability('ki_usb_pc')) await this.setCapabilityValue('ki_usb_pc', String(st.usb_pc || 1)).catch(this.error);
    if (this.hasCapability('ki_voice')) await this.setCapabilityValue('ki_voice', st.voice !== false).catch(this.error);
    if (this.hasCapability('ki_voice_profile')) await this.setCapabilityValue('ki_voice_profile', st.voice_profile || 'en').catch(this.error);
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
  }

  async setPower(on) {
    const st = await this.request('POST', '/power', { on: !!on });
    await this.apply(st);
  }

  async setVolume(v) { await this.apply(await this.request('POST', '/volume', { volume: v })); }
  async setMute(m) { await this.apply(await this.request('POST', '/mute', { mute: !!m })); }
  async btPair() { await this.apply(await this.request('POST', '/bt', { pairing: true })); }
  async setLoudness(on, level) {
    const body = {}; if (on !== undefined) body.on = !!on; if (level !== undefined) body.level = level;
    await this.apply(await this.request('POST', '/loudness', body));
  }
  async transport(action) { await this.apply(await this.request('POST', '/transport', { action })); }
  async playPreset(n) { await this.apply(await this.request('POST', '/preset', { n })); }
  async savePreset(n) { await this.apply(await this.request('POST', '/preset', { n, save: true })); }
  presetList() { return (this._presets || []).filter((p) => p.title); }
  async setInput(i) { await this.apply(await this.request('POST', '/input', { input: i })); }

  async togglePower() {
    const st = await this.request('POST', '/toggle');
    await this.apply(st);
  }
}

module.exports = PultforsterkerDevice;
