'use strict';
const { AccessoryDriver, call } = require('../../lib/SkjoldAccessory');

class KassettDriver extends AccessoryDriver {
  static get KIND() { return 'kassett'; }

  /** Én Kassett-spiller per Skjold (den som har kassetter eller har lest en). */
  async listOn(host, port) {
    const r = await call(host, port, 'GET', '/nfc');
    if (!(r.cards || []).length && !((r.last || {}).uid)) return [];
    return [{ id: 'spiller', name: 'Skjold Kassett' }];
  }
}
module.exports = KassettDriver;
