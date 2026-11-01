// Skall: telefon (App v2) under 900 px eller i Capacitor, ellers PC (S1 Web v3).
import { useEffect, useState } from 'preact/hooks';
import { App as CapApp } from '@capacitor/app';
import { isNative, hostLabel, PRODUCT_HW, PRODUCT_LABEL } from './lib/api';
import { setVolume } from './lib/store';
import { atRoot, closeFull, deviceName, fullPlayer, go, lastError, mode, online, product, queueOpen, route, srcOpen, status, toast, type Page } from './lib/store';
import { Welcome } from './screens/welcome';
import { HomePhone, MiniPhone, FullSheet, RoomsPhone, useRooms, switchRoom } from './screens/phone';
import { ndConfigured } from './lib/navidrome';
import { LibraryPage, libBack, libTitle, libUi } from './screens/library';
import { ob, obBack } from './screens/onboard';
import { ICONS } from './lib/settings';
import { cats } from './screens/settings';
import { Icon, Logo, PRODUCT_ICON, Slider } from './components/ui';
import { HomePage, EqPage } from './screens/pages';
import { RadioPage } from './screens/radio';
import { SettingsPage, CategoryDetail } from './screens/settings';
import { Art, PlayerBody, PowerButton, Transport, VolumeRow, artFor, nowTitle, subLine } from './screens/player';
import { openFull } from './lib/store';
import { FindDevice, Setup } from './screens/onboard';
import { showToast, settings } from './lib/store';
import { canSelfUpdate, fetchLatestAppRelease, installedAppVersion, isNewer } from './lib/appUpdate';

function useWide(): boolean {
  const q = '(min-width: 900px)';
  const [w, setW] = useState(() => !isNative && window.matchMedia(q).matches);
  useEffect(() => {
    if (isNative) return;
    const m = window.matchMedia(q); const f = () => setW(m.matches);
    m.addEventListener('change', f); return () => m.removeEventListener('change', f);
  }, []);
  return w;
}

export function App() {
  const wide = useWide();
  useEffect(() => {   // Android tilbakeknapp/-sveip: ett nivå opp i appen, avslutt bare fra Hjem
    if (!isNative) return;
    const h = CapApp.addListener('backButton', () => {
      if (mode.value !== 'app') { if (!obBack()) void CapApp.minimizeApp(); return; }
      if (route.value.page === 'lib' && !fullPlayer.value && libBack()) return;
      if (atRoot()) void CapApp.minimizeApp(); else if (fullPlayer.value) closeFull(); else window.history.back();
    });
    return () => { void h.then((x) => x.remove()); };
  }, []);
  useEffect(() => {   // Android: si fra én gang per oppstart hvis det finnes en nyere app på GitHub
    if (!canSelfUpdate) return;
    void (async () => {
      try {
        const [cur, rel] = await Promise.all([installedAppVersion(), fetchLatestAppRelease(settings.value.updChannel === 1)]);
        if (rel && isNewer(rel, cur)) showToast(`Ny app-versjon ${rel.version} – Innstillinger › Oppdatering`, 6000);
      } catch { /* offline – ikke noe å si fra om */ }
    })();
  }, []);
  let body;
  if (mode.value === 'welcome') body = <Welcome />;
  else if (mode.value === 'find') body = <FindDevice />;
  else if (mode.value === 'setup') body = <Setup />;
  else body = wide ? <Desktop /> : <Phone />;
  return <>{body}{toast.value && <div class="toast fade" role="status">{toast.value}</div>}</>;
}

function Offline() {
  if (online.value) return null;
  return (
    <div class="banner bad" data-testid="offline">
      <span>Får ikke kontakt med {hostLabel()}{lastError.value ? ' (' + lastError.value + ')' : ''}.</span>
      {isNative && <button class="btn sm" onClick={() => { mode.value = 'find'; }}>Finn Skjold</button>}
    </div>
  );
}

const TAB_ICON: Record<string, preact.JSX.Element> = {
  home: <path d="M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10" />,
  eq: <><path d="M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3" /><circle cx="5" cy="12" r="2" /><circle cx="12" cy="9" r="2" /><circle cx="19" cy="15" r="2" /></>,
  rooms: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
  settings: <><circle cx="12" cy="12" r="3" /><path d={(ICONS.settings ?? '').replace(/^M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z/, '')} /></>
};
const TABS: [Page, string][] = [['home', 'Hjem'], ['eq', 'Lyd'], ['rooms', 'Rom'], ['settings', 'Innstillinger']];

const TITLES: Record<Page, string> = { home: 'Hjem', play: 'Spiller', eq: 'Lyd', radio: 'Radio', rooms: 'Ditt system', settings: 'Innstillinger', lib: 'Bibliotek' };

function Phone() {
  const s = status.value, r = route.value;
  const page = r.page;
  useEffect(() => { if (page === 'play') { go('home'); openFull(); } }, [page]);
  useEffect(() => { if (!fullPlayer.value) { queueOpen.value = false; srcOpen.value = false; } }, [fullPlayer.value]);
  const cat = page === 'settings' ? cats.value.find((c) => c.id === r.cat) : undefined;
  const tabOf = page === 'radio' || page === 'play' || page === 'lib' ? 'home' : page;
  const title = cat ? cat.n : page === 'lib' ? libTitle() : TITLES[page];
  return (
    <div class="phone">
      {page !== 'home' && <div class="top"><span class="title">{title}</span></div>}
      <div class="scroll" key={page + (r.cat ?? '')}>
        <Offline />
        {page === 'home' && <HomePhone />}
        {page === 'eq' && <EqPage />}
        {page === 'radio' && <RadioPage />}
        {page === 'rooms' && <RoomsPhone />}
        {page === 'settings' && <SettingsPage />}
        {page === 'lib' && <LibraryPage />}
      </div>
      {s && !fullPlayer.value && <MiniPhone />}
      <nav class="tabs">
        {TABS.map(([id, n]) => (
          <button key={id} class={'tab' + (tabOf === id ? ' on' : '')} onClick={() => go(id)}>
            <span class="pill"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{TAB_ICON[id]}</svg></span>{n}
          </button>
        ))}
      </nav>
      {fullPlayer.value && <FullSheet />}
    </div>
  );
}

/** Styr appen i samme tilstander som designfilen (window.__skjoldApp.setState) – brukes til skjermbilder mot fasit. */
interface DesignState { welcome?: boolean; mode?: string; ob?: number; scan?: boolean; net?: number | 'man'; ssid?: string; roomCustom?: boolean; room?: string; tab?: number; sub?: string; lib?: string; libTab?: number; full?: boolean; queueOpen?: boolean; setCat?: number | string }
(window as unknown as { __skjoldApp: unknown }).__skjoldApp = {
  setState(d: DesignState) {
    if (d.welcome) { mode.value = 'welcome'; return; }
    if (d.mode === 'onboard') {
      const n = d.ob ?? 0;
      ob.qr.value = !!d.scan; if (d.net !== undefined) ob.net.value = d.net; if (d.ssid !== undefined) ob.ssid.value = d.ssid;
      if (d.roomCustom !== undefined) ob.custom.value = d.roomCustom; if (d.room !== undefined) ob.room.value = d.room;
      if (n === 0) mode.value = 'find'; else { ob.step.value = n; mode.value = 'setup'; }
      return;
    }
    mode.value = 'app';
    const t = d.tab ?? 0;
    if (t === 0 && d.sub === 'radio') route.value = { page: 'radio' };
    else if (t === 0 && d.sub === 'lib') { route.value = { page: 'lib', cat: d.lib === 'ytm' ? 'ytm' : 'nd' }; libUi.tab.value = d.libTab ?? 0; libUi.pl.value = null; }
    else if (t === 3) { const c = d.setCat === 'RADIO' ? 'radio' : typeof d.setCat === 'number' && d.setCat >= 0 ? cats.value[d.setCat]?.id : undefined; route.value = c ? { page: 'settings', cat: c } : { page: 'settings' }; }
    else route.value = { page: (['home', 'eq', 'rooms', 'settings'] as Page[])[t] ?? 'home' };
    fullPlayer.value = !!d.full; queueOpen.value = !!d.queueOpen;
  }
};

const NAV: [Page, string][] = [['home', 'Hjem'], ['play', 'Spiller'], ['radio', 'Radio'], ['eq', 'Equalizer']];
const NICON: Record<string, string> = { tjenester: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', lib: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', home: 'M4 11l8-7 8 7v9H4zM10 20v-5h4v5', play: 'M8 5v14l11-7z', eq: 'M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3M3 12h4M10 9h4M17 15h4', radio: 'M4 9h16v11H4zM8 9l9-5M8 14.5h.01M14 13h4M14 16h4', lyd: 'M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12', tilkobling: 'M7 7l10 10-5 5V2l5 5L7 17', stemme: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3', skjerm: 'M3 5h18v12H3zM8 21h8M12 17v4', strom: 'M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0', oppdatering: 'M12 4v11M7 10l5 5 5-5M5 20h14', system: 'M12 8v4M12 16h.01M12 3l9 4v6c0 5-4 8-9 9-5-1-9-4-9-9V7z' };
const PAGE_SUB: Partial<Record<Page, string>> = { radio: 'Norske kanaler og over 50 000 fra hele verden', eq: 'Egen profil per inngang og for hodetelefoner' };

function Desktop() {
  const s = status.value, r = route.value, p = product.value;
  const t = nowTitle(s);
  const cat = r.page === 'settings' ? cats.value.find((c) => c.id === r.cat) : undefined;
  const title = cat ? cat.n : r.page === 'lib' ? libTitle() : TITLES[r.page];
  const sideCats = cats.value.filter((c) => c.id !== 'eq');
  const st0 = settings.value;
  const libs: [string, string][] = [...(st0.ytmEn ? [['ytm', 'YouTube Music'] as [string, string]] : []), ...(st0.ndEn || ndConfigured() ? [['nd', 'Navidrome'] as [string, string]] : [])];
  const isLib = r.page === 'lib';
  const air = s?.input === 'airplay' && s.airplay_device ? 'Fra ' + s.airplay_device : '';
  return (
    <div class="desktop">
      <header class="hdr">
        <div class="row" style={{ minWidth: 0, gap: '14px' }}>
          <Logo lg word={false} />
          <div class="col" style={{ minWidth: 0 }}>
            <span class="row" style={{ gap: '10px', position: 'relative' }}><PlayerPicker /><span class="type-badge" data-testid="type-badge"><Icon d={PRODUCT_ICON[p]} size={15} sw={1.5} />{PRODUCT_LABEL[p]}</span></span>
            <span class="sub ellip">{PRODUCT_HW[p]}{s?.version ? ' · v' + s.version : ''}</span>
          </div>
        </div>
        <div class="row gap10">
          <span class="link-pill"><i style={{ background: online.value ? 'var(--green)' : 'var(--red)' }} />{online.value ? (s?.power ? 'På' : 'Standby') : 'Frakoblet'}</span>
          <PowerButton s={s} />
        </div>
      </header>
      <Offline />
      <div class="cols">
        <nav class="side">
          <div class="head">LYTT</div>
          {NAV.map(([id, n]) => <button key={id} class={'nv' + (r.page === id ? ' on' : '')} onClick={() => go(id)}><span class="row gap12"><Icon d={NICON[id] ?? ''} size={18} sw={1.6} />{n}</span></button>)}
          {libs.map(([id, n]) => <button key={id} class={'nv' + (isLib && r.cat === id ? ' on' : '')} onClick={() => go('lib', id)}><span class="row gap12"><Icon d={NICON.lib ?? ''} size={18} sw={1.6} />{n}</span></button>)}
          <div class="head">INNSTILLINGER</div>
          {sideCats.map((c) => <button key={c.id} class={'nv' + (r.page === 'settings' && r.cat === c.id ? ' on' : '')} onClick={() => go('settings', c.id)}><span class="row gap12"><Icon d={NICON[c.id] ?? NICON.system ?? ''} size={18} sw={1.6} />{c.n}</span></button>)}
        </nav>
        <main class="main">
          <div class="pgh"><h1>{title}</h1>{cat ? <span class="sub">Endringer lagres på forsterkeren med en gang</span> : PAGE_SUB[r.page] ? <span class="sub">{PAGE_SUB[r.page]}</span> : null}</div>
          {r.page === 'home' && <><div class="player"><Art s={s} /><div class="col gap16"><div class="col gap4"><span style={{ fontSize: '24px', fontWeight: 600 }} data-testid="now-title">{t.title}</span><span class="muted">{t.sub}</span>{t.album && <span class="muted" style={{ fontSize: '13px', opacity: 0.8 }} data-testid="album">{t.album}</span>}{air && <span class="muted" style={{ fontSize: '12px' }}>{air}</span>}</div><Transport s={s} /><VolumeRow s={s} /></div></div><HomePage wide /></>}
          {r.page === 'play' && <div class="player"><PlayerBody /></div>}
          {r.page === 'radio' && <RadioPage wide />}
          {r.page === 'rooms' && <RoomsPhone wide />}
          {r.page === 'lib' && <LibraryPage />}
          {r.page === 'eq' && <EqPage />}
          {r.page === 'settings' && (cat ? <CategoryDetail cat={cat} wide /> : <SettingsPage wide />)}
        </main>
        {!isLib && <aside class="sys">
          <span style={{ fontSize: '17px', fontWeight: 600 }}>Ditt system</span>
          <RoomsPhone wide />
          {s?.overtemp && <div class="banner bad"><span>Forsterkeren er for varm</span></div>}
        </aside>}
      </div>
      <div class="dock">
        <button class="np" onClick={() => go('play')}><div class="cover" style={{ background: artFor(s).bg }} /><div class="col" style={{ minWidth: 0, gap: '1px' }}><span class="mono ellip" style={{ fontSize: '10px', color: '#8b8b86' }}>{deviceName.value}</span><span class="ellip" style={{ fontSize: '14px', fontWeight: 600 }}>{t.title}</span><span class="ellip muted" style={{ fontSize: '12px' }}>{air || subLine(t)}</span></div></button>
        <Transport s={s} />
        <div class="dvol"><span class="mono" style={{ fontSize: '11px', color: '#8b8b86' }}>VOL</span><Slider value={s?.volume ?? 0} label="Volum" onCommit={setVolume} /><span class="mono" style={{ fontSize: '13px', minWidth: '2.5ch', textAlign: 'right' }}>{s?.volume ?? 0}</span></div>
      </div>
    </div>
  );
}

/** Web v3: velg spiller i toppen (samme side styrer alle enhetene appen kjenner). */
function PlayerPicker() {
  const [open, setOpen] = useState(false);
  const rooms = useRooms();
  return (
    <>
      <button onClick={() => setOpen(!open)} aria-label="Velg spiller" style="display:flex;align-items:center;gap:6px;border:none;background:none;padding:0;cursor:pointer;font-weight:600;font-size:17px;color:#f2f2ee">{deviceName.value}<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6" /></svg></button>
      {open && <>
        <button onClick={() => setOpen(false)} aria-label="Lukk" style="position:fixed;inset:0;z-index:40;border:none;background:transparent;cursor:default" />
        <div style="position:absolute;top:calc(100% + 10px);left:0;z-index:41;width:380px;max-width:calc(100vw - 40px);background:#141415;border:1px solid #2e2e30;border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,.55);display:flex;flex-direction:column;overflow:hidden">
          <span style="padding:12px 14px 8px;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#8b8b86">VELG SPILLER</span>
          {rooms.map((pl, i) => { const fg = pl.active ? '#f0c46a' : '#f2f2ee', host = (pl.base || location.origin).replace(/^https?:\/\//, ''); return (
            <div key={pl.key} style={`display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;padding:0 8px 0 0;border-top:1px solid #242426;background:${pl.active ? '#1c170d' : 'transparent'}`}>
              <button onClick={() => { setOpen(false); if (!pl.active) void switchRoom(pl.base); }} style="display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;align-items:center;min-height:58px;padding:0 14px;border:none;background:transparent;cursor:pointer;text-align:left">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={fg} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[pl.product]} /></svg>
                <span style="display:flex;flex-direction:column;gap:2px;min-width:0">
                  <span style={`display:flex;align-items:center;gap:8px;font-size:14px;color:${fg}`}>{pl.name}<span style="font-size:11px;color:#8b8b86">{PRODUCT_LABEL[pl.product]}</span></span>
                  <span style="display:flex;align-items:center;gap:6px;font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8b8b86"><div style={`width:6px;height:6px;border-radius:50%;background:${pl.st ? '#6fcf7f' : '#e05a4a'}`} />{host} {i === 0 ? '· denne' : ''}</span>
                </span>
              </button>
              <a href={(pl.base || location.origin) + '/?solo=1'} target="_blank" rel="noreferrer" title="Enhetens eget web-UI" style="display:flex;align-items:center;height:30px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;font-size:11px;color:#c9c9c4;white-space:nowrap">Eget UI ↗</a>
            </div>
          ); })}
          <span style="padding:10px 14px 12px;border-top:1px solid #242426;font-size:11px;color:#8b8b86;line-height:1.45;text-wrap:pretty">Samme side på alle adressene. «Eget UI» åpner bare den enheten, som reserve hvis noe er galt med nettverket.</span>
        </div>
      </>}
    </>
  );
}
