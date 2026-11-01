import * as drivelist from 'drivelist';
import { promises as fsp } from 'fs';
import path from 'path';
import type { DriveInfo } from '../shared/types';
import { isSafeTarget, mediaKind } from '../shared/drivefilter';

/**
 * Skrivebeskyttelse. drivelist leser den allerede fra OS-et: Linux `lsblk ro` (= /sys/block/<dev>/ro, settes av
 * kjernen ved BLKROSET / WP-bit fra kortleseren), macOS DADiskDescriptionMediaWritable (= IOMedia «Writable»),
 * Windows IOCTL_DISK_IS_WRITABLE. På Linux leses sysfs i tillegg direkte, i tilfelle lsblk-utdata er utdatert.
 */
async function linuxReadOnly(device: string): Promise<boolean> {
  try { return (await fsp.readFile(path.join('/sys/block', path.basename(device), 'ro'), 'utf8')).trim() === '1'; }
  catch { return false; }
}

export async function listDrives(): Promise<DriveInfo[]> {
  const all = (await drivelist.list()).filter(isSafeTarget);
  return Promise.all(all.map(async d => {
    const media = mediaKind(d);
    const readOnly = d.isReadOnly || (process.platform === 'linux' && await linuxReadOnly(d.device));
    const bus = media === 'sd' ? (d.isCard || /mmcblk/.test(d.device) ? 'innebygd kortleser' : 'USB-kortleser')
      : d.isUSB ? 'USB' : d.busType || 'flyttbar';
    return { device: d.device, name: d.description || d.device, path: `${d.device} · ${bus}`, size: d.size ?? 0,
      mountpoints: d.mountpoints.map(m => m.path), media, readOnly };
  }));
}
