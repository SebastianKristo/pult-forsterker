'use strict';
const Homey = require('homey');
const http = require('http');

// Leser hendelsesstrømmen til ESPHome-webserveren (GET /events, server-sent events) og setter capabilities etter
// navnet på entiteten: Temperatur, Luftfuktighet, Lys og Bevegelse. Bevegelse kommer da med en gang (ingen polling).
// Strømmen kobles opp igjen etter brudd (strøm av, ny IP via mDNS).
// Korte brudd (Wi-Fi-blaff, omstart) skal ikke synes eller utløse noe: enheten blir først «utilgjengelig» etter
// BORTE_MS uten forbindelse, og flytkortene utløses ikke av verdiene som kommer rett etter at forbindelsen er tilbake.
const BORTE_MS = 3 * 60 * 1000;
const ROLIG_MS = 15 * 1000;
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

// Innstillinger og diagnostikk: entitet i ESPHome → innstilling i Homey
const INNST = {   // [nøkkel, ESPHome-domene] – kan endres fra Homey
  Oppdateringsintervall: ['oppdatering', 'number'],
  'Bevegelse av etter': ['bevegelse_av', 'number'],
  'Tilstedeværelse av etter': ['tilstede_av', 'number'],
  'Status-LED': ['led', 'switch'],
};
const tid = (s) => { s = Math.floor(Number(s) || 0); const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return (d ? d + ' d ' : '') + (d || h ? h + ' t ' : '') + m + ' min'; };
const DIAG = {    // vises som etiketter (bare lesing)
  'IP-adresse': ['ip', String],
  'MAC-adresse': ['mac', String],
  'Wi-Fi-nett': ['ssid', String],
  'Wi-Fi-signal': ['signal', (v) => Math.round(Number(v)) + ' dBm'],
  Oppetid: ['oppetid', tid],
  'ESPHome-versjon': ['versjon', String],
};

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
    if (!this.hasCapability('button.fastvare')) await this.addCapability('button.fastvare').catch(this.error);
    this.registerCapabilityListener('button.fastvare', async () => {
      if (!this._fastvare) throw new Error('Sensoren har ikke fastvaren fra skjold-lab.com. Flash den én gang med USB fra skjold-lab.com/flasher/sensor/.');
      if (this._fastvare.installert && this._fastvare.installert === this._fastvare.siste) throw new Error(`Sensoren har allerede nyeste fastvare (${this._fastvare.installert}).`);
      await this.post('/update/Fastvare/install');
    });
    this.connect();
  }

  // «Fastvare» (ESPHome update): installert og nyeste versjon, og et varsel i Homey én gang per ny versjon
  fastvare(o) {
    const f = { installert: o.current_version || '', siste: o.latest_version || o.value || '', tilstand: String(o.state || '') };
    this._fastvare = f;
    const tekst = !f.installert ? '–' : f.tilstand.toUpperCase() === 'INSTALLING' ? 'Oppdaterer …'
      : (f.siste && f.siste !== f.installert ? `${f.installert} → ${f.siste} finnes` : `${f.installert} (nyeste)`);
    this.settInnst('fastvare', tekst);
    if (f.siste && f.installert && f.siste !== f.installert && this.getStoreValue('varslet') !== f.siste) {
      this.setStoreValue('varslet', f.siste).catch(this.error);
      this.homey.notifications.createNotification({ excerpt: `Ny fastvare for **${this.getName()}**: ${f.siste}. Oppdater under Vedlikehold på enheten.` }).catch(this.error);
    }
  }

  // Endret i Homey → send til sensoren (ESPHome-webserveren: POST /number/<navn>/set?value= og /switch/<navn>/turn_on|off)
  async onSettings({ newSettings, changedKeys }) {
    for (const k of changedKeys) {
      const navn = Object.keys(INNST).find((n) => INNST[n][0] === k);
      if (!navn) continue;
      const [, domene] = INNST[navn];
      const sti = domene === 'switch'
        ? `/switch/${encodeURIComponent(navn)}/${newSettings[k] ? 'turn_on' : 'turn_off'}`
        : `/number/${encodeURIComponent(navn)}/set?value=${encodeURIComponent(newSettings[k])}`;
      await this.post(sti);
    }
  }

  post(sti) {
    const host = this.getStoreValue('address');
    if (!host) return Promise.reject(new Error('Fant ikke sensoren på nettet'));
    return new Promise((ok, feil) => {
      const req = http.request({ host, port: this.getStoreValue('port') || 80, path: sti, method: 'POST', headers: { 'Content-Length': 0 } }, (res) => {
        res.resume();
        if (res.statusCode >= 200 && res.statusCode < 300) ok(); else feil(new Error('Sensoren svarte ' + res.statusCode));
      });
      req.setTimeout(8000, () => req.destroy(new Error('Sensoren svarte ikke')));
      req.on('error', feil);
      req.end();
    });
  }

  // Verdier fra sensoren som hører til innstillingene: samle og skriv dem samlet (setSettings utløser ikke onSettings)
  settInnst(nokkel, verdi) {
    this._innst = { ...(this._innst || {}), [nokkel]: verdi };
    clearTimeout(this._innstT);
    this._innstT = this.homey.setTimeout(() => {
      const nye = this._innst; this._innst = {};
      const gamle = this.getSettings();
      const endret = Object.fromEntries(Object.entries(nye).filter(([k, v]) => gamle[k] !== v));
      if (Object.keys(endret).length) this.setSettings(endret).catch(this.error);
    }, 1500);
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
      this._koblet = Date.now();
      clearTimeout(this._borteT); this._borteT = null;
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
    // ikke utilgjengelig med en gang: sensoren er som regel tilbake innen et minutt (Wi-Fi-blaff eller omstart)
    if (!this._borteT) this._borteT = this.homey.setTimeout(() => { this._borteT = null; this.setUnavailable(why).catch(this.error); }, BORTE_MS);
    clearTimeout(this._retry);
    this._retry = this.homey.setTimeout(() => this.connect(), 10000);
  }

  onEvent(ev, data) {
    if (ev !== 'state' || !data) return;
    let o; try { o = JSON.parse(data); } catch (e) { return; }
    const navn = entNavn(o);
    if (navn === 'Fastvare') { if (this.homey) this.fastvare(o); return; }
    const rå = o.value !== undefined ? o.value : o.state;
    const inn = INNST[navn], dia = DIAG[navn];
    if ((inn || dia) && this.homey) {
      if (inn) this.settInnst(inn[0], inn[1] === 'switch' ? PA(rå) : Number(rå));
      else if (rå !== null && rå !== undefined && rå !== '') this.settInnst(dia[0], dia[1](rå));
      return;
    }
    const m = MAP[navn] || MAP[Object.keys(MAP).find((k) => k.toLowerCase() === String(navn).toLowerCase())];
    if (!m || !this.hasCapability(m[0])) return;
    if ((o.value === undefined || o.value === null) && (o.state === '' || o.state === 'NA' || o.state === undefined)) return;   // ukjent (rett etter start)
    const v = m[1](o.value !== undefined ? o.value : o.state);
    if (typeof v === 'number' && !Number.isFinite(v)) return;
    const gammel = this.getCapabilityValue(m[0]);
    if (gammel === v) return;
    this.setCapabilityValue(m[0], v).catch(this.error);
    // flytkort for Tilstedeværelse og Mørkt (ikke ved første verdi etter oppkobling)
    const kort = { ki_tilstede: ['ki_tilstede_pa', 'ki_tilstede_av'], ki_mork: ['ki_mork_pa', 'ki_mork_av'] }[m[0]];
    const rolig = Date.now() - (this._koblet || 0) < ROLIG_MS;   // verdiene rett etter oppkobling: bare oppdater
    if (kort && !rolig && gammel !== null && gammel !== undefined && this.homey && this.homey.flow) {
      this.homey.flow.getDeviceTriggerCard(kort[v ? 0 : 1]).trigger(this).catch(this.error);
    }
  }

  onDeleted() { this._stopped = true; clearTimeout(this._retry); clearTimeout(this._borteT); if (this._req) this._req.destroy(); }
  onUninit() { this.onDeleted(); }
}
module.exports = SensorDevice;
module.exports.parseSse = parseSse;
module.exports.entNavn = entNavn;
module.exports.INNST = INNST;
