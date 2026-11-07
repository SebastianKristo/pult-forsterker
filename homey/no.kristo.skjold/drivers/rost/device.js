'use strict';
// Skjold Røst: liten høyttaler (ESP32-S3 med squeezelite-esp32) som spiller i Lyrion. Styres via Skjold (/api/rost).
const { AccessoryDevice } = require('../../lib/SkjoldAccessory');

class RostDevice extends AccessoryDevice {
  async onInit() {
    this.registerCapabilityListener('onoff', (v) => this.act('power', !!v));
    this.registerCapabilityListener('volume_set', (v) => this.act('volume', Math.round(Number(v) * 100)));
    this.registerCapabilityListener('ki_rost_synced', (v) => this.act(v ? 'sync' : 'unsync'));
    await super.onInit();
  }

  async act(action, value) {
    const r = await this.request('POST', '/rost', { id: this.acc, action, value });
    await this.apply(r);
  }

  /** Legg Skjolds radiofavoritter på høyttalerens knapper 1–4 (liste med favorittnumre, 0 = tom). */
  async setButtons(picks) { await this.act('presets', picks); }

  async update() { await this.apply(await this.request('GET', '/rost')); }

  async apply(r) {
    const m = (r.minis || []).find((x) => String(x.id).toLowerCase() === String(this.acc).toLowerCase());
    if (!m) throw new Error('Røst-høyttaleren finnes ikke i Lyrion');
    if (!m.connected) throw new Error('Røst-høyttaleren er ikke tilkoblet');
    await this.setIf('onoff', !!m.power);
    await this.setIf('speaker_playing', !!m.playing);
    await this.setIf('ki_rost_synced', !!m.synced);
    if (typeof m.volume === 'number') await this.setIf('volume_set', m.volume / 100);
  }
}
module.exports = RostDevice;
