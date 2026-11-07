'use strict';
// Tilbehør til en Skjold-enhet: Skjold Røst (høyttaler i Lyrion), Skjold Kassett (NFC-kassettspiller) og Skjold Hjul
// (fjernkontroll). De har ikke eget API – alt går via Skjold-enheten de hører til (/api/rost, /api/nfc, /api/hjul).
const Homey = require('homey');
const http = require('http');

const DEFAULT_PORT = 8765;
const POLL_MS = 15000;

/** JSON-kall mot Skjold-daemonen (timeout 5 s). */
function call(host, port, method, path, body) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const req = http.request({
      host, port: Number(port) || DEFAULT_PORT, method, path: `/api${path}`, timeout: 5000,
      headers: data ? { 'Content-Type': 'application/json', 'Content-Length': data.length } : {},
    }, (res) => {
      let buf = '';
      res.on('data', (c) => { buf += c; });
      res.on('end', () => {
        if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode}`));
        try { resolve(buf ? JSON.parse(buf) : {}); } catch (e) { reject(new Error('Ugyldig svar fra Skjold')); }
      });
    });
    req.on('timeout', () => req.destroy(new Error('Tidsavbrudd')));
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

/** Skjold-verter Homey kjenner: fra mDNS og fra Skjold-enheter som allerede er lagt til. */
function knownHosts(driver) {
  const hosts = new Map();
  try {
    for (const r of Object.values(driver.getDiscoveryStrategy().getDiscoveryResults() || {})) {
      hosts.set(`${r.address}:${r.port || DEFAULT_PORT}`, { host: r.address, port: r.port || DEFAULT_PORT, name: (r.txt || {}).name || r.address });
    }
  } catch (e) { /* ingen mDNS-resultater */ }
  for (const id of ['s1', 'node', 'core', 'touch', 'pultforsterker']) {
    let devs = [];
    try { devs = driver.homey.drivers.getDriver(id).getDevices(); } catch (e) { devs = []; }
    for (const d of devs) {
      const s = d.getSettings() || {};
      if (s.host) hosts.set(`${s.host}:${s.port || DEFAULT_PORT}`, { host: s.host, port: s.port || DEFAULT_PORT, name: d.getName ? d.getName() : s.host });
    }
  }
  return [...hosts.values()];
}

class AccessoryDriver extends Homey.Driver {
  /** 'rost' | 'kassett' | 'hjul' */
  static get KIND() { return null; }

  /** → [{id, name}] tilbehør av denne typen på Skjold-enheten (overstyres). */
  // eslint-disable-next-line no-unused-vars
  async listOn(host, port) { return []; }

  async onPairListDevices() {
    const out = [];
    await Promise.all(knownHosts(this).map(async (h) => {
      try {
        for (const a of await this.listOn(h.host, h.port)) {
          out.push({ name: a.name, data: { id: `${this.constructor.KIND}:${h.host}:${a.id}`, acc: a.id },
            settings: { host: h.host, port: Number(h.port) || DEFAULT_PORT }, store: { skjold: h.name } });
        }
      } catch (e) { this.error(`${h.host}: ${e.message}`); }
    }));
    return out;
  }
}

class AccessoryDevice extends Homey.Device {
  get acc() { return this.getData().acc; }

  request(method, path, body) {
    const s = this.getSettings();
    return call(s.host, s.port, method, path, body);
  }

  async onInit() {
    await this.refresh();
    this._timer = this.homey.setInterval(() => this.refresh().catch(() => {}), POLL_MS);
  }

  onDeleted() { if (this._timer) this.homey.clearInterval(this._timer); }

  async onSettings() { setTimeout(() => this.refresh().catch(() => {}), 200); }

  /** Hent status fra Skjold og oppdater capabilities (overstyres med update(data)). */
  async refresh() {
    try {
      await this.update();
      if (!this.getAvailable()) await this.setAvailable();
    } catch (e) {
      await this.setUnavailable(`Får ikke kontakt med Skjold: ${e.message}`);
    }
  }

  async setIf(cap, value) {
    if (this.hasCapability(cap) && value !== undefined && this.getCapabilityValue(cap) !== value) await this.setCapabilityValue(cap, value);
  }
}

module.exports = { AccessoryDriver, AccessoryDevice, call, knownHosts, DEFAULT_PORT };
