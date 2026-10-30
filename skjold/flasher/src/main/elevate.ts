import { execFile } from 'child_process';
import { promises as fsp } from 'fs';
import os from 'os';
import path from 'path';
import { spawn } from 'child_process';
import sudo from 'sudo-prompt';

const NAME = 'Skjold Flasher';

function sudoExec(cmd: string, env?: Record<string, string>): Promise<void> {
  return new Promise((res, rej) => sudo.exec(cmd, { name: NAME, env }, (err, _out, stderr) => {
    if (err) rej(new Error(/did not grant|User did not grant|cancel/i.test(err.message) ? 'Tilgang ble ikke gitt.' : `${err.message}${stderr ? `\n${stderr}` : ''}`));
    else res();
  }));
}

const LINUX_DEV = /^\/dev\/(sd[a-z]{1,2}|mmcblk\d+|vd[a-z])$/;

/**
 * Linux: AppImage-en ligger på en FUSE-montering som root ikke kan lese, så vi kjører ikke Electron som root.
 * I stedet avmonterer vi partisjonene og gir brukeren eierskap til blokkenheten (gjelder til kortet tas ut,
 * udev lager noden på nytt da). Ett pkexec-spørsmål.
 */
export async function prepareLinuxDevice(device: string): Promise<void> {
  if (process.getuid?.() === 0) return;
  if (!LINUX_DEV.test(device)) throw new Error(`Uventet enhetsnavn: ${device}`);
  const uid = process.getuid?.() ?? 0;
  await sudoExec(`/bin/sh -c 'for p in ${device}?*; do [ -b "$p" ] && umount "$p" 2>/dev/null; done; umount ${device} 2>/dev/null; chown ${uid} ${device}'`);
}

/** Starter skriveprosessen. På macOS/Windows med administratorrettigheter, på Linux som vanlig bruker. */
export async function runWriter(writerJs: string, jobFile: string): Promise<void> {
  const exe = process.execPath;
  if (process.platform === 'linux' || (process.platform !== 'win32' && process.getuid?.() === 0)) {
    await new Promise<void>((res, rej) => {
      const p = spawn(exe, [writerJs, '--job', jobFile], { env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' }, stdio: ['ignore', 'ignore', 'pipe'] });
      let err = '';
      p.stderr.on('data', d => { err += d; });
      p.on('error', rej);
      p.on('exit', code => (code === 0 ? res() : rej(new Error(err.trim() || `skriveprosessen avsluttet med ${code}`))));
    });
    return;
  }
  const q = (s: string) => `"${s.replace(/"/g, '\\"')}"`;
  await sudoExec(`${q(exe)} ${q(writerJs)} --job ${q(jobFile)}`, { ELECTRON_RUN_AS_NODE: '1' });
}

export async function writeJobFile(job: object): Promise<string> {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), 'skjold-'));
  const f = path.join(dir, 'job.json');
  await fsp.writeFile(f, JSON.stringify(job), { mode: 0o600 });
  return f;
}

/** Løs ut kortet etter skriving (best effort). */
export function eject(device: string): void {
  if (process.platform === 'linux' && LINUX_DEV.test(device)) execFile('udisksctl', ['power-off', '-b', device], () => undefined);
  if (process.platform === 'darwin' && /^\/dev\/disk\d+$/.test(device)) execFile('diskutil', ['eject', device], () => undefined);
}
