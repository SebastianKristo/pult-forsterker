'use strict';
const { AccessoryDriver, call } = require('../../lib/SkjoldAccessory');

class RostDriver extends AccessoryDriver {
  static get KIND() { return 'rost'; }

  async listOn(host, port) {
    const r = await call(host, port, 'GET', '/rost');
    return (r.minis || []).map((m) => ({ id: m.id, name: m.name || 'Skjold Røst' }));
  }
}
module.exports = RostDriver;
