export interface DriveInfo {
  device: string;        // /dev/sdb, /dev/disk4, \\.\PHYSICALDRIVE2
  name: string;
  path: string;          // vist tekst: enhet · buss
  size: number;
  mountpoints: string[];
  media: MediaKind;      // SD-kort (kortleser) eller USB-pinne/SSD
  readOnly: boolean;     // skrivebeskyttet (låsebryter på SD-kort/USB-pinne)
}

export type MediaKind = 'sd' | 'usb';

export interface StaticIp {
  ip: string;            // 192.168.1.50/24 (prefiks valgfritt, standard /24)
  gw: string;            // ruter, valgfri
  dns: string;           // én eller flere adresser skilt med komma/mellomrom, valgfri
}

export interface ReleaseImage {
  tag: string;
  name: string;
  url: string;
  size: number;
  sha256?: string;       // fra SHA256SUMS / <asset>.sha256 hvis release har det
  publishedAt: string;
  base?: boolean;        // true = Raspberry Pi OS Lite 64-bit; Skjold installeres ved første oppstart
}

export interface SetupOptions {
  device: 's1' | 'node-pi4' | 'node-pi3' | 'core';
  preset: boolean;       // Wi-Fi/navn forhåndsinnstilt
  ssid: string;
  wifiPassword: string;
  country: string;       // ISO 3166-1 alpha-2 for Wi-Fi-regulering
  name: string;          // vist navn / rom
  hostname: string;      // mDNS-navn uten .local
  lang: 'nb' | 'en' | 'sv' | 'da';
  ssh: boolean;
  user: string;
  userPassword: string;  // klartekst – hashes med sha512crypt før det skrives
  sshKey: string;        // valgfri offentlig nøkkel (authorized_keys)
  lyrionServer?: boolean;
  net?: 'wifi' | 'eth';  // nettverk ved forhåndsinnstilling (standard wifi)
  staticIp?: StaticIp | null; // bare for eth; null = DHCP
  media?: MediaKind;     // det som skrives til (påvirker bare tekst) // installer Lyrion Music Server på enheten (ellers brukes en eksisterende server)
}

export type ImageChoice = { kind: 'latest'; release: ReleaseImage } | { kind: 'local'; path: string };

export interface FlashRequest {
  image: ImageChoice;
  drive: string;
  setup: SetupOptions;
}

export type FlashPhase = 'download' | 'decompress' | 'configure' | 'authorize' | 'flashing' | 'verifying' | 'done' | 'error';

export interface FlashProgress {
  phase: FlashPhase;
  percent: number;       // 0–100 innen fasen
  bytes?: number;
  total?: number;
  speed?: number;        // byte/s
  eta?: number;          // sekunder
  message?: string;
}

export interface FlashResult {
  ok: boolean;
  error?: string;
  url?: string;          // onboarding-URL
  install?: boolean;     // Skjold installeres ved første oppstart (tar 15–30 min)
  qr?: string;           // data:-URL (SVG) for QR-koden
}

/** Melding fra skriveprosessen til hovedprosessen (JSON-linjer over lokal socket). */
export type WriterMessage =
  | { type: 'hello'; token: string }
  | { type: 'progress'; phase: 'flashing' | 'verifying'; percent: number; bytes?: number; total?: number; speed?: number; eta?: number }
  | { type: 'done' }
  | { type: 'error'; message: string };

export interface WriterJob {
  image: string;
  device: string;
  port: number;
  token: string;
}
