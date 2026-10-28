'use strict';

const Homey = require('homey');

class KiPultforsterkerApp extends Homey.App {
  async onInit() {
    this.log('Pultforsterker-appen starter');

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
    this.homey.flow.getActionCard('ki_transport')
      .registerRunListener(async ({ device, action }) => device.transport(action));
    const play = this.homey.flow.getActionCard('ki_play_preset');
    play.registerRunListener(async ({ device, preset }) => device.playPreset(Number(preset.id)));
    play.registerArgumentAutocompleteListener('preset', async (query, { device }) => device.presetList()
      .map((p) => ({ id: String(p.n), name: `${p.n}. ${p.title}` }))
      .filter((r) => r.name.toLowerCase().includes((query || '').toLowerCase())));
    this.homey.flow.getActionCard('ki_save_preset')
      .registerRunListener(async ({ device, n }) => device.savePreset(Number(n)));
    this.homey.flow.getActionCard('ki_set_loudness')
      .registerRunListener(async ({ device, on, level }) => device.setLoudness(on === 'on', level));
  }
}

module.exports = KiPultforsterkerApp;
