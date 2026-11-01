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
      { ...bool('perIn', 'Volum per inngang', 'Hver inngang husker sitt eget volum'), dev: ['s1', 'node'] }, { ...bool('hpOwn', 'Eget volum for hodetelefoner'), dev: 's1' },
      { ...num('lvlAux', 'Nivå AUX', -6, 6, 'dB', 'Juster så AUX er like høy som strømming'), dev: 's1' }, { ...num('lvlUsb', 'Nivå USB', -6, 6, 'dB'), dev: 's1' },
      { kind: 'act', n: 'Test høyttalerne', id: 'testSpk', label: 'Spill av', safe: true, hint: 'Spiller en kort tone i venstre og så i høyre høyttaler, så du kan sjekke at de er koblet riktig' }] },
    { id: 'utgang', n: 'Lydutgang', sub: 'DAC, HDMI, optisk eller 3,5 mm', dev: ['node', 'core'], items: [
      opt('out', 'Utgang', ['3,5 mm (innebygd)', 'HDMI', 'USB-DAC', 'I²S-kort (HiFiBerry / IQaudio)', 'Optisk (S/PDIF)'], 'Pi 3B og Pi 4 har 3,5 mm og HDMI. Et I²S-kort gir best lyd.'),
      opt('hat', 'I²S-kort', ['HiFiBerry DAC+', 'HiFiBerry DAC2 HD', 'IQaudio DAC Pro', 'Allo Boss'], 'Brukes bare når utgang er I²S-kort'),
      opt('rate', 'Samplingsfrekvens', ['44,1 kHz', '48 kHz', '96 kHz', 'Følg kilden']),
      opt('mixer', 'Volumkontroll', ['Programvare', 'Maskinvare (DAC)', 'Fast 100 % (styres av forsterker)'], 'Velg fast hvis enheten er koblet til en egen forsterker med volumknapp'),
      { kind: 'act', n: 'Test utgang', id: 'testOut', label: 'Spill testtone', safe: true }] },
    { id: 'tilkobling', n: 'Tilkobling', sub: 'Navn og Blåtann', items: [
      opt('name', 'Enhetsnavn', NAMES, 'Navnet som vises i AirPlay og Blåtann'),
      { ...str('nAux1', 'Navn på AUX 1', 'AUX 1', 'Vises på skjermen og i appen'), dev: 's1' }, { ...str('nAux2', 'Navn på AUX 2', 'AUX 2'), dev: 's1' },
      { ...str('nUsb1', 'Navn på USB-C «PC 1»', 'PC', 'For eksempel Mac eller Jobb-PC'), dev: 's1' }, { ...str('nUsb2', 'Navn på USB-C «PC 2»', 'Switch'), dev: 's1' },
      { kind: 'info', n: 'Parede enheter', key: 'btDev' },
      { kind: 'act', n: 'Blåtann-paring', id: 'btPair', label: 'Start paring', safe: true, dev: ['node', 'core'], hint: 'Enheten har ingen knapp. Gjør den synlig for Blåtann i 2 minutter herfra.' },
      { ...bool('btAuto', 'Blåtann alltid synlig', 'Kan pares uten å starte paring først. Mindre sikkert.'), dev: ['node', 'core'] },
      { kind: 'act', n: 'Glem alle Blåtann-enheter', id: 'forget', label: 'Glem alle' }] },
    { id: 'radio', n: 'Radio', sub: 'Favoritter, knapper og oppstart', items: [
      { ...opt('hold', 'Hold radioknappen', PRESETS_RADIO, 'Kanalen som spilles når du holder radioknappen inne'), dev: 's1' },
      { ...opt('nodeStart', 'Kanal ved oppstart', ['Ingen', ...PRESETS_RADIO], 'Enheten har ingen knapper. Velg om den skal starte en radiokanal når den slås på.'), dev: ['node', 'core'] }] },
    { id: 'tjenester', n: 'Musikktjenester', sub: 'Spotify, UPnP/DLNA, YouTube Music, Navidrome', items: [
      bool('spEn', 'Spotify Connect', 'Vises som høyttaler i Spotify-appen'),
      bool('upnpEn', 'UPnP/DLNA-mottaker', 'Vises som høyttaler i apper som BubbleUPnP, foobar2000, Plex og «Cast til enhet» i Windows'),
      { kind: 'info', n: 'Navn på nettverket', val: 'Skjold · romnavn', hint: 'Samme navn som i AirPlay. Endres under Enhet.' },
      bool('ytmEn', 'YouTube Music', 'Krever YouTube Music Premium. Gratiskontoer virker ikke.'),
      { ...str('ytmUser', 'Google-konto', 'navn@gmail.com', 'Gmail-adressen, eller den 21-sifrede ID-en for en merkekonto'), long: true, max: 64 },
      { ...str('ytmCookie', 'Innloggings-cookie', 'Lim inn Cookie-verdien', 'Google tillater ikke vanlig innlogging for andre apper. Cookien må hentes på nytt når den utløper.'), long: true, max: 8000, secret: true },
      { kind: 'steps', n: 'Slik henter du cookien', steps: ['Åpne music.youtube.com i et privat vindu (inkognito) på en datamaskin og logg inn.', 'Åpne utviklerverktøyene og velg fanen Nettverk (Network).', 'Skriv /browse i filterfeltet. Åpne en av spillelistene dine.', 'Klikk på forespørselen som dukker opp. Under Request Headers kopierer du hele verdien til Cookie, uten mellomrom foran eller bak.', 'Lukk det private vinduet med en gang, uten å logge ut. Lim inn verdien over.'] },
      { kind: 'info', n: 'PO-token-tjeneste', val: 'Innebygd · kjører', hint: 'Bekrefter overfor Google at avspillingen kommer fra en ekte YouTube-klient' },
      { kind: 'act', n: 'Test innlogging', id: 'ytmTest', label: 'Test', safe: true },
      bool('ndEn', 'Navidrome', 'Eget musikkbibliotek via Subsonic-API'),
      str('ndUrl', 'Navidrome-server', 'http://192.168.1.10:4533', 'Adressen til Navidrome-serveren på hjemmenettet'),
      str('ndUser', 'Brukernavn', 'brukernavn'),
      { kind: 'act', n: 'Test Navidrome', id: 'ndTest', label: 'Test tilkobling', safe: true }] },
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
    names: ['Dypbass', 'Bass', 'Mellomtone', 'Presens', 'Luft'],
    desc: ['Trommer, bassgitar og dunk. Mye her kan gi rumling.', 'Fylde og varme. For mye gjør lyden grøtete.', 'Stemmer og de fleste instrumenter.', 'Klarhet i tale og vokal. For mye blir skarpt.', 'Cymbaler, glans og romfølelse.'],
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
  function searchRadio(q) { const u = 'https://de1.api.radio-browser.info/json/stations/search?limit=20&hidebroken=true&order=clickcount&reverse=true&name=' + encodeURIComponent(q);
    return fetch(u).then(r => r.json()).then(a => a.map(s => ({ name: (s.name || '').trim(), genre: (s.tags || '').split(',').filter(Boolean).slice(0, 2).join(', '), url: s.url_resolved || s.url, country: s.countrycode || '', br: s.bitrate || 0, codec: s.codec || '' })).filter(s => s.name && s.url)).catch(() => []); }
  function testStream(url) { return new Promise(res => { if (!/^https?:\/\//i.test(url)) return res(false); const a = new Audio(); let done = false; const fin = ok => { if (done) return; done = true; try { a.pause(); a.removeAttribute('src'); a.load(); } catch (e) {} res(ok); }; a.oncanplay = () => fin(true); a.onerror = () => fin(false); setTimeout(() => fin(false), 8000); a.preload = 'auto'; a.src = url; a.load(); }); }
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
  function loadNames() { let j = {}; try { j = JSON.parse(localStorage.getItem('skjold-names') || '{}') || {}; } catch (e) {} return { ...j, nAux1: j.nAux1 || 'AUX 1', nAux2: j.nAux2 || 'AUX 2', nUsb1: j.nUsb1 || 'PC', nUsb2: j.nUsb2 || 'Switch' }; }
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
  // System med flere rom. S1 = forsterker med skjerm og knapper. Node = ren Raspberry Pi (3B/4) med bare lydutgang. Core = sentral enhet (Lyrion-server) uten skjerm.
  const DEVTYPES = { s1: { n: 'Skjold S1', d: 'Forsterker med skjerm, knapper og AUX/USB-innganger', icon: 'M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1', inputs: ['AirPlay', 'Blåtann', 'AUX', 'Radio', 'USB'] }, node: { n: 'Skjold Node', d: 'Raspberry Pi 3B eller 4 med bare lydutgang. Kobles til egen forsterker, aktive høyttalere eller DAC.', icon: 'M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0', inputs: ['AirPlay', 'Blåtann', 'Radio'] }, core: { n: 'Skjold Core', d: 'Sentral enhet uten skjerm. Kjører Lyrion-serveren for hele systemet og kan spille via linjeutgang eller digital utgang.', icon: 'M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 8h8v8H8zM12 4V2M12 22v-2M4 12H2M22 12h-2M10 11h4M10 13h4', inputs: ['AirPlay', 'Blåtann', 'Radio'] } };
  const SYS_DEF = { active: 'stue', rooms: [
    { id: 'stue', name: 'Stue', type: 's1', hw: 'Pi Zero 2 W · TPA3116 2 × 50 W', vol: 42, group: 'g1', np: null },
    { id: 'kjokken', name: 'Kjøkken', type: 'node', hw: 'Raspberry Pi 4 · HiFiBerry DAC+', vol: 30, group: 'g1', np: null },
    { id: 'kontor', name: 'Kontor', type: 'node', hw: 'Raspberry Pi 3B · 3,5 mm', vol: 25, group: null, np: ['Teardrop', 'Massive Attack', 'AirPlay'] },
    { id: 'core', name: 'Hjemmekino', type: 'core', hw: 'Raspberry Pi 5 · Lyrion-server · optisk ut', vol: 35, group: null, np: null }] };
  function loadSys() { try { const j = JSON.parse(localStorage.getItem('skjold-sys') || 'null'); if (j && j.rooms) { j.rooms.forEach(r => { if (r.type === 's1' && /Raspberry Pi 4/.test(r.hw || '')) r.hw = 'Pi Zero 2 W · TPA3116 2 × 50 W'; }); return j; } } catch (e) {} return JSON.parse(JSON.stringify(SYS_DEF)); }
  function saveSys(s) { try { localStorage.setItem('skjold-sys', JSON.stringify(s)); } catch (e) {} }
  const forDev = (x, type) => !x.dev || [].concat(x.dev).includes(type); // dev: 's1' | 'node' | 'core' or a list
  const catsFor = type => CATS.filter(c => forDev(c, type)).map(c => ({ ...c, items: c.items.filter(d => forDev(d, type)) })).filter(c => c.items.length);
  function groupOf(sys, id) { const r = sys.rooms.find(x => x.id === id); return r && r.group ? sys.rooms.filter(x => x.group === r.group) : [r]; }
  function groupLabel(sys, id) { const g = groupOf(sys, id); return g[0] ? (g.find(x => x.id === id) || g[0]).name + (g.length > 1 ? ' + ' + (g.length - 1) : '') : ''; }
  function toggleInGroup(sys, activeId, id) { const n = JSON.parse(JSON.stringify(sys)), a = n.rooms.find(x => x.id === activeId), r = n.rooms.find(x => x.id === id); if (!a || !r || r.id === a.id) return n;
    if (!a.group) a.group = 'g' + Date.now(); if (r.group === a.group) r.group = null; else { r.group = a.group; r.np = null; }
    const left = n.rooms.filter(x => x.group === a.group); if (left.length === 1) a.group = null; return n; }
  function groupAll(sys) { const n = JSON.parse(JSON.stringify(sys)); n.rooms.forEach(r => { r.group = 'gall'; r.np = null; }); return n; }
  const ROLES = ['Stereo', 'Venstre', 'Høyre', 'Bak V', 'Bak H', 'Sub'];
  function setGroupMode(sys, gid, mode) { const n = JSON.parse(JSON.stringify(sys)); n.modes = { ...(n.modes || {}), [gid]: mode }; if (mode === 'surround') { let i = 0; n.rooms.forEach(r => { if (r.group === gid && r.role == null) r.role = [0, 3, 4, 5][Math.min(3, i++)]; }); } return n; }
  function setRole(sys, id, role) { const n = JSON.parse(JSON.stringify(sys)); n.rooms.forEach(r => { if (r.id === id) r.role = role; }); return n; }
  const BRAND = { spotify: 'spotify.com', lyrion: 'lyrion.org', ha: 'home-assistant.io', homey: 'homey.app', airplay: 'apple.com', bluetooth: 'bluetooth.com', ytmusic: 'music.youtube.com', navidrome: 'navidrome.org' };
  // [bakgrunn, farge, strek-sti, fyll-sti, merke-sti (viewBox 24, fyll), ikonstørrelse]
  const BP = {"spotify":"M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z","youtubemusic":"M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z","bluetooth":"M12 0C6.76 0 3.1484 2.4895 3.1484 12S6.76 24 12 24c5.24 0 8.8516-2.4895 8.8516-12S17.24 0 12 0zm-.7773 1.6816l6.2148 6.2149L13.334 12l4.1035 4.1035-6.2148 6.2149V14.125l-3.418 3.42-1.2422-1.2442L10.8515 12l-4.289-4.3008 1.2422-1.2441 3.418 3.4199V1.6816zm1.748 4.2442v3.9687l1.9844-1.9843-1.9844-1.9844zm0 8.1816v3.9668l1.9844-1.9844-1.9844-1.9824Z","airplayaudio":"M11.908.183a12.012 12.012 0 00-8.044 3.172c-4.882 4.475-5.166 12.08-.692 16.962.204.244.448.447.692.692a.315.315 0 00.408-.04l.53-.61a.32.32 0 000-.448C.53 15.965.243 9.253 4.23 4.982 8.217.711 14.889.427 19.16 4.414c4.271 3.986 4.555 10.655.568 14.927-.203.203-.365.407-.568.57a.32.32 0 000 .447l.53.611a.37.37 0 00.446.04c4.882-4.516 5.166-12.081.692-16.962a11.98 11.98 0 00-8.92-3.864zm.387 3.518A8.607 8.607 0 006.143 6c-3.458 3.213-3.66 8.623-.447 12.08.122.123.243.285.406.407a.319.319 0 00.447 0l.53-.61a.32.32 0 000-.446A7.263 7.263 0 014.8 12.183c0-3.946 3.212-7.16 7.158-7.16s7.16 3.253 7.16 7.199a7.207 7.207 0 01-2.238 5.209.319.319 0 000 .447l.529.61c.122.121.325.162.447.04a8.599 8.599 0 00.408-12.122 8.494 8.494 0 00-5.97-2.705zm-.266 3.316A5.198 5.198 0 008.34 8.48c-2.075 1.993-2.115 5.247-.122 7.322l.121.123a.319.319 0 00.447 0l.53-.611a.32.32 0 000-.448 3.814 3.814 0 01-1.098-2.683 3.732 3.732 0 013.742-3.742 3.732 3.732 0 013.742 3.742c0 1.017-.406 1.951-1.139 2.683a.32.32 0 000 .448l.53.61a.32.32 0 00.447 0c2.034-1.992 2.116-5.246.123-7.321a5.128 5.128 0 00-3.633-1.586zm.006 7.744a.599.599 0 00-.402.146l-.04.041-7.159 8.055a.506.506 0 00.041.69.437.437 0 00.283.124h14.36a.495.495 0 00.489-.488.463.463 0 00-.121-.326l-7.08-8.055a.5.5 0 00-.37-.187z"};
  const SRCICON = {
    Radio: ['#d9a441', '#0b0b0c', 'M4 9h16v11H4zM8 9l9-5M14 13h3M14 16h3', 'M9.5 12.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z', '', '47%'],
    AirPlay: ['linear-gradient(160deg,#3a3a3e,#0b0b0c)', '#ffffff', '', '', BP.airplayaudio, '48%'],
    'Blåtann': ['#0082fc', '#ffffff', '', '', BP.bluetooth, '46%'],
    Spotify: ['#000000', '#1ed760', '', '', BP.spotify, '100%'],
    'YouTube Music': ['#ffffff', '#ff0000', '', '', BP.youtubemusic, '100%'],
    Navidrome: ['url("logo/brands/navidrome.png") center / 104% auto no-repeat, #0b0b0c', '#ffffff', '', '', '', '0'],
    Lyrion: ['url("logo/brands/lyrion_fav.png") center / cover no-repeat, #0b0b0c', '#ffffff', '', '', '', '0'],
    'UPnP/DLNA': ['#ffffff', '#1b1b1c', '', '', 'M23.255 12.667H13.02c-1.052 0-2.1.489-2.693 1.266v-.017a3.24 3.24 0 01-2.629 1.353 3.25 3.25 0 010-6.502c1.085 0 2.04.536 2.63 1.353v-.013c.591.776 1.64 1.273 2.692 1.273h10.129c.186-.005.873-.095.848-.981-.884-5.086-5.88-8.987-11.923-8.987-3.722 0-7.048 1.48-9.263 3.803-.356.527.014.689.35.734H9.77c1.05 0 2.1-.498 2.692-1.277v.018a3.242 3.242 0 012.63-1.355 3.252 3.252 0 010 6.503 3.24 3.24 0 01-2.63-1.355v.019c-.592-.78-1.642-1.266-2.692-1.266H2.55l.028.003s-1.068-.06-1.719.859C.361 8.9 0 10.62 0 12.002c0 1.388.198 2.65.867 3.923.564.908 1.71.85 1.71.85l-.042.005h7.233c1.05 0 2.1-.49 2.692-1.268v.02a3.242 3.242 0 012.63-1.356 3.251 3.251 0 010 6.502 3.242 3.242 0 01-2.63-1.354v.018c-.592-.779-1.642-1.277-2.692-1.277H3.164c-.328.042-.698.198-.379.7 2.216 2.336 5.555 3.823 9.289 3.823 6.054 0 11.056-3.91 11.926-9.009-.004-.713-.489-.877-.745-.912z', '60%'],
    AUX: ['#3a3a37', '#f2f2ee', 'M12 2.5v3M9.5 5.5h5v4h-5zM10.8 9.5h2.4v8.2a1.2 1.2 0 0 1-2.4 0zM10.8 13h2.4', '', '', '47%'],
    USB: ['#2a2a2c', '#f2f2ee', 'M12 3v15M8 9v2.5l4 3M16 8v3l-4 3', 'M12 2l-2 3h4zM12 18a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM7 7.5h2v2H7zM16 6.5a1.1 1.1 0 1 0 0 2.2 1.1 1.1 0 0 0 0-2.2z', '', '47%'] };
  SRCICON['YT Music'] = SRCICON['YouTube Music'];
  function srcIcon(label) { const s = SRCICON[label] || ['#2a2a2c', '#f2f2ee', '', '', '', '47%']; return { bg: s[0], fg: s[1], st: s[2], fi: s[3], fp: s[4], sz: s[5] }; }
  function brandBg(id) { const d = BRAND[id]; return d ? 'url("https://www.google.com/s2/favicons?domain=' + d + '&sz=128") center / 58% auto no-repeat, #f4f2ee' : ''; }
  const slug = s => s.toLowerCase().replace(/æ/g, 'ae').replace(/ø/g, 'o').replace(/å/g, 'a').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  window.SKJOLD = { srcIcon, searchRadio, testStream, ROLES, setGroupMode, setRole, brandBg, fetchLogos, onLogos, slug, DEVTYPES, loadSys, saveSys, catsFor, groupOf, groupLabel, toggleInGroup, groupAll, CLOCKS, drawClock, wordTime, loadNames, saveName, loadUpd, saveUpd, findRelease, runJob, backupNow, RELEASES, now, CATALOG, art, loadRadio, saveRadio, nowPlaying, MAXRADIO: 50, CATS, DEF, EQ, NAMES, PRESETS_RADIO, fmt, loadEq, saveEq, activeSrc, curve };
})();
