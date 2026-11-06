// Tegner alle skjermtilstandene headless (Chromium via Playwright) til PNG, for sammenligning med designet.
//   node pi/skjold_ui/test_render.js <ut-mappe>
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const out = process.argv[2] || 'render'; fs.mkdirSync(out, { recursive: true });
const url = 'file://' + path.join(__dirname, 'web', 'index.html') + '?demo=1';
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
(async () => {
  const b = await chromium.launch();
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
  console.log(errs.length ? 'feil: ' + [...new Set(errs)].join(' | ') : 'ingen sidefeil', STATES.length + ' tilstander');
  await b.close();
})();
