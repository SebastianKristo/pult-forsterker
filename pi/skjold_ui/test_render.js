// Tegner skjermtilstandene headless (Chromium via Playwright) til PNG, for sammenligning med designet.
//   node pi/skjold_ui/test_render.js <ut-mappe> [s1|radio|alle]
//   s1    – Skjold S1 (960 × 320): alle 32 tilstander, filnavn som før
//   radio – Skjold Radio (800 × 480): skjerm-*.png (brukes i kabinett/radio/render/), med en falsk daemon
// Avslutter med kode 1 ved sidefeil eller når en kontroll feiler.
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const out = process.argv[2] || 'render'; fs.mkdirSync(out, { recursive: true });
const which = process.argv[3] || 'alle';
const WEB = path.join(__dirname, 'web');
let failed = false;

// ---------------------------------------------------------------- S1 (960 × 320)
async function s1(b) {
  const url = 'file://' + path.join(WEB, 'index.html') + '?demo=1';
  const base = { power: true, input: 'airplay', volume: 42, mute: false, playing: true, title: 'Midnight City', artist: 'M83', duration: 243, position: 71, airplay_device: 'iPhone' };
  const STATES = [
    ['01_oppstart', { boot: 1300 }],
    ['02_airplay', {}],
    ['03_blatann', { st: { input: 'bt', title: 'Teardrop', artist: 'Massive Attack', duration: 331, position: 40 } }],
    ['04_radio', { st: { input: 'radio', radio_now: { name: 'NRK P3', now: 'Pop og humor', n: 3 }, title: 'NRK P3' } }],
    ['05_aux', { st: { input: 'aux' } }],
    ['06_usb', { st: { input: 'usb', usb_pc: 2 } }],
    ['07_volum', { js: 'S.volT=performance.now()-400' }],
    ['08_dempet', { st: { mute: true }, js: 'S.muteT=performance.now()-2000' }],
    ['09_bt_paring', { js: 'S.pairT=performance.now()-1500' }],
    ['10_hold_radio', { st: { input: 'radio', radio_now: { name: 'NRK P3', n: 3 } }, js: 'S.holdWhat="radio";S.holdMs=3000;S.knobHoldT=performance.now()-1800' }],
    ['11_omstart', { js: 'S.rebootT=performance.now()-900' }],
    ['12_nattmodus', { js: 'nightMode("Home Assistant",true);S.nightT=performance.now()-2400' }],
    ['13_innstillinger', { js: 'S.set.open=true;S.set.t=performance.now();S.set.cat=-1;S.set.idx=0' }],
    ['14_innst_kategori', { js: 'S.set.open=true;S.set.t=performance.now();S.set.cat=0;S.set.idx=1;S.set.edit=true;S.set.bass=2' }],
    ['15_hilsen', { js: 'S.bdayDemo=true;S.bdayHide=false' }],
    ['16_feil_varme', { st: { overtemp: true }, js: 'S.errT=performance.now()-300' }],
  ];
  for (let i = 0; i < 16; i++) STATES.push(['standby_' + String(i).padStart(2, '0'), { st: { power: false }, js: 'S.set.clock=true;S.set.clockStyle=' + i }]);
  const p = await b.newPage({ viewport: { width: 960, height: 320 }, deviceScaleFactor: 1 });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  for (const [name, o] of STATES) {
    await p.goto(url); await p.waitForFunction(() => window.SKJOLD_SCREEN);
    await p.evaluate(([st, js, boot]) => {
      const X = window.SKJOLD_SCREEN; X.apply(Object.assign({}, st));
      bootT = performance.now() - (boot || 99999);
      if (js) eval(js);
      drawTFT1(); drawBar();
    }, [Object.assign({}, base, o.st || {}), o.js || '', o.boot || 0]);
    await p.waitForTimeout(150);
    await p.evaluate(() => { drawTFT1(); drawBar(); });
    await p.screenshot({ path: path.join(out, name + '.png') });
  }
  if (errs.length) failed = true;
  console.log('S1:', errs.length ? 'feil: ' + [...new Set(errs)].join(' | ') : 'ingen sidefeil', STATES.length + ' tilstander');
  await p.close();
}

// ---------------------------------------------------------------- Skjold Radio (800 × 480)
// Falsk daemon: samme felt og endepunkter som ki_amp_daemon.py (bare det skjermen leser).
const PRESETS = ['NRK P1', 'NRK P2', 'NRK P3', 'P4 Norge', 'Radio Norge', 'NRK Klassisk'].map((t, i) => ({ n: i + 1, title: t, logo: '' }));
const RADIO = { power: true, input: 'radio', volume: 34, mute: false, playing: true, title: 'Dance The Way I Feel', artist: 'Ofenbach', name: 'Skjold Radio',
  version: '2026.11', radio_now: { name: 'NRK P3', now: 'Ofenbach – Dance The Way I Feel', n: 3, genre: 'Pop og humor', logo: '' }, preset: 3,
  presets: PRESETS, presets_count: 6, cover_url: '', duration: 0, position: 0, inputs: ['radio', 'airplay', 'bt', 'spotify'], sleep: 0, input_seq: 1 };
const COVER = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
  <defs><radialGradient id="a" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#ff4f8b"/><stop offset=".45" stop-color="#7b2ff7"/><stop offset="1" stop-color="#1a0b3d"/></radialGradient>
  <radialGradient id="b" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>
  <rect width="600" height="600" fill="url(#a)"/><circle cx="410" cy="380" r="120" fill="url(#b)"/><circle cx="410" cy="380" r="62" fill="#fff" opacity=".9"/>
  <path d="M0 470 L80 430 L120 450 L170 400 L230 440 L300 380 L360 430 L430 410 L520 450 L600 420 L600 600 L0 600Z" fill="#0d0620" opacity=".85"/></svg>`;
const MOCK = {
  '/api/radio/browse': { offline: false, shelves: [
    { id: 'popular_no', title: 'Populære i Norge', items: ['NRK P1', 'NRK P3', 'P4 Lyden av Norge', 'Radio Norge', 'NRK mP3', 'P5 Hits', 'NRK Jazz', 'Radio Rock', 'NRK Klassisk', 'P7 Klem'].map((n, i) => ({ name: n, url: 'http://radio.test/' + i, image: '', genre: ['Nyheter og distrikt', 'Pop', 'Hits', 'Pop og rock', 'Pop', 'Hits', 'Jazz', 'Rock', 'Klassisk', 'Gull'][i], codec: 'MP3', bitrate: 128 })) },
    { id: 'jazz', title: 'Jazz', items: [{ name: 'NRK Jazz', url: 'http://radio.test/j', image: '', genre: 'Jazz' }] },
    { id: 'klassisk', title: 'Klassisk', items: [{ name: 'NRK Klassisk', url: 'http://radio.test/k', image: '', genre: 'Klassisk' }] },
    { id: 'rock', title: 'Rock', items: [{ name: 'Radio Rock', url: 'http://radio.test/r', image: '', genre: 'Rock' }] },
    { id: 'nyheter', title: 'Nyheter og prat', items: [{ name: 'NRK P2', url: 'http://radio.test/n', image: '', genre: 'Prat' }] }] },
  '/api/plugins': { sleep: 0, plugins: [
    { id: 'sleep', name: 'Sovetimer', enabled: false, cfg: { enabled: false, minutes: 30 } },
    { id: 'alarm', name: 'Vekkerklokke', enabled: true, cfg: { enabled: true, alarms: [{ time: '06:45', days: [0, 1, 2, 3, 4], preset: 1, volume: 25, fade: 3, on: true }, { time: '09:00', days: [5, 6], preset: 2, volume: 20, fade: 3, on: false }] } }] },
  '/api/medialib': { plex: { configured: true, url: 'http://plex.test:32400' }, jellyfin: { configured: false, url: '' } },
  '/api/medialib/plex/playlists': [{ id: '1', name: 'Søndagsmorgen', songCount: 42, cover: '' }, { id: '2', name: 'Kjøkkenfest', songCount: 87, cover: '' }],
  '/api/settings': { settings: { bright: 0, clock: true } },
  '/api/wifi': { networks: [{ ssid: 'Hjemme', signal: 78, security: 'wpa2', active: true }, { ssid: 'Naboen', signal: 40, security: 'wpa2', active: false }] },
  '/ui/net': { host: 'skjold-radio', ip: '192.168.1.42' },
  '/greeting': { name: 'Pappa', state: 'none' },
};
const RSTATES = [
  ['skjerm-1-radio', 'Nå spilles: NRK P3 (favoritt 3)', {}],
  ['skjerm-2-airplay', 'Nå spilles: AirPlay med omslag og fremdrift', { st: { input: 'airplay', title: 'Midnight City', artist: 'M83', album: 'Hurry Up, We\'re Dreaming', airplay_device: 'Sebastians iPhone', cover_url: '/api/cover?v=demo', duration: 243, position: 71, radio_now: null } }],
  ['skjerm-3-volum', 'Volumknotten dreies', { vol: 46 }],
  ['skjerm-4-bla', 'Hjulet blar i favorittene (gull ring på 5)', { ui: [{ ev: 'browse', d: 1 }, { ev: 'browse', d: 1 }] }],
  ['skjerm-5-meny', 'Menyen (hold hjulet)', { ui: [{ ev: 'menu_toggle' }] }],
  ['skjerm-6-meny-radio', 'Meny › Radio › Populære i Norge', { ui: [{ ev: 'menu_toggle' }, { ev: 'press' }, { wait: 400 }, { ev: 'turn', d: 1 }, { ev: 'press' }, { ev: 'turn', d: 1 }, { ev: 'turn', d: 1 }] }],
  ['skjerm-7-sovetimer', 'Meny › Sovetimer', { ui: [{ ev: 'menu_toggle' }, { ev: 'turn', d: 1 }, { ev: 'turn', d: 1 }, { ev: 'turn', d: 1 }, { ev: 'press' }, { ev: 'turn', d: 1 }, { ev: 'turn', d: 1 }] }],
  ['skjerm-8-nettverk', 'Meny › Innstillinger › Nettverk', { ui: [{ ev: 'menu_toggle' }, ...Array(5).fill({ ev: 'turn', d: 1 }), { ev: 'press' }, { ev: 'turn', d: 1 }, { ev: 'turn', d: 1 }, { ev: 'press' }, { wait: 300 }] }],
  ['skjerm-9-standby', 'Av: klokke, dato og neste vekking (dempet)', { st: { power: false, playing: false } }],
  ['skjerm-10-lagret', 'Favoritt 4 holdt i 2 s: lagret', { ui: [{ ev: 'saved', n: 4 }] }],
];

async function radio(b) {
  const ORIGIN = 'http://skjold-radio.test';
  const ctx = await b.newContext({ viewport: { width: 800, height: 480 }, deviceScaleFactor: 1, colorScheme: 'dark' });
  await ctx.route(ORIGIN + '/**', route => {
    const u = new URL(route.request().url()), p = u.pathname;
    if (p === '/api/cover') return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: COVER });
    if (MOCK[p] !== undefined) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK[p]) });
    if (p.startsWith('/api/') || p.startsWith('/ui/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(Object.assign({}, RADIO)) });
    const f = path.join(WEB, p === '/' ? 'index.html' : p.slice(1));
    if (!f.startsWith(WEB) || !fs.existsSync(f)) return route.fulfill({ status: 404, body: '' });
    const ct = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' }[path.extname(f)] || 'application/octet-stream';
    return route.fulfill({ status: 200, contentType: ct + '; charset=utf-8', body: fs.readFileSync(f) });
  });
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date('2026-11-07T18:42:00'));
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  const check = (ok, what) => { if (!ok) { failed = true; console.log('FEIL radio:', what); } };

  // automatisk valg: 800 × 480 uten ?layout gir radio, ?layout=s1 gir S1
  await p.goto(ORIGIN + '/?demo=1'); await p.waitForFunction(() => window.SKJOLD_RADIO);
  check(await p.evaluate(() => window.SKJOLD_LAYOUT === 'radio'), '800 × 480 skal velge radio-oppsettet');
  await p.goto(ORIGIN + '/?demo=1&layout=s1'); await p.waitForFunction(() => window.SKJOLD_SCREEN);
  check(await p.evaluate(() => window.SKJOLD_LAYOUT === 's1' && !window.SKJOLD_RADIO), '?layout=s1 skal gi S1');

  for (const [name, what, o] of RSTATES) {
    await p.goto(ORIGIN + '/?layout=radio&demo=1'); await p.waitForFunction(() => window.SKJOLD_RADIO);
    await p.evaluate(async ([st, plugins, lib]) => { const R = window.SKJOLD_RADIO; R.setPlugins(plugins); R.setLib(lib); R.applySettings({ bright: 1, clock: true }); R.apply(st); }, [Object.assign({}, RADIO, o.st || {}), MOCK['/api/plugins'], MOCK['/api/medialib']]);
    if (o.st && o.st.power === false) await p.evaluate(() => { window.SKJOLD_RADIO.applySettings({ bright: 0 }); });
    if (o.vol) await p.evaluate(v => window.SKJOLD_RADIO.apply(Object.assign({}, window.SKJOLD_RADIO.state(), { volume: v })), o.vol);
    for (const ev of o.ui || []) {
      if (ev.wait) { await p.waitForTimeout(ev.wait); continue; }
      await p.evaluate(e => window.SKJOLD_RADIO.onUi(e), ev); await p.waitForTimeout(60);
    }
    await p.waitForTimeout(450);
    await p.screenshot({ path: path.join(out, name + '.png') });
    console.log('  ' + name + '.png – ' + what);
  }

  // kontroller: favorittbrikkene står over knappene, menyen har de riktige punktene, hjulet styrer den
  await p.goto(ORIGIN + '/?layout=radio&demo=1'); await p.waitForFunction(() => window.SKJOLD_RADIO);
  await p.evaluate(([st, plugins, lib]) => { const R = window.SKJOLD_RADIO; R.setPlugins(plugins); R.setLib(lib); R.apply(st); }, [RADIO, MOCK['/api/plugins'], MOCK['/api/medialib']]);
  const xs = await p.$$eval('.fav', fs => fs.map(f => { const r = f.getBoundingClientRect(); return Math.round(r.left + r.width / 2); }));
  const want = [0, 1, 2, 3, 4, 5].map(i => Math.round((135 + 16 * i - (175 - 95.04 / 2)) * 800 / 95.04));
  check(xs.every((x, i) => Math.abs(x - want[i]) <= 1), 'favorittene skal stå over knappene: ' + xs + ' ≠ ' + want);
  check((await p.textContent('.fav.on .nm')) === 'NRK P3', 'aktiv favoritt skal være NRK P3');
  await p.evaluate(() => window.SKJOLD_RADIO.onUi({ ev: 'menu_toggle' })); await p.waitForTimeout(100);
  const rows = await p.$$eval('#menu .row .t', r => r.map(x => x.textContent));
  check(JSON.stringify(rows) === JSON.stringify(['Radio', 'Kilder', 'Bibliotek', 'Sovetimer', 'Vekkerklokke', 'Innstillinger']), 'menypunkter: ' + rows);
  await p.evaluate(() => { const R = window.SKJOLD_RADIO; R.onUi({ ev: 'turn', d: 1 }); R.onUi({ ev: 'press' }); }); await p.waitForTimeout(100);
  check((await p.textContent('#menu .crumb b')) === 'Kilder', 'trykk på hjulet skal åpne Kilder');
  await p.evaluate(() => window.SKJOLD_RADIO.onUi({ ev: 'back' })); await p.waitForTimeout(100);
  check((await p.textContent('#menu .crumb b')) === 'Meny', 'hold (tilbake) skal gå opp ett nivå');
  await p.evaluate(() => { window.SKJOLD_RADIO.onUi({ ev: 'back' }); }); await p.waitForTimeout(100);
  check(await p.$eval('#menu', m => m.classList.contains('hide')), 'tilbake fra toppen skal lukke menyen');
  await p.evaluate(() => window.SKJOLD_RADIO.apply(Object.assign({}, window.SKJOLD_RADIO.state(), { power: false })));
  check(!(await p.$eval('#standby', m => m.classList.contains('hide'))), 'av skal vise standby-klokka');

  if (errs.length) failed = true;
  console.log('Radio:', errs.length ? 'feil: ' + [...new Set(errs)].join(' | ') : 'ingen sidefeil', RSTATES.length + ' tilstander');
  await ctx.close();
}

(async () => {
  const b = await chromium.launch();
  if (which === 's1' || which === 'alle') await s1(b);
  if (which === 'radio' || which === 'alle') await radio(b);
  await b.close();
  process.exit(failed ? 1 : 0);
})();
