'use strict';
const { AccessoryDriver, call } = require('../../lib/SkjoldAccessory');

// Skjold Stav: fjernkontrollen melder seg hos Skjold-en den styrer (POST /api/stav). Paring lister stavene Skjold kjenner.
class StavDriver extends AccessoryDriver {
  static get KIND() { return 'stav'; }

  async onInit() {
    await super.onInit();
    // «En bestemt tast ble trykket»: tast og trykktype velges i flyten («alle» = hvilken som helst)
    this.homey.flow.getDeviceTriggerCard('ki_stav_tast_knapp').registerRunListener(async (args, state) =>
      (args.knapp === 'alle' || args.knapp === state.knapp) && (args.type === 'alle' || args.type === state.type));
  }

  async listOn(host, port) {
    const r = await call(host, port, 'GET', '/stav');
    return Object.entries(r.enheter || {}).map(([id, e]) => ({ id, name: (e && e.navn) || 'Skjold Stav' }));
  }
}
module.exports = StavDriver;
