// Felles innstillingsskjema og EQ-profiler for Skjold S1 (web + app). Samme nøkler som forsterkerens meny.
(function () {
  const NAMES = ['Skjold S1', 'Stue', 'Kontor', 'Soverom'];
  const PRESETS_RADIO = ['NRK P1', 'NRK P2', 'NRK P3', 'P4 Norge', 'Radio Norge', 'NRK Klassisk'];
  const fmt = {
    dB: v => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + ' dB',
    bal: v => v === 0 ? 'Midt' : (v < 0 ? 'V ' : 'H ') + Math.abs(v),
    pct: v => v * 10 + ' %'
  };
  // Skjermtyper. tech styrer menyene: OLED har innbrenning og kontrast, TFT har bakgrunnslys og farge.
  const DISPLAYS = {
    oled13: { n: '1,3″ OLED', res: '128 × 64', tech: 'oled', w: 128, h: 64 },
    oled242: { n: '2,42″ OLED', res: '128 × 64', tech: 'oled', w: 128, h: 64 },
    oled091: { n: '0,91″ OLED', res: '128 × 32', tech: 'oled', w: 128, h: 32 },
    tft18: { n: '1,8″ TFT', res: '160 × 128', tech: 'tft', w: 160, h: 128 },
    tft20: { n: '2,0″ TFT', res: '320 × 240', tech: 'tft', w: 320, h: 240 },
    tft458: { n: '4,58″ TFT bar', res: '960 × 320', tech: 'tft', w: 960, h: 320 },
    none: { n: 'Ingen skjerm', res: '', tech: 'none', w: 0, h: 0 } };
  const DISP_FOR = { s1: ['tft458', 'oled13', 'oled242', 'tft20'], node: ['oled091', 'oled13', 'tft18', 'none'] };
  const DISP_DEF = { s1: 'tft458', node: 'oled091' };
  const dispKey = room => { const t = (room && room.type) || 's1', k = room && room.disp; return DISP_FOR[t] && DISP_FOR[t].includes(k) ? k : DISP_DEF[t] || 'none'; };
  const dispOf = room => DISPLAYS[dispKey(room)];
  const COMPACT_CLOCKS = [0, 1, 3, 4];
  const clocksFor = key => { const D = DISPLAYS[key] || DISPLAYS.oled13; if (D.tech === 'none') return []; if (D.w >= 960) return CLOCKS.map((n, i) => [n, i]); return (D.h / D.w < 0.4 ? COMPACT_CLOCKS : [0, 1, 2, 3, 4, 5]).map(i => [CLOCKS[i], i]); };
  const CLOCK_COLS = ['#e8e8e2', '#f0c46a', '#7dd88f', '#7fb2ff'];
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
    { id: 'touch', n: 'Skjold Touch', sub: 'Rolle, skjerm og standby', dev: 'touch', items: [
      opt('tRole', 'Rolle', ['Spiller og fjernkontroll', 'Bare spiller', 'Bare fjernkontroll'], 'Som spiller har den egen lydutgang (RCA og 3,5 mm). Som fjernkontroll styrer den alle Skjold-enhetene i huset.'),
      opt('tCtl', 'Styrer som standard', ['Seg selv', 'Sist brukte rom', 'Alle rom'], 'Hvilket rom «Spiller nå» viser når skjermen våkner'),
      num('tBri', 'Lysstyrke', 10, 100, '%'), opt('tDim', 'Dimme etter', ['Av', '30 s', '1 min', '5 min']), opt('tOff', 'Slå av skjermen etter', ['Aldri', '5 min', '15 min', '1 t']),
      opt('tIdle', 'I standby vis', ['Klokke', 'Cover og klokke', 'Bilderamme', 'Svart']), bool('tNight', 'Nattmodus', 'Rødlig, svakt lys mellom 23 og 07'),
      bool('tWake', 'Vekk ved berøring', 'Første trykk vekker bare skjermen'), opt('tBtn', 'Av/på-knappen', ['Kort trykk: standby, hold: slå av', 'Kort trykk: pause', 'Kort trykk: skjerm av'])] },
    { id: 'utgang', n: 'Lydutgang', sub: 'DAC, HDMI, optisk eller 3,5 mm', dev: ['node', 'core', 'touch'], items: [
      opt('out', 'Utgang', ['3,5 mm (innebygd)', 'HDMI', 'USB-DAC', 'I²S-kort (HiFiBerry / IQaudio)', 'Optisk (S/PDIF)'], 'Pi 3B og Pi 4 har 3,5 mm og HDMI. Et I²S-kort gir best lyd.'),
      opt('hat', 'I²S-kort', ['Spotpear HIFI HAT (PCM5122)', 'HiFiBerry DAC+', 'HiFiBerry DAC2 HD', 'IQaudio DAC Pro', 'Allo Boss'], 'Brukes bare når utgang er I²S-kort'),
      opt('rate', 'Samplingsfrekvens', ['44,1 kHz', '48 kHz', '96 kHz', 'Følg kilden']),
      opt('mixer', 'Volumkontroll', ['Programvare', 'Maskinvare (DAC)', 'Fast 100 % (styres av forsterker)'], 'Velg fast hvis enheten er koblet til en egen forsterker med volumknapp'),
      { kind: 'act', n: 'Test utgang', id: 'testOut', label: 'Spill testtone', safe: true }] },
    { id: 'tilkobling', n: 'Tilkobling', sub: 'Navn og Blåtann', items: [
      opt('name', 'Enhetsnavn', NAMES, 'Navnet som vises i AirPlay og Blåtann'),
      { ...str('nAux1', 'Navn på AUX 1', 'AUX 1', 'Vises på skjermen og i appen'), dev: 's1' }, { ...str('nAux2', 'Navn på AUX 2', 'AUX 2'), dev: 's1' },
      { ...str('nUsb1', 'Navn på USB-C «PC 1»', 'PC', 'For eksempel Mac eller Jobb-PC'), dev: 's1' }, { ...str('nUsb2', 'Navn på USB-C «PC 2»', 'Switch'), dev: 's1' },
      { kind: 'info', n: 'Parede enheter', key: 'btDev' },
      { kind: 'act', n: 'Blåtann-paring', id: 'btPair', label: 'Start paring', safe: true, dev: ['node', 'core', 'touch'], hint: 'Enheten har ingen knapp. Gjør den synlig for Blåtann i 2 minutter herfra.' },
      { ...bool('btAuto', 'Blåtann alltid synlig', 'Kan pares uten å starte paring først. Mindre sikkert.'), dev: ['node', 'core', 'touch'] },
      { kind: 'act', n: 'Glem alle Blåtann-enheter', id: 'forget', label: 'Glem alle' }] },
    { id: 'radio', n: 'Radio', sub: 'Favoritter, knapper og oppstart', items: [
      { ...opt('hold', 'Hold radioknappen', PRESETS_RADIO, 'Kanalen som spilles når du holder radioknappen inne'), dev: 's1' },
      { ...opt('nodeStart', 'Kanal ved oppstart', ['Ingen', ...PRESETS_RADIO], 'Enheten har ingen knapper. Velg om den skal starte en radiokanal når den slås på.'), dev: ['node', 'core', 'touch'] }] },
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
    { id: 'skjerm', n: 'Skjerm og lys', dev: ['s1', 'node'], sub: 'Dimming, klokke, LED', items: [
      { ...opt('dim', 'Dimme skjermen etter', ['Av', '30 s', '1 min']), only: 'screen' },
      { ...opt('off', 'Slukk skjermen etter', ['Av', '2 min', '5 min']), only: 'screen', hintBy: { oled: 'Beskytter OLED-skjermen mot innbrenning', tft: 'Sparer strøm. TFT-skjermer får ikke innbrenning' }, listBy: { tft: ['Av', '5 min', '15 min'] } },
      { ...opt('contrast', 'Kontrast', ['Lav', 'Middels', 'Høy'], 'Lavere kontrast gir lengre levetid'), only: 'oled' },
      { ...num('bri', 'Bakgrunnslys', 1, 10, 'pct'), only: 'tft' },
      { ...opt('clockCol', 'Farge på klokken', ['Hvit', 'Gull', 'Grønn', 'Blå']), only: 'tft' },
      { ...bool('clock', 'Klokke i standby'), only: 'screen' }, { kind: 'clocks', k: 'clockStyle', n: 'Klokke i standby', only: 'screen' },
      { ...opt('led', 'LED-ringer', ['Høy', 'Middels', 'Lav', 'Av']), nBy: { node: 'LED over knappene' } }] },
    { id: 'strom', n: 'Strøm', sub: 'Standby og påslag', items: [
      opt('auto', 'Auto-standby uten lyd', ['Av', '20 min', '60 min']), bool('wake', 'Slå på ved signal', 'AirPlay eller Blåtann vekker forsterkeren')] },
    { id: 'oppdatering', n: 'Oppdatering', sub: 'GitHub, backup og gjenoppretting', items: [{ kind: 'update', n: 'Oppdatering' }] },
    { id: 'system', n: 'System', sub: 'Om, oppsett og tilbakestilling', items: [
      { kind: 'info', n: 'Programvare', val: '1.4.2' }, { kind: 'info', n: 'IP-adresse', val: '192.168.1.42' },
      { kind: 'info', n: 'Lyrion', key: 'lyrion' }, { kind: 'info', n: 'Serienummer', val: 'SKJ-S1-0001' },
      { kind: 'act', n: 'Kjør oppsett på nytt', id: 'setup', label: 'Start oppsett' },
      { kind: 'act', n: 'Fabrikkinnstillinger', id: 'reset', label: 'Tilbakestill' }] }
  ];
  const DEF = { bri: 8, contrast: 1, clockCol: 1, nodeStart: 0, btAuto: false, out: 3, hat: 0, rate: 3, mixer: 0, clockStyle: 0, nAux1: 'AUX 1', nAux2: 'AUX 2', nUsb1: 'PC', nUsb2: 'Switch', name: 0, lvlAux: 0, lvlUsb: 0, led: 0, voice: false, lang: 0, vv: 1, hold: 2, bass: 0, treb: 0, bal: 0, vstart: 0, vmax: 0, perIn: true, hpOwn: true, dim: 1, off: 1, clock: true, auto: 1, wake: true };
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
  const CLOCKS = ['Tynn', 'Stor', 'Analog', 'Ord', 'Linje', 'Dato', 'VU-metre', 'Radioskala', 'Glasspanel', 'Klokke og vær', 'Bare tid', 'Døgnstripe', 'Klokka i ord', 'Fotoramme', 'Nattlys', 'Analog og kalender'];
  const HW = ['tolv', 'ett', 'to', 'tre', 'fire', 'fem', 'seks', 'sju', 'åtte', 'ni', 'ti', 'elleve', 'tolv'];
  const DAYS = ['søndag', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag'], MON = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember'];
  function wordTime(d) { const m = Math.round(d.getMinutes() / 5) * 5 % 60, h0 = d.getHours() + (d.getMinutes() >= 58 ? 1 : 0), h = h0 % 12, n = HW[h === 0 ? 12 : h], n1 = HW[(h + 1) % 12 === 0 ? 12 : (h + 1) % 12];
    return [['klokka er', n], ['fem over', n], ['ti over', n], ['kvart over', n], ['ti på halv', n1], ['fem på halv', n1], ['halv', n1], ['fem over halv', n1], ['ti over halv', n1], ['kvart på', n1], ['ti på', n1], ['fem på', n1]][m / 5]; }
  function drawClockCompact(g, w, h, style, d, o) {
    const k = Math.min(h / 32, w / 128), ox = (w - 128 * k) / 2, oy = (h - 32 * k) / 2, F = '"Helvetica Neue",Arial,sans-serif', C = o.color || '#5a5a55', mi = d.getMinutes(), dx = o.still ? 0 : ((mi % 5) - 2) * 1.5;
    const hh = String(d.getHours()).padStart(2, '0'), mm = String(mi).padStart(2, '0');
    g.save(); g.translate(ox, oy); g.scale(k, k); g.translate(dx, 0); g.fillStyle = C; g.textAlign = 'center';
    if (style === 1) { g.font = '700 28px ' + F; g.fillText(hh + ':' + mm, 64, 27); }
    else if (style === 3) { const [a, b] = wordTime(d); g.font = '300 10px ' + F; g.fillText(a, 64, 13); g.font = '600 13px ' + F; g.fillText(b, 64, 28); }
    else if (style === 4) { const p = (d.getHours() * 60 + mi) / 1440; g.fillRect(8, 24, 112, 0.8); for (let i = 0; i <= 24; i += 6) g.fillRect(8 + 112 * i / 24 - 0.4, 22, 0.8, 4.5);
      g.beginPath(); g.arc(8 + 112 * p, 24.4, 2.2, 0, Math.PI * 2); g.fill(); g.font = '400 10px ' + F; g.textAlign = p > 0.75 ? 'right' : p < 0.25 ? 'left' : 'center'; g.fillText(hh + ':' + mm, 8 + 112 * p, 16); }
    else { g.font = '300 22px ' + F; g.fillText(hh + ':' + mm, 64, 24); }
    g.restore(); }

  // Brede standby-skjermer (S1 4,58″ bar, 960 × 320). Tegnes i 1920 × 640 og skaleres. Stil 6–15.
  const WIDE_DEF = { name: 'Skjold Stue', last: 'Midnight City · M83', weather: { t: 4, c: 'Lett regn · Oslo', hours: [['23', 4], ['00', 3], ['01', 3], ['02', 2]] }, sun: ['08:04', '16:06'], cal: { day: 'I MORGEN', items: ['09:30 Fotballtrening', '12:00 Middag hos mormor'] }, photo: null, caption: 'Hardangervidda · juli 2025', alarm: '06:30' };
  function drawWide(g, w, h, style, d, o) {
    o = Object.assign({}, WIDE_DEF, o || {}); const k = Math.min(w / 1920, h / 640), F = '"Helvetica Neue",Arial,sans-serif', t = (o.t != null ? o.t : performance.now() / 1000);
    const W = '#f6f3ee', Dm = 'rgba(246,243,238,.62)', Lo = 'rgba(246,243,238,.38)', mi = d.getMinutes(), hh = String(d.getHours()).padStart(2, '0'), mm = String(mi).padStart(2, '0'), HM = hh + ':' + mm;
    const date = DAYS[d.getDay()] + ' ' + d.getDate() + '. ' + MON[d.getMonth()];
    g.save(); g.translate((w - 1920 * k) / 2, (h - 640 * k) / 2); g.scale(k, k); g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 640); g.textBaseline = 'alphabetic';
    const tx = (s, x, y, px, wt, c, al) => { g.font = (wt || '') + ' ' + px + 'px ' + F; g.fillStyle = c; g.textAlign = al || 'left'; g.fillText(s, x, y); };
    const sp = (s, x, y, px, c, al) => { if ('letterSpacing' in g) g.letterSpacing = (px * 0.12) + 'px'; tx(s, x, y, px, '', c, al); if ('letterSpacing' in g) g.letterSpacing = '0px'; };
    const rr = (x, y, ww, hh2, r) => { g.beginPath(); g.roundRect(x, y, ww, hh2, r); };
    if (style === 6) {
      const face = (x0, lbl, ph) => { const fw = 500, fh = 400, y0 = 120, cx = x0 + fw / 2, cy = y0 + fh - 30, r = 300; const gr = g.createRadialGradient(cx, y0 + fh * 0.9, 20, cx, y0 + fh * 0.6, fw * 0.8); gr.addColorStop(0, '#fff4d8'); gr.addColorStop(1, '#d9bd7c'); g.fillStyle = gr; rr(x0, y0, fw, fh, 24); g.fill();
        g.save(); rr(x0, y0, fw, fh, 24); g.clip(); const a0 = -Math.PI * 0.78, a1 = -Math.PI * 0.22, ar = a0 + (a1 - a0) * 0.7;
        g.lineWidth = 5; g.strokeStyle = '#2a1f14'; g.beginPath(); g.arc(cx, cy, r - 60, a0, ar); g.stroke(); g.lineWidth = 12; g.strokeStyle = '#c0392b'; g.beginPath(); g.arc(cx, cy, r - 60, ar, a1); g.stroke();
        for (let i = 0; i <= 10; i++) { const a = a0 + (a1 - a0) * i / 10, l = i % 5 ? 16 : 30; g.lineWidth = i % 5 ? 3 : 5; g.strokeStyle = a > ar ? '#c0392b' : '#2a1f14'; g.beginPath(); g.moveTo(cx + Math.cos(a) * (r - 60), cy + Math.sin(a) * (r - 60)); g.lineTo(cx + Math.cos(a) * (r - 60 + l), cy + Math.sin(a) * (r - 60 + l)); g.stroke(); }
        tx('VU', cx, cy - 70, 44, 'bold', '#2a1f14', 'center'); tx(lbl, lbl === 'L' ? x0 + 40 : x0 + fw - 40, y0 + fh - 24, 30, 'bold', '#2a1f14', 'center');
        const v = 0.18 + 0.10 * Math.sin(t * 1.3 + ph) + 0.06 * Math.sin(t * 3.1 + ph * 2) + 0.03 * Math.sin(t * 7.7 + ph), a = a0 + (a1 - a0) * v; g.strokeStyle = '#1b1410'; g.lineWidth = 4; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a) * (r - 20), cy + Math.sin(a) * (r - 20)); g.stroke(); g.fillStyle = '#1b1410'; g.beginPath(); g.arc(cx, cy, 14, 0, 7); g.fill(); g.restore(); };
      face(40, 'L', 0); face(1380, 'R', 1.7); tx(HM, 960, 390, 230, '200', W, 'center'); tx(date, 960, 480, 40, '', Dm, 'center');
    } else if (style === 7) {
      const top = 420, H = 220, mins = d.getHours() * 60 + mi + d.getSeconds() / 60, X = f => 60 + f * 1800; const gr = g.createLinearGradient(0, top, 0, 640); gr.addColorStop(0, '#0d0a06'); gr.addColorStop(1, '#1d150b'); g.fillStyle = gr; g.fillRect(0, top, 1920, H);
      g.fillStyle = 'rgba(245,158,11,.3)'; g.fillRect(0, top, 1920, 2);
      for (let i = 0; i <= 96; i++) { const x = X(i / 96), maj = i % 4 === 0; g.fillStyle = maj ? 'rgba(246,243,238,.7)' : 'rgba(246,243,238,.3)'; g.fillRect(x - 1.5, top, 3, maj ? 70 : 40); }
      for (let hr = 0; hr <= 24; hr += 3) tx(String(hr).padStart(2, '0'), X(hr / 24), top + 140, 40, '', Math.abs(mins / 60 - hr) < 1.5 ? '#fde3b0' : 'rgba(246,243,238,.45)', 'center');
      const nx = X(mins / 1440); g.save(); g.shadowColor = 'rgba(255,90,31,.9)'; g.shadowBlur = 36; g.fillStyle = '#ff5a1f'; g.fillRect(nx - 4, top, 8, H); g.restore();
      tx(HM, 80, 330, 260, '200', W); tx(date, 1840, 150, 44, '', Dm, 'right'); if ('letterSpacing' in g) g.letterSpacing = '5px'; tx(o.name.toUpperCase(), 1840, 330, 30, 'bold', '#f59e0b', 'right'); if ('letterSpacing' in g) g.letterSpacing = '0px';
    } else if (style === 8) {
      const bg = g.createRadialGradient(290, 190, 0, 290, 190, 1000); bg.addColorStop(0, 'rgba(224,48,111,.28)'); bg.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = '#07050a'; g.fillRect(0, 0, 1920, 640); g.fillStyle = bg; g.fillRect(0, 0, 1920, 640);
      g.save(); g.globalAlpha = 0.55; const ag = g.createRadialGradient(240, 240, 10, 320, 320, 420); ag.addColorStop(0, '#e0306f'); ag.addColorStop(0.55, '#7a2fd0'); ag.addColorStop(1, '#3b1a8a'); g.fillStyle = o.artColor || ag; rr(56, 56, 528, 528, 28); g.fill(); g.restore();
      rr(632, 56, 1232, 528, 36); g.fillStyle = 'rgba(255,255,255,.06)'; g.fill(); g.strokeStyle = 'rgba(255,255,255,.1)'; g.lineWidth = 2; g.stroke();
      sp('STANDBY', 684, 124, 30, Lo); sp(o.name.toUpperCase(), 1812, 124, 30, Lo, 'right');
      g.font = '200 240px ' + F; const tw = g.measureText(HM).width; tx(HM, 676, 420, 240, '200', W); tx(date, 676 + tw + 44, 420, 48, '', Dm);
      tx('Sist spilt: ' + o.last, 684, 540, 34, '', Lo);
    } else if (style === 9) {
      tx(HM, 104, 340, 236, '200', W); tx(date, 108, 420, 48, '', Dm); g.fillStyle = 'rgba(255,255,255,.12)'; g.fillRect(959, 120, 2, 400);
      const wx = o.weather; g.font = '300 144px ' + F; const tw = g.measureText(wx.t + '°').width; tx(wx.t + '°', 1048, 300, 144, '300', W); tx(wx.c, 1048 + tw + 32, 300, 44, '', Dm);
      wx.hours.slice(0, 4).forEach(([hr, tt], i) => { tx(hr, 1048 + i * 200, 420, 30, '', Lo); tx(tt + '°', 1048 + i * 200, 484, 48, '', W); });
    } else if (style === 10) {
      const x = 960 + ((mi * 37) % 400) - 200, y = 360 + ((mi * 23) % 160) - 80; tx(HM, x, y, 192, '200', 'rgba(246,243,238,.42)', 'center');
    } else if (style === 11) {
      tx(HM, 104, 300, 220, '200', W); tx(date, 1816, 300, 44, '', Dm, 'right');
      const toF = s => { const [a, b] = s.split(':').map(Number); return (a * 60 + b) / 1440; }, s0 = toF(o.sun[0]), s1 = toF(o.sun[1]), X0 = 104, XW = 1712, Y = 452;
      const gr = g.createLinearGradient(X0, 0, X0 + XW, 0); gr.addColorStop(0, '#0d1530'); gr.addColorStop(Math.max(0, s0 - 0.02), '#0d1530'); gr.addColorStop(s0, '#d98a3a'); gr.addColorStop((s0 + s1) / 2, '#f2c76b'); gr.addColorStop(s1, '#d98a3a'); gr.addColorStop(Math.min(1, s1 + 0.02), '#0d1530'); gr.addColorStop(1, '#0d1530');
      rr(X0, Y, XW, 32, 16); g.fillStyle = gr; g.fill(); const p = (d.getHours() * 60 + mi) / 1440; rr(X0 + XW * p - 4, Y - 16, 8, 64, 4); g.fillStyle = W; g.fill();
      [['00', 0], ['☀ ' + o.sun[0], s0], ['12', 0.5], ['☾ ' + o.sun[1], s1], ['24', 1]].forEach(([s, f], i) => tx(s, X0 + XW * f, Y + 100, 30, '', Lo, i === 0 ? 'left' : i === 4 ? 'right' : 'center'));
    } else if (style === 12) {
      const [a, b] = wordTime(d), WS = ['KLOKKA', 'ER', 'FEM', 'TI', 'KVART', 'PÅ', 'OVER', 'HALV', 'ETT', 'TO', 'TRE', 'FIRE', 'FEM', 'SEKS', 'SJU', 'ÅTTE', 'NI', 'TI', 'ELLEVE', 'TOLV'];
      const lit = new Set([0, 1]), mw = a.toUpperCase().split(' ').filter(x => x !== 'KLOKKA' && x !== 'ER'); let from = 2; mw.forEach(x => { for (let i = from; i < 8; i++) if (WS[i] === x) { lit.add(i); from = i + 1; break; } });
      for (let i = 8; i < 20; i++) if (WS[i] === b.toUpperCase()) { lit.add(i); break; }
      g.font = 'bold 88px ' + F; if ('letterSpacing' in g) g.letterSpacing = '6px'; let x = 96, y = 160; WS.forEach((s, i) => { const ww = g.measureText(s).width; if (x + ww > 1824) { x = 96; y += 128; } g.fillStyle = lit.has(i) ? W : 'rgba(246,243,238,.1)'; g.textAlign = 'left'; g.fillText(s, x, y); x += ww + 48; }); if ('letterSpacing' in g) g.letterSpacing = '0px';
    } else if (style === 13) {
      if (o.photo && o.photo.width) { const s = Math.max(1920 / o.photo.width, 640 / o.photo.height); g.drawImage(o.photo, (1920 - o.photo.width * s) / 2, (640 - o.photo.height * s) / 2, o.photo.width * s, o.photo.height * s); }
      else { const gr = g.createLinearGradient(0, 0, 1920, 640); gr.addColorStop(0, '#2b3a2a'); gr.addColorStop(0.4, '#5b6b4a'); gr.addColorStop(0.75, '#c9b27a'); gr.addColorStop(1, '#e9d9a8'); g.fillStyle = gr; g.fillRect(0, 0, 1920, 640); }
      const sh = g.createLinearGradient(0, 0, 1056, 0); sh.addColorStop(0, 'rgba(0,0,0,.55)'); sh.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = sh; g.fillRect(0, 0, 1920, 640);
      tx(HM, 80, 520, 168, '300', '#fff'); tx(o.caption, 84, 584, 40, '', 'rgba(255,255,255,.85)');
    } else if (style === 14) {
      tx(HM, 1180, 400, 260, '200', '#7a1410', 'right'); if (o.alarm) tx('Alarm ' + o.alarm, 1260, 330, 40, '', '#4a0d0a'); tx('Nattmodus', 1260, 390, 40, '', '#4a0d0a');
    } else if (style === 15) {
      const cx = 380, cy = 320, r = 260; for (let i = 0; i < 60; i++) { const a = i / 60 * Math.PI * 2, maj = i % 5 === 0, l = maj ? 44 : 20; g.strokeStyle = maj ? W : 'rgba(246,243,238,.25)'; g.lineWidth = maj ? 8 : 4; g.beginPath(); g.moveTo(cx + Math.sin(a) * r, cy - Math.cos(a) * r); g.lineTo(cx + Math.sin(a) * (r - l), cy - Math.cos(a) * (r - l)); g.stroke(); }
      const s = d.getSeconds(), ha = ((d.getHours() % 12) + mi / 60) / 12 * Math.PI * 2, ma = (mi + s / 60) / 60 * Math.PI * 2, sa = s / 60 * Math.PI * 2; g.lineCap = 'round';
      [[ha, 144, 12, W], [ma, 216, 8, W], [sa, 232, 4, '#f59e0b']].forEach(([a, l, lw, c]) => { g.strokeStyle = c; g.lineWidth = lw; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.sin(a) * l, cy - Math.cos(a) * l); g.stroke(); });
      g.fillStyle = '#f59e0b'; g.beginPath(); g.arc(cx, cy, 14, 0, 7); g.fill(); g.lineCap = 'butt';
      tx(date, 820, 200, 44, '', Dm); sp(o.cal.day, 820, 300, 30, Lo); if (o.cal.items[0]) tx(o.cal.items[0], 820, 380, 72, '600', W); if (o.cal.items[1]) tx(o.cal.items[1], 820, 450, 44, '', Dm);
    }
    g.textAlign = 'left'; g.restore(); }
  function drawClock(g, w, h, style, d, o) {
    o = o || {}; if (style >= 6) return drawWide(g, w, h, style, d, o); if (h / w < 0.4) return drawClockCompact(g, w, h, style, d, o); const k = Math.min(w / 128, h / 64), oy = (h - 64 * k) / 2, ox = (w - 128 * k) / 2, F = '"Helvetica Neue",Arial,sans-serif', C = o.color || '#5a5a55', mi = d.getMinutes(), dx = o.still ? 0 : ((mi % 5) - 2) * 1.5, dy = o.still ? 0 : ((mi % 3) - 1) * 1.5;
    const hh = String(d.getHours()).padStart(2, '0'), mm = String(mi).padStart(2, '0');
    g.save(); g.translate(ox, oy); g.scale(k, k); g.translate(dx, dy); g.fillStyle = C; g.strokeStyle = C; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
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
  const DEVTYPES = { s1: { n: 'Skjold S1', d: 'Forsterker med skjerm, knapper og AUX/USB-innganger', icon: 'M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1', inputs: ['AirPlay', 'Blåtann', 'AUX', 'Radio', 'USB'] }, node: { n: 'Skjold Node', d: 'Raspberry Pi 3B eller 4 med bare lydutgang. Kobles til egen forsterker, aktive høyttalere eller DAC.', icon: 'M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0', inputs: ['AirPlay', 'Blåtann', 'Radio'] }, touch: { n: 'Skjold Touch', d: '7″ berøringsskjerm med Raspberry Pi 3, 4 eller 5 og PCM5122 HIFI HAT. RCA linje ut og 3,5 mm hodetelefon. Kan også styre alle de andre rommene.', icon: 'M5 4.5h14a1.5 1.5 0 0 1 1.5 1.5v8a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 14V6A1.5 1.5 0 0 1 5 4.5zM6 6.8h12v6.2H6zM7 15.5l-2 4h14l-2-4M11 17.6h2', inputs: ['AirPlay', 'Blåtann', 'Radio'] }, core: { n: 'Skjold Core', d: 'Sentral enhet uten skjerm. Kjører Lyrion-serveren for hele systemet og kan spille via linjeutgang eller digital utgang.', icon: 'M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 8h8v8H8zM12 4V2M12 22v-2M4 12H2M22 12h-2M10 11h4M10 13h4', inputs: ['AirPlay', 'Blåtann', 'Radio'] } };
  const SYS_DEF = { active: 'stue', rooms: [
    { id: 'stue', name: 'Stue', type: 's1', hw: 'Pi Zero 2 W · TPA3116 2 × 50 W', vol: 42, group: 'g1', np: null },
    { id: 'kjokken', name: 'Kjøkken', type: 'node', hw: 'Raspberry Pi 4 · HiFiBerry DAC+', vol: 30, group: 'g1', np: null },
    { id: 'kontor', name: 'Kontor', type: 'node', hw: 'Raspberry Pi 3B · 3,5 mm', vol: 25, group: null, np: ['Teardrop', 'Massive Attack', 'AirPlay'] },
    { id: 'soverom', name: 'Soverom', type: 'touch', hw: 'Raspberry Pi 5 · 7″ DSI · PCM5122 HAT', vol: 20, group: null, np: null },
    { id: 'core', name: 'Hjemmekino', type: 'core', hw: 'Raspberry Pi 5 · Lyrion-server · optisk ut', vol: 35, group: null, np: null }] };
  function loadSys() { try { const j = JSON.parse(localStorage.getItem('skjold-sys') || 'null'); if (j && j.rooms) { j.rooms.forEach(r => { if (r.type === 's1' && /Raspberry Pi 4/.test(r.hw || '')) r.hw = 'Pi Zero 2 W · TPA3116 2 × 50 W'; }); return j; } } catch (e) {} return JSON.parse(JSON.stringify(SYS_DEF)); }
  function saveSys(s) { try { localStorage.setItem('skjold-sys', JSON.stringify(s)); } catch (e) {} }
  const forDev = (x, type) => !x.dev || [].concat(x.dev).includes(type); // dev: 's1' | 'node' | 'core' or a list
  const fitDisp = (d, type, tech) => ({ ...d, n: (d.nBy && d.nBy[type]) || d.n, hint: (d.hintBy && d.hintBy[tech]) || d.hint, list: (d.listBy && d.listBy[tech]) || d.list });
  const onlyOk = (d, tech) => !d.only || (d.only === 'screen' ? tech !== 'none' : d.only === tech);
  const catsFor = (type, disp) => { const tech = (DISPLAYS[disp || DISP_DEF[type]] || DISPLAYS.none).tech;
    return CATS.filter(c => forDev(c, type)).map(c => ({ ...c, n: c.id === 'skjerm' && tech === 'none' ? 'Lys' : c.n, sub: c.id === 'skjerm' ? (tech === 'none' ? 'LED over knappene' : tech === 'tft' ? 'Bakgrunnslys, klokke, LED' : 'Dimming, kontrast, klokke, LED') : c.sub,
      items: c.items.filter(d => forDev(d, type) && onlyOk(d, tech)).map(d => fitDisp(d, type, tech)) })).filter(c => c.items.length); };
  function groupOf(sys, id) { const r = sys.rooms.find(x => x.id === id); return r && r.group ? sys.rooms.filter(x => x.group === r.group) : [r]; }
  function groupLabel(sys, id) { const g = groupOf(sys, id); return g[0] ? (g.find(x => x.id === id) || g[0]).name + (g.length > 1 ? ' + ' + (g.length - 1) : '') : ''; }
  function toggleInGroup(sys, activeId, id) { const n = JSON.parse(JSON.stringify(sys)), a = n.rooms.find(x => x.id === activeId), r = n.rooms.find(x => x.id === id); if (!a || !r || r.id === a.id) return n;
    if (!a.group) a.group = 'g' + Date.now(); if (r.group === a.group) r.group = null; else { r.group = a.group; r.np = null; }
    const left = n.rooms.filter(x => x.group === a.group); if (left.length === 1) a.group = null; return n; }
  function groupAll(sys) { const n = JSON.parse(JSON.stringify(sys)); n.rooms.forEach(r => { r.group = 'gall'; r.np = null; }); return n; }
  const ROLES = ['Stereo', 'Venstre', 'Høyre', 'Bak V', 'Bak H', 'Sub', 'Senter'];
  // Surround-oppsett: [id, navn, plasser (ROLES-indekser)]. Synk: buffer og volumkobling per gruppe i sys.gset[gid].
  const LAYOUTS = [['stereo', 'Stereopar', [1, 2]], ['2.1', '2.1', [1, 2, 5]], ['3.1', '3.1', [1, 6, 2, 5]], ['4.0', '4.0', [1, 2, 3, 4]], ['5.1', '5.1', [1, 6, 2, 3, 4, 5]]];
  const SLOT_POS = { 1: [16, 16], 6: [50, 12], 2: [84, 16], 5: [70, 30], 3: [12, 84], 4: [88, 84] };
  const ROLE_FULL = { 1: 'Front venstre', 2: 'Front høyre', 3: 'Bak venstre', 4: 'Bak høyre', 5: 'Sub', 6: 'Senter' };
  const GSET_DEF = { layout: 'stereo', vol: 'rel', buf: 1, xo: 80, phase: 0, dist: {}, lvl: {}, trim: {} };
  const gset = (sys, gid) => ({ ...GSET_DEF, ...((sys.gset && sys.gset[gid]) || {}) });
  function setGset(sys, gid, patch) { const n = JSON.parse(JSON.stringify(sys)); n.gset = { ...(n.gset || {}), [gid]: { ...gset(sys, gid), ...patch } }; return n; }
  function applyLayout(sys, gid, layout) { let n = setGset(sys, gid, { layout }); const L = LAYOUTS.find(l => l[0] === layout) || LAYOUTS[0]; let i = 0; n.rooms.forEach(r => { if (r.group === gid) r.role = i < L[2].length ? L[2][i++] : null; }); return n; }
  function placeRoom(sys, gid, roomId, role) { const n = JSON.parse(JSON.stringify(sys)); n.rooms.forEach(r => { if (r.group !== gid) return; if (r.id === roomId) r.role = role; else if (role != null && r.role === role) r.role = null; }); return n; }
  const delayMs = (d, maxD) => Math.max(0, (maxD - d) / 343 * 1000);
  function setGroupMode(sys, gid, mode) { let n = JSON.parse(JSON.stringify(sys)); n.modes = { ...(n.modes || {}), [gid]: mode }; if (mode === 'surround') { const cnt = n.rooms.filter(r => r.group === gid).length, lay = cnt >= 6 ? '5.1' : cnt >= 4 ? '3.1' : cnt === 3 ? '2.1' : 'stereo'; n = applyLayout(n, gid, gset(n, gid).layout !== 'stereo' ? gset(n, gid).layout : lay); } return n; }
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
  window.SKJOLD = { drawWide, WIDE_DEF, srcIcon, searchRadio, testStream, ROLES, setGroupMode, setRole, brandBg, fetchLogos, onLogos, slug, DEVTYPES, loadSys, saveSys, catsFor, LAYOUTS, SLOT_POS, ROLE_FULL, gset, setGset, applyLayout, placeRoom, delayMs, DISPLAYS, DISP_FOR, DISP_DEF, dispKey, dispOf, clocksFor, CLOCK_COLS, groupOf, groupLabel, toggleInGroup, groupAll, CLOCKS, drawClock, wordTime, loadNames, saveName, loadUpd, saveUpd, findRelease, runJob, backupNow, RELEASES, now, CATALOG, art, loadRadio, saveRadio, nowPlaying, MAXRADIO: 50, CATS, DEF, EQ, NAMES, PRESETS_RADIO, fmt, loadEq, saveEq, activeSrc, curve };
})();
