// Skall: telefon (App v2) under 900 px eller i Capacitor, ellers PC (S1 Web v3).
import { useEffect, useState } from 'preact/hooks';
import { isNative, hostLabel } from './lib/api';
import { deviceName, fullPlayer, go, lastError, mode, online, route, status, toast, type Page } from './lib/store';
import { ICONS, CATS } from './lib/settings';
import { Icon, Logo, PlayPauseIcon } from './components/ui';
import { HomePage, RadioPage, RoomsPage, EqPage } from './screens/pages';
import { SettingsPage, CategoryDetail } from './screens/settings';
import { Art, PlayerBody, PowerButton, Transport, VolumeRow, nowTitle } from './screens/player';
import { FindDevice, Setup } from './screens/onboard';
import { api } from './lib/api';
import { act, inputLabel, showToast, settings } from './lib/store';
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

const TABS: [Page, string, string][] = [['home', 'Hjem', ICONS.home ?? ''], ['eq', 'Lyd', ICONS.eq ?? ''], ['radio', 'Radio', ICONS.radio ?? ''], ['settings', 'Innstillinger', ICONS.settings ?? '']];
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
            <button class="cover" style={{ padding: 0 }} onClick={() => { fullPlayer.value = true; }}><Art s={s} size="small" /></button>
            <button class="txt" onClick={() => { fullPlayer.value = true; }}><span class="ellip" style={{ fontSize: '13px' }}>{t.title}</span><span class="ellip muted" style={{ fontSize: '11px' }}>{t.sub}</span></button>
            <button class="tbtn" aria-label="Spill/pause" onClick={() => act(() => api.transport('playpause'), { playing: !s.playing })}><PlayPauseIcon playing={s.playing} size={22} /></button>
          </div>
        )}
        <nav class="tabs">
          {TABS.map(([id, n, d]) => (
            <button key={id} class={'tab' + (page === id ? ' on' : '')} onClick={() => go(id)}><span class="pill"><Icon d={d} size={20} /></span>{n}</button>
          ))}
        </nav>
      </div>
      {fullPlayer.value && (
        <div class="full">
          <div class="grab"><button aria-label="Lukk" onClick={() => { fullPlayer.value = false; }}><i /></button></div>
          <div class="body"><PlayerBody /></div>
        </div>
      )}
    </div>
  );
}

const NAV: [Page, string][] = [['home', 'Hjem'], ['play', 'Spiller nå'], ['radio', 'Radio'], ['rooms', 'Rom']];

function Desktop() {
  const s = status.value, r = route.value;
  const t = nowTitle(s);
  const cat = r.page === 'settings' ? CATS.find((c) => c.id === r.cat) : undefined;
  const title = cat ? cat.n : TITLES[r.page];
  return (
    <div class="desktop">
      <header class="hdr">
        <div class="row gap16"><Logo /><div class="col"><span class="name">{deviceName.value}</span><span class="sub">{hostLabel()} · v{s?.version ?? '–'}</span></div></div>
        <div class="row gap10">
          <span class="link-pill"><i style={{ background: online.value ? 'var(--green)' : 'var(--red)' }} />{online.value ? 'Tilkoblet' : 'Frakoblet'}</span>
          <PowerButton s={s} />
        </div>
      </header>
      <Offline />
      <div class="cols">
        <nav class="side">
          {NAV.map(([id, n]) => <button key={id} class={'nv' + (r.page === id ? ' on' : '')} onClick={() => go(id)}>{n}</button>)}
          <div class="head">INNSTILLINGER</div>
          {CATS.map((c) => <button key={c.id} class={'nv' + (r.page === 'settings' && r.cat === c.id ? ' on' : '')} onClick={() => go('settings', c.id)}>{c.n}</button>)}
        </nav>
        <main class="main">
          <div class="pgh"><h1>{title}</h1>{cat && <span class="sub">{cat.sub}</span>}</div>
          {r.page === 'home' && <><div class="player"><Art s={s} /><div class="col gap16"><div class="col gap4"><span style={{ fontSize: '24px', fontWeight: 600 }} data-testid="now-title">{t.title}</span><span class="muted">{t.sub}</span></div><Transport s={s} /><VolumeRow s={s} /></div></div><HomePage wide /></>}
          {r.page === 'play' && <div class="player"><PlayerBody /></div>}
          {r.page === 'radio' && <RadioPage />}
          {r.page === 'rooms' && <RoomsPage />}
          {r.page === 'eq' && <EqPage />}
          {r.page === 'settings' && (cat ? <CategoryDetail cat={cat} wide /> : <SettingsPage wide />)}
        </main>
        <aside class="sys">
          <span class="kicker">System</span>
          <div class="col gap6" style={{ fontSize: '13px' }}>
            <div class="row between"><span class="muted">Kilde</span><span>{s ? inputLabel(s.input) : '–'}</span></div>
            <div class="row between"><span class="muted">Volum</span><span class="mono">{s?.volume ?? '–'}</span></div>
            <div class="row between"><span class="muted">Hodetelefoner</span><span>{s?.headphones ? 'Ja' : 'Nei'}</span></div>
            <div class="row between"><span class="muted">Lyrion</span><span>{s?.lyrion ? 'Tilkoblet' : 'Ikke funnet'}</span></div>
            <div class="row between"><span class="muted">Blåtann</span><span class="ellip">{s?.bt_device || '–'}</span></div>
            {s?.overtemp && <div class="banner bad"><span>Forsterkeren er for varm</span></div>}
          </div>
        </aside>
      </div>
      <div class="dock">
        <button class="np" onClick={() => go('play')}><div class="cover" style={{ width: '46px', flexShrink: 0 }}><Art s={s} size="small" /></div><div class="col" style={{ minWidth: 0 }}><span class="ellip">{t.title}</span><span class="ellip muted" style={{ fontSize: '12px' }}>{t.sub}</span></div></button>
        <Transport s={s} />
        <VolumeRow s={s} />
      </div>
    </div>
  );
}
