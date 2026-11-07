'use strict';
// Skjold Kassett: NFC-kassettspiller. Viser hvilken kassett som står i, og trigger flyt når en kassett settes inn.
const { AccessoryDevice } = require('../../lib/SkjoldAccessory');

class KassettDevice extends AccessoryDevice {
  async onInit() {
    this.registerCapabilityListener('ki_spoler', (v) => this.request('POST', '/nfc/spoler', { på: !!v }));
    this._lastT = null;
    await super.onInit();
  }

  cards() { return this._cards || []; }

  /** Spill en kassett som om den ble satt i spilleren. */
  async play(uid) {
    await this.request('POST', '/nfc/scan', { uid, device: 'homey' });
    await this.refresh();
  }

  async update() {
    const r = await this.request('GET', '/nfc');
    this._cards = (r.cards || []).filter((c) => c && c.uid);
    const byUid = Object.fromEntries(this._cards.map((c) => [c.uid, c]));
    const active = r.active ? (byUid[r.active] || {}).navn || r.active : '';
    await this.setIf('ki_kassett', active || this.homey.__('kassett.none') || 'Ingen');
    const last = r.last || {};
    if (last.t && this._lastT !== null && last.t !== this._lastT && last.known) {
      await this.homey.flow.getDeviceTriggerCard('ki_kassett_inserted').trigger(this, { navn: last.navn || '' }).catch(this.error);
    }
    this._lastT = last.t || 0;
    try {
      const sp = await this.request('GET', '/nfc/spoler');
      await this.setIf('ki_spoler', sp.på !== false);
    } catch (e) { /* eldre Skjold uten spoler */ }
  }
}
module.exports = KassettDevice;
