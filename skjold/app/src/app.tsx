// Skall: telefon (App v2) under 900 px eller i Capacitor, ellers PC (S1 Web v3).
import { useEffect, useRef, useState } from 'preact/hooks';
import { App as CapApp } from '@capacitor/app';
import { isNative, hostLabel, PRODUCT_HW, PRODUCT_LABEL } from './lib/api';
import { setVolume } from './lib/store';
import { atRoot, closeFull, deviceName, fullPlayer, go, lastError, mode, online, product, route, status, toast, type Page } from './lib/store';
import { ICONS } from './lib/settings';
import { cats } from './screens/settings';
import { Icon, Logo, PRODUCT_ICON, Slider } from './components/ui';
import { HomePage, RoomsPage, EqPage } from './screens/pages';
import { RadioPage } from './screens/radio';
import { SettingsPage, CategoryDetail } from './screens/settings';
import { Art, MiniPlayer, PhoneFullBody, PlayerBody, PowerButton, Transport, VolumeRow, artFor, nowTitle, subLine } from './screens/player';
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
      if (mode.value !== 'app') { if (mode.value === 'setup') mode.value = 'app'; else void CapApp.minimizeApp(); return; }
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
  if (mode.value === 'find') body = <FindDevice />;
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

/** Fullskjermspilleren: dra ned mer enn 90 px for å lukke. */
function FullPlayer() {
  const [dy, setDy] = useState(0);
  const start = useRef<number | null>(null);
  const body = useRef<HTMLDivElement>(null);
  const cur = useRef(0);
  const down = (e: PointerEvent) => {
    const t = e.target as HTMLElement;
    if (t.closest('input, button')) return;
    if ((body.current?.scrollTop ?? 0) > 0) return;
    start.current = e.clientY;
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch { /* ignore */ }
  };
  const move = (e: PointerEvent) => { if (start.current !== null) { cur.current = Math.max(0, e.clientY - start.current); setDy(cur.current); } };
  const up = () => { if (start.current === null) return; start.current = null; if (cur.current > 90) closeFull(); cur.current = 0; setDy(0); };
  const a = artFor(status.value);
  return (
    <div class="full" data-testid="full" style={{ background: 'linear-gradient(180deg, rgba(11,11,12,0.15) 0%, rgba(11,11,12,0.55) 55%, rgba(11,11,12,0.8) 100%), ' + a.bg, transform: dy ? `translateY(${dy}px)` : undefined, transition: dy ? 'none' : 'transform .25s ease' }}
      onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
      <div class="grab"><button class="grab-btn" aria-label="Lukk" onClick={closeFull}><i /></button></div>
      <div class="body" ref={body}><PhoneFullBody /></div>
    </div>
  );
}
const TITLES: Record<Page, string> = { home: 'Hjem', play: 'Spiller', eq: 'Lyd', radio: 'Radio', rooms: 'Ditt system', settings: 'Innstillinger' };

function Phone() {
  const s = status.value, r = route.value;
  const page = r.page;
  const cat = page === 'settings' ? cats.value.find((c) => c.id === r.cat) : undefined;
  const tabOf = page === 'radio' || page === 'play' ? 'home' : page;
  return (
    <div class="phone">
      {page !== 'home' && <div class="top"><span class="title">{cat ? cat.n : TITLES[page]}</span></div>}
      <div class="scroll">
        <Offline />
        {page === 'home' && <HomePage />}
        {page === 'play' && <PhoneFullBody />}
        {page === 'eq' && <EqPage />}
        {page === 'radio' && <RadioPage />}
        {page === 'rooms' && <RoomsPage />}
        {page === 'settings' && <SettingsPage />}
      </div>
      {s && !fullPlayer.value && <MiniPlayer />}
      <nav class="tabs">
        {TABS.map(([id, n]) => (
          <button key={id} class={'tab' + (tabOf === id ? ' on' : '')} onClick={() => go(id)}>
            <span class="pill"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{TAB_ICON[id]}</svg></span>{n}
          </button>
        ))}
      </nav>
      {fullPlayer.value && <FullPlayer />}
    </div>
  );
}

const NAV: [Page, string][] = [['home', 'Hjem'], ['play', 'Spiller'], ['radio', 'Radio'], ['eq', 'Equalizer']];
const NICON: Record<string, string> = { home: 'M4 11l8-7 8 7v9H4zM10 20v-5h4v5', play: 'M8 5v14l11-7z', eq: 'M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3M3 12h4M10 9h4M17 15h4', radio: 'M4 9h16v11H4zM8 9l9-5M8 14.5h.01M14 13h4M14 16h4', lyd: 'M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12', tilkobling: 'M7 7l10 10-5 5V2l5 5L7 17', stemme: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3', skjerm: 'M3 5h18v12H3zM8 21h8M12 17v4', strom: 'M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0', oppdatering: 'M12 4v11M7 10l5 5 5-5M5 20h14', system: 'M12 8v4M12 16h.01M12 3l9 4v6c0 5-4 8-9 9-5-1-9-4-9-9V7z' };
const PAGE_SUB: Partial<Record<Page, string>> = { radio: 'Norske kanaler og over 50 000 fra hele verden', eq: 'Egen profil per inngang og for hodetelefoner' };

function Desktop() {
  const s = status.value, r = route.value, p = product.value;
  const t = nowTitle(s);
  const cat = r.page === 'settings' ? cats.value.find((c) => c.id === r.cat) : undefined;
  const title = cat ? cat.n : TITLES[r.page];
  const sideCats = cats.value.filter((c) => c.id !== 'eq');
  const air = s?.input === 'airplay' && s.airplay_device ? 'Fra ' + s.airplay_device : '';
  return (
    <div class="desktop">
      <header class="hdr">
        <div class="row" style={{ minWidth: 0, gap: '14px' }}>
          <Logo lg word={false} />
          <div class="col" style={{ minWidth: 0 }}>
            <span class="row" style={{ gap: '10px' }}><span class="name ellip">{deviceName.value}</span><span class="type-badge" data-testid="type-badge"><Icon d={PRODUCT_ICON[p]} size={15} sw={1.5} />{PRODUCT_LABEL[p]}</span></span>
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
          <div class="head">INNSTILLINGER</div>
          {sideCats.map((c) => <button key={c.id} class={'nv' + (r.page === 'settings' && r.cat === c.id ? ' on' : '')} onClick={() => go('settings', c.id)}><span class="row gap12"><Icon d={NICON[c.id] ?? NICON.system ?? ''} size={18} sw={1.6} />{c.n}</span></button>)}
        </nav>
        <main class="main">
          <div class="pgh"><h1>{title}</h1>{cat ? <span class="sub">Endringer lagres på forsterkeren med en gang</span> : PAGE_SUB[r.page] ? <span class="sub">{PAGE_SUB[r.page]}</span> : null}</div>
          {r.page === 'home' && <><div class="player"><Art s={s} /><div class="col gap16"><div class="col gap4"><span style={{ fontSize: '24px', fontWeight: 600 }} data-testid="now-title">{t.title}</span><span class="muted">{t.sub}</span>{t.album && <span class="muted" style={{ fontSize: '13px', opacity: 0.8 }} data-testid="album">{t.album}</span>}{air && <span class="muted" style={{ fontSize: '12px' }}>{air}</span>}</div><Transport s={s} /><VolumeRow s={s} /></div></div><HomePage wide /></>}
          {r.page === 'play' && <div class="player"><PlayerBody /></div>}
          {r.page === 'radio' && <RadioPage wide />}
          {r.page === 'rooms' && <RoomsPage wide />}
          {r.page === 'eq' && <EqPage />}
          {r.page === 'settings' && (cat ? <CategoryDetail cat={cat} wide /> : <SettingsPage wide />)}
        </main>
        <aside class="sys">
          <span style={{ fontSize: '17px', fontWeight: 600 }}>Ditt system</span>
          <RoomsPage wide />
          {s?.overtemp && <div class="banner bad"><span>Forsterkeren er for varm</span></div>}
        </aside>
      </div>
      <div class="dock">
        <button class="np" onClick={() => go('play')}><div class="cover" style={{ background: artFor(s).bg }} /><div class="col" style={{ minWidth: 0, gap: '1px' }}><span class="mono ellip" style={{ fontSize: '10px', color: '#8b8b86' }}>{deviceName.value}</span><span class="ellip" style={{ fontSize: '14px', fontWeight: 600 }}>{t.title}</span><span class="ellip muted" style={{ fontSize: '12px' }}>{air || subLine(t)}</span></div></button>
        <Transport s={s} />
        <div class="dvol"><span class="mono" style={{ fontSize: '11px', color: '#8b8b86' }}>VOL</span><Slider value={s?.volume ?? 0} label="Volum" onCommit={setVolume} /><span class="mono" style={{ fontSize: '13px', minWidth: '2.5ch', textAlign: 'right' }}>{s?.volume ?? 0}</span></div>
      </div>
    </div>
  );
}
