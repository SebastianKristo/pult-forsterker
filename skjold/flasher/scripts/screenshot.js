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
      { device: '/dev/disk4', name: 'SanDisk Extreme 32 GB', path: '/dev/disk4 · USB-kortleser', size: 31.9e9, mountpoints: [], media: 'sd', readOnly: false },
      { device: '/dev/disk5', name: 'Kingston Canvas Go! 64 GB', path: '/dev/disk5 · innebygd kortleser', size: 63.9e9, mountpoints: [], media: 'sd', readOnly: true },
      { device: '/dev/disk6', name: 'Samsung BAR Plus 64 GB', path: '/dev/disk6 · USB', size: 64.1e9, mountpoints: [], media: 'usb', readOnly: false },
      { device: '/dev/disk7', name: 'Samsung T7 500 GB (SSD)', path: '/dev/disk7 · USB', size: 500.1e9, mountpoints: [], media: 'usb', readOnly: false },
      { device: '/dev/disk8', name: 'Kanguru FlashTrust 16 GB', path: '/dev/disk8 · USB', size: 16e9, mountpoints: [], media: 'usb', readOnly: true },
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
  const shot = n => page.screenshot({ path: path.join(out, n + '.png'), fullPage: true });
  const fresh = async () => { await page.goto('file://' + path.join(__dirname, '..', 'dist', 'renderer', 'index.html')); await page.waitForSelector('[data-drive]'); };
  await fresh();
  // SD-kort med en skrivebeskyttet disk
  await page.click('[data-drive="/dev/disk5"]', { force: true });
  if (await page.$('[data-drive="/dev/disk5"].sel')) throw new Error('Skrivebeskyttet disk kunne velges');
  await page.click('[data-drive="/dev/disk4"]');
  await shot('1-velg-sd');
  await page.click('#next');
  await page.fill('input[data-k="ssid"]', 'Hjemme');
  await page.fill('input[data-k="pw"]', 'hemmelig123');
  await page.click('[data-toggle="ssh"]');
  await page.fill('input[data-k="userPw"]', 'passord1');
  await shot('2-forhand-wifi');
  if (await page.isDisabled('#next')) throw new Error('Neste er deaktivert med gyldig skjema');
  await page.click('#next');
  await page.waitForSelector('text=Skriver til SD-kortet');
  await shot('3-skriver-sd');
  await page.evaluate(() => window.__finish());
  await page.waitForSelector('text=SD-kortet er klart');
  await shot('4-ferdig-sd-wifi');

  // USB-disk + Ethernet med fast IP
  await fresh();
  await page.click('[data-media="usb"]');
  await page.click('[data-dev="2"]');
  await shot('5-velg-usb-pi3');
  await page.click('[data-dev="0"]');
  await page.click('[data-drive="/dev/disk7"]');
  await shot('6-velg-usb');
  await page.click('#next');
  await page.click('[data-net="eth"]');
  await page.click('[data-toggle="stat"]');
  await page.fill('input[data-k="ip"]', '192.168.1.500/24');
  await page.fill('input[data-k="gw"]', '192.168.1.1');
  if (!(await page.isDisabled('#next'))) throw new Error('Ugyldig IP godtatt');
  await shot('7-eth-ugyldig');
  await page.fill('input[data-k="ip"]', '192.168.1.50/24');
  await page.fill('input[data-k="dns"]', '1.1.1.1');
  if (await page.isDisabled('#next')) throw new Error('Gyldig fast IP avvist');
  await shot('8-eth-fast-ip');
  await page.click('#next');
  await page.waitForSelector('text=Skriver til USB-disken');
  await page.evaluate(() => window.__finish());
  await page.waitForSelector('text=USB-disken er klar');
  await shot('9-ferdig-usb-eth');
  await browser.close();
  if (errors.length) { console.error('Feil i siden:\n' + errors.join('\n')); process.exit(1); }
  console.log('skjermbilder i ' + out);
})().catch(e => { console.error(e); process.exit(1); });
