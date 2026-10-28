'use strict';

const Homey = require('homey');

class KiPultforsterkerApp extends Homey.App {
  async onInit() {
    this.log('KI Pultforsterker-appen starter');

    this.homey.flow.getConditionCard('ki_is_playing')
      .registerRunListener(async ({ device }) => device.getCapabilityValue('speaker_playing') === true);
    this.homey.flow.getConditionCard('ki_input_is')
      .registerRunListener(async ({ device, input }) => device.getCapabilityValue('ki_input') === input);

    this.homey.flow.getActionCard('ki_toggle')
      .registerRunListener(async ({ device }) => device.togglePower());
    this.homey.flow.getActionCard('ki_bt_pair')
      .registerRunListener(async ({ device }) => device.btPair());
    this.homey.flow.getActionCard('ki_set_input')
      .registerRunListener(async ({ device, input }) => device.setInput(input));
  }
}

module.exports = KiPultforsterkerApp;
