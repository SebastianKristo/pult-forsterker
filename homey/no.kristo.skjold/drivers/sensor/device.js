'use strict';
const Homey = require('homey');
const http = require('http');

// Leser hendelsesstrømmen til ESPHome-webserveren (GET /events, server-sent events) og setter capabilities etter
// navnet på entiteten: Temperatur, Luftfuktighet, Lys og Bevegelse. Bevegelse kommer da med en gang (ingen polling).
// Strømmen kobles opp igjen etter brudd (strøm av, ny IP via mDNS).
const PA = (v) => v === true || v === 1 || v === 'ON' || v === 'on' || v === 'true';
const MAP = {
  Temperatur: ['measure_temperature', Number],
  Luftfuktighet: ['measure_humidity', Number],
  Lys: ['measure_luminance', Number],
  Bevegelse: ['alarm_motion', PA],
  // utledet i fastvaren (esphome/skjold-sensor*.yaml)
  'Føles som': ['measure_temperature.foles', Number],
  Tilstedeværelse: ['ki_tilstede', PA],
  'Høy fuktighet': ['alarm_generic.fukt', PA],
  Mørkt: ['ki_mork', PA],
  Komfort: ['ki_komfort', String],
};
const KAPASITETER = Object.values(MAP).map((m) => m[0]);

// Navnet på entiteten: «name» kommer bare i første melding (alle verdier når strømmen starter). Senere endringer har
// bare id, «binary_sensor/Bevegelse» (ESPHome 2025+) eller «binary_sensor-bevegelse» (eldre).
function entNavn(o) {
  if (o.name) return o.name;
  const id = String(o.id || '');
  return id.includes('/') ? id.split('/').pop() : id.replace(/^[a-z_]+-/, '');
}

function parseSse(buf, onEvent) {
  // ESPHome avslutter linjene med \r\n. Gjør dem om til \n, men vent med en \r helt til slutt (resten kommer i neste bit).
  const hale = buf.endsWith('\r') ? '\r' : '';
  buf = (hale ? buf.slice(0, -1) : buf).replace(/\r\n?/g, '\n');
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
  return buf + hale;
}

class SensorDevice extends Homey.Device {
  async onInit() {
    this._req = null; this._retry = null; this._stopped = false;
    for (const c of KAPASITETER) {   // enheter lagt til med en eldre versjon av appen får de nye verdiene
      if (!this.hasCapability(c)) await this.addCapability(c).catch(this.error);
    }
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
    const navn = entNavn(o);
    const m = MAP[navn] || MAP[Object.keys(MAP).find((k) => k.toLowerCase() === String(navn).toLowerCase())];
    if (!m || !this.hasCapability(m[0])) return;
    const v = m[1](o.value !== undefined ? o.value : o.state);
    if (typeof v === 'number' && !Number.isFinite(v)) return;
    const gammel = this.getCapabilityValue(m[0]);
    if (gammel === v) return;
    this.setCapabilityValue(m[0], v).catch(this.error);
    // flytkort for Tilstedeværelse og Mørkt (ikke ved første verdi etter oppkobling)
    const kort = { ki_tilstede: ['ki_tilstede_pa', 'ki_tilstede_av'], ki_mork: ['ki_mork_pa', 'ki_mork_av'] }[m[0]];
    if (kort && gammel !== null && gammel !== undefined && this.homey && this.homey.flow) {
      this.homey.flow.getDeviceTriggerCard(kort[v ? 0 : 1]).trigger(this).catch(this.error);
    }
  }

  onDeleted() { this._stopped = true; clearTimeout(this._retry); if (this._req) this._req.destroy(); }
  onUninit() { this.onDeleted(); }
}
module.exports = SensorDevice;
module.exports.parseSse = parseSse;
module.exports.entNavn = entNavn;
