'use strict';
const { AccessoryDriver, call } = require('../../lib/SkjoldAccessory');

class KassettDriver extends AccessoryDriver {
  static get KIND() { return 'kassett'; }

  /** Én Kassett-spiller per Skjold (den som har kassetter, har lest en, eller har kontakt nå). */
  async listOn(host, port) {
    const r = await call(host, port, 'GET', '/nfc');
    // vises så snart en kassettspiller har kontakt med denne Skjold-en, også før første kassett er koblet
    if (!(r.cards || []).length && !((r.last || {}).uid) && !(r.spillere || []).length) return [];
    return [{ id: 'spiller', name: 'Skjold Kassett' }];
  }
}
module.exports = KassettDriver;
