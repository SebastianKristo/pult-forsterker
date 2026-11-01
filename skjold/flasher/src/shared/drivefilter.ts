import type { Drive } from 'drivelist';
import type { MediaKind } from './types';

const SYSTEM_MOUNTS = new Set(['/', '/boot', '/boot/efi', '/usr', '/home', '/var', 'C:\\', '/System/Volumes/Data']);

/**
 * Bare flyttbare ikke-system-disker (SD-kort/kortlesere, USB-pinner og USB-SSD-er, 1 GB–2 TB – MBR-grensen i
 * Raspberry Pi OS). Brukes både i GUI-et og (på nytt) i den privilegerte skriveprosessen. Skrivebeskyttede disker
 * slipper gjennom her så GUI-et kan vise dem med hengelås; skriveprosessen avviser dem eksplisitt.
 */
export function isSafeTarget(d: Drive): boolean {
  if (d.isSystem || d.isVirtual) return false;
  if (!d.size || d.size < 1e9 || d.size > 2.2e12) return false;
  if (!(d.isRemovable || d.isUSB || d.isCard)) return false;
  if (d.mountpoints.some(m => SYSTEM_MOUNTS.has(m.path))) return false;
  if (/^\/dev\/(loop|ram|zram|dm-|md|nvme)/.test(d.device)) return false;
  return true;
}

/**
 * SD-kort eller USB-disk. drivelist gir isCard på macOS/Windows, men alltid null på Linux – der brukes
 * mmcblk-navnet, busstype og beskrivelsen (USB-kortlesere heter typisk «… SD/MMC …», «Card Reader» o.l.).
 */
export function mediaKind(d: Pick<Drive, 'device' | 'description' | 'busType' | 'isCard' | 'isUSB'>): MediaKind {
  if (d.isCard) return 'sd';
  if (/^\/dev\/mmcblk/.test(d.device)) return 'sd';
  if (/^(SD|MMC)$/i.test(d.busType || '')) return 'sd';
  if (/\b(SD|SDHC|SDXC|MMC|micro ?SD|card|reader|kortleser)\b|SD\/MMC|MS\/MS-Pro/i.test(d.description || '')) return 'sd';
  return 'usb';
}
