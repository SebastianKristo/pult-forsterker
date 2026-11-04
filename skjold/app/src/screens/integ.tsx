// Integrasjoner og Plugins (S1 Web v3: sidene «int» og «plug»).
import { signal } from '@preact/signals';
import { useState } from 'preact/hooks';
import { go, setSetting, settings } from '../lib/store';
import { Toggle } from '../components/ui';
import type { Settings } from '../lib/settings';

const A = '#d9a441';
const MONO = "'IBM Plex Mono',monospace";
const host = (): string => (typeof location !== 'undefined' && location.hostname) || 'skjold.local';

// ---------- Integrasjoner ----------
interface Int { id: string; name: string; mono: string; tile: string; status: string; ok: boolean; desc: string }

function ints(s: Settings): Int[] {
  const nd = !!s.ndUrl, ytm = !!s.ytmCookie;
  return [
    { id: 'lyrion', name: 'Lyrion', mono: 'L', tile: '#f2f2ee', status: 'Innebygd · kjører', ok: true, desc: 'Radio, favoritter og musikkbibliotek. Styrer også flere rom samtidig.' },
    { id: 'spotify', name: 'Spotify Connect', mono: 'S', tile: '#6fcf7f', status: s.spEn ? 'Installert · på' : 'Installert · av', ok: s.spEn, desc: 'Spill fra Spotify-appen rett til forsterkeren. Krever Spotify Premium.' },
    { id: 'ytmusic', name: 'YouTube Music', mono: 'YT', tile: '#e86a6a', status: ytm ? (s.ytmEn ? 'Innlogget · på' : 'Innlogget · av') : 'Ikke innlogget', ok: ytm && s.ytmEn, desc: 'Spillelister, mikser og historikk fra Google-kontoen din. Via Music Assistant.' },
    { id: 'navidrome', name: 'Navidrome', mono: 'N', tile: '#7fa8e8', status: nd ? (s.ndEn ? 'Tilkoblet · på' : 'Tilkoblet · av') : 'Ikke tilkoblet', ok: nd && s.ndEn, desc: 'Ditt eget musikkbibliotek på hjemmenettet, i FLAC. Bruker Subsonic-API.' },
    { id: 'upnp', name: 'UPnP/DLNA', mono: 'DL', tile: '#ffffff', status: s.upnpEn ? 'På · venter' : 'Av', ok: s.upnpEn, desc: 'Ta imot lyd fra Android-apper, PC og NAS. Forsterkeren vises som en vanlig DLNA-høyttaler.' },
    { id: 'ha', name: 'Home Assistant', mono: 'HA', tile: '#7fb7e8', status: 'Klar', ok: true, desc: 'Styr volum, inngang og av/på fra automasjoner og dashbord.' },
    { id: 'homey', name: 'Homey', mono: 'H', tile: '#e8c77f', status: 'Klar', ok: true, desc: 'Bruk forsterkeren i Homey Flows, for eksempel radio når du kommer hjem.' },
    { id: 'api', name: 'Lokalt API', mono: '{ }', tile: '#c9c9c4', status: 'Aktivt', ok: true, desc: 'REST og Server-Sent Events for egne skript og andre systemer.' }
  ];
}

/** Antall aktive integrasjoner (badge i sidemenyen): Lyrion + de som er slått på. */
export function intCount(s: Settings): number {
  return 1 + [s.spEn, !!s.ytmCookie && s.ytmEn, !!s.ndUrl && s.ndEn, s.upnpEn].filter(Boolean).length;
}

type Row = { n: string; hint?: string; el: preact.ComponentChildren };
const txt = (v: string) => <span style={`font-family:${MONO};font-size:13px;color:#c9c9c4;text-align:right`}>{v}</span>;
const tog = (k: 'spEn' | 'ytmEn' | 'ndEn' | 'upnpEn', v: boolean) => <Toggle on={v} onChange={(b) => setSetting(k, b)} />;
const inp = (k: 'ndUrl' | 'ndUser', v: string, ph: string) => <input value={v} placeholder={ph} onChange={(e) => setSetting(k, (e.currentTarget as HTMLInputElement).value)} style={`height:36px;width:220px;max-width:100%;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-family:${MONO};font-size:12px;outline:none;color:#f2f2ee`} />;
const btn = (label: string, f: () => void) => <button onClick={f} style="height:36px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;cursor:pointer;white-space:nowrap;color:#f2f2ee">{label}</button>;

function detail(id: string, s: Settings): { links: [string, string][]; rows: Row[] } {
  const h = host();
  switch (id) {
    case 'lyrion': return { links: [['Åpne Lyrion', `http://${h}:9000/`], ['Lyrion-innstillinger', `http://${h}:9000/settings/index.html`]],
      rows: [{ n: 'Server', el: txt('Innebygd · port 9000') }, { n: 'Synkroniser med andre rom', hint: 'Rom med hake i «Ditt system» spiller det samme', el: btn('Grupper og surround', () => go('grp')) }] };
    case 'spotify': return { links: [['Åpne Spotify', 'https://open.spotify.com/']],
      rows: [{ n: 'Spotify Connect', hint: 'Vises som egen inngang', el: tog('spEn', s.spEn) }, { n: 'Versjon', el: txt('librespot') }] };
    case 'ytmusic': return { links: [['Åpne YouTube Music', 'https://music.youtube.com/']],
      rows: [{ n: 'YouTube Music', hint: 'Vises i menyen og under Kilder', el: tog('ytmEn', s.ytmEn) },
        { n: 'Innlogging', hint: s.ytmCookie ? 'Innlogget med cookie' + (s.ytmUser ? ' · ' + s.ytmUser : '') : 'Krever Premium. Logges inn med en cookie fra nettleseren, slik Music Assistant gjør.', el: btn(s.ytmCookie ? 'Endre' : 'Sett opp', () => go('settings', 'tjenester')) },
        { n: 'Bibliotek', el: btn('Åpne', () => go('lib', 'ytm')) }] };
    case 'navidrome': return { links: s.ndUrl ? [['Åpne Navidrome', s.ndUrl]] : [],
      rows: [{ n: 'Navidrome', hint: 'Vises i menyen og under Kilder', el: tog('ndEn', s.ndEn) },
        { n: 'Server', el: inp('ndUrl', s.ndUrl, 'http://192.168.1.10:4533') },
        { n: 'Brukernavn', el: inp('ndUser', s.ndUser, 'brukernavn') },
        { n: 'Passord', hint: 'Settes under Innstillinger → Musikktjenester', el: btn('Åpne', () => go('settings', 'tjenester')) },
        { n: 'Bibliotek', el: btn('Åpne', () => go('lib', 'nd')) }] };
    case 'upnp': return { links: [],
      rows: [{ n: 'UPnP/DLNA-mottaker', hint: 'Lyden går via Lyrion, så rom kan grupperes som vanlig.', el: tog('upnpEn', s.upnpEn) },
        { n: 'Format', el: txt('FLAC, WAV, ALAC, MP3, AAC og OGG') },
        { n: 'Kompatible apper', el: txt('BubbleUPnP, Hi-Fi Cast, foobar2000, Plex, «Cast til enhet»') }] };
    case 'ha': return { links: [['Åpne Home Assistant', 'http://homeassistant.local:8123/']],
      rows: [{ n: 'Skjold-integrasjonen', hint: 'Installeres fra HACS. Home Assistant finner Skjold selv på nettverket.', el: txt('Klar') },
        { n: 'Entiteter', el: txt('media_player, select, number, switch') },
        { n: 'Kort', hint: 'custom:skjold-card og custom:skjold-rom-card i dashbordet', el: txt('2') }] };
    case 'homey': return { links: [['Åpne Homey', 'https://my.homey.app/']],
      rows: [{ n: '1. Installer Skjold-appen på Homey', el: btn('Homey App Store', () => window.open('https://homey.app/apps/', '_blank')) },
        { n: '2. Legg til enhet i Homey', hint: 'Homey finner Skjold selv på nettverket', el: txt('S1, Node, Core, Touch') },
        { n: 'Flow-kort', el: txt('Av/på · Inngang · Radio · Volum · Spill lyd') }] };
    default: return { links: [],
      rows: [{ n: 'Adresse', el: txt(`http://${h}:8765/api/status`) }, { n: 'Hendelser', el: txt(`http://${h}:8765/api/events`) }, { n: 'Avspilling', el: txt('POST /api/play {url}') }] };
  }
}

const intSel = signal('lyrion');

export function IntegrationsPage() {
  const s = settings.value, sel = intSel.value, list = ints(s), cur = list.find((x) => x.id === sel) ?? list[0]!, d = detail(cur.id, s);
  return (
    <>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px">
        {list.map((x) => { const on = x.id === cur.id; return (
          <button key={x.id} onClick={() => { intSel.value = x.id; }} style={`display:flex;flex-direction:column;align-items:flex-start;gap:10px;padding:18px;border-radius:14px;border:1px solid ${on ? A : '#242426'};background:${on ? '#1c170d' : '#141415'};cursor:pointer;text-align:left;color:#f2f2ee`}>
            <div style="display:flex;align-items:center;justify-content:space-between;width:100%;gap:10px">
              <span style={`width:44px;height:44px;border-radius:11px;background:${x.tile};color:#0b0b0c;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px`}>{x.mono}</span>
              <span style={`display:flex;align-items:center;gap:6px;font-size:11px;color:${x.ok ? '#6fcf7f' : '#8b8b86'}`}><i style={`width:6px;height:6px;border-radius:50%;background:${x.ok ? '#6fcf7f' : '#8b8b86'}`} />{x.status}</span>
            </div>
            <span style="font-size:15px;font-weight:600">{x.name}</span>
            <span style="font-size:12px;color:#8b8b86;line-height:1.45;text-wrap:pretty">{x.desc}</span>
          </button>
        ); })}
      </div>
      <section style="background:#141415;border:1px solid #242426;border-radius:16px;display:flex;flex-direction:column">
        <div style="padding:18px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <span style="font-size:17px;font-weight:600">{cur.name}</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            {d.links.map(([l, h]) => <a key={l} href={h} target="_blank" rel="noreferrer" style="display:flex;align-items:center;height:34px;padding:0 12px;border-radius:8px;border:1px solid #3a2e17;background:#1c170d;font-size:12px;white-space:nowrap;color:#f2f2ee;text-decoration:none">{l} ↗</a>)}
          </div>
        </div>
        {d.rows.map((r) => (
          <div key={r.n} style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;padding:14px 20px;border-top:1px solid #242426">
            <div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:14px">{r.n}</span>{r.hint && <span style="font-size:12px;color:#8b8b86;text-wrap:pretty">{r.hint}</span>}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;align-items:center;min-width:0">{r.el}</div>
          </div>
        ))}
      </section>
    </>
  );
}

// ---------- Plugins ----------
const PLUGINS: [string, string, string, string, string, string, string][] = [
  ['spotty', 'Spotty', 'Lyrion', 'Musikk', 'SP', '#1ed760', 'Spotify i Lyrion, med søk, spillelister og Spotify Connect. Krever Spotify Premium.'],
  ['tidal', 'TIDAL', 'Lyrion', 'Musikk', 'TI', '#f2f2ee', 'Strømming i FLAC fra TIDAL. Krever abonnement.'],
  ['qobuz', 'Qobuz', 'Lyrion', 'Musikk', 'QB', '#7fb2ff', 'Hi-res opptil 24-bit / 192 kHz. Krever abonnement.'],
  ['deezer', 'Deezer', 'Lyrion', 'Musikk', 'DZ', '#c38bff', 'Flow, mikser og spillelister fra Deezer.'],
  ['podcast', 'Podkaster', 'Lyrion', 'Radio og podkast', 'PC', '#e8893a', 'Abonner på podkaster. Fortsetter der du slapp, også i et annet rom.'],
  ['rp', 'Radio Paradise', 'Lyrion', 'Radio og podkast', 'RP', '#d8cfb4', 'Reklamefri radio i FLAC.'],
  ['bbc', 'BBC Sounds', 'Lyrion', 'Radio og podkast', 'BBC', '#f2f2ee', 'Direktesendinger og opptak fra BBC.'],
  ['lastfm', 'Last.fm', 'Lyrion', 'Verktøy', 'FM', '#ff8a7a', 'Registrerer det du spiller på Last.fm (scrobbling).'],
  ['dstm', 'Ikke stopp musikken', 'Lyrion', 'Verktøy', 'DS', '#7dd88f', 'Fyller køen med lignende musikk når den tar slutt.'],
  ['alarm', 'Vekkerklokke', 'Skjold', 'Verktøy', 'AL', '#f0c46a', 'Vekk med radio eller en spilleliste. Egen tid per rom.'],
  ['sleep', 'Sovetimer', 'Skjold', 'Verktøy', 'ZZ', '#7fb2ff', 'Skrur ned lyden og slår av etter 15 til 90 minutter.'],
  ['lyrics', 'Sangtekster', 'Skjold', 'Verktøy', 'TX', '#c9c9c4', 'Viser teksten til låten i appen og på Skjold Touch.'],
  ['snap', 'Snapcast', 'Skjold', 'Verktøy', 'SN', '#4a8cff', 'Send lyden til andre høyttalere på nettet, synkronisert med Skjold.']
];
const PL_KEY = 'skjold-plugins';
function loadPl(): Record<string, boolean> {
  try { const v = JSON.parse(localStorage.getItem(PL_KEY) || 'null') as Record<string, boolean> | null; if (v) return v; } catch { /* ignore */ }
  return { podcast: true, dstm: true, alarm: true };
}
/** Plugins som er på (lagres i nettleseren til daemonen får en plugin-API). */
export const plugState = signal<Record<string, boolean>>(loadPl());
function savePl(n: Record<string, boolean>): void { plugState.value = n; try { localStorage.setItem(PL_KEY, JSON.stringify(n)); } catch { /* ignore */ } }
export const plugCount = (): number => Object.values(plugState.value).filter(Boolean).length;

const CATS = ['Alle', 'Installert', 'Musikk', 'Radio og podkast', 'Verktøy'];

export function PluginsPage() {
  const [cat, setCat] = useState('Alle'), [q, setQ] = useState(''), [busy, setBusy] = useState<string | null>(null);
  const st = plugState.value, ql = q.trim().toLowerCase();
  const list = PLUGINS.filter((p) => (cat === 'Alle' || (cat === 'Installert' ? st[p[0]] : p[3] === cat)) && (!ql || (p[1] + ' ' + p[6]).toLowerCase().includes(ql)));
  return (
    <>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
        <div style="display:flex;gap:4px;padding:4px;border-radius:10px;background:#141415;border:1px solid #242426;flex-wrap:wrap">
          {CATS.map((n) => <button key={n} onClick={() => setCat(n)} style={`height:34px;padding:0 14px;border-radius:7px;border:none;background:${cat === n ? '#2a2a2c' : 'transparent'};color:${cat === n ? '#f2f2ee' : '#8b8b86'};font-size:13px;cursor:pointer;white-space:nowrap`}>{n}</button>)}
        </div>
        <input value={q} onInput={(e) => setQ((e.currentTarget as HTMLInputElement).value)} placeholder="Søk i plugins" style="height:42px;width:280px;max-width:100%;padding:0 14px;border-radius:10px;border:1px solid #2e2e30;background:#141415;font-size:14px;outline:none;color:#f2f2ee" />
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px">
        {list.map(([id, name, by, c, mono, col, desc]) => {
          const on = !!st[id], b = busy === id;
          const fg = b ? '#f0c46a' : on ? '#6fcf7f' : '#6a6a65';
          const act = () => { if (b) return; if (on) { savePl({ ...plugState.value, [id]: false }); return; } setBusy(id); window.setTimeout(() => { setBusy(null); savePl({ ...plugState.value, [id]: true }); }, 1400); };
          return (
            <div key={id} style={`display:flex;flex-direction:column;gap:12px;padding:18px;border-radius:14px;border:1px solid ${on ? '#3a3220' : '#242426'};background:#141415`}>
              <div style="display:flex;align-items:center;gap:12px">
                <span style={`width:44px;height:44px;border-radius:11px;background:${col};color:#0b0b0c;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0`}>{mono}</span>
                <div style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:15px;font-weight:600">{name}</span><span style={`font-family:${MONO};font-size:10px;color:#8b8b86`}>Fra {by} · {c}</span></div>
              </div>
              <span style="font-size:12.5px;color:#a9a9a3;line-height:1.45;text-wrap:pretty;flex:1">{desc}</span>
              <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
                <span style={`display:flex;align-items:center;gap:6px;font-size:11px;color:${fg};white-space:nowrap`}><i style={`width:6px;height:6px;border-radius:50%;background:${fg};flex-shrink:0`} />{b ? 'Installerer …' : on ? 'Installert' : 'Ikke installert'}</span>
                <button onClick={act} style={`height:34px;padding:0 16px;border-radius:999px;border:1px solid ${on || b ? '#2e2e30' : A};background:${on || b ? 'transparent' : A};color:${on || b ? '#c9c9c4' : '#0b0b0c'};font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`}>{b ? 'Vent' : on ? 'Fjern' : 'Installer'}</button>
              </div>
            </div>
          );
        })}
      </div>
      {list.length === 0 && <span style="font-size:13px;color:#8b8b86">Ingen plugins passer søket.</span>}
    </>
  );
}
