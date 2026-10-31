import * as drivelist from 'drivelist';
import type { DriveInfo } from '../shared/types';
import { isSafeTarget } from '../shared/drivefilter';

export async function listDrives(): Promise<DriveInfo[]> {
  const all = await drivelist.list();
  return all.filter(isSafeTarget).map(d => ({
    device: d.device,
    name: d.description || d.device,
    path: `${d.device} · ${d.isCard ? 'innebygd kortleser' : d.isUSB ? 'USB-kortleser' : d.busType || 'flyttbar'}`,
    size: d.size ?? 0,
    mountpoints: d.mountpoints.map(m => m.path),
  }));
}
