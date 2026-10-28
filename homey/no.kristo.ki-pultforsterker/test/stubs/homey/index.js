'use strict';
// Minimal stubb av Homey SDK v3 – nok til å kjøre app.js og device.js utenfor Homey.
const EventEmitter = require('events');

class Card {
  constructor(id) { this.id = id; this.triggered = []; this.listener = null; }
  registerRunListener(fn) { this.listener = fn; return this; }
  async trigger(device, tokens) { this.triggered.push({ device, tokens }); }
  async run(args) { return this.listener(args); }
}
class Flow {
  constructor() { this.cards = {}; }
  _get(id) { return (this.cards[id] = this.cards[id] || new Card(id)); }
  getDeviceTriggerCard(id) { return this._get(id); }
  getConditionCard(id) { return this._get(id); }
  getActionCard(id) { return this._get(id); }
}
class HomeyCtx {
  constructor() { this.flow = new Flow(); this.setInterval = setInterval; this.clearInterval = clearInterval; this.__ = (k) => k; }
}

class Device {
  constructor({ homey, driver, data, settings, capabilities }) {
    this.homey = homey || new HomeyCtx(); this.driver = driver || { getDiscoveryStrategy() { return { getDiscoveryResult() { return null; } }; } };
    this._data = data || { id: 'test' }; this._settings = settings || {}; this._caps = capabilities || [];
    this._values = {}; this._listeners = {}; this._available = true; this.logs = [];
  }
  registerCapabilityListener(cap, fn) { this._listeners[cap] = fn; }
  hasCapability(c) { return this._caps.includes(c); }
  async addCapability(c) { this._caps.push(c); }
  async setCapabilityValue(c, v) { this._values[c] = v; }
  getCapabilityValue(c) { return this._values[c]; }
  getData() { return this._data; }
  getSettings() { return this._settings; }
  async setSettings(s) { Object.assign(this._settings, s); }
  getAvailable() { return this._available; }
  async setAvailable() { this._available = true; }
  async setUnavailable(msg) { this._available = false; this._unavailableReason = msg; }
  log(...a) { this.logs.push(a); }
  error(...a) { this.logs.push(['error', ...a]); }
  // hjelpere for test: utløs en capability som fra Homey-appen
  async triggerCapability(cap, value) { return this._listeners[cap](value); }
}
class Driver { constructor({ homey } = {}) { this.homey = homey || new HomeyCtx(); } log() {} error() {} }
class App { constructor({ homey } = {}) { this.homey = homey || new HomeyCtx(); } log() {} error() {} }

module.exports = { Device, Driver, App, HomeyCtx };
