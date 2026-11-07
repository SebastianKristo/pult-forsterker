'use strict';
// Skjold Hjul: fjernkontroll på batteri. Viser batteri og rom, og trigger flyt når hjulet brukes.
// Hjulet sender ikke enkelttrykk til Homey; «brukt» oppdages når Skjold registrerer ny aktivitet (innen ~15 s).
const { AccessoryDevice } = require('../../lib/SkjoldAccessory');

class HjulDevice extends AccessoryDevice {
  async onInit() {
    this.registerCapabilityListener('ki_hjul_room', (v) => this.request('POST', '/hjul', { enheter: { [this.acc]: { rom: v } } }));
    this._sist = null;
    await super.onInit();
  }

  async update() {
    const r = await this.request('GET', '/hjul');
    const e = (r.enheter || {})[this.acc];
    if (!e) throw new Error('Hjulet er ikke registrert på Skjold');
    const rooms = (r.rom || []).map(String);
    if (this.hasCapability('ki_hjul_room') && rooms.length && JSON.stringify(rooms) !== this._rooms) {
      this._rooms = JSON.stringify(rooms);
      await this.setCapabilityOptions('ki_hjul_room', { values: rooms.map((x) => ({ id: x, title: { en: x, no: x } })) }).catch(this.error);
    }
    await this.setIf('ki_hjul_room', e.rom || rooms[0]);
    if (typeof e.batteri === 'number') await this.setIf('measure_battery', e.batteri);
    if (e.sist && this._sist !== null && e.sist !== this._sist) {
      await this.homey.flow.getDeviceTriggerCard('ki_hjul_used').trigger(this, { rom: e.rom || '' }).catch(this.error);
    }
    this._sist = e.sist || 0;
  }
}
module.exports = HjulDevice;
