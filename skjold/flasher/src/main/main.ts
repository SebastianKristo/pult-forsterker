import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron';
import { randomBytes } from 'crypto';
import { promises as fsp } from 'fs';
import net from 'net';
import path from 'path';
import QRCode from 'qrcode';
import { listDrives } from './drives';
import { latestImage, download } from './release';
import { decompress, prepareBoot } from './image';
import { eject, prepareLinuxDevice, runWriter, writeJobFile } from './elevate';
import { hostnameFromName, type InitMode, onboardingUrl, validate } from '../shared/bootconfig';
import type { FlashProgress, FlashRequest, FlashResult, WriterMessage } from '../shared/types';

let win: BrowserWindow | null = null;
let busy = false;
let abort: AbortController | null = null;

function createWindow(): void {
  win = new BrowserWindow({
    width: 880, height: 660, minWidth: 720, minHeight: 560,
    backgroundColor: '#0f0f10',
    title: 'Skjold Flasher',
    icon: path.join(__dirname, '..', 'renderer', 'icon.png'),   // Windows/Linux (macOS bruker icon.icns fra pakken)
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: true,
    },
  });
  win.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', e => e.preventDefault());
  win.on('close', e => {
    if (busy && dialog.showMessageBoxSync(win!, { type: 'warning', buttons: ['Avbryt', 'Lukk likevel'], defaultId: 0,
      message: 'Disken skrives nå. Lukker du, blir den ubrukelig til den skrives på nytt.' }) === 0) e.preventDefault();
  });
  if (process.argv.includes('--dev')) win.webContents.openDevTools({ mode: 'detach' });
}

const send = (p: FlashProgress) => win?.webContents.send('flash:progress', p);

async function flash(req: FlashRequest): Promise<FlashResult> {
  const err = validate(req.setup);
  if (err) return { ok: false, error: err };
  const target = (await listDrives().catch(() => [])).find(d => d.device === req.drive);
  if (target?.readOnly) return { ok: false, error: target.media === 'sd'
    ? 'Kortet er skrivebeskyttet. Låsen på siden av kortet står på «Lock». Ta ut kortet, skyv låsen opp og sett det inn igjen.'
    : 'Disken er skrivebeskyttet. Slå av bryteren for skrivebeskyttelse på pinnen, eller velg en annen disk.' };
  const work = path.join(app.getPath('userData'), 'work');
  const cache = path.join(app.getPath('userData'), 'cache');
  let prepared: string | null = null;
  let mode: InitMode = 'skjold';
  busy = true; abort = new AbortController();
  try {
    let src: string;
    if (req.image.kind === 'latest') {
      send({ phase: 'download', percent: 0 });
      src = await download(req.image.release, cache, (bytes, total) =>
        send({ phase: 'download', percent: total ? bytes / total * 100 : 0, bytes, total }), abort.signal);
    } else src = req.image.path;

    send({ phase: 'decompress', percent: 0 });
    prepared = await decompress(src, work, pct => send({ phase: 'decompress', percent: pct }));

    send({ phase: 'configure', percent: 0, message: 'Skriver oppsett til boot-partisjonen' });
    mode = await prepareBoot(prepared, req.setup);
    if (mode !== 'skjold') send({ phase: 'configure', percent: 100, message: 'Raspberry Pi OS Lite – Skjold installeres ved første oppstart' });

    send({ phase: 'authorize', percent: 0, message: 'Venter på administratortilgang' });
    if (process.platform === 'linux') await prepareLinuxDevice(req.drive);
    await runWriterWithProgress(prepared, req.drive);

    eject(req.drive);
    const url = onboardingUrl(req.setup.hostname);
    const qr = await QRCode.toString(url, { type: 'svg', margin: 1, color: { dark: '#0b0b0c', light: '#f2f2ee' } });
    send({ phase: 'done', percent: 100 });
    return { ok: true, url, install: mode !== 'skjold', qr: 'data:image/svg+xml;base64,' + Buffer.from(qr).toString('base64') };
  } catch (e) {
    let message = e instanceof Error ? e.message : String(e);
    if (process.platform === 'darwin' && /EPERM|operation not permitted/i.test(message) && /\/dev\/r?disk/.test(message)) {
      message += '\n\nKortet kan være skrivebeskyttet: skyv låsebryteren på SD-kortet/adapteren opp mot kontaktene og sett det inn igjen. ' +
        'Hjelper ikke det: macOS stoppet tilgangen til SD-kortet. Åpne Systeminnstillinger → Personvern og sikkerhet → Full disktilgang, ' +
        'legg til «Skjold Flasher» og slå den på, avslutt appen helt (⌘Q) og prøv igjen.';
    }
    send({ phase: 'error', percent: 0, message });
    return { ok: false, error: message };
  } finally {
    busy = false; abort = null;
    if (prepared) await fsp.rm(prepared, { force: true }).catch(() => undefined);
  }
}

async function runWriterWithProgress(image: string, device: string): Promise<void> {
  const token = randomBytes(24).toString('hex');
  let result: { ok: boolean; error?: string } | null = null;
  const server = net.createServer(sock => {
    let authed = false, buf = '';
    sock.setEncoding('utf8');
    sock.on('data', chunk => {
      buf += chunk;
      let nl: number;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        let m: WriterMessage;
        try { m = JSON.parse(line); } catch { continue; }
        if (!authed) { if (m.type === 'hello' && m.token === token) authed = true; else sock.destroy(); continue; }
        if (m.type === 'progress') send({ phase: m.phase, percent: m.percent, bytes: m.bytes, total: m.total, speed: m.speed, eta: m.eta });
        else if (m.type === 'done') result = { ok: true };
        else if (m.type === 'error') result = { ok: false, error: m.message };
      }
    });
    sock.on('error', () => undefined);
  });
  await new Promise<void>(res => server.listen(0, '127.0.0.1', res));
  const port = (server.address() as net.AddressInfo).port;
  try {
    const jobFile = await writeJobFile({ image, device, port, token });
    const writerJs = path.join(__dirname, '..', 'writer', 'writer.js');
    await runWriter(writerJs, jobFile);
    const r = result as { ok: boolean; error?: string } | null;
    if (!r) throw new Error('Skriveprosessen avsluttet uten å melde fra.');
    if (!r.ok) throw new Error(r.error);
  } finally {
    server.close();
  }
}

app.whenReady().then(() => {
  ipcMain.handle('drives:list', () => listDrives());
  ipcMain.handle('release:latest', () => latestImage());
  ipcMain.handle('image:pick', async () => {
    const r = await dialog.showOpenDialog(win!, { title: 'Velg Skjold-bilde', properties: ['openFile'],
      filters: [{ name: 'Diskbilde', extensions: ['img', 'xz', 'zip', 'gz'] }] });
    if (r.canceled || !r.filePaths[0]) return null;
    const st = await fsp.stat(r.filePaths[0]);
    return { path: r.filePaths[0], name: path.basename(r.filePaths[0]), size: st.size };
  });
  ipcMain.handle('flash:start', (_e, req: FlashRequest) => (busy ? { ok: false, error: 'Skriver allerede.' } : flash(req)));
  ipcMain.handle('flash:cancel', () => { abort?.abort(); });
  ipcMain.handle('hostname', (_e, name: string) => hostnameFromName(String(name)));
  ipcMain.handle('open', (_e, url: string) => { if (/^https?:\/\//.test(url)) shell.openExternal(url); });
  ipcMain.handle('app:version', () => app.getVersion());
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('window-all-closed', () => app.quit());
