'use strict';

const Homey = require('homey');
const http = require('http');
const { productOf } = require('./SkjoldDevice');

const DEFAULT_PORT = 8765;
const NAMES = { s1: 'Skjold S1', node: 'Skjold Node', core: 'Skjold Core', touch: 'Skjold Touch' };

/** GET http://host:port/api/status (timeout 4 s). */
function fetchStatus(host, port, timeout = 4000) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host, port, path: '/api/status', timeout }, (res) => {
      let buf = '';
      res.on('data', (c) => { buf += c; });
      res.on('end', () => {
        if (res.statusCode !== 200) return reject(new Error(`HTTP ${res.statusCode}`));
        try {
          const st = JSON.parse(buf);
          if (!st || typeof st !== 'object' || !('power' in st)) return reject(new Error('Ikke en Skjold-enhet'));
          resolve(st);
        } catch (e) { reject(new Error('Ugyldig svar fra enheten')); }
      });
    });
    req.on('timeout', () => req.destroy(new Error('Tidsavbrudd')));
    req.on('error', reject);
  });
}

/**
 * Felles driver for Skjold S1 / Node / Core. Paring: enheter funnet med mDNS (_kipultamp._tcp) filtrert på TXT «product»
 * (eldre daemoner uten product: spør /api/status), eller manuell IP i pair/start.html (emit «manual»).
 */
class SkjoldDriver extends Homey.Driver {
  /** s1 | node | core (null = gammel driver: alle produkter). */
  static get PRODUCT() { return null; }

  get product() { return this.constructor.PRODUCT; }

  async onInit() { this.log(`Driver klar (${this.product || 'alle'})`); }

  deviceFromStatus(st, host, port) {
    const product = productOf(st);
    return {
      name: st.name || NAMES[product] || 'Skjold',
      data: { id: String(st.id || host) },
      settings: { host, port: Number(port) || DEFAULT_PORT },
      store: { product },
    };
  }

  /** Enheter fra mDNS som hører til denne driveren. */
  async discoveredDevices() {
    let results = [];
    try { results = Object.values(this.getDiscoveryStrategy().getDiscoveryResults() || {}); } catch (e) { return []; }
    const out = [];
    await Promise.all(results.map(async (r) => {
      const txt = r.txt || {};
      const port = r.port || DEFAULT_PORT;
      let product = txt.product;
      let name = txt.name;
      if (!product) {   // eldre daemon: produktet står i status
        try { const st = await fetchStatus(r.address, port, 3000); product = productOf(st); name = name || st.name; } catch (e) { product = null; }
      }
      if (this.product && product && product !== this.product) return;
      if (this.product && !product) return;   // ukjent produkt – kan legges til manuelt
      out.push({ name: name || NAMES[product] || 'Skjold', data: { id: String(txt.id || r.id) }, settings: { host: r.address, port }, store: { product } });
    }));
    return out;
  }

  /** Manuell IP: validerer /api/status og sjekker at produktet passer driveren. */
  async manualDevice({ host, port } = {}) {
    host = String(host || '').trim().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    let p = Number(port) || DEFAULT_PORT;
    const m = host.match(/^(.+):(\d+)$/); if (m) { host = m[1]; p = Number(m[2]); }
    if (!host) throw new Error(this.homey.__('pair.no_host') || 'Skriv inn IP-adresse');
    let st;
    try { st = await fetchStatus(host, p); } catch (e) {
      throw new Error(`${this.homey.__('pair.cannot_connect') || 'Fikk ikke kontakt'} (${host}:${p}): ${e.message}`);
    }
    const product = productOf(st);
    if (this.product && product !== this.product) {
      throw new Error(`${this.homey.__('pair.wrong_product') || 'Dette er en annen Skjold-modell'}: ${NAMES[product] || product}`);
    }
    return this.deviceFromStatus(st, host, p);
  }

  async onPair(session) {
    session.setHandler('list_devices', async () => this.discoveredDevices());
    session.setHandler('manual', async (data) => this.manualDevice(data));
  }

  /** SDK-fallback (gammel driver uten egne visninger). */
  async onPairListDevices() { return this.discoveredDevices(); }
}

SkjoldDriver.fetchStatus = fetchStatus;
SkjoldDriver.NAMES = NAMES;
module.exports = SkjoldDriver;
