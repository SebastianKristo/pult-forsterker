// Oppdatering av selve Android-appen fra GitHub Releases (skjold-v*-utgivelser med en .apk som vedlegg).
// iOS- og nettversjonen kan ikke oppdatere seg selv; der vises bare en lenke.
import { Capacitor, registerPlugin, type PluginListenerHandle } from '@capacitor/core';
import { REPO, cmpVersion } from './api';

interface AppUpdaterPlugin {
  getInfo(): Promise<{ versionName: string; versionCode: number }>;
  canInstall(): Promise<{ allowed: boolean }>;
  openInstallSettings(): Promise<void>;
  downloadAndInstall(o: { url: string }): Promise<void>;
  addListener(ev: 'progress', cb: (e: { percent: number }) => void): Promise<PluginListenerHandle>;
}

export const AppUpdater = registerPlugin<AppUpdaterPlugin>('AppUpdater');
export const canSelfUpdate = Capacitor.getPlatform() === 'android';

export interface AppRelease { tag: string; version: string; name: string; date: string; apkUrl: string; apkSize: string; pageUrl: string; prerelease: boolean }

/** Nyeste skjold-v*-utgivelse som har en APK (betaer tas med bare når includePre). */
export async function fetchLatestAppRelease(includePre: boolean): Promise<AppRelease | null> {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 10000);
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/releases?per_page=20`, { headers: { Accept: 'application/vnd.github+json' }, signal: ctl.signal });
    if (!r.ok) throw new Error('GitHub svarte ' + r.status);
    const list = (await r.json()) as Record<string, unknown>[];
    for (const rel of list) {
      const tag = String(rel['tag_name'] ?? '');
      if (rel['draft'] || !tag.startsWith('skjold-v') || (rel['prerelease'] && !includePre)) continue;
      const apk = ((rel['assets'] as { name: string; browser_download_url: string; size: number }[]) ?? []).find((a) => a.name.endsWith('.apk'));
      if (!apk) continue;
      return {
        tag, version: tag.replace(/^skjold-v/, ''), name: String(rel['name'] || tag), date: String(rel['published_at'] ?? '').slice(0, 10),
        apkUrl: apk.browser_download_url, apkSize: (apk.size / 1048576).toFixed(1).replace('.', ',') + ' MB',
        pageUrl: String(rel['html_url'] ?? `https://github.com/${REPO}/releases`), prerelease: !!rel['prerelease']
      };
    }
    return null;
  } finally { clearTimeout(t); }
}

export async function installedAppVersion(): Promise<string> {
  if (!canSelfUpdate) return '';
  try { return (await AppUpdater.getInfo()).versionName; } catch { return ''; }
}

export function isNewer(rel: AppRelease, installed: string): boolean {
  return !!installed && cmpVersion(rel.version, installed) > 0;
}
