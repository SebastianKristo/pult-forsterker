// Finn Skjold-enheter på nettet: mDNS (_kipultamp._tcp via native plugin) → kjente .local-navn → søk i /24-nett på :8765.
// Android WebView/HttpURLConnection kan ikke slå opp «.local», så navn alene virker ikke der – derfor mDNS + IP-søk.
import { mDNS } from '@devioarts/capacitor-mdns';
import { CANDIDATE_HOSTS, getBase, isNative, probe, type Status } from './api';

export interface Found { base: string; st: Status; via: 'mdns' | 'navn' | 'søk' | 'lagret' }

const PORT = 8765;
const DEFAULT_NETS = ['192.168.1', '192.168.0', '10.0.0', '192.168.68', '192.168.86', '10.0.1', '192.168.2', '192.168.10', '172.16.0'];
const KNOWN_KEY = 'skjold-known';

/** Enheter appen har vært koblet til før (Rom → Legg til enhet, bytte mellom dem). */
export function knownDevices(): { base: string; name: string; product?: string }[] {
  try { return JSON.parse(localStorage.getItem(KNOWN_KEY) || '[]') as { base: string; name: string; product?: string }[]; } catch { return []; }
}
export function remember(base: string, st: Status): void {
  const list = knownDevices().filter((d) => d.base !== base);
  list.unshift({ base, name: st.name, ...(st.product ? { product: st.product } : {}) });
  try { localStorage.setItem(KNOWN_KEY, JSON.stringify(list.slice(0, 12))); } catch { /* ignore */ }
}
export function forget(base: string): void {
  try { localStorage.setItem(KNOWN_KEY, JSON.stringify(knownDevices().filter((d) => d.base !== base))); } catch { /* ignore */ }
}

const ipv4 = (h: string) => /^\d{1,3}(\.\d{1,3}){3}$/.test(h);
const net24 = (ip: string) => ip.split('.').slice(0, 3).join('.');
const hostOf = (base: string) => base.replace(/^https?:\/\//, '').replace(/:\d+$/, '');

async function mdnsBases(): Promise<string[]> {
  if (!isNative) return [];
  try {
    const r = await mDNS.discover({ type: '_kipultamp._tcp.', timeout: 3500 });
    const out: string[] = [];
    for (const s of r.services ?? []) {
      const ip = (s.hosts ?? []).find(ipv4);
      if (ip) out.push(`http://${ip}:${s.port || PORT}`);
    }
    return out;
  } catch { return []; }
}

/** Lokal IP via WebRTC (gir ofte et anonymisert «.local»-navn i nyere nettlesere – da brukes standardnettene). */
async function webrtcIp(): Promise<string | null> {
  try {
    const pc = new RTCPeerConnection({ iceServers: [] });
    pc.createDataChannel('x');
    await pc.setLocalDescription(await pc.createOffer());
    const ip = await new Promise<string | null>((res) => {
      const t = setTimeout(() => res(null), 800);
      pc.onicecandidate = (e) => {
        const m = e.candidate?.candidate.match(/(\d{1,3}(?:\.\d{1,3}){3})/);
        if (m && m[1] && !m[1].startsWith('0.')) { clearTimeout(t); res(m[1]); }
      };
    });
    pc.close();
    return ip;
  } catch { return null; }
}

async function pool<T>(items: T[], n: number, fn: (x: T) => Promise<void>, stop: () => boolean): Promise<void> {
  let i = 0;
  await Promise.all(Array.from({ length: n }, async () => {
    while (i < items.length && !stop()) { const x = items[i++] as T; await fn(x); }
  }));
}

export interface ScanHandle { cancel: () => void; done: Promise<void> }

/**
 * Let etter enheter. onFound kalles for hver ny (unik på id/adresse). onPhase forteller hva som pågår.
 * Web (servert fra Pi-en) bruker samme origin og trenger ikke dette.
 */
export function scan(onFound: (f: Found) => void, onPhase: (p: string) => void): ScanHandle {
  let cancelled = false;
  const seen = new Set<string>();
  const add = (base: string, st: Status, via: Found['via']) => {
    const key = st.id || base;
    if (seen.has(key) || seen.has(base)) return;
    seen.add(key); seen.add(base); onFound({ base, st, via });
  };
  const tryBase = async (base: string, via: Found['via'], ms = 2500) => { const st = await probe(base, ms); if (st) add(base, st, via); };
  const done = (async () => {
    onPhase('Ser etter Skjold med Bonjour/mDNS …');
    const stored = getBase() || (!isNative && location.protocol.startsWith('http') ? location.origin : '');
    const named = [...knownDevices().map((d) => d.base), ...(stored ? [stored] : [])];
    const [mdns] = await Promise.all([
      mdnsBases(),
      ...named.map((b) => tryBase(b, 'lagret')),
      ...CANDIDATE_HOSTS.map((b) => tryBase(b, 'navn'))
    ]);
    await Promise.all(mdns.map((b) => tryBase(b, 'mdns')));
    if (cancelled || !isNative) return;
    // Nett å søke i: der vi har funnet/kjent enheter, telefonens eget nett (hvis vi får det), så vanlige hjemmenett
    const nets: string[] = [];
    const push = (n: string) => { if (!nets.includes(n)) nets.push(n); };
    for (const b of [...mdns, ...named]) { const h = hostOf(b); if (ipv4(h)) push(net24(h)); }
    const me = await webrtcIp(); if (me && ipv4(me)) push(net24(me));
    DEFAULT_NETS.forEach(push);
    for (const n of nets) {
      if (cancelled) return;
      onPhase(`Søker i ${n}.x …`);
      const ips = Array.from({ length: 254 }, (_, i) => `http://${n}.${i + 1}:${PORT}`).filter((b) => !seen.has(b));
      let hits = 0;
      await pool(ips, 48, async (b) => { const st = await probe(b, 1200); if (st) { hits++; add(b, st, 'søk'); } }, () => cancelled);
      if (hits) break;   // Skjold-enhetene står normalt på samme nett – ikke søk videre
    }
  })();
  return { cancel: () => { cancelled = true; }, done };
}
