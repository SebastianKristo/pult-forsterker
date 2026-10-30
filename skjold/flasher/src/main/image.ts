import { promises as fsp } from 'fs';
import path from 'path';
import { promisify } from 'util';
import type * as Fs from 'fs';
import { sourceDestination, multiWrite } from 'etcher-sdk';
import { interact } from 'balena-image-fs';
import type { BootFile } from '../shared/bootconfig';

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

/** Skriver filene til partisjon 1 (FAT boot-partisjonen på Raspberry Pi OS-bilder). */
export async function writeBootFiles(imagePath: string, files: BootFile[]): Promise<void> {
  await interact(imagePath, 1, async (fs: typeof Fs) => {
    const readdir = promisify(fs.readdir);
    const writeFile = promisify(fs.writeFile) as (p: string, d: string) => Promise<void>;
    const entries = (await readdir('/')).map(e => String(e).toLowerCase());
    if (!entries.includes('config.txt') && !entries.includes('cmdline.txt'))
      throw new Error('Fant ikke boot-partisjonen (config.txt) i bildet. Er dette et Raspberry Pi-bilde?');
    for (const f of files) await writeFile('/' + f.name, f.content);
  });
}
