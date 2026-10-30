// Felles innstillingsskjema og EQ-profiler for Skjold S1 (web + app). Samme nøkler som forsterkerens meny.
(function () {
  const NAMES = ['Skjold S1', 'Stue', 'Kontor', 'Soverom'];
  const PRESETS_RADIO = ['NRK P1', 'NRK P2', 'NRK P3', 'P4 Norge', 'Radio Norge', 'NRK Klassisk'];
  const fmt = {
    dB: v => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + ' dB',
    bal: v => v === 0 ? 'Midt' : (v < 0 ? 'V ' : 'H ') + Math.abs(v)
  };
  const num = (k, n, mn, mx, f, hint) => ({ kind: 'num', k, n, mn, mx, f, hint });
  const opt = (k, n, list, hint) => ({ kind: 'opt', k, n, list, hint });
  const bool = (k, n, hint) => ({ kind: 'bool', k, n, hint });
  const str = (k, n, ph, hint) => ({ kind: 'str', k, n, ph, hint });
  const CATS = [
    { id: 'eq', n: 'Equalizer', sub: 'Egen profil per inngang', items: [{ kind: 'eq', n: 'Equalizer' }] },
    { id: 'lyd', n: 'Lyd', sub: 'Tone, volum og nivå', items: [
      num('bass', 'Bass', -6, 6, 'dB'), num('treb', 'Diskant', -6, 6, 'dB'), num('bal', 'Balanse', -5, 5, 'bal'),
      opt('vstart', 'Startvolum', ['Sist brukt', '20', '30', '40']), opt('vmax', 'Maksvolum', ['100', '90', '80', '70']),
      bool('perIn', 'Volum per inngang', 'Hver inngang husker sitt eget volum'), bool('hpOwn', 'Eget volum for hodetelefoner'),
      num('lvlAux', 'Nivå AUX', -6, 6, 'dB', 'Juster så AUX er like høy som strømming'), num('lvlUsb', 'Nivå USB', -6, 6, 'dB')] },
    { id: 'utgang', n: 'Lydutgang', sub: 'DAC, HDMI eller 3,5 mm', dev: 'node', items: [
      opt('out', 'Utgang', ['3,5 mm (innebygd)', 'HDMI', 'USB-DAC', 'I²S-kort (HiFiBerry / IQaudio)'], 'Pi 3B og Pi 4 har 3,5 mm og HDMI. Et I²S-kort gir best lyd.'),
      opt('hat', 'I²S-kort', ['HiFiBerry DAC+', 'HiFiBerry DAC2 HD', 'IQaudio DAC Pro', 'Allo Boss'], 'Brukes bare når utgang er I²S-kort'),
      opt('rate', 'Samplingsfrekvens', ['44,1 kHz', '48 kHz', '96 kHz', 'Følg kilden']),
      opt('mixer', 'Volumkontroll', ['Programvare', 'Maskinvare (DAC)', 'Fast 100 % (styres av forsterker)'], 'Velg fast hvis Node er koblet til en egen forsterker med volumknapp'),
      { kind: 'act', n: 'Test utgang', id: 'testOut', label: 'Spill testtone', safe: true }] },
    { id: 'tilkobling', n: 'Tilkobling', sub: 'Navn og Blåtann', items: [
      opt('name', 'Enhetsnavn', NAMES, 'Navnet som vises i AirPlay og Blåtann'),
      { ...str('nAux1', 'Navn på AUX 1', 'AUX 1', 'Vises på skjermen og i appen'), dev: 's1' }, { ...str('nAux2', 'Navn på AUX 2', 'AUX 2'), dev: 's1' },
      { ...str('nUsb1', 'Navn på USB-C «PC 1»', 'PC', 'For eksempel Mac eller Jobb-PC'), dev: 's1' }, { ...str('nUsb2', 'Navn på USB-C «PC 2»', 'Switch'), dev: 's1' },
      { kind: 'info', n: 'Parede enheter', key: 'btDev' },
      { kind: 'act', n: 'Blåtann-paring', id: 'btPair', label: 'Start paring', safe: true, dev: 'node', hint: 'Node har ingen knapp. Gjør den synlig for Blåtann i 2 minutter herfra.' },
      { ...bool('btAuto', 'Blåtann alltid synlig', 'Kan pares uten å starte paring først. Mindre sikkert.'), dev: 'node' },
      { kind: 'act', n: 'Glem alle Blåtann-enheter', id: 'forget', label: 'Glem alle' }] },
    { id: 'radio', n: 'Radio', sub: 'Lyrion-favoritter', items: [
      { ...opt('hold', 'Hold radioknappen', PRESETS_RADIO, 'Kanalen som spilles når du holder radioknappen inne'), dev: 's1' },
      { ...opt('nodeStart', 'Kanal ved oppstart', ['Ingen', ...PRESETS_RADIO], 'Node har ingen knapper. Velg om den skal starte en radiokanal når den slås på.'), dev: 'node' },
      { kind: 'act', n: 'Administrer favoritter', id: 'openRadio', label: 'Åpne', safe: true }] },
    { id: 'stemme', n: 'Stemme', sub: 'Talebeskjeder', items: [
      bool('voice', 'Talebeskjed ved bytte'), opt('lang', 'Språk', ['Norsk', 'English', 'Svenska', 'Dansk']), opt('vv', 'Stemmevolum', ['Lav', 'Middels', 'Høy']),
      { kind: 'act', n: 'Test stemme', id: 'testVoice', label: 'Spill av', safe: true }] },
    { id: 'skjerm', n: 'Skjerm og lys', dev: 's1', sub: 'Dimming, klokke, LED', items: [
      opt('dim', 'Dimme skjermen etter', ['Av', '30 s', '1 min']), opt('off', 'Slukk skjermen etter', ['Av', '2 min', '5 min'], 'Beskytter OLED-skjermen mot innbrenning'),
      bool('clock', 'Klokke i standby'), { kind: 'clocks', k: 'clockStyle', n: 'Klokke i standby' }, opt('led', 'LED-ringer', ['Høy', 'Middels', 'Lav', 'Av'])] },
    { id: 'strom', n: 'Strøm', sub: 'Standby og påslag', items: [
      opt('auto', 'Auto-standby uten lyd', ['Av', '20 min', '60 min']), bool('wake', 'Slå på ved signal', 'AirPlay eller Blåtann vekker forsterkeren')] },
    { id: 'oppdatering', n: 'Oppdatering', sub: 'GitHub, backup og gjenoppretting', items: [{ kind: 'update', n: 'Oppdatering' }] },
    { id: 'system', n: 'System', sub: 'Om, oppsett og tilbakestilling', items: [
      { kind: 'info', n: 'Programvare', val: '1.4.2' }, { kind: 'info', n: 'IP-adresse', val: '192.168.1.42' },
      { kind: 'info', n: 'Lyrion', key: 'lyrion' }, { kind: 'info', n: 'Serienummer', val: 'SKJ-S1-0001' },
      { kind: 'act', n: 'Kjør oppsett på nytt', id: 'setup', label: 'Start oppsett' },
      { kind: 'act', n: 'Fabrikkinnstillinger', id: 'reset', label: 'Tilbakestill' }] }
  ];
  const DEF = { nodeStart: 0, btAuto: false, out: 3, hat: 0, rate: 3, mixer: 0, clockStyle: 0, nAux1: 'AUX 1', nAux2: 'AUX 2', nUsb1: 'PC', nUsb2: 'Switch', name: 0, lvlAux: 0, lvlUsb: 0, led: 0, voice: false, lang: 0, vv: 1, hold: 2, bass: 0, treb: 0, bal: 0, vstart: 0, vmax: 0, perIn: true, hpOwn: true, dim: 1, off: 1, clock: true, auto: 1, wake: true };
  const EQ = {
    bands: ['60', '250', '1k', '4k', '12k'],
    presets: [['Flat', [0, 0, 0, 0, 0]], ['Bass+', [6, 3, 0, 0, 1]], ['Vokal', [-2, 0, 3, 2, 0]], ['Kveld', [3, 1, -1, -2, -3]], ['Podkast', [-4, 0, 4, 3, -1]], ['Klassisk', [2, 0, -1, 1, 3]]],
    sources: [['air', 'AirPlay'], ['bt', 'Blåtann'], ['radio', 'Radio'], ['aux', 'AUX'], ['usb', 'USB'], ['hp', 'Hodetelefoner']],
    defaults: { air: 0, bt: 1, radio: 2, aux: 0, usb: 0, hp: 3 }
  };
  function loadEq() {
    try { const j = JSON.parse(localStorage.getItem('skjold-eq') || 'null'); if (j && j.air) return j; } catch (e) {}
    const o = {}; EQ.sources.forEach(([k]) => { const p = EQ.defaults[k]; o[k] = { preset: p, eq: EQ.presets[p][1].slice(), loud: k !== 'hp' }; }); return o;
  }
  function saveEq(o) { try { localStorage.setItem('skjold-eq', JSON.stringify(o)); } catch (e) {} }
  // aktiv EQ-kilde ut fra forsterkerens tilstand
  function activeSrc(st) { if (!st) return 'air'; if (st.hp) return 'hp'; return st.input === 0 ? (st.wl === 'bt' ? 'bt' : 'air') : ['air', 'aux', 'radio', 'usb'][st.input]; }
  function curve(eq, w, h) {
    const n = eq.length, xs = eq.map((_, i) => w * (i + 0.5) / n), mid = h / 2, ys = eq.map(v => mid - v * (h / 2 - 6) / 12);
    let d = 'M0 ' + ys[0].toFixed(1) + ' L' + xs[0].toFixed(1) + ' ' + ys[0].toFixed(1);
    for (let i = 0; i < n - 1; i++) { const mx = (xs[i] + xs[i + 1]) / 2; d += ' C' + mx.toFixed(1) + ' ' + ys[i].toFixed(1) + ' ' + mx.toFixed(1) + ' ' + ys[i + 1].toFixed(1) + ' ' + xs[i + 1].toFixed(1) + ' ' + ys[i + 1].toFixed(1); }
    d += ' L' + w + ' ' + ys[n - 1].toFixed(1); return { line: d, area: d + ' L' + w + ' ' + mid + ' L0 ' + mid + ' Z', mid };
  }
  const CATALOG = [['NRK P1','Distriktsprogram'],['NRK P1+','Musikk for voksne'],['NRK P2','Kultur og samfunn'],['NRK P3','Pop og humor'],['NRK mP3','Hits'],['NRK Klassisk','Klassisk musikk'],['NRK Jazz','Jazz'],['NRK Folkemusikk','Folkemusikk'],['NRK Alltid Nyheter','Nyheter'],['NRK Sport','Sport'],['P4 Norge','Hits'],['P5 Hits','Hits'],['P6 Rock','Rock'],['P7 Klem','Ballader'],['P9 Retro','80- og 90-tallet'],['Radio Norge','Pop og rock'],['NRJ','Dance og pop'],['Radio Rock','Rock'],['Kiss','Pop'],['BBC Radio 6 Music','Alternativ']];
  const NOWP = { 'NRK P1': ['Nyheter', 'NRK Dagsnytt'], 'NRK P2': ['Ekko', 'Et aktuelt samfunnsprogram'], 'NRK P3': ['Dance The Way I Feel', 'Ofenbach'], 'P4 Norge': ['Flowers', 'Miley Cyrus'], 'Radio Norge': ['Mr. Brightside', 'The Killers'], 'NRK Klassisk': ['Clair de lune', 'Claude Debussy'] };
  const hue = s => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
  // Plassholder for omslag / stasjonslogo (ekte bilde kommer fra AirPlay-metadata eller Lyrion)
  // Ekte stasjonslogoer hentes fra Radio Browser (åpent API, samme kilde som Lyrion kan bruke) og caches lokalt.
  let LOGOS = {}; try { LOGOS = JSON.parse(localStorage.getItem('skjold-logos') || '{}') || {}; } catch (e) {}
  const logoCbs = new Set(), pending = {};
  function onLogos(cb) { logoCbs.add(cb); return () => logoCbs.delete(cb); }
  const RB = 'https://de1.api.radio-browser.info/json/stations/search';
  const QUERY = { 'NRK P1': ['NRK P1', 'NO'], 'NRK P1+': ['NRK P1+', 'NO'], 'NRK P2': ['NRK P2', 'NO'], 'NRK P3': ['NRK P3', 'NO'], 'NRK mP3': ['NRK mP3', 'NO'], 'NRK Klassisk': ['NRK Klassisk', 'NO'], 'NRK Jazz': ['NRK Jazz', 'NO'], 'NRK Folkemusikk': ['NRK Folkemusikk', 'NO'], 'NRK Alltid Nyheter': ['NRK Alltid Nyheter', 'NO'], 'NRK Sport': ['NRK Sport', 'NO'], 'P4 Norge': ['P4', 'NO'], 'P5 Hits': ['P5', 'NO'], 'P6 Rock': ['P6 Rock', 'NO'], 'P7 Klem': ['P7 Klem', 'NO'], 'P9 Retro': ['P9 Retro', 'NO'], 'Radio Norge': ['Radio Norge', 'NO'], 'NRJ': ['NRJ Norge', 'NO'], 'Radio Rock': ['Radio Rock', 'NO'], 'Kiss': ['Kiss', 'NO'], 'BBC Radio 6 Music': ['BBC Radio 6 Music', 'GB'] };
  const NRK = n => 'https://static.nrk.no/radio/dist/images/channel-logos/nrk-logo-nrk-' + n + '--color-light.svg';
  const OVR = { 'NRK P1': NRK('p1'), 'NRK P1+': NRK('p1+'), 'NRK P2': NRK('p2'), 'NRK P3': NRK('p3'), 'NRK mP3': NRK('mp3'), 'NRK Klassisk': NRK('klassisk'), 'NRK Jazz': NRK('jazz'), 'NRK Folkemusikk': NRK('folkemusikk'), 'NRK Alltid Nyheter': NRK('alltid-nyheter'), 'NRK Sport': NRK('sport') };
  const probe = url => new Promise(res => { if (typeof Image === 'undefined') return res(true); const im = new Image(); im.onload = () => res(im.naturalWidth >= 32 || /\.svg/.test(url)); im.onerror = () => res(false); im.src = url; });
  const LV = 2; if (LOGOS.__v !== LV) LOGOS = { __v: LV };
  function fetchLogos(names) { names.forEach(name => { if (LOGOS[name] !== undefined || pending[name] || !QUERY[name]) return; pending[name] = 1; const [q, cc] = QUERY[name];
    const done = url => { LOGOS[name] = url || ''; try { localStorage.setItem('skjold-logos', JSON.stringify(LOGOS)); } catch (e) {} logoCbs.forEach(cb => cb()); };
    const viaApi = () =>
    fetch(RB + '?name=' + encodeURIComponent(q) + '&countrycode=' + cc + '&hidebroken=true&order=clickcount&reverse=true&limit=25').then(r => r.json()).then(list => {
      const ql = q.toLowerCase(), score = s => (s.name.trim().toLowerCase() === ql ? 4 : s.name.toLowerCase().startsWith(ql) ? 2 : 0) + (/\.ico(\?|$)/i.test(s.favicon) ? -3 : 2) + (/logo/i.test(s.favicon) ? 1 : 0);
      const hit = (list || []).filter(s => s.favicon && /^https:/.test(s.favicon)).sort((x, y) => score(y) - score(x))[0];
      if (!hit || /\.ico(\?|$)|16x16|32x32/i.test(hit.favicon)) return done(''); probe(hit.favicon).then(ok => done(ok ? hit.favicon : ''));
    }).catch(() => { delete pending[name]; });
    if (OVR[name]) probe(OVR[name]).then(ok => ok ? done(OVR[name]) : viaApi()); else viaApi(); }); }
  function art(key) { if (key !== '__v' && LOGOS[key]) { const u = LOGOS[key].replace(/"/g, ''), nrk = /static\.nrk\.no/.test(u); return { bg: 'url("' + u + '") center / ' + (nrk ? '72% auto' : 'cover') + ' no-repeat, ' + (nrk ? '#121214' : '#f4f2ee'), ink: 'transparent', logo: u }; } const h = hue(key); return { bg: 'linear-gradient(150deg, oklch(0.42 0.09 ' + h + ') 0%, oklch(0.2 0.04 ' + ((h + 40) % 360) + ') 100%)', ink: 'oklch(0.93 0.03 ' + h + ')' }; }
  function loadRadio() { try { const j = JSON.parse(localStorage.getItem('skjold-radio') || 'null'); if (Array.isArray(j) && j.length) return j; } catch (e) {} return [['NRK P1','Distriktsprogram'],['NRK P2','Kultur og samfunn'],['NRK P3','Pop og humor'],['P4 Norge','Hits'],['Radio Norge','Pop og rock'],['NRK Klassisk','Klassisk musikk']]; }
  function saveRadio(l) { try { localStorage.setItem('skjold-radio', JSON.stringify(l)); } catch (e) {} }
  function nowPlaying(name) { return NOWP[name] || ['Direkte', name]; }
  // Programvareoppdatering fra GitHub Releases + backup/gjenoppretting (simulert i prototypen)
  const UPD_DEF = { version: '1.4.2', repo: 'skjold-audio/skjold-s1', channel: 0, auto: true, failNext: false, latest: null, checkedAt: '', log: [],
    backups: [{ id: 'b3', ver: '1.4.2', date: '2026-10-28 03:12', kind: 'Automatisk før oppdatering' }, { id: 'b2', ver: '1.4.1', date: '2026-10-02 03:08', kind: 'Automatisk før oppdatering' }, { id: 'b1', ver: '1.4.0', date: '2026-09-14 19:40', kind: 'Manuell' }] };
  const RELEASES = [{ tag: 'v1.5.0', name: 'Skjold 1.5.0', date: '2026-10-29', notes: ['Spotify Connect som egen inngang', 'EQ-profiler per inngang', 'Raskere oppstart (2,1 s)', 'Retter: Blåtann kobler ikke til etter standby'], size: '18,4 MB', pre: false }, { tag: 'v1.6.0-beta.1', name: 'Skjold 1.6.0 beta 1', date: '2026-10-30', notes: ['Multirom med Lyrion-synk', 'Ny radiomeny på skjermen'], size: '19,1 MB', pre: true }];
  function loadUpd() { try { const j = JSON.parse(localStorage.getItem('skjold-upd') || 'null'); if (j && j.version) return { ...UPD_DEF, ...j }; } catch (e) {} return JSON.parse(JSON.stringify(UPD_DEF)); }
  function saveUpd(u) { try { localStorage.setItem('skjold-upd', JSON.stringify(u)); } catch (e) {} }
  const now = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };
  const vnum = t => t.replace(/^v/, '');
  function findRelease(u) { const r = RELEASES.filter(x => u.channel === 1 || !x.pre).sort((a, b) => a.date < b.date ? 1 : -1)[0]; return r && vnum(r.tag) !== u.version ? r : null; }
  // runJob: steg med fremdrift; onTick(state) kalles underveis. Returnerer stop-funksjon.
  function runJob(kind, u, onTick) {
    const rel = u.latest, fail = kind === 'update' && u.failNext;
    const steps = kind === 'update' ? ['Tar backup av ' + u.version, 'Laster ned ' + rel.tag + ' fra github.com/' + u.repo, 'Verifiserer SHA-256', 'Installerer', fail ? 'Starter tjenester …' : 'Starter på nytt'] : ['Stopper tjenester', 'Gjenoppretter ' + kind.ver, 'Starter på nytt'];
    let i = 0, p = 0; const t = setInterval(() => {
      p += kind === 'update' ? 4 : 6;
      if (p >= 100) { p = 0; i++; }
      if (fail && i === 4 && p > 40) { clearInterval(t); const prev = u.version; const n = { ...u, failNext: false, log: [{ date: now(), text: 'Oppdatering til ' + vnum(rel.tag) + ' feilet ved oppstart. Gjenopprettet ' + prev + ' automatisk.', bad: true }, ...u.log].slice(0, 8) }; saveUpd(n); onTick({ done: true, failed: true, upd: n }); return; }
      if (i >= steps.length) { clearInterval(t); let n;
        if (kind === 'update') n = { ...u, version: vnum(rel.tag), latest: null, backups: [{ id: 'b' + Date.now(), ver: u.version, date: now(), kind: 'Automatisk før oppdatering' }, ...u.backups].slice(0, 6), log: [{ date: now(), text: 'Oppdatert ' + u.version + ' → ' + vnum(rel.tag) }, ...u.log].slice(0, 8) };
        else n = { ...u, version: kind.ver, latest: null, log: [{ date: now(), text: 'Gjenopprettet backup ' + kind.ver + ' (' + kind.date + ')' }, ...u.log].slice(0, 8) };
        saveUpd(n); onTick({ done: true, failed: false, upd: n }); return; }
      onTick({ done: false, step: steps[i], idx: i, total: steps.length, pct: Math.round(((i + p / 100) / steps.length) * 100) });
    }, 70);
    return () => clearInterval(t);
  }
  function backupNow(u) { const n = { ...u, backups: [{ id: 'b' + Date.now(), ver: u.version, date: now(), kind: 'Manuell' }, ...u.backups].slice(0, 6) }; saveUpd(n); return n; }
  function loadNames() { let j = {}; try { j = JSON.parse(localStorage.getItem('skjold-names') || '{}') || {}; } catch (e) {} return { nAux1: j.nAux1 || 'AUX 1', nAux2: j.nAux2 || 'AUX 2', nUsb1: j.nUsb1 || 'PC', nUsb2: j.nUsb2 || 'Switch' }; }
  function saveName(key, v) { const n = loadNames(); n[key] = v; try { localStorage.setItem('skjold-names', JSON.stringify(n)); } catch (e) {} return n; }
  // Standby-klokker. Tegnes i 128×64 logiske piksler (OLED) og skaleres. Dempet farge + små forskyvninger mot innbrenning.
  const CLOCKS = ['Tynn', 'Stor', 'Analog', 'Ord', 'Linje', 'Dato'];
  const HW = ['tolv', 'ett', 'to', 'tre', 'fire', 'fem', 'seks', 'sju', 'åtte', 'ni', 'ti', 'elleve', 'tolv'];
  const DAYS = ['søndag', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag'], MON = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember'];
  function wordTime(d) { const m = Math.round(d.getMinutes() / 5) * 5 % 60, h0 = d.getHours() + (d.getMinutes() >= 58 ? 1 : 0), h = h0 % 12, n = HW[h === 0 ? 12 : h], n1 = HW[(h + 1) % 12 === 0 ? 12 : (h + 1) % 12];
    return [['klokka er', n], ['fem over', n], ['ti over', n], ['kvart over', n], ['ti på halv', n1], ['fem på halv', n1], ['halv', n1], ['fem over halv', n1], ['ti over halv', n1], ['kvart på', n1], ['ti på', n1], ['fem på', n1]][m / 5]; }
  function drawClock(g, w, h, style, d, o) {
    o = o || {}; const k = w / 128, oy = (h - 64 * k) / 2, F = '"Helvetica Neue",Arial,sans-serif', C = o.color || '#5a5a55', mi = d.getMinutes(), dx = o.still ? 0 : ((mi % 5) - 2) * 1.5, dy = o.still ? 0 : ((mi % 3) - 1) * 1.5;
    const hh = String(d.getHours()).padStart(2, '0'), mm = String(mi).padStart(2, '0');
    g.save(); g.translate(0, oy); g.scale(k, k); g.translate(dx, dy); g.fillStyle = C; g.strokeStyle = C; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    if (style === 0) { g.font = '300 22px ' + F; g.fillText(hh + ':' + mm, 64, 40); }
    else if (style === 1) { g.font = '700 40px ' + F; g.fillText(hh + ':' + mm, 64, 47); }
    else if (style === 2) { const cx = 40, cy = 32, r = 24; g.lineWidth = 1; g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke();
      for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2, l = i % 3 ? 2 : 4; g.beginPath(); g.moveTo(cx + Math.sin(a) * (r - 1.5), cy - Math.cos(a) * (r - 1.5)); g.lineTo(cx + Math.sin(a) * (r - 1.5 - l), cy - Math.cos(a) * (r - 1.5 - l)); g.stroke(); }
      const ha = ((d.getHours() % 12) + mi / 60) / 12 * Math.PI * 2, ma = mi / 60 * Math.PI * 2; g.lineCap = 'round';
      g.lineWidth = 2.4; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.sin(ha) * 12, cy - Math.cos(ha) * 12); g.stroke();
      g.lineWidth = 1.4; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.sin(ma) * 19, cy - Math.cos(ma) * 19); g.stroke(); g.beginPath(); g.arc(cx, cy, 1.6, 0, Math.PI * 2); g.fill();
      g.textAlign = 'left'; g.font = '600 9px ' + F; g.fillText(DAYS[d.getDay()].slice(0, 3).replace(/^./, c => c.toUpperCase()), 74, 30); g.font = '400 8px ' + F; g.fillText(d.getDate() + '. ' + MON[d.getMonth()].slice(0, 3), 74, 41); }
    else if (style === 3) { const [a, b] = wordTime(d); g.font = '300 11px ' + F; g.fillText(a, 64, 28); g.font = '600 15px ' + F; g.fillText(b, 64, 45); }
    else if (style === 4) { const p = (d.getHours() * 60 + mi) / 1440; g.fillRect(8, 40, 112, 0.8); for (let i = 0; i <= 24; i += 6) g.fillRect(8 + 112 * i / 24 - 0.4, 37.5, 0.8, 5);
      g.beginPath(); g.arc(8 + 112 * p, 40.4, 2.4, 0, Math.PI * 2); g.fill(); g.font = '400 10px ' + F; g.textAlign = p > 0.75 ? 'right' : p < 0.25 ? 'left' : 'center'; g.fillText(hh + ':' + mm, 8 + 112 * p, 31); }
    else { g.font = '300 26px ' + F; g.fillText(hh + ':' + mm, 64, 34); g.font = '400 8px ' + F; g.fillText(DAYS[d.getDay()].replace(/^./, c => c.toUpperCase()) + ' ' + d.getDate() + '. ' + MON[d.getMonth()], 64, 48); }
    g.restore(); }
  // System med flere rom. S1 = forsterker med skjerm og knapper. Node = ren Raspberry Pi (3B/4) med bare lydutgang.
  const DEVTYPES = { s1: { n: 'Skjold S1', d: 'Forsterker med skjerm, knapper og AUX/USB-innganger', icon: 'M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1', inputs: ['AirPlay', 'Blåtann', 'AUX', 'Radio', 'USB'] }, node: { n: 'Skjold Node', d: 'Raspberry Pi 3B eller 4 med bare lydutgang. Kobles til egen forsterker, aktive høyttalere eller DAC.', icon: 'M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0', inputs: ['AirPlay', 'Blåtann', 'Radio'] } };
  const SYS_DEF = { active: 'stue', rooms: [
    { id: 'stue', name: 'Stue', type: 's1', hw: 'Raspberry Pi 4 · TPA3116 2 × 50 W', vol: 42, group: 'g1', np: null },
    { id: 'kjokken', name: 'Kjøkken', type: 'node', hw: 'Raspberry Pi 4 · HiFiBerry DAC+', vol: 30, group: 'g1', np: null },
    { id: 'kontor', name: 'Kontor', type: 'node', hw: 'Raspberry Pi 3B · 3,5 mm', vol: 25, group: null, np: ['Teardrop', 'Massive Attack', 'AirPlay'] }] };
  function loadSys() { try { const j = JSON.parse(localStorage.getItem('skjold-sys') || 'null'); if (j && j.rooms) return j; } catch (e) {} return JSON.parse(JSON.stringify(SYS_DEF)); }
  function saveSys(s) { try { localStorage.setItem('skjold-sys', JSON.stringify(s)); } catch (e) {} }
  const catsFor = type => CATS.filter(c => !c.dev || c.dev === type).map(c => ({ ...c, items: c.items.filter(d => !d.dev || d.dev === type) }));
  function groupOf(sys, id) { const r = sys.rooms.find(x => x.id === id); return r && r.group ? sys.rooms.filter(x => x.group === r.group) : [r]; }
  function groupLabel(sys, id) { const g = groupOf(sys, id); return g[0] ? (g.find(x => x.id === id) || g[0]).name + (g.length > 1 ? ' + ' + (g.length - 1) : '') : ''; }
  function toggleInGroup(sys, activeId, id) { const n = JSON.parse(JSON.stringify(sys)), a = n.rooms.find(x => x.id === activeId), r = n.rooms.find(x => x.id === id); if (!a || !r || r.id === a.id) return n;
    if (!a.group) a.group = 'g' + Date.now(); if (r.group === a.group) r.group = null; else { r.group = a.group; r.np = null; }
    const left = n.rooms.filter(x => x.group === a.group); if (left.length === 1) a.group = null; return n; }
  function groupAll(sys) { const n = JSON.parse(JSON.stringify(sys)); n.rooms.forEach(r => { r.group = 'gall'; r.np = null; }); return n; }
  const ROLES = ['Stereo', 'Venstre', 'Høyre', 'Bak V', 'Bak H', 'Sub'];
  function setGroupMode(sys, gid, mode) { const n = JSON.parse(JSON.stringify(sys)); n.modes = { ...(n.modes || {}), [gid]: mode }; if (mode === 'surround') { let i = 0; n.rooms.forEach(r => { if (r.group === gid && r.role == null) r.role = [0, 3, 4, 5][Math.min(3, i++)]; }); } return n; }
  function setRole(sys, id, role) { const n = JSON.parse(JSON.stringify(sys)); n.rooms.forEach(r => { if (r.id === id) r.role = role; }); return n; }
  const BRAND = { spotify: 'spotify.com', lyrion: 'lyrion.org', ha: 'home-assistant.io', homey: 'homey.app', airplay: 'apple.com', bluetooth: 'bluetooth.com' };
  function brandBg(id) { const d = BRAND[id]; return d ? 'url("https://www.google.com/s2/favicons?domain=' + d + '&sz=128") center / 58% auto no-repeat, #f4f2ee' : ''; }
  const slug = s => s.toLowerCase().replace(/æ/g, 'ae').replace(/ø/g, 'o').replace(/å/g, 'a').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  window.SKJOLD = { ROLES, setGroupMode, setRole, brandBg, fetchLogos, onLogos, slug, DEVTYPES, loadSys, saveSys, catsFor, groupOf, groupLabel, toggleInGroup, groupAll, CLOCKS, drawClock, wordTime, loadNames, saveName, loadUpd, saveUpd, findRelease, runJob, backupNow, RELEASES, now, CATALOG, art, loadRadio, saveRadio, nowPlaying, MAXRADIO: 6, CATS, DEF, EQ, NAMES, PRESETS_RADIO, fmt, loadEq, saveEq, activeSrc, curve };
})();
