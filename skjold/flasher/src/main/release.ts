import { createHash } from 'crypto';
import { createWriteStream, promises as fsp } from 'fs';
import path from 'path';
import { net } from 'electron';
import type { ReleaseImage } from '../shared/types';

import { REPO } from '../shared/bootconfig';
export { REPO };
/** skjold-s1-2026-10-30.img.xz, skjold-node-….img.zip osv. (design/sdbilde: deploy/skjold-s1-<dato>.img.xz) */
export const IMAGE_ASSET = /^skjold-.*\.img(\.xz|\.zip|\.gz)?$/i;

interface GhAsset { name: string; browser_download_url: string; size: number }
interface GhRelease { tag_name: string; draft: boolean; prerelease: boolean; published_at: string; assets: GhAsset[] }

async function getText(url: string): Promise<string> {
  const r = await net.fetch(url, { headers: { 'User-Agent': 'skjold-flasher', Accept: 'application/vnd.github+json' } });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.text();
}

/** Raspberry Pi sin offisielle OS-liste (samme som Raspberry Pi Imager bruker). */
export const RPI_OS_LIST = 'https://downloads.raspberrypi.com/os_list_imagingutility_v4.json';
export const RPI_OS_NAME = 'Raspberry Pi OS Lite (64-bit)';

interface RpiOs { name?: string; url?: string; image_download_size?: number; image_download_sha256?: string; release_date?: string; subitems?: RpiOs[] }

function findOs(list: RpiOs[]): RpiOs | null {
  for (const o of list) {
    if (o.name === RPI_OS_NAME && o.url) return o;
    const sub = o.subitems && findOs(o.subitems);
    if (sub) return sub;
  }
  return null;
}

/** Raspberry Pi OS Lite 64-bit – grunnbildet. Skjold installeres på det ved første oppstart. */
export async function baseImage(): Promise<ReleaseImage> {
  const d = JSON.parse(await getText(RPI_OS_LIST)) as { os_list: RpiOs[] };
  const o = findOs(d.os_list);
  if (!o?.url) throw new Error(`Fant ikke «${RPI_OS_NAME}» i Raspberry Pi sin OS-liste.`);
  return { tag: `Pi OS Lite 64-bit ${o.release_date ?? ''}`.trim(), name: o.url.split('/').pop()!, url: o.url,
    size: o.image_download_size ?? 0, sha256: o.image_download_sha256?.toLowerCase(), publishedAt: o.release_date ?? '', base: true };
}

/** Ferdig Skjold-bilde fra GitHub Releases hvis det finnes, ellers Raspberry Pi OS Lite 64-bit. */
export async function latestImage(): Promise<ReleaseImage | null> {
  const skjold = await latestSkjoldImage().catch(() => null);
  return skjold ?? baseImage();
}

export async function latestSkjoldImage(): Promise<ReleaseImage | null> {
  const list = JSON.parse(await getText(`https://api.github.com/repos/${REPO}/releases?per_page=30`)) as GhRelease[];
  const rels = list.filter(r => !r.draft && !r.prerelease && r.tag_name.startsWith('skjold-v'))
    .sort((a, b) => b.published_at.localeCompare(a.published_at));
  for (const r of rels) {
    const asset = r.assets.find(a => IMAGE_ASSET.test(a.name) && !a.name.endsWith('.sha256'));
    if (!asset) continue;
    let sha256: string | undefined;
    const sums = r.assets.find(a => a.name === `${asset.name}.sha256`) ?? r.assets.find(a => /^SHA256SUMS(\.txt)?$/i.test(a.name));
    if (sums) {
      try {
        const txt = await getText(sums.browser_download_url);
        const line = txt.split(/\r?\n/).find(l => l.includes(asset.name)) ?? txt.split(/\r?\n/)[0];
        sha256 = line.match(/\b[0-9a-f]{64}\b/i)?.[0]?.toLowerCase();
      } catch { /* sjekksum er valgfri */ }
    }
    return { tag: r.tag_name, name: asset.name, url: asset.browser_download_url, size: asset.size, sha256, publishedAt: r.published_at };
  }
  return null;
}

/** Laster ned til cacheDir (gjenbruker en ferdig fil med riktig sjekksum) og kontrollerer SHA-256. */
export async function download(img: ReleaseImage, cacheDir: string, onProgress: (bytes: number, total: number) => void, signal: AbortSignal): Promise<string> {
  await fsp.mkdir(cacheDir, { recursive: true });
  const dest = path.join(cacheDir, path.basename(img.name));
  const ok = await fsp.stat(dest).then(s => !img.size || s.size === img.size, () => false);
  if (ok && img.sha256 && (await sha256File(dest)) === img.sha256) return dest;

  const tmp = dest + '.part';
  const r = await net.fetch(img.url, { signal, headers: { 'User-Agent': 'skjold-flasher' } });
  if (!r.ok || !r.body) throw new Error(`Nedlasting feilet: HTTP ${r.status}`);
  const total = Number(r.headers.get('content-length')) || img.size;
  const hash = createHash('sha256');
  const out = createWriteStream(tmp);
  let bytes = 0;
  const reader = r.body.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      hash.update(value); bytes += value.length; onProgress(bytes, total);
      if (!out.write(value)) await new Promise<void>(res => out.once('drain', () => res()));
    }
  } finally {
    await new Promise<void>(res => out.end(res));
  }
  const got = hash.digest('hex');
  if (img.sha256 && got !== img.sha256) { await fsp.rm(tmp, { force: true }); throw new Error('SHA-256 stemmer ikke for nedlastet bilde.'); }
  await fsp.rename(tmp, dest);
  return dest;
}

async function sha256File(p: string): Promise<string> {
  const { createReadStream } = await import('fs');
  const h = createHash('sha256');
  for await (const c of createReadStream(p)) h.update(c as Buffer);
  return h.digest('hex');
}
