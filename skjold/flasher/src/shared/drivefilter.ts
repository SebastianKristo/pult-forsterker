import type { Drive } from 'drivelist';

const SYSTEM_MOUNTS = new Set(['/', '/boot', '/boot/efi', '/usr', '/home', '/var', 'C:\\', '/System/Volumes/Data']);

/** Bare flyttbare, skrivbare, ikke-system-disker. Brukes både i GUI-et og (på nytt) i den privilegerte skriveprosessen. */
export function isSafeTarget(d: Drive): boolean {
  if (d.isSystem || d.isReadOnly || d.isVirtual) return false;
  if (!d.size || d.size < 1e9 || d.size > 256e9) return false; // SD-kort: 1–256 GB
  if (!(d.isRemovable || d.isUSB || d.isCard)) return false;
  if (d.mountpoints.some(m => SYSTEM_MOUNTS.has(m.path))) return false;
  if (/^\/dev\/(loop|ram|zram|dm-|md)/.test(d.device)) return false;
  return true;
}
