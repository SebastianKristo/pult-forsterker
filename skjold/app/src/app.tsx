// Skall: telefon (App v2) under 900 px eller i Capacitor, ellers PC (S1 Web v3).
import { useEffect, useRef, useState } from 'preact/hooks';
import { App as CapApp } from '@capacitor/app';
import { isNative, hostLabel, PRODUCT_HW, PRODUCT_LABEL, PRODUCT_SHORT } from './lib/api';
import { atRoot, closeFull, deviceName, fullPlayer, go, lastError, mode, online, openFull, playPause, product, route, status, toast, type Page } from './lib/store';
import { ICONS } from './lib/settings';
import { cats } from './screens/settings';
import { Icon, Logo, PlayPauseIcon, PRODUCT_ICON } from './components/ui';
import { HomePage, RadioPage, RoomsPage, EqPage } from './screens/pages';
import { SettingsPage, CategoryDetail } from './screens/settings';
import { Art, PlayerBody, PowerButton, Transport, VolumeRow, nowTitle, subLine } from './screens/player';
import { FindDevice, Setup } from './screens/onboard';
import { inputLabel, showToast, settings } from './lib/store';
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

const ROOM_ICON = 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z';
const TABS: [Page, string, string][] = [['home', 'Hjem', ICONS.home ?? ''], ['rooms', 'Rom', ROOM_ICON], ['eq', 'Lyd', ICONS.eq ?? ''], ['radio', 'Radio', ICONS.radio ?? ''], ['settings', 'Innstillinger', ICONS.settings ?? '']];

/** Fullskjermspilleren: dra ned mer enn 90 px for å lukke. */
function FullPlayer() {
  const [dy, setDy] = useState(0);
  const start = useRef<{ y: number; ok: boolean } | null>(null);
  const body = useRef<HTMLDivElement>(null);
  const down = (e: PointerEvent) => {
    const t = e.target as HTMLElement;
    if (t.closest('input, select, button:not(.grab-btn)') && !t.closest('.grab')) return;   // ikke når volumet dras
    if ((body.current?.scrollTop ?? 0) > 0 && !t.closest('.grab')) return;
    start.current = { y: e.clientY, ok: true };
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch { /* ignore */ }
  };
  const cur = useRef(0);
  const move = (e: PointerEvent) => { if (start.current) { cur.current = Math.max(0, e.clientY - start.current.y); setDy(cur.current); } };
  const up = () => { if (!start.current) return; start.current = null; if (cur.current > 90) closeFull(); cur.current = 0; setDy(0); };
  return (
    <div class="full" data-testid="full" style={{ transform: dy ? `translateY(${dy}px)` : undefined, transition: dy ? 'none' : 'transform .2s' }}
      onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
      <div class="grab"><button class="grab-btn" aria-label="Lukk" onClick={closeFull}><i /></button></div>
      <div class="body" ref={body}><PlayerBody /></div>
    </div>
  );
}
const TITLES: Record<Page, string> = { home: 'Hjem', play: 'Spiller nå', eq: 'Lyd', radio: 'Radio', rooms: 'Rom', settings: 'Innstillinger' };

function Phone() {
  const s = status.value, r = route.value;
  const t = nowTitle(s);
  const page = r.page;
  return (
    <div class="phone">
      <div class="top">
        {page === 'home' ? <Logo /> : <span class="title">{TITLES[page]}</span>}
        <div class="row gap8">
          <button class="sys-pill" onClick={() => go('rooms')}><i class={online.value ? '' : 'off'} />{deviceName.value}</button>
          <PowerButton s={s} />
        </div>
      </div>
      <div class="scroll">
        <Offline />
        {page === 'home' && <HomePage />}
        {page === 'play' && <PlayerBody />}
        {page === 'eq' && <EqPage />}
        {page === 'radio' && <RadioPage />}
        {page === 'rooms' && <RoomsPage />}
        {page === 'settings' && <SettingsPage />}
      </div>
      <div class="bottom">
        {s && page !== 'home' && (
          <div class="mini">
            <button class="cover" style={{ padding: 0 }} onClick={openFull}><Art s={s} size="small" /></button>
            <button class="txt" onClick={openFull} data-testid="mini"><span class="ellip" style={{ fontSize: '13px' }}>{t.title}{t.sub && t.title !== t.sub ? <span class="muted"> · {t.sub}</span> : null}</span><span class="ellip muted" style={{ fontSize: '11px' }}>{deviceName.value} · {PRODUCT_SHORT[product.value]}</span></button>
            <button class="tbtn" aria-label="Spill/pause" data-testid="mini-pp" onClick={playPause}><PlayPauseIcon playing={s.playing} size={22} /></button>
          </div>
        )}
        <nav class="tabs">
          {TABS.map(([id, n, d]) => (
            <button key={id} class={'tab' + (page === id ? ' on' : '')} onClick={() => go(id)}><span class="pill"><Icon d={d} size={20} /></span>{n}</button>
          ))}
        </nav>
      </div>
      {fullPlayer.value && <FullPlayer />}
    </div>
  );
}

const NAV: [Page, string][] = [['home', 'Hjem'], ['play', 'Spiller nå'], ['radio', 'Radio'], ['rooms', 'Rom']];

function Desktop() {
  const s = status.value, r = route.value, p = product.value;
  const t = nowTitle(s);
  const cat = r.page === 'settings' ? cats.value.find((c) => c.id === r.cat) : undefined;
  const title = cat ? cat.n : TITLES[r.page];
  const sideCats = cats.value.filter((c) => c.id !== 'rom');   // Rom ligger i hovedmenyen
  const air = s?.input === 'airplay' && s.airplay_device ? 'Fra ' + s.airplay_device : '';
  const sysRows: [string, string][] = s ? [
    ['Kilde', inputLabel(s.input)],
    ['Volum', String(s.volume)],
    ...(p === 's1' ? [['Hodetelefoner', s.headphones ? 'Ja' : 'Nei'] as [string, string]] : []),
    ['Lyrion', s.lyrion ? 'Tilkoblet' : 'Ikke funnet'],
    ['Blåtann', s.bt_device || '–'],
    ...(s.input === 'airplay' && s.airplay_device ? [['AirPlay', s.airplay_device] as [string, string]] : []),
    ['Enhet', PRODUCT_LABEL[p]],
    ['Adresse', hostLabel()],
    ['Versjon', s.version ? 'v' + s.version : '–']
  ] : [['Adresse', hostLabel()]];
  return (
    <div class="desktop">
      <header class="hdr">
        <div class="row gap16" style={{ minWidth: 0 }}>
          <Logo />
          <span class="dev-ico"><Icon d={PRODUCT_ICON[p]} size={24} sw={1.3} /></span>
          <div class="col" style={{ minWidth: 0 }}>
            <span class="row gap8"><span class="name ellip">{deviceName.value}</span><span class="type-badge" data-testid="type-badge">{PRODUCT_LABEL[p]}</span></span>
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
          {NAV.map(([id, n]) => <button key={id} class={'nv' + (r.page === id || (id === 'rooms' && r.page === 'settings' && r.cat === 'rom') ? ' on' : '')} onClick={() => go(id)}>{n}</button>)}
          <div class="head">INNSTILLINGER</div>
          {sideCats.map((c) => <button key={c.id} class={'nv' + (r.page === 'settings' && r.cat === c.id ? ' on' : '')} onClick={() => go('settings', c.id)}>{c.n}</button>)}
        </nav>
        <main class="main">
          <div class="pgh"><h1>{title}</h1>{cat && <span class="sub">{cat.sub}</span>}</div>
          {r.page === 'home' && <><div class="player"><Art s={s} /><div class="col gap16"><div class="col gap4"><span style={{ fontSize: '24px', fontWeight: 600 }} data-testid="now-title">{t.title}</span><span class="muted">{t.sub}</span>{t.album && <span class="muted" style={{ fontSize: '13px', opacity: 0.8 }} data-testid="album">{t.album}</span>}{air && <span class="muted" style={{ fontSize: '12px' }}>{air}</span>}</div><Transport s={s} /><VolumeRow s={s} /></div></div><HomePage wide /></>}
          {r.page === 'play' && <div class="player"><PlayerBody /></div>}
          {r.page === 'radio' && <RadioPage />}
          {r.page === 'rooms' && <RoomsPage />}
          {r.page === 'eq' && <EqPage />}
          {r.page === 'settings' && (cat ? <CategoryDetail cat={cat} wide /> : <SettingsPage wide />)}
        </main>
        <aside class="sys">
          <span class="kicker">Ditt system</span>
          <button class="sys-dev" onClick={() => go('rooms')}>
            <span class="dev-ico"><Icon d={PRODUCT_ICON[p]} size={22} sw={1.3} /></span>
            <span class="col" style={{ minWidth: 0 }}><span class="ellip" style={{ fontWeight: 600 }}>{deviceName.value}</span><span class="muted ellip" style={{ fontSize: '12px' }}>{PRODUCT_HW[p]}</span></span>
          </button>
          <div class="col gap6" style={{ fontSize: '13px' }} data-testid="sys-rows">
            {sysRows.map(([k, v]) => <div class="row between gap8" key={k}><span class="muted">{k}</span><span class={'ellip' + (k === 'Adresse' || k === 'Volum' ? ' mono' : '')} style={k === 'Adresse' ? { fontSize: '11px', color: 'var(--muted)' } : undefined}>{v}</span></div>)}
            {s?.overtemp && <div class="banner bad"><span>Forsterkeren er for varm</span></div>}
          </div>
        </aside>
      </div>
      <div class="dock">
        <button class="np" onClick={() => go('play')}><div class="cover" style={{ width: '46px', flexShrink: 0 }}><Art s={s} size="small" /></div><div class="col" style={{ minWidth: 0 }}><span class="ellip">{t.title}</span><span class="ellip muted" style={{ fontSize: '12px' }}>{air || subLine(t)}</span></div></button>
        <Transport s={s} />
        <VolumeRow s={s} />
      </div>
    </div>
  );
}
