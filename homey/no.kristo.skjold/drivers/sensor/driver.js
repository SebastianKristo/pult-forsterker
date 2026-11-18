'use strict';
const Homey = require('homey');

// Skjold Sensor (esphome/skjold-sensor.yaml): ESPHome-romsensor som Homey finner på mDNS (_esphomelib._tcp,
// project_name «skjold.sensor»). Paring lister sensorene på nettet; adressen følges når den endres.
class SensorDriver extends Homey.Driver {
  async onPairListDevices() {
    const res = this.getDiscoveryStrategy().getDiscoveryResults();
    return Object.values(res).map((r) => ({
      name: (r.txt && r.txt.friendly_name) || r.name || 'Skjold Sensor',
      data: { id: String((r.txt && r.txt.mac) || r.id) },
      store: { address: r.address, port: 80 },
    }));
  }
}
module.exports = SensorDriver;
