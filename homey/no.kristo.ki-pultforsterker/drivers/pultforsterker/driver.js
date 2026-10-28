'use strict';

const Homey = require('homey');

class PultforsterkerDriver extends Homey.Driver {
  async onInit() {
    this.log('Driver klar');
  }

  /** Paring: viser alle forsterkere funnet med mDNS (_kipultamp._tcp). */
  async onPairListDevices() {
    const strategy = this.getDiscoveryStrategy();
    const results = Object.values(strategy.getDiscoveryResults());
    return results.map((r) => ({
      name: (r.txt && r.txt.name) || 'Pultforsterker',
      data: { id: r.id },
      settings: { host: r.address, port: r.port || 8765 },
    }));
  }
}

module.exports = PultforsterkerDriver;
