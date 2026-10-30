import { createHash } from 'crypto';
import { createWriteStream, promises as fsp } from 'fs';
import path from 'path';
import { net } from 'electron';
import type { ReleaseImage } from '../shared/types';

export const REPO = 'SebastianKristo/pult-forsterker';
/** skjold-s1-2026-10-30.img.xz, skjold-node-….img.zip osv. (design/sdbilde: deploy/skjold-s1-<dato>.img.xz) */
export const IMAGE_ASSET = /^skjold-.*\.img(\.xz|\.zip|\.gz)?$/i;

interface GhAsset { name: string; browser_download_url: string; size: number }
interface GhRelease { tag_name: string; draft: boolean; prerelease: boolean; published_at: string; assets: GhAsset[] }

async function getText(url: string): Promise<string> {
  const r = await net.fetch(url, { headers: { 'User-Agent': 'skjold-flasher', Accept: 'application/vnd.github+json' } });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.text();
}

export async function latestImage(): Promise<ReleaseImage | null> {
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
  const ok = await fsp.stat(dest).then(s => s.size === img.size, () => false);
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
