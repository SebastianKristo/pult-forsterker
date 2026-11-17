'use strict';
// Skjold Stav: fjernkontroll med skjerm. Viser batteri, lading og siste tast, og trigger flyter når en tast trykkes.
// Tastene kommer via Skjold (/api/stav). Homey spør hvert 2,5 s, så en flyt starter innen et par sekunder etter trykket.
const { AccessoryDevice } = require('../../lib/SkjoldAccessory');

class StavDevice extends AccessoryDevice {
  static get POLL_MS() { return 2500; }   // tastene skal starte flyter raskt

  async onInit() {
    this._seq = null;
    await super.onInit();
  }

  async update() {
    const r = await this.request('GET', '/stav');
    const e = (r.enheter || {})[this.acc];
    if (!e) throw new Error('Staven er ikke registrert på Skjold');
    if (typeof e.batteri === 'number' && e.batteri >= 0) {
      await this.setIf('measure_battery', e.batteri);
      await this.setIf('alarm_battery', e.batteri < 15);
    }
    if (typeof e.lader === 'boolean') await this.setIf('ki_stav_lader', e.lader);
    const t = e.tast || {};
    if (t.knapp) await this.setIf('ki_stav_tast', t.type && t.type !== 'kort' ? `${t.knapp} (${t.type})` : t.knapp);
    if (t.seq && this._seq !== null && t.seq !== this._seq) {
      const tokens = { knapp: t.knapp, type: t.type || 'kort' };
      await this.homey.flow.getDeviceTriggerCard('ki_stav_tast').trigger(this, tokens).catch(this.error);
      await this.homey.flow.getDeviceTriggerCard('ki_stav_tast_knapp').trigger(this, tokens, tokens).catch(this.error);
    }
    this._seq = t.seq || 0;
  }
}
module.exports = StavDevice;
