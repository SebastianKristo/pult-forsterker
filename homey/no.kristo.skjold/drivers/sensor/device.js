'use strict';
const Homey = require('homey');
const http = require('http');

// Leser hendelsesstrømmen til ESPHome-webserveren (GET /events, server-sent events) og setter capabilities etter
// navnet på entiteten: Temperatur, Luftfuktighet, Lys og Bevegelse. Bevegelse kommer da med en gang (ingen polling).
// Strømmen kobles opp igjen etter brudd (strøm av, ny IP via mDNS).
const MAP = {
  Temperatur: ['measure_temperature', Number],
  Luftfuktighet: ['measure_humidity', Number],
  Lys: ['measure_luminance', Number],
  Bevegelse: ['alarm_motion', (v) => v === true || v === 'ON' || v === 'on'],
};

function parseSse(buf, onEvent) {
  let i;
  while ((i = buf.indexOf('\n\n')) >= 0) {
    const block = buf.slice(0, i); buf = buf.slice(i + 2);
    let ev = 'message', data = '';
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) ev = line.slice(6).trim();
      else if (line.startsWith('data:')) data += line.slice(5).trim();
    }
    onEvent(ev, data);
  }
  return buf;
}

class SensorDevice extends Homey.Device {
  async onInit() {
    this._req = null; this._retry = null; this._stopped = false;
    this.connect();
  }

  onDiscoveryResult(r) { return String((r.txt && r.txt.mac) || r.id) === String(this.getData().id); }
  async onDiscoveryAvailable(r) { await this.setStoreValue('address', r.address).catch(this.error); this.connect(); }
  onDiscoveryAddressChanged(r) { this.setStoreValue('address', r.address).catch(this.error); this.connect(); }

  connect() {
    if (this._stopped) return;
    if (this._req) { this._req.destroy(); this._req = null; }
    clearTimeout(this._retry);
    const host = this.getStoreValue('address');
    if (!host) { this.setUnavailable('Fant ikke sensoren på nettet').catch(this.error); return; }
    let buf = '';
    const req = http.get({ host, port: this.getStoreValue('port') || 80, path: '/events', headers: { Accept: 'text/event-stream' } }, (res) => {
      if (res.statusCode !== 200) { res.resume(); this.retry('Svarte ' + res.statusCode); return; }
      this.setAvailable().catch(this.error);
      res.setEncoding('utf8');
      res.on('data', (c) => { buf = parseSse(buf + c, (ev, data) => this.onEvent(ev, data)); });
      res.on('end', () => this.retry('Strømmen ble lukket'));
    });
    req.setTimeout(90000, () => req.destroy(new Error('ingen data på 90 s')));   // ESPHome sender ping hvert ~10. s
    req.on('error', (e) => this.retry(e.message));
    this._req = req;
  }

  retry(why) {
    if (this._stopped) return;
    this.setUnavailable(why).catch(this.error);
    clearTimeout(this._retry);
    this._retry = this.homey.setTimeout(() => this.connect(), 10000);
  }

  onEvent(ev, data) {
    if (ev !== 'state' || !data) return;
    let o; try { o = JSON.parse(data); } catch (e) { return; }
    const navn = o.name || String(o.id || '').replace(/^[a-z_]+-/, '');
    const m = MAP[navn] || MAP[Object.keys(MAP).find((k) => k.toLowerCase() === String(navn).toLowerCase())];
    if (!m || !this.hasCapability(m[0])) return;
    const v = m[1](o.value !== undefined ? o.value : o.state);
    if (typeof v === 'number' && !Number.isFinite(v)) return;
    if (this.getCapabilityValue(m[0]) !== v) this.setCapabilityValue(m[0], v).catch(this.error);
  }

  onDeleted() { this._stopped = true; clearTimeout(this._retry); if (this._req) this._req.destroy(); }
  onUninit() { this.onDeleted(); }
}
module.exports = SensorDevice;
module.exports.parseSse = parseSse;
