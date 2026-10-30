// Renderer-røyktest: laster dist/renderer/index.html i Chromium (Playwright) med et falskt preload-API
// og tar skjermbilder av alle fire stegene.  node scripts/screenshot.js [utmappe]
const path = require('path');
let playwright;
try { playwright = require('playwright'); } catch { console.error('playwright er ikke installert (npm i -g playwright)'); process.exit(1); }
const out = path.resolve(process.argv[2] || path.join(__dirname, '..', 'screenshots'));
require('fs').mkdirSync(out, { recursive: true });

const mock = () => {
  let cb = null;
  window.skjold = {
    platform: 'darwin',
    version: async () => '1.0.0',
    listDrives: async () => [
      { device: '/dev/disk4', name: 'SanDisk Extreme 32 GB', path: '/dev/disk4 · USB-kortleser', size: 31.9e9, mountpoints: [] },
      { device: '/dev/disk5', name: 'Kingston Canvas Go! 64 GB', path: '/dev/disk5 · innebygd kortleser', size: 63.9e9, mountpoints: [] },
    ],
    latestImage: async () => ({ tag: 'skjold-v1.0.0', name: 'skjold-s1-2026-10-30.img.xz', url: '#', size: 1.1e9, sha256: 'x'.repeat(64), publishedAt: '' }),
    pickImage: async () => null,
    hostname: async n => 'skjold-' + n.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
    open: async () => {},
    cancel: async () => {},
    onProgress: f => { cb = f; return () => {}; },
    flash: () => new Promise(res => {
      window.__finish = () => res({ ok: true, url: 'http://skjold-stue.local:8765/',
        qr: 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="#f2f2ee"/><rect x="1" y="1" width="3" height="3"/><rect x="6" y="1" width="3" height="3"/><rect x="1" y="6" width="3" height="3"/></svg>') });
      setTimeout(() => cb && cb({ phase: 'flashing', percent: 42, bytes: 1596e6, total: 3800e6, speed: 24e6, eta: 92 }), 50);
    }),
  };
};

(async () => {
  const browser = await playwright.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 880, height: 660 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) errors.push(m.text()); });
  await page.addInitScript(mock);
  await page.goto('file://' + path.join(__dirname, '..', 'dist', 'renderer', 'index.html'));
  await page.waitForSelector('[data-drive]');
  await page.click('[data-drive="/dev/disk4"]');
  await page.screenshot({ path: path.join(out, '1-velg.png') });
  await page.click('#next');
  await page.fill('input[data-k="ssid"]', 'Hjemme');
  await page.fill('input[data-k="pw"]', 'hemmelig123');
  await page.click('[data-toggle="ssh"]');
  await page.fill('input[data-k="userPw"]', 'passord1');
  await page.screenshot({ path: path.join(out, '2-forhand.png') });
  if (await page.isDisabled('#next')) throw new Error('Neste er deaktivert med gyldig skjema');
  await page.click('#next');
  await page.waitForSelector('text=Skriver til SD-kortet');
  await page.screenshot({ path: path.join(out, '3-skriver.png') });
  await page.evaluate(() => window.__finish());
  await page.waitForSelector('text=SD-kortet er klart');
  await page.screenshot({ path: path.join(out, '4-ferdig.png') });
  await browser.close();
  if (errors.length) { console.error('Feil i siden:\n' + errors.join('\n')); process.exit(1); }
  console.log('skjermbilder i ' + out);
})().catch(e => { console.error(e); process.exit(1); });
