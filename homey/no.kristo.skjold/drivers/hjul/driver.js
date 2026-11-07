'use strict';
const { AccessoryDriver, call } = require('../../lib/SkjoldAccessory');

class HjulDriver extends AccessoryDriver {
  static get KIND() { return 'hjul'; }

  async listOn(host, port) {
    const r = await call(host, port, 'GET', '/hjul');
    return Object.entries(r.enheter || {}).map(([id, e]) => ({ id, name: (e && e.navn) || 'Skjold Hjul' }));
  }
}
module.exports = HjulDriver;
