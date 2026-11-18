import { openSetup } from './setupwiz';
import { SubwaveMark } from '../components/brandmarks';
import { pickImage } from '../lib/pickimage';
import { loadSw, swStations } from '../lib/subwave';
import { SRC_ICON } from '../lib/srcicons';
// Integrasjoner og Plugins (S1 Web v3: sidene «int» og «plug»).
import { signal } from '@preact/signals';
import { useEffect } from 'preact/hooks';
import { api, type HomeKitInfo, type MaStatus } from '../lib/api';
import { qrMatrix } from '../lib/qr';
import { matter, matterLoad, matterRows, matterStatus } from './platform';
import { go, setSetting, settings, showToast, everyVisible, status } from '../lib/store';
import { Toggle } from '../components/ui';
import { settVises, skjult } from '../lib/meny';
import type { Settings } from '../lib/settings';

const MONO = "'IBM Plex Mono',monospace";
const host = (): string => (typeof location !== 'undefined' && location.hostname) || 'skjold.local';

// ---------- Apple Hjem (HomeKit) ----------
const hk = signal<HomeKitInfo | null>(null);
const hkErr = signal('');
async function hkLoad(): Promise<void> { try { hk.value = await api.homekit(); hkErr.value = ''; } catch { hk.value = null; } }
async function hkSet(b: { enabled?: boolean; reset?: boolean }): Promise<void> { try { hk.value = await api.setHomekit(b); hkErr.value = ''; } catch (e) { hkErr.value = e instanceof Error ? e.message : String(e); } }
function hkStatus(): string {
  const h = hk.value;
  if (!h) return 'Av';
  if (!h.available) return 'Krever HAP-python';
  if (!h.enabled) return 'Av';
  return h.paired ? 'Paret · på' : 'Venter på paring';
}
function QR({ text, size = 168 }: { text: string; size?: number }) {
  let m: boolean[][] = [];
  try { m = qrMatrix(text); } catch { return null; }
  const n = m.length, q = 2;
  let d = '';
  m.forEach((row, y) => row.forEach((on, x) => { if (on) d += `M${x + q} ${y + q}h1v1h-1z`; }));
  return <svg viewBox={`0 0 ${n + 2 * q} ${n + 2 * q}`} width={size} height={size} role="img" aria-label="QR-kode for Apple Hjem" style="display:block;border-radius:10px;background:#fff;shape-rendering:crispEdges"><path d={d} fill="#0b0b0c" /></svg>;
}
function homekitRows(): Row[] {
  const h = hk.value;
  if (!h) return [{ n: 'Apple Hjem', hint: 'Får ikke kontakt med Skjold.', el: btn('Prøv igjen', () => void hkLoad()) }];
  if (!h.available) return [{ n: 'HAP-python mangler', hint: h.error || 'Kjør pi/update.sh på Skjold for å installere HomeKit-støtten.', el: txt('Krever oppdatering') }];
  const rows: Row[] = [{ n: 'Vis Skjold i Apple Hjem', hint: 'Skjold annonserer seg på nettet som et TV-tilbehør.', el: <Toggle on={h.enabled} onChange={(b) => void hkSet({ enabled: b })} /> }];
  if (!h.enabled) return rows;
  rows.push({ n: 'Status', hint: h.error || (h.paired ? 'Lagt til i Hjem-appen.' : 'Ikke lagt til ennå.'), el: txt(h.paired ? '● Paret' : '○ Venter') });
  if (!h.paired) {
    rows.push({ n: 'Oppsettkode', hint: 'Skann QR-koden med kameraet eller Hjem-appen, eller skriv inn koden.', el: <div style="display:flex;flex-direction:column;align-items:flex-end;gap:10px">{h.setup_uri && <QR text={h.setup_uri} />}<span style={`font-family:${MONO};font-size:22px;letter-spacing:.08em;color:#f0c46a`}>{h.pin}</span></div> });
    rows.push({ n: 'Slik legger du til', hint: 'Hjem-appen → + → Legg til tilbehør → Flere valg … → Skjold. Trykk «Legg til likevel» når den sier ikke-sertifisert tilbehør, og skriv inn koden.', el: txt('') });
  }
  rows.push({ n: 'I Hjem-appen', hint: 'Av/på, kildene og radiofavorittene som innganger, volum med iPhone-fjernkontrollen. AirPlay-lyden fungerer som før.', el: txt('TV-tilbehør') });
  rows.push({ n: 'Glem paringer', hint: 'Fjern Skjold fra Hjem-appen først. Etterpå kan den legges til på nytt.', el: btn('Glem paringer', () => void hkSet({ reset: true })) });
  if (hkErr.value) rows.push({ n: 'Feil', el: txt(hkErr.value) });
  return rows;
}

// ---------- Integrasjoner ----------
interface Int { id: string; name: string; mono: string; tile: string; status: string; ok: boolean; desc: string }

/** Lyrion slik daemonen faktisk ser den: innebygd (på denne enheten), ekstern server, eller ikke funnet. */
function lyrionState(): { ok: boolean; local: boolean; server: string; text: string } {
  const st = status.value, server = st?.lyrion_server || '', ok = !!st?.lyrion;
  const ip = server.split(':')[0] || '', local = !!ip && (ip === '127.0.0.1' || ip === 'localhost' || ip === host());
  const text = !st ? 'Sjekker …' : !server ? 'Ikke funnet' : !ok ? (local ? 'Innebygd · svarer ikke' : 'Ekstern · svarer ikke') : local ? 'Innebygd · kjører' : 'Ekstern server · ' + ip;
  return { ok, local, server, text };
}

function ints(s: Settings): Int[] {
  const ly = lyrionState();
  const nd = !!s.ndUrl, ytm = !!s.ytmCookie;
  return [
    { id: 'lyrion', name: 'Lyrion', mono: 'L', tile: '#f2f2ee', status: ly.text, ok: ly.ok, desc: 'Radio, favoritter og musikkbibliotek. Styrer også flere rom samtidig.' },
    { id: 'spotify', name: 'Spotify Connect', mono: 'S', tile: '#6fcf7f', status: s.spEn ? 'Installert · på' : 'Installert · av', ok: s.spEn, desc: 'Spill fra Spotify-appen rett til forsterkeren. Krever Spotify Premium.' },
    { id: 'ytmusic', name: 'YouTube Music', mono: 'YT', tile: '#e86a6a', status: ytm ? (s.ytmEn ? 'Innlogget · på' : 'Innlogget · av') : 'Ikke innlogget', ok: ytm && s.ytmEn, desc: 'Spillelister, mikser og album fra kontoen din, innebygd i Skjold. Krever Premium.' },
    { id: 'ma', name: 'Music Assistant', mono: 'MA', tile: '#18bcf2', status: s.maUrl ? (maSt.value?.ok ? 'Tilkoblet' + (maSt.value.player ? ' · ' + maSt.value.player : '') : maSt.value ? 'Feil' : 'Sjekker …') : 'Ikke satt opp', ok: !!s.maUrl && !!maSt.value?.ok, desc: 'TIDAL, Qobuz, Deezer, Spotify, YouTube Music, Plex, Jellyfin og podkaster i ett bibliotek, med søk i Skjold.' },
    { id: 'navidrome', name: 'Navidrome', mono: 'N', tile: '#7fa8e8', status: nd ? (s.ndEn ? 'Tilkoblet · på' : 'Tilkoblet · av') : 'Ikke tilkoblet', ok: nd && s.ndEn, desc: 'Ditt eget musikkbibliotek på hjemmenettet, i FLAC. Bruker Subsonic-API.' },
    { id: 'subwave', name: 'SUB/WAVE', mono: 'SW', tile: '#1a1a1b', status: swStations.value.length ? swStations.value.length + (swStations.value.length === 1 ? ' stasjon' : ' stasjoner') : 'Ikke satt opp', ok: swStations.value.length > 0, desc: 'Din egen AI-DJ-radio: selvhostede stasjoner der en AI-DJ velger låtene. Vises i Bibliotek og Kilder.' },
    { id: 'upnp', name: 'UPnP/DLNA', mono: 'DL', tile: '#ffffff', status: s.upnpEn ? 'På · venter' : 'Av', ok: s.upnpEn, desc: 'Ta imot lyd fra Android-apper, PC og NAS. Forsterkeren vises som en vanlig DLNA-høyttaler.' },
    { id: 'homekit', name: 'Apple Hjem (HomeKit)', mono: 'H', tile: '#f5a623', status: hkStatus(), ok: !!hk.value?.enabled && !!hk.value?.running, desc: 'Skjold som TV-tilbehør i Hjem-appen: av/på, kilder, radiofavoritter og volum. Med Siri og automasjoner.' },
    { id: 'matter', name: 'Matter', mono: 'M', tile: '#9b8cf2', status: matterStatus(), ok: !!matter.value?.enabled && !!matter.value?.commissioned, desc: 'Skjold som Matter-høyttaler i Apple Hjem, Google Home, Alexa og SmartThings: av/på, volum, demp, radiofavoritter og kilde.' },
    { id: 'ha', name: 'Home Assistant', mono: 'HA', tile: '#7fb7e8', status: 'Klar', ok: true, desc: 'Styr volum, inngang og av/på fra automasjoner og dashbord.' },
    { id: 'homey', name: 'Homey', mono: 'H', tile: '#e8c77f', status: 'Klar', ok: true, desc: 'Bruk forsterkeren i Homey Flows, for eksempel radio når du kommer hjem.' },
    { id: 'api', name: 'Lokalt API', mono: '{ }', tile: '#c9c9c4', status: 'Aktivt', ok: true, desc: 'REST og Server-Sent Events for egne skript og andre systemer.' }
  ];
}

/** Antall aktive integrasjoner (badge i sidemenyen): Lyrion hvis tilkoblet + de som er slått på. */
export function intCount(s: Settings): number {
  return [!!status.value?.lyrion, s.spEn, !!s.ytmCookie && s.ytmEn, !!s.ndUrl && s.ndEn, s.upnpEn, !!hk.value?.enabled, !!matter.value?.enabled].filter(Boolean).length;
}

type Row = { n: string; hint?: string; el: preact.ComponentChildren };
const txt = (v: string) => <span style={`font-family:${MONO};font-size:13px;color:#c9c9c4;text-align:right`}>{v}</span>;
const tog = (k: 'spEn' | 'ytmEn' | 'ndEn' | 'upnpEn', v: boolean) => <Toggle on={v} onChange={(b) => setSetting(k, b)} />;
const inp = (k: 'ndUrl' | 'ndUser', v: string, ph: string) => <input value={v} placeholder={ph} onChange={(e) => setSetting(k, (e.currentTarget as HTMLInputElement).value)} style={`height:36px;width:220px;max-width:100%;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-family:${MONO};font-size:12px;outline:none;color:#f2f2ee`} />;
const btn = (label: string, f: () => void) => <button onClick={f} style="height:36px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;cursor:pointer;white-space:nowrap;color:#f2f2ee">{label}</button>;

function detail(id: string, s: Settings): { links: [string, string][]; rows: Row[] } {
  const h = host();
  switch (id) {
    case 'lyrion': { const ly = lyrionState(), lh = ly.server || `${h}:9000`; return { links: ly.server ? [['Åpne Lyrion', `http://${lh}/`], ['Lyrion-innstillinger', `http://${lh}/settings/index.html`]] : [],
      rows: [{ n: 'Server', hint: ly.server ? '' : 'Fant ingen Lyrion-server. Installer Lyrion på denne enheten, eller sett KI_AMP_LMS_SERVER til adressen til en annen Skjold eller server.', el: txt(ly.server ? (ly.local ? 'Innebygd · ' : 'Ekstern · ') + ly.server + (ly.ok ? '' : ' · svarer ikke') : 'Ikke funnet') }, { n: 'Synkroniser med andre rom', hint: 'Rom med hake i «Ditt system» spiller det samme', el: btn('Grupper og surround', () => go('grp')) }] }; }
    case 'spotify': return { links: [['Åpne Spotify', 'https://open.spotify.com/']],
      rows: [{ n: 'Spotify Connect', hint: 'Vises som egen inngang', el: tog('spEn', s.spEn) }, { n: 'Versjon', el: txt('librespot') }] };
    case 'ytmusic': return { links: [['Åpne YouTube Music', 'https://music.youtube.com/']],
      rows: [{ n: 'YouTube Music', hint: 'Vises i menyen og under Kilder', el: tog('ytmEn', s.ytmEn) },
        { n: 'Innlogging', hint: s.ytmCookie ? 'Innlogget med cookie' + (s.ytmUser ? ' · ' + s.ytmUser : '') : 'Krever Premium. Logges inn med en cookie fra nettleseren, slik Music Assistant gjør.', el: btn(s.ytmCookie ? 'Endre' : 'Sett opp', () => openSetup('ytm')) },
        { n: 'Bibliotek', el: btn('Åpne', () => go('lib', 'ytm')) },
        { n: 'Vis i menyen', hint: 'Skjul YouTube Music fra sidemenyen og kildene uten å logge ut', el: <Toggle on={!skjult('ytm')} onChange={(b) => settVises('ytm', b)} /> }] };
    case 'ma': return { links: s.maUrl ? [['Åpne Music Assistant', maHttp(s.maUrl)]] : [['Om Music Assistant', 'https://music-assistant.io/']],
      rows: [{ n: 'Adresse', hint: 'For eksempel 192.168.1.5 eller homeassistant.local:8095', el: <span style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end"><input value={s.maUrl} placeholder="192.168.1.5:8095" onChange={(e) => { setSetting('maUrl', (e.currentTarget as HTMLInputElement).value.trim()); setTimeout(checkMa, 300); }} style={`height:36px;width:200px;max-width:100%;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-family:${MONO};font-size:12px;outline:none;color:#f2f2ee`} />{btn('Finn automatisk', () => void findMa())}</span> },
        { n: 'Token', hint: 'Nyere Music Assistant krever en token (Innstillinger → Brukere i MA). Lagres på Skjold.', el: <input type="password" value={s.maToken} placeholder="valgfritt" onChange={(e) => { setSetting('maToken', (e.currentTarget as HTMLInputElement).value.trim()); setTimeout(checkMa, 300); }} style={`height:36px;width:220px;max-width:100%;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-family:${MONO};font-size:12px;outline:none;color:#f2f2ee`} /> },
        { n: 'Status', hint: maSt.value?.error || (maSt.value?.ok && !maSt.value.player ? 'Fant ikke denne Skjold-en som spiller i MA. Legg til Squeezelite-, AirPlay- eller DLNA-provideren i Music Assistant.' : ''), el: <span style="display:flex;gap:6px;align-items:center">{txt(maSt.value?.ok ? 'MA ' + (maSt.value.version || '') : s.maUrl ? 'Ikke tilkoblet' : '–')}{btn('Test', checkMa)}</span> },
        { n: 'Bibliotek', el: btn('Åpne', () => go('ma')) },
        { n: 'Vis i menyen', hint: 'Skjul Music Assistant fra sidemenyen og kildene uten å logge ut', el: <Toggle on={!skjult('ma')} onChange={(b) => settVises('ma', b)} /> }] };
    case 'navidrome': return { links: s.ndUrl ? [['Åpne Navidrome', s.ndUrl]] : [],
      rows: [{ n: 'Navidrome', hint: 'Vises i menyen og under Kilder', el: tog('ndEn', s.ndEn) },
        { n: 'Server', el: inp('ndUrl', s.ndUrl, 'http://192.168.1.10:4533') },
        { n: 'Brukernavn', el: inp('ndUser', s.ndUser, 'brukernavn') },
        { n: 'Passord', hint: 'Settes under Innstillinger → Musikktjenester', el: btn('Åpne', () => openSetup('nd')) },
        { n: 'Bibliotek', el: btn('Åpne', () => go('lib', 'nd')) },
        { n: 'Vis i menyen', hint: 'Skjul Navidrome fra sidemenyen og kildene uten å logge ut', el: <Toggle on={!skjult('nd')} onChange={(b) => settVises('nd', b)} /> }] };
    case 'subwave': return { links: [],
      rows: [...swStations.value.map((x) => ({ n: x.name, hint: x.admin ? 'Admin · kan hoppe over' : 'Stasjon ' + (x.i + 1), el: swAdm.value === x.i ? <SwAdminFelt i={x.i} /> : <span style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end"><button onClick={() => void bildeSw(x.i)} title="Velg bilde" aria-label={'Velg bilde for ' + x.name} style={`width:36px;height:36px;border-radius:8px;border:1px solid #2e2e30;background:${x.image ? `url("${x.image.replace(/"/g, '')}") center / cover no-repeat` : '#1b1b1c'};color:#8b8b86;cursor:pointer;flex-shrink:0`}>{x.image ? '' : '+'}</button>{btn('Spill', () => void api.subwavePost({ play: true, station: x.i }).then(() => go('play')).catch(() => {}))}{btn(x.admin ? 'Admin ✓' : 'Admin', () => { swAdm.value = x.i; })}{btn('Fjern', () => void fjernSw(x.i))}</span> })),
        { n: swStations.value.length ? 'Legg til en stasjon til' : 'Ingen stasjon ennå', hint: 'Du kan ha så mange stasjoner du vil. Alle vises under Bibliotek → SUB/WAVE.', el: btn('+ Legg til stasjon', () => openSetup('sw')) },
        { n: 'Navn, brukernavn og passord', hint: 'Endres under Plugins → SUB/WAVE', el: btn('Åpne', () => go('plug')) },
        { n: 'Bibliotek', el: btn('Åpne', () => go('lib', 'sw')) },
        { n: 'Vis i menyen', hint: 'Skjul SUB/WAVE fra sidemenyen og kildene uten å logge ut', el: <Toggle on={!skjult('sw')} onChange={(b) => settVises('sw', b)} /> }] };
    case 'upnp': return { links: [],
      rows: [{ n: 'UPnP/DLNA-mottaker', hint: 'Lyden går via Lyrion, så rom kan grupperes som vanlig.', el: tog('upnpEn', s.upnpEn) },
        { n: 'Format', el: txt('FLAC, WAV, ALAC, MP3, AAC og OGG') },
        { n: 'Kompatible apper', el: txt('BubbleUPnP, Hi-Fi Cast, foobar2000, Plex, «Cast til enhet»') }] };
    case 'homekit': return { links: [], rows: homekitRows() };
    case 'matter': return { links: [['Om Matter', 'https://csa-iot.org/all-solutions/matter/']], rows: matterRows() };
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
const maSt = signal<MaStatus | null>(null);
const maHttp = (a: string) => (/^https?:\/\//.test(a) ? a : 'http://' + a + (/:\d+$/.test(a) ? '' : ':8095'));
function checkMa() { if (!settings.value.maUrl) { maSt.value = null; return; } maSt.value = null; api.maStatus().then((r) => (maSt.value = r)).catch((e) => (maSt.value = { configured: true, ok: false, error: e instanceof Error ? e.message : String(e) })); }
async function findMa() { try { const r = await api.maDiscover(); if (r.found[0]) { setSetting('maUrl', r.found[0]); setTimeout(checkMa, 300); showToast('Fant Music Assistant på ' + r.found[0]); } else showToast('Fant ingen Music Assistant på nettet'); } catch (e) { showToast(e instanceof Error ? e.message : String(e)); } }

export function IntegrationsPage() {
  useEffect(() => { checkMa(); loadSw(true); void hkLoad(); void matterLoad(); const t = everyVisible(() => { if (hk.value?.enabled && !hk.value.paired) void hkLoad(); if (matter.value?.enabled && !matter.value.commissioned) void matterLoad(); }, 5000); return () => clearInterval(t); }, []);
  const s = settings.value, sel = intSel.value, list = ints(s), cur = list.find((x) => x.id === sel) ?? list[0]!, d = detail(cur.id, s);
  return (
    <div class="int-wrap">
      <style>{INT_CSS}</style>
      <div class="int-list">
        {GRUPPER.map(([tittel, ids, ekstra]) => (
          <section key={tittel} class="int-grp">
            <div class="int-gh"><span>{tittel}</span>{ekstra === 'oppsett' && <button class="int-setup" onClick={() => openSetup()}>Sett opp steg for steg ›</button>}</div>
            <div class="int-grid">
              {list.filter((x) => ids.includes(x.id)).map((x) => { const on = x.id === cur.id; return (
                <button key={x.id} class={'int-card' + (on ? ' on' : '')} onClick={() => { intSel.value = x.id; }}>
                  <IntLogo id={x.id} mono={x.mono} tile={x.tile} />
                  <span class="int-tx"><b>{x.name}</b><span class={'int-st' + (x.ok ? ' ok' : '')}><i />{x.status}</span></span>
                </button>
              ); })}
            </div>
          </section>
        ))}
        <section class="int-grp">
          <div class="int-gh"><span>Skjold-tilbehør</span></div>
          <div class="int-grid">
            <button class="int-card" onClick={() => go('kass')}><span class="int-ic">▭</span><span class="int-tx"><b>Skjold Kassett</b><span class="int-st">NFC-kassetter ›</span></span></button>
            <button class="int-card" onClick={() => go('vinyl')}><span class="int-ic">◎</span><span class="int-tx"><b>Platesamling</b><span class="int-st">Vinyl til FLAC ›</span></span></button>
          </div>
        </section>
      </div>
      <section class="int-det">
        <div class="int-dh">
          <IntLogo id={cur.id} mono={cur.mono} tile={cur.tile} />
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:3px"><span style="font-size:17px;font-weight:600">{cur.name}</span><span class={'int-st' + (cur.ok ? ' ok' : '')}><i />{cur.status}</span></div>
        </div>
        <p class="int-desc">{cur.desc}</p>
        {d.links.length > 0 && <div style="display:flex;gap:8px;flex-wrap:wrap;padding:0 20px 14px">
          {d.links.map(([l, h]) => <a key={l} href={h} target="_blank" rel="noreferrer" style="display:flex;align-items:center;height:32px;padding:0 12px;border-radius:8px;border:1px solid #3a2e17;background:#1c170d;font-size:12px;white-space:nowrap;color:#f2f2ee;text-decoration:none">{l} ↗</a>)}
        </div>}
        {d.rows.map((r) => (
          <div key={r.n} style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;padding:14px 20px;border-top:1px solid #242426">
            <div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:14px">{r.n}</span>{r.hint && <span style="font-size:12px;color:#8b8b86;text-wrap:pretty">{r.hint}</span>}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;align-items:center;min-width:0">{r.el}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

const GRUPPER: [string, string[], string?][] = [
  ['Musikk', ['lyrion', 'spotify', 'ytmusic', 'navidrome', 'ma', 'subwave', 'upnp'], 'oppsett'],
  ['Smarthjem og styring', ['homekit', 'matter', 'ha', 'homey', 'api']],
];
const INT_CSS = `
.int-wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,400px);gap:24px;align-items:start}
.int-list{display:flex;flex-direction:column;gap:22px;min-width:0}
.int-grp{display:flex;flex-direction:column;gap:10px}
.int-gh{display:flex;align-items:center;justify-content:space-between;gap:10px;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#8b8b86}
.int-setup{border:none;background:none;color:#d9a441;font:600 12.5px Sora,system-ui,sans-serif;letter-spacing:0;text-transform:none;cursor:pointer;padding:0}
.int-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.int-card{display:flex;align-items:center;gap:12px;padding:12px;border-radius:14px;border:1px solid #242426;background:#141415;cursor:pointer;text-align:left;color:#f2f2ee;min-width:0}
.int-card:hover{border-color:#34342f}
.int-card.on{border-color:#d9a441;background:#1c170d}
.int-tx{display:flex;flex-direction:column;gap:3px;min-width:0}
.int-tx b{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.int-st{display:flex;align-items:center;gap:6px;font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.int-st.ok{color:#6fcf7f}
.int-st i{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0}
.int-ic{width:44px;height:44px;border-radius:11px;background:#1f1f21;color:#d9a441;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.int-det{position:sticky;top:16px;background:#141415;border:1px solid #242426;border-radius:16px;display:flex;flex-direction:column;overflow:hidden}
.int-dh{display:flex;align-items:center;gap:14px;padding:18px 20px 10px}
.int-desc{margin:0;padding:0 20px 14px;font-size:13px;line-height:1.5;color:#a9a9a3;text-wrap:pretty}
@media (max-width:1100px){.int-wrap{grid-template-columns:minmax(0,1fr)}.int-det{position:static}}
`;

// ---------- Plugins ----------
export { PluginsPage, plugCount } from './plugins';

/** Ekte logo per integrasjon: merkene fra kildeikonene, Home Assistant fra Simple Icons, Homey som ordmerke. */
const INT_SRC: Record<string, string> = { lyrion: 'Lyrion', spotify: 'Spotify', ytmusic: 'YouTube Music', navidrome: 'Navidrome', upnp: 'UPnP/DLNA' };
const HA_PATH = 'M22.939 10.627 13.061.749a1.505 1.505 0 0 0-2.121 0l-9.879 9.878C.478 11.21 0 12.363 0 13.187v9c0 .826.675 1.5 1.5 1.5h9.227l-4.063-4.062a2.034 2.034 0 0 1-.664.113c-1.13 0-2.05-.92-2.05-2.05s.92-2.05 2.05-2.05 2.05.92 2.05 2.05c0 .233-.041.456-.113.665l3.163 3.163V9.928a2.05 2.05 0 0 1-1.15-1.84c0-1.13.92-2.05 2.05-2.05s2.05.92 2.05 2.05a2.05 2.05 0 0 1-1.15 1.84v8.127l3.146-3.146A2.051 2.051 0 0 1 18 12.239c1.13 0 2.05.92 2.05 2.05s-.92 2.05-2.05 2.05c-.25 0-.488-.047-.709-.13L12.9 20.602v3.088h9.6c.825 0 1.5-.675 1.5-1.5v-9c0-.825-.477-1.977-1.061-2.561z';
/** Fjern SUB/WAVE-stasjon nummer i (blant stasjonene med gyldig adresse). Fjernes den første, rykker neste opp. */
/** Velg bilde for SUB/WAVE-stasjon nummer i (blant stasjonene med gyldig adresse). */
async function bildeSw(i: number): Promise<void> {
  const d = await pickImage(); if (!d) return;
  const r = await api.plugins(); const p = r.plugins.find((x) => x.id === 'subwave'); if (!p) return;
  const c = p.cfg as { url?: string; extra?: { url?: string; image?: string }[] };
  const ok = (u?: string) => /^https?:\/\//.test(String(u ?? '').trim());
  const idx: (number | 'top')[] = [...(ok(c.url) ? ['top' as const] : []), ...(c.extra ?? []).map((x, n) => (ok(x.url) ? n : -1)).filter((n) => n >= 0)];
  const hvor = idx[i]; if (hvor === undefined) return;
  if (hvor === 'top') await api.setPlugin('subwave', { image: d });
  else await api.setPlugin('subwave', { extra: (c.extra ?? []).map((x, n) => (n === hvor ? { ...x, image: d } : x)) });
  loadSw(true);
}

/** Stasjonsindeks i → hvor den ligger i pluginoppsettet ('top' = den første, ellers indeks i extra). */
async function swPlass(i: number): Promise<{ hvor: number | 'top'; extra: Record<string, unknown>[] } | null> {
  const r = await api.plugins(); const p = r.plugins.find((x) => x.id === 'subwave'); if (!p) return null;
  const c = p.cfg as { url?: string; extra?: Record<string, unknown>[] };
  const ok = (u?: unknown) => /^https?:\/\//.test(String(u ?? '').trim());
  const idx: (number | 'top')[] = [...(ok(c.url) ? ['top' as const] : []), ...(c.extra ?? []).map((x, n) => (ok(x.url) ? n : -1)).filter((n) => n >= 0)];
  const hvor = idx[i]; return hvor === undefined ? null : { hvor, extra: c.extra ?? [] };
}

const swAdm = signal<number | null>(null);

/** Admin-passordet til en SUB/WAVE-stasjon. Med det kan Skjold hoppe over låter («neste» på Touch, knotten og appen). */
function SwAdminFelt({ i }: { i: number }) {
  const lagre = async (pw: string) => {
    const pl = await swPlass(i); if (!pl) return;
    if (pl.hvor === 'top') await api.setPlugin('subwave', { password: pw });
    else await api.setPlugin('subwave', { extra: pl.extra.map((x, n) => (n === pl.hvor ? { ...x, password: pw } : x)) });
    swAdm.value = null; loadSw(true); showToast(pw ? 'Admin er koblet til – «neste» hopper nå over låten' : 'Admin er fjernet');
  };
  let felt: HTMLInputElement | null = null;
  return (
    <span style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end">
      <input ref={(e) => { felt = e; e?.focus(); }} type="password" autocomplete="off" placeholder="Admin-passord" aria-label="Admin-passord for stasjonen"
        onKeyDown={(e) => { if (e.key === 'Enter') void lagre((e.currentTarget as HTMLInputElement).value); if (e.key === 'Escape') swAdm.value = null; }}
        style={`height:36px;width:150px;max-width:100%;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-family:${MONO};font-size:12px;outline:none;color:#f2f2ee`} />
      {btn('Lagre', () => void lagre(felt?.value ?? ''))}
      {swStations.value[i]?.admin && btn('Fjern admin', () => void lagre(''))}
      {btn('Avbryt', () => { swAdm.value = null; })}
    </span>
  );
}

async function fjernSw(i: number): Promise<void> {
  if (!confirm('Fjerne stasjonen fra Skjold?')) return;
  const r = await api.plugins(); const p = r.plugins.find((x) => x.id === 'subwave'); if (!p) return;
  const c = p.cfg as { name?: string; url?: string; user?: string; password?: string; extra?: { name?: string; url?: string; user?: string; password?: string }[] };
  const ok = (u?: string) => /^https?:\/\//.test(String(u ?? '').trim());
  const alle = [{ name: c.name ?? '', url: c.url ?? '', user: c.user ?? '', password: c.password ?? '' }, ...(c.extra ?? [])].filter((x) => ok(x.url));
  alle.splice(i, 1);
  const [f, ...rest] = alle;
  await api.setPlugin('subwave', f ? { enabled: true, name: f.name ?? '', url: f.url ?? '', user: f.user ?? '', password: f.password ?? '', extra: rest } : { enabled: false, url: '', name: '', extra: [] });
  loadSw(true);
}

function IntLogo({ id, mono, tile }: { id: string; mono: string; tile: string }) {
  const box = 'width:44px;height:44px;border-radius:11px;overflow:hidden;display:flex;align-items:center;justify-content:center;flex-shrink:0';
  const src = INT_SRC[id] ? SRC_ICON[INT_SRC[id]] : undefined;
  if (src) return (
    <span style={`${box};background:${src.bg};color:${src.fg}`}>
      {src.sz !== '0' && <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style={`width:${src.sz === '100%' ? '70%' : src.sz};height:${src.sz === '100%' ? '70%' : src.sz};display:block`}>{src.st && <path d={src.st} />}{src.fi && <path d={src.fi} fill="currentColor" stroke="none" />}{src.fp && <path d={src.fp} fill="currentColor" stroke="none" />}</svg>}
    </span>
  );
  if (id === 'ha') return <span style={`${box};background:#18bcf2;color:#fff`}><svg viewBox="0 0 24 24" style="width:60%;height:60%;display:block"><path d={HA_PATH} fill="currentColor" /></svg></span>;
  if (id === 'homekit') return <span style={`${box};background:#fff`}><img src="./logo/brands/apple-home.png" alt="" style="width:74%;height:74%;object-fit:contain" /></span>;
  if (id === 'homey') return <span style={`${box};background:#fff`}><img src="./logo/brands/homey.png" alt="" style="width:76%;height:76%;object-fit:contain" /></span>;
  if (id === 'subwave') return <span style={`${box};background:#1a1a1b`}><SubwaveMark /></span>;
  // Offisielle merker (fra Home Assistants merkebibliotek): Music Assistant på mørk flis, Matter på hvit
  if (id === 'ma') return <span style={`${box};background:#0e2a36`}><img src="./logo/brands/music-assistant.png" alt="" style="width:72%;height:72%;object-fit:contain" /></span>;
  if (id === 'matter') return <span style={`${box};background:#fff`}><img src="./logo/brands/matter.png" alt="" style="width:66%;height:66%;object-fit:contain" /></span>;
  return <span style={`${box};background:${tile};color:#0b0b0c;font-weight:700;font-size:14px`}>{mono}</span>;
}
