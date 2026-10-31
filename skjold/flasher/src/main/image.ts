import { promises as fsp } from 'fs';
import path from 'path';
import { promisify } from 'util';
import type * as Fs from 'fs';
import { sourceDestination, multiWrite } from 'etcher-sdk';
import { interact } from 'balena-image-fs';
import { buildBootFiles, patchCmdline, type InitMode } from '../shared/bootconfig';
import type { SetupOptions } from '../shared/types';

/**
 * Pakker ut (xz/zip/gz) til en rå .img i arbeidsmappen. Konfigurasjonen skrives inn i *kopien* av bildet før det
 * flashes – da trengs ingen montering av SD-kortet etterpå, og verifiseringen dekker også oppsettfilene.
 */
export async function decompress(src: string, workDir: string, onProgress: (pct: number) => void): Promise<string> {
  await fsp.mkdir(workDir, { recursive: true });
  const out = path.join(workDir, 'skjold-prepared.img');
  await fsp.rm(out, { force: true });
  const file = new sourceDestination.File({ path: src });
  const inner = await file.getInnerSource();
  const dest = new sourceDestination.File({ path: out, write: true });
  const { failures } = await multiWrite.pipeSourceToDestinations({
    source: inner,
    destinations: [dest],
    verify: false,
    numBuffers: 16,
    onFail: () => undefined,
    onProgress: p => onProgress(p.percentage ?? 0),
  });
  await inner.close().catch(() => undefined);
  await file.close().catch(() => undefined);
  const err = [...failures.values()][0];
  if (err) throw err;
  return out;
}

/**
 * Skriver oppsettet til partisjon 1 (FAT boot-partisjonen). Modus velges ut fra innholdet:
 * markørfila skjold-image → ferdig Skjold-bilde; user-data/meta-data → cloud-init (Trixie+); ellers firstrun.sh (Bookworm).
 */
export async function prepareBoot(imagePath: string, o: SetupOptions): Promise<InitMode> {
  return interact(imagePath, 1, async (fs: typeof Fs) => {
    const readdir = promisify(fs.readdir);
    const readFile = promisify(fs.readFile) as (p: string) => Promise<Buffer>;
    const writeFile = promisify(fs.writeFile) as (p: string, d: string) => Promise<void>;
    const entries = (await readdir('/')).map(e => String(e));
    const has = (n: string) => entries.some(e => e.toLowerCase() === n);
    if (!has('config.txt') && !has('cmdline.txt'))
      throw new Error('Fant ikke boot-partisjonen (config.txt) i bildet. Er dette et Raspberry Pi-bilde?');
    const mode: InitMode = has('skjold-image') ? 'skjold' : has('user-data') || has('meta-data') ? 'cloudinit' : 'systemd';
    for (const f of buildBootFiles(o, mode)) await writeFile('/' + f.name, f.content);
    if (mode === 'systemd') {
      const name = entries.find(e => e.toLowerCase() === 'cmdline.txt');
      if (!name) throw new Error('Fant ikke cmdline.txt i bildet.');
      await writeFile('/' + name, patchCmdline((await readFile('/' + name)).toString('utf8'), o));
    }
    return mode;
  });
}
