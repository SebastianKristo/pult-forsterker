import { NrkContinueShelf } from './nrk';
// PC-sider (skall dk2): Hjem, Spiller, Radio og bibliotekene (YouTube Music / Navidrome) med eget, bredt oppsett.
// Samme data og handlinger som telefonsidene – bare ny plassering og størrelser.
import { useEffect, useState } from 'preact/hooks';
import { type ComponentChildren } from 'preact';
import { homeOrder, orderSources } from '../lib/homelayout';
import { Boundary } from '../components/boundary';
import { localOn, localVol, setLocalVol } from '../lib/localplay';
import { api, PRODUCT_LABEL, type Fav, type InputId, type Station } from '../lib/api';
import { act, deviceName, eqActiveSource, go, inputLabel, recent, setVolume, settings, status } from '../lib/store';
import { art, EQ } from '../lib/settings';
import { Icon, PRODUCT_ICON, Slider, SrcCircle } from '../components/ui';
import { browseState, currentStation, favOf, favs, favsLoaded, loadBrowse, loadFavs, norm, playFav, playStation, search, searchBusy, searchRes, shelves, toggleFav } from '../lib/radio';
import { ndAlbumList, ndConf, ndConfigured, ndCover, ndPlaylists, ndSearch, type NdAlbum, type NdPlaylist, type NdSong } from '../lib/navidrome';
import { addToQueue, clearHist, fmtDur, hist, li, LIB_NAME, lq, lsvc, playNd, whenText, type LibId } from '../lib/library';
import { InputChips, SeekBar, Transport, artFor, canSeek, nowTitle, seekTo, sourceLine, subLine } from './player';
import { useRooms } from './phone';
import { SpeakerButton } from './groups';
import { collSongs, libUi } from './library';
import { ytmHomeCached, ytmSearch, ytmWhy } from '../lib/ytm';
import { LyricsPane, SubwavePane } from './plugins';
import { WrappedTeaser } from './extras';
import { RecognizeBox, RoutinesShelf } from './features';
import { DiscoverCard, SmartRadioBox } from './extras2';
import { AskBox } from './ai';

const PLAY = 'M8 5v14l11-7z';
const SRC_ORDER: [InputId, string][] = [['radio', 'Radio'], ['airplay', 'AirPlay'], ['bt', 'Blåtann'], ['spotify', 'Spotify'], ['plex', 'Plex'], ['aux', 'AUX'], ['aux2', 'AUX'], ['usb', 'USB']];
const favToSt = (f: Fav): Station => ({ name: f.title, url: f.url, ...(f.genre ? { genre: f.genre } : {}), ...(f.image ? { image: f.image } : {}) });
const ndBg = (id: string | undefined, key: string, size = 300) => { const u = ndCover(id, size), a = art(key); return u ? 'url("' + u.replace(/"/g, '') + '") center / cover no-repeat, ' + a.bg : a.bg; };

function greet(): string { const h = new Date().getHours(); return h < 5 ? 'God natt' : h < 10 ? 'God morgen' : h < 17 ? 'God dag' : h < 22 ? 'God kveld' : 'God natt'; }

function SecHead({ title, kicker, more, onMore }: { title: string; kicker?: string; more?: string; onMore?: () => void }) {
  return (
    <div class="dkx-sh">
      <div class="col" style={{ gap: '2px', minWidth: 0 }}>{kicker && <span class="kicker">{kicker}</span>}<h2>{title}</h2></div>
      {more && <button class="link0" onClick={onMore}>{more}</button>}
    </div>
  );
}

function Tile({ bg, ink, label, name, meta, src, round, live, onClick }: { bg: string; ink?: string; label?: string; name: string; meta?: string; src?: string; round?: boolean; live?: boolean; onClick: () => void }) {
  return (
    <button class="dkx-tile" onClick={onClick}>
      <div class={"sq" + (round ? " rnd" : "")} style={{ background: bg, color: ink ?? "transparent" }}>
        {label && <b>{label}</b>}
        {live && <span class="live">DIREKTE</span>}
        <span class="pl"><Icon d={PLAY} size={14} sw={0} color="#f2f2ee" style={{ fill: '#f2f2ee' }} /></span>
      </div>
      <span class="n">{name}</span>
      {meta && <span class="m">{src && <SrcCircle label={src} size={15} />}<span class="ellip">{meta}</span></span>}
    </button>
  );
}

// ---------- Hjem ----------
function useNdHome() {
  const [pls, setPls] = useState<NdPlaylist[]>([]), [alb, setAlb] = useState<NdAlbum[]>([]);
  const on = ndConfigured(), key = on ? ndConf.value.url + '|' + ndConf.value.user : '';   // innloggingen kan komme fra Skjold etter første visning
  useEffect(() => {
    if (!on) return;
    ndPlaylists().then(setPls).catch(() => setPls([]));
    ndAlbumList('recent', 10).then((a) => setAlb(a.length ? a : [])).catch(() => setAlb([]));
  }, [key]);
  return { pls, alb };
}
/** YouTube Music-spillelister og «Til deg» fra Skjold-enheten (når YouTube Music er slått på). */
function useYtmHome() {
  const [l, setL] = useState<NdAlbum[]>([]);
  const on = settings.value.ytmEn;
  useEffect(() => {
    if (!on) { setL([]); return; }
    let live = true;
    ytmHomeCached().then((h) => { if (live) setL(uniqId([...h.playlists, ...h.frequent.slice(0, 8), ...h.other.slice(0, 8)]).slice(0, 16)); }).catch(() => { if (live) setL([]); });
    return () => { live = false; };
  }, [on]);
  return l;
}
const uniqId = <T extends { id: string },>(l: T[]): T[] => l.filter((x, i) => l.findIndex((y) => y.id === x.id) === i);

export function DeskHome() {
  const s = status.value, t = nowTitle(s), a = artFor(s);
  useEffect(() => { if (!favsLoaded.value) void loadFavs(); }, []);
  const nd = useNdHome();
  const yt = useYtmHome();
  const rooms = useRooms();
  const inputs = s?.inputs?.length ? s.inputs : ['airplay', 'bt', 'spotify', 'radio', 'aux', 'aux2', 'usb'];
  const services = orderSources(SRC_ORDER.filter(([id]) => inputs.includes(id)), (x) => x[1]);
  const pickSrc = (id: InputId) => { if (id === 'radio') { go('radio'); return; } void act(() => api.input(id), { input: id }); go('play'); };
  const live = s?.input === 'radio' && !s.source_label;
  const eqSrc = eqActiveSource.value, eq = settings.value.eq[eqSrc]?.eq ?? [0, 0, 0, 0, 0];
  const rc = recent.value.slice(0, 12);
  useEffect(() => { if (browseState.value === 'idle') void loadBrowse(); }, []);
  const srcOf = (id: InputId) => SRC_ORDER.find(([k]) => k === id)?.[1];
  const popular = shelves.value.find((x) => x.id === 'popular_no') ?? shelves.value[0];
  const curName = (s?.input === 'radio' && (s.radio_now?.name || s.station)) || '';
  const playRecent = (x: typeof rc[number]) => {
    if (x.station) { const f = favs.value.find((f) => f.title === x.title); if (f) playFav(f); else if (x.url) void act(() => api.radioPlay({ url: x.url!, title: x.title }), { input: 'radio' }); else go('radio'); }
    else void act(() => api.input(x.input), { input: x.input });
  };
  const sections: Record<string, ComponentChildren> = {
    wrapped: <WrappedTeaser />,
    ask: <AskBox />,
    discover: <DiscoverCard />,
    routines: <RoutinesShelf />,
    recent: (rc.length > 0 && <section class="col gap12">
          <SecHead title="Nylig spilt" />
          <div class="dkx-row">{rc.map((x) => { const ra = art(x.title, x.image); return <Tile key={x.key} bg={ra.bg} ink={ra.ink} label={ra.logo ? '' : x.big} name={x.title} meta={x.kind} src={x.station ? 'Radio' : srcOf(x.input)} onClick={() => playRecent(x)} />; })}</div>
        </section>),
    nrk: <NrkContinueShelf />,
    trending: (popular && popular.items.length > 0 && <section class="col gap12">
          <SecHead title="Populært på radio nå" kicker="RADIO" more="Se all radio ›" onMore={() => go('radio')} />
          <div class="dkx-row">{popular.items.slice(0, 14).map((st: Station) => { const ra = art(st.name, st.image); return <Tile key={st.url || st.name} bg={ra.bg} ink={ra.ink} label={ra.logo ? '' : st.name} name={st.name} meta={st.genre || 'Nettradio'} src="Radio" live={!!curName && norm(curName) === norm(st.name)} onClick={() => playStation(st)} />; })}</div>
        </section>),
    favs: (
        <section class="col gap12">
          <SecHead title="Radiofavoritter" kicker={favs.value.length ? favs.value.length + ' KANALER' : undefined} more="Se all radio ›" onMore={() => go('radio')} />
          {favs.value.length ? (
            <div class="dkx-row">
              {favs.value.map((f) => { const fa = art(f.title, f.image); const on = s?.input === 'radio' && s.preset === f.n; return (
                <Tile key={f.n} bg={fa.bg} ink={fa.ink} label={fa.logo ? '' : f.title} name={f.title} meta={on ? 'Spiller nå' : f.genre || 'Radio'} src="Radio" live={on} onClick={() => playFav(f)} />
              ); })}
            </div>
          ) : favsLoaded.value ? <button class="dashed" onClick={() => go('radio')}>Legg til radiokanal</button> : null}
        </section>
    ),
    playlists: (
        <section class="col gap12">
          <SecHead title="Dine spillelister" kicker="FRA MUSIKKTJENESTENE" more={ndConfigured() ? 'Navidrome ›' : undefined} onMore={() => go('lib', 'nd')} />
          {nd.pls.length || nd.alb.length || yt.length ? (
            <div class="dkx-row">
              {yt.map((p) => <Tile key={'y' + p.id} bg={ndBg(p.coverArt, p.name)} label={ndCover(p.coverArt) ? '' : p.name} name={p.name} meta={p.playlist ? 'Spilleliste' : p.artist || 'YouTube Music'} src="YouTube Music" onClick={() => { go('lib', 'ytm'); libUi.pl.value = { kind: p.playlist ? 'pl' : 'album', id: p.id, name: p.name }; }} />)}
              {nd.pls.map((p) => <Tile key={'p' + p.id} bg={ndBg(p.coverArt, p.name)} label={ndCover(p.coverArt) ? '' : p.name} name={p.name} meta={p.songCount + ' låter'} src="Navidrome" onClick={() => { go('lib', 'nd'); libUi.pl.value = { kind: 'pl', id: p.id, name: p.name }; }} />)}
              {nd.alb.map((al) => <Tile key={'a' + al.id} bg={ndBg(al.coverArt, al.name)} label={ndCover(al.coverArt) ? '' : al.name} name={al.name} meta={al.artist} src="Navidrome" onClick={() => { go('lib', 'nd'); libUi.pl.value = { kind: 'album', id: al.id, name: al.name }; }} />)}
            </div>
          ) : (
            <div class="dkx-empty"><span>Koble til Navidrome eller YouTube Music for å se spillelistene dine her.</span><button class="btn" onClick={() => go('int')}>Integrasjoner</button></div>
          )}
        </section>
    ),
    sources: (
        <section class="col gap12">
          <SecHead title="Dine tjenester" more="Rediger" onMore={() => go('settings', 'hjemskjerm')} />
          <div class="dkx-srcs">
            {services.map(([id, label]) => <button key={id} class={'svc' + (s?.input === id ? ' on' : '')} onClick={() => pickSrc(id)}><SrcCircle label={label} size={84} /><span>{id === 'aux' || id === 'aux2' ? inputLabel(id) : label}</span></button>)}
            {(['ytm', 'nd'] as LibId[]).map((id) => <button key={id} class="svc" onClick={() => go('lib', id)}><SrcCircle label={LIB_NAME[id]} size={84} /><span>{LIB_NAME[id]}</span></button>)}
          </div>
        </section>
    )
  };
  return (
    <div class="dkx-home" data-testid="dashboard">
      <div class="dkx-main">
        <div class="dkx-hi">
          <div class="col" style={{ gap: '4px', minWidth: 0 }}>
            <span class="kicker">{deviceName.value.toUpperCase()} · {s?.power ? (s.playing ? 'SPILLER' : 'KLAR') : 'STANDBY'}</span>
            <h1>{greet()}</h1>
          </div>
          <button class="dkx-now" onClick={() => go('play')} aria-label="Åpne spilleren">
            <span class="cv" style={{ background: a.bg, color: a.ink }}>{!a.img && t.title.slice(0, 2)}</span>
            <span class="col" style={{ gap: '2px', minWidth: 0, textAlign: 'left' }}>
              <span class="kicker">{live ? <span class="live">DIREKTE</span> : 'NÅ SPILLES'}</span>
              <b class="ellip">{t.title}</b>
              <span class="ellip muted" style={{ fontSize: '12.5px' }}>{subLine(t) || sourceLine(s)}</span>
            </span>
            <span class="go">Åpne spiller ›</span>
          </button>
        </div>

        {homeOrder(['recent', 'sources', 'playlists', 'trending', 'favs', 'nrk', 'routines', 'ask', 'discover', 'wrapped']).map((id) => <Boundary key={id} liten>{sections[id]}</Boundary>)}
        <button class="link0" style={{ alignSelf: 'flex-start' }} onClick={() => go('settings', 'hjemskjerm')}>Rediger hjemskjerm</button>
      </div>

      <aside class="dkx-side">
        <section class="card dkx-card">
          <SecHead title="Ditt system" more="Grupper ›" onMore={() => go('grp')} />
          <div class="col" style={{ gap: '8px' }}>
            {rooms.map((x) => (
              <button key={x.key} class={'mini-room' + (x.active ? ' on' : '')} onClick={() => go('rooms')}>
                <span class="ri"><Icon d={PRODUCT_ICON[x.product]} size={18} sw={1.5} /></span>
                <span class="col" style={{ minWidth: 0, gap: '2px' }}><span class="row between" style={{ gap: '8px' }}><b class="ellip">{x.name}</b><span class="mono muted" style={{ fontSize: '12px' }}>{x.st ? x.st.volume : '–'}</span></span><span class="muted ellip" style={{ fontSize: '12px' }}>{PRODUCT_LABEL[x.product]}{x.st ? ' · ' + nowTitle(x.st).title : ' · frakoblet'}</span></span>
              </button>
            ))}
          </div>
        </section>
        <section class="card dkx-card">
          <SecHead title="Lyd nå" more="Equalizer ›" onMore={() => go('eq')} />
          <div class="eq-mini">{eq.map((v, i) => <div key={i} class="b"><span style={{ height: Math.max(6, 40 + v * 3.2) + 'px' }} /><em>{EQ.bands[i]}</em></div>)}</div>
          <span class="muted" style={{ fontSize: '12px' }}>Profil for {EQ.sources.find((x) => x[0] === eqSrc)?.[1] ?? ''}</span>
        </section>
      </aside>
    </div>
  );
}

// ---------- Spiller ----------
export function DeskPlayer() {
  const s = status.value, t = nowTitle(s), a = artFor(s);
  const [tab, setTab] = useState<'song' | 'queue' | 'lyrics' | 'booth'>('song');
  const dur = s?.duration ?? 0, pos = s?.position ?? 0;
  const live = s?.input === 'radio' && !s.source_label;
  const libQ = !!lsvc.value && lq.value.length > 0;
  return (
    <div class="dkx-player">
      <div class="glow" style={{ background: a.bg }} />
      <div class="cvwrap"><div class="cv" style={{ background: a.bg, color: a.ink }}>{!a.img && <span>{t.title}</span>}</div></div>
      <div class="info">
        <div class="seg">{((s?.subwave ? [['song', 'Låt'], ['booth', 'Booth'], ['queue', 'Kø']] : [['song', 'Låt'], ['queue', 'Kø'], ['lyrics', 'Tekst']]) as ['song' | 'queue' | 'lyrics' | 'booth', string][]).map(([k, n]) => <button key={k} class={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{n}</button>)}</div>
        {tab === 'song' ? <>
          <RecognizeBox />
          <SmartRadioBox seed={libQ && lq.value[li.value] ? { source: 'navidrome', id: lq.value[li.value]!.id, title: lq.value[li.value]!.title, artist: lq.value[li.value]!.artist } : s?.playing && s.artist ? { title: t.title, artist: s.artist } : null} />
          <div class="col" style={{ gap: '6px', minWidth: 0 }}>
            <span class="kicker">{live ? <span class="live">DIREKTE</span> : sourceLine(s).toUpperCase()}</span>
            <h1 class="tt" data-testid="now-title">{t.title}</h1>
            <span class="sub">{t.sub}</span>
            {t.album && <span class="muted" data-testid="album">{t.album}</span>}
            {s?.input === 'airplay' && s.airplay_device && <span class="muted" style={{ fontSize: '12px' }}>Fra {s.airplay_device}</span>}
          </div>
          {dur > 0 ? (
            <SeekBar pos={pos} dur={dur} seek={canSeek(s) ? seekTo : null} />
          ) : live ? <div class="bar live"><i /></div> : null}
          <div class="ctl"><Transport s={s} /></div>
          <div class="vol"><Icon d="M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12" size={20} sw={1.6} /><Slider value={localOn.value ? localVol.value : s?.volume ?? 0} label={localOn.value ? 'Volum på denne enheten' : 'Volum'} onCommit={localOn.value ? setLocalVol : setVolume} /><span class="num">{localOn.value ? localVol.value : s?.volume ?? 0}</span></div>
          <div class="row gap10" style={{ flexWrap: 'wrap' }}><span class="kicker">SPILL PÅ</span><SpeakerButton /></div>
          <div class="col gap8"><span class="kicker">KILDE</span><InputChips s={s} /></div>
        </> : tab === 'lyrics' ? <LyricsPane pos={pos} /> : tab === 'booth' ? <SubwavePane mode="booth" /> : s?.subwave ? <SubwavePane mode="queue" /> : (
          <div class="dkx-queue">
            {libQ ? lq.value.map((x, i) => (
              <button key={x.id + i} class={i === li.value ? 'on' : ''} onClick={() => playNd(lq.value, i, lsvc.value ?? 'nd')}>
                <span class="qc" style={{ background: ndBg(x.coverArt, x.album, 120) }} />
                <span class="col" style={{ minWidth: 0, gap: '2px', textAlign: 'left' }}><b class="ellip">{x.title}</b><span class="ellip muted" style={{ fontSize: '12px' }}>{x.artist}</span></span>
                <span class="mono muted" style={{ fontSize: '11px' }}>{fmtDur(x.duration)}</span>
              </button>
            )) : (
              <div class="dkx-empty"><span>{live ? 'Radio har ingen kø. Det som spilles nå er «' + t.title + '».' : 'Køen er tom. Spill et album eller en spilleliste fra Navidrome for å fylle den.'}</span><button class="btn" onClick={() => go('lib', 'nd')}>Åpne Navidrome</button></div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- Radio ----------
export function DeskRadio() {
  useEffect(() => { void loadFavs(); if (browseState.value === 'idle') void loadBrowse(); }, []);
  const [q, setQ] = useState('');
  const [genre, setGenre] = useState<string | null>(null);
  const s = status.value, cur = currentStation(s), ql = norm(q);
  const allSt: Station[] = [...favs.value.map(favToSt), ...shelves.value.flatMap((x) => x.items)];
  const curSt: Station | null = cur ? (allSt.find((x) => norm(x.name) === norm(cur)) ?? { name: cur, url: s?.radio_now?.url ?? '', ...(s?.radio_now?.image ? { image: s.radio_now.image } : {}), ...(s?.radio_now?.genre ? { genre: s.radio_now.genre } : {}) }) : null;
  const hero = curSt ?? (favs.value[0] ? favToSt(favs.value[0]) : shelves.value[0]?.items[0] ?? null);
  const hl = !!hero && !!cur && norm(cur) === norm(hero.name);
  const ha = hero ? art(hero.name, hero.image) : null;
  const heroNow = hl && s?.radio_now?.now ? s.radio_now.now : hl && s?.title ? [s.title, s.artist].filter(Boolean).join(' · ') : '';
  const genres = shelves.value.filter((x) => x.id !== 'popular_no');
  const gSel = genre ? genres.find((g) => g.id === genre) : undefined;
  const isOn = (st: Station) => !!cur && norm(cur) === norm(st.name);
  const rows = gSel ? [{ kicker: 'SJANGER', title: gSel.title, items: gSel.items }]
    : [...shelves.value.filter((x) => x.id === 'popular_no').map((x) => ({ kicker: 'NORGE', title: x.title, items: x.items.slice(0, 12) })),
      ...genres.slice(0, 3).map((x) => ({ kicker: 'SJANGER', title: x.title, items: x.items.slice(0, 12) }))];
  const res = searchRes.value && norm(searchRes.value.q) === ql ? searchRes.value : null;
  const locMap = new Map<string, Station>();
  if (ql) { for (const x of allSt) if ((x.name + ' ' + (x.genre ?? '')).toLowerCase().includes(ql) && !locMap.has(norm(x.name))) locMap.set(norm(x.name), x); }
  for (const x of res?.norway ?? []) if (!locMap.has(norm(x.name))) locMap.set(norm(x.name), x);
  const loc = [...locMap.values()], onl = (res?.world ?? []).filter((x) => !locMap.has(norm(x.name)));
  const row = (x: Station, i: number) => { const ra = art(x.name, x.image), f = !!favOf(x.name, x.url); return (
    <div key={x.url + x.name + i} class="dkx-srow">
      <button class="lg" style={{ background: ra.bg, color: ra.ink }} onClick={() => playStation(x)} aria-label={'Spill ' + x.name}>{ra.logo ? '' : x.name.slice(0, 3)}</button>
      <button class="tx" onClick={() => playStation(x)}><b class="ellip">{x.name}</b><span class="ellip muted">{[x.genre, x.country, x.bitrate ? x.bitrate + ' kbps' : ''].filter(Boolean).join(' · ') || 'Nettradio'}</span></button>
      <button class="star" style={{ color: f ? 'var(--accent-2)' : 'var(--muted)' }} aria-label={f ? 'Fjern fra favoritter' : 'Legg til favoritter'} onClick={() => void toggleFav(x)}>{f ? '★' : '☆'}</button>
    </div>
  ); };
  return (
    <div class="dkx-radio">
      <div class="dkx-rmain">
        <div class="dkx-search"><Icon d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4" size={18} sw={1.8} /><input value={q} placeholder="Søk etter kanal, by eller sjanger" onInput={(e) => { const v = e.currentTarget.value; setQ(v); search(v); }} aria-label="Søk etter radiokanal" />{q && <button class="x" onClick={() => setQ('')} aria-label="Tøm søket">×</button>}</div>
        {ql ? <div class="col gap16">
          {loc.length > 0 && <section class="col gap8"><span class="kicker">NORSKE KANALER</span><div class="dkx-list">{loc.map(row)}</div></section>}
          {searchBusy.value && <span class="muted" style={{ fontSize: '13px' }}>Søker i Radio Browser …</span>}
          {onl.length > 0 && <section class="col gap8"><span class="kicker">FRA HELE VERDEN · RADIO BROWSER</span><div class="dkx-list">{onl.map(row)}</div></section>}
          {res?.offline && !searchBusy.value && <span class="muted" style={{ fontSize: '13px' }}>Radio Browser svarer ikke akkurat nå. Prøv igjen litt senere.</span>}
          {!searchBusy.value && !loc.length && !onl.length && ql.length >= 3 && !res?.offline && <span class="muted" style={{ fontSize: '13px' }}>Ingen kanaler funnet. Du kan legge til en strømadresse under Innstillinger → Radio.</span>}
        </div> : <>
          {hero && ha && (
            <div class="dkx-rhero">
              <div class="glow" style={{ background: ha.bg }} />
              <button class="cv" style={{ background: ha.bg, color: ha.ink }} onClick={() => playStation(hero)} aria-label={'Spill ' + hero.name}>{ha.logo ? '' : hero.name}</button>
              <div class="col" style={{ gap: '8px', minWidth: 0, position: 'relative' }}>
                <span class="kicker"><i class="dot" style={{ background: hl ? 'var(--red)' : 'var(--line-3)' }} />{hl ? 'SPILLER NÅ' : 'FRA FAVORITTENE'}</span>
                <h2>{hero.name}</h2>
                <span class="muted">{hero.genre || 'Radio'}</span>
                {heroNow && <span class="now">{heroNow}</span>}
                <div class="row gap10" style={{ marginTop: '6px', flexWrap: 'wrap' }}>
                  <button class="btn primary" onClick={() => playStation(hero)}>{hl ? 'Spiller' : 'Spill'}</button>
                  <button class="btn" onClick={() => void toggleFav(hero)}>{favOf(hero.name, hero.url) ? '★ I favorittene' : '☆ Legg til favoritter'}</button>
                </div>
              </div>
            </div>
          )}
          {genres.length > 0 && (
            <div class="dkx-chips">{[{ id: null as string | null, title: 'Alle' }, ...genres.map((g) => ({ id: g.id as string | null, title: g.title }))].map((g) => <button key={g.title} class={genre === g.id ? 'on' : ''} onClick={() => setGenre(g.id)}>{g.title}</button>)}</div>
          )}
          {rows.filter((r) => r.items.length).map((r) => (
            <section class="col gap12" key={r.title}>
              <SecHead title={r.title} kicker={r.kicker} />
              <div class="dkx-grid">{r.items.map((st) => { const sa = art(st.name, st.image); return <Tile key={st.url + st.name} bg={sa.bg} ink={sa.ink} label={sa.logo ? '' : st.name} name={st.name} meta={st.genre || 'Radio'} live={isOn(st)} onClick={() => playStation(st)} />; })}</div>
            </section>
          ))}
          {browseState.value === 'offline' && <span class="muted" style={{ fontSize: '13px' }}>Radio Browser svarer ikke akkurat nå, så bare favorittene vises.</span>}
        </>}
      </div>
      <aside class="dkx-rside card">
        <SecHead title="Dine favoritter" kicker={favs.value.length + ' AV 50'} more="Administrer" onMore={() => go('settings', 'radio')} />
        <div class="col" style={{ gap: '2px' }}>
          {favs.value.map((f) => { const fa = art(f.title, f.image), on = s?.input === 'radio' && s.preset === f.n; return (
            <button key={f.n} class={'dkx-frow' + (on ? ' on' : '')} onClick={() => playFav(f)}>
              <em>{f.n}</em><span class="lg" style={{ background: fa.bg, color: fa.ink }}>{fa.logo ? '' : f.title.slice(0, 2)}</span>
              <span class="col" style={{ minWidth: 0, gap: '1px', textAlign: 'left' }}><b class="ellip">{f.title}</b><span class="ellip muted" style={{ fontSize: '11.5px' }}>{on ? 'Spiller nå' : f.genre || 'Radio'}</span></span>
            </button>
          ); })}
          {favsLoaded.value && !favs.value.length && <span class="muted" style={{ fontSize: '13px', padding: '8px 0' }}>Trykk ☆ på en kanal for å legge den til.</span>}
        </div>
      </aside>
    </div>
  );
}

// ---------- Bibliotek (YouTube Music / Navidrome) ----------
const TABS: Record<LibId, string[]> = { nd: ['Utforsk', 'Album', 'Spillelister', 'Historikk'], ytm: ['Utforsk', 'Spillelister', 'Historikk'] };

function useNdLib(on: boolean) {
  const [d, setD] = useState<{ newest: NdAlbum[]; rnd: NdAlbum[]; freq: NdAlbum[]; all: NdAlbum[]; pls: NdPlaylist[]; err: string; done: boolean }>({ newest: [], rnd: [], freq: [], all: [], pls: [], err: '', done: false });
  useEffect(() => {
    if (!on) return;
    Promise.all([ndAlbumList('newest', 12), ndAlbumList('random', 12), ndAlbumList('frequent', 12).catch(() => []), ndPlaylists().catch(() => []), ndAlbumList('newest', 60).catch(() => [])])
      .then(([newest, rnd, freq, pls, all]) => setD({ newest, rnd, freq, pls, all, err: '', done: true }))
      .catch((e: unknown) => setD((x) => ({ ...x, err: e instanceof Error ? e.message : String(e), done: true })));
  }, [on]);
  return d;
}

/** YouTube Music fra Skjold-enheten i samme form som useNdLib: rnd = «Til deg», pls = spillelister + «Til deg». */
function useYtmLib(on: boolean) {
  const [d, setD] = useState<{ newest: NdAlbum[]; rnd: NdAlbum[]; freq: NdAlbum[]; all: NdAlbum[]; pls: NdAlbum[]; err: string; done: boolean }>({ newest: [], rnd: [], freq: [], all: [], pls: [], err: '', done: false });
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!on) return;
    let live = true;
    setD((x) => ({ ...x, err: '', done: false }));
    ytmHomeCached(n > 0).then((h) => {
      if (!live) return;
      const rnd = uniqId([...h.frequent, ...h.other]);
      const pls = uniqId([...h.playlists, ...h.frequent.slice(0, 8), ...h.other.slice(0, 8)]);
      const empty = !h.newest.length && !pls.length;
      setD({ newest: h.newest, rnd, freq: [], all: h.newest, pls, err: empty ? 'Fant ingenting i YouTube Music. Legg inn cookien under Innstillinger → Musikktjenester for biblioteket ditt.' : '', done: true });
    }).catch(async (e: unknown) => { const err = await ytmWhy(e); if (live) setD((x) => ({ ...x, err, done: true })); });
    return () => { live = false; };
  }, [on, n]);
  return { ...d, retry: () => setN((x) => x + 1) };
}

function NotConnected({ lib, err, retry }: { lib: LibId; err?: string; retry?: () => void }) {
  const why = lib === 'ytm' ? err || 'Henter YouTube Music fra Skjold-enheten …' : err ? 'Fikk ikke kontakt med Navidrome: ' + err + '.' : 'Legg inn adressen til Navidrome-serveren, brukernavn og passord.';
  return (
    <div class="dkx-off" data-testid="lib-off">
      <SrcCircle label={LIB_NAME[lib]} size={64} />
      <div class="col" style={{ gap: '6px', minWidth: 0 }}>
        <span class="kicker" style={{ color: 'var(--accent-2)' }}>IKKE TILKOBLET</span>
        <h2>{lib === 'ytm' ? 'YouTube Music er ikke tilgjengelig' : LIB_NAME[lib] + ' er ikke koblet til'}</h2>
        <span class="muted" style={{ maxWidth: '60ch', lineHeight: 1.5 }}>{why}</span>
      </div>
      {retry && <button class="btn" onClick={retry}>Prøv igjen</button>}
      <button class="btn primary" onClick={() => go('int')}>Åpne Integrasjoner</button>
    </div>
  );
}

function TrackTable({ list, onPick, meta }: { list: NdSong[]; onPick: (i: number) => void; meta?: (i: number) => string }) {
  const cur = lsvc.value ? lq.value[li.value] : undefined;
  return (
    <div class="dkx-tt" role="table">
      <div class="hd" role="row"><span>#</span><span>Tittel</span><span>Album</span><span style={{ textAlign: 'right' }}>{meta ? 'Spilt' : 'Tid'}</span></div>
      {list.map((x, i) => (
        <button key={x.id + i} role="row" class={cur && cur.id === x.id ? 'on' : ''} onClick={() => onPick(i)}>
          <span class="mono muted">{i + 1}</span>
          <span class="t"><span class="qc" style={{ background: ndBg(x.coverArt, x.album, 120) }} /><span class="col" style={{ minWidth: 0, gap: '1px' }}><b class="ellip">{x.title}</b><span class="ellip muted" style={{ fontSize: '12px' }}>{x.artist}</span></span></span>
          <span class="ellip muted">{x.album}</span>
          <span class="mono muted" style={{ textAlign: 'right' }}>{meta ? meta(i) : fmtDur(x.duration)}</span>
        </button>
      ))}
    </div>
  );
}

function OpenList({ lib }: { lib: LibId }) {
  const pl = libUi.pl.value!;
  const [songs, setSongs] = useState<NdSong[] | null>(null), [err, setErr] = useState('');
  useEffect(() => { setSongs(null); setErr(''); collSongs(lib, pl.kind, pl.id).then(setSongs).catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e))); }, [pl.id]);
  const list = songs ?? [], total = list.reduce((a, x) => a + x.duration, 0);
  const play = (l: NdSong[], i: number) => { playNd(l, i, lib); go('play'); };
  return (
    <div class="col gap20">
      <div class="dkx-alhead">
        <div class="glow" style={{ background: ndBg(list[0]?.coverArt, pl.name, 400) }} />
        <div class="cv" style={{ background: ndBg(list[0]?.coverArt, pl.name, 400) }} />
        <div class="col" style={{ gap: '8px', minWidth: 0, position: 'relative' }}>
          <span class="kicker">{pl.kind === 'album' ? 'ALBUM' : 'SPILLELISTE'}</span>
          <h1>{pl.name}</h1>
          <span class="muted">{songs ? list.length + ' låter' + (total ? ' · ' + Math.round(total / 60) + ' min' : '') + (list[0] && pl.kind === 'album' ? ' · ' + list[0].artist : '') : err || 'Henter …'}</span>
          <div class="row gap10" style={{ marginTop: '6px' }}>
            <button class="btn primary" onClick={() => { if (list.length) play(list, 0); }}>Spill</button>
            <button class="btn" onClick={() => { if (list.length) play([...list].sort(() => Math.random() - 0.5), 0); }}>Tilfeldig</button>
            <button class="btn" onClick={() => { if (list.length) addToQueue(list, lib); }}>Legg i kø</button>
          </div>
        </div>
      </div>
      {list.length > 0 && <TrackTable list={list} onPick={(i) => play(list, i)} />}
    </div>
  );
}

export function DeskLibrary({ lib }: { lib: LibId }) {
  const nd = lib === 'nd' && ndConfigured(), ytm = lib === 'ytm';
  const ndData = useNdLib(nd && !!ndConf.value.url), ytmData = useYtmLib(ytm);
  const data = ytm ? ytmData : { ...ndData, retry: undefined };
  const tabs = TABS[lib];
  const tab = Math.min(libUi.tab.value, tabs.length - 1), open = libUi.pl.value, q = libUi.q.value.trim();
  const [res, setRes] = useState<NdSong[] | null>(null);
  useEffect(() => {
    if ((!nd && !ytm) || q.length < 2) { setRes(null); return undefined; }
    setRes(null);
    const t = setTimeout(() => { (ytm ? ytmSearch(q) : ndSearch(q)).then(setRes).catch(() => setRes([])); }, 350);
    return () => clearTimeout(t);
  }, [q, nd, ytm]);
  const off = ytm ? !!data.err && !data.newest.length && !data.pls.length : !ndConfigured() || (!!data.err && !data.newest.length);
  const play = (l: NdSong[], i: number) => { playNd(l, i, lib); go('play'); };
  const openAl = (al: NdAlbum) => { libUi.pl.value = { kind: al.playlist ? 'pl' : 'album', id: al.id, name: al.name }; };
  const alTile = (al: NdAlbum) => <Tile key={al.id} bg={ndBg(al.coverArt, al.name)} label={ndCover(al.coverArt) ? '' : al.name} name={al.name} meta={al.playlist ? 'Spilleliste' : al.artist + (al.year ? ' · ' + al.year : '')} onClick={() => openAl(al)} />;
  const plTile = (p: NdPlaylist | NdAlbum) => <Tile key={p.id} bg={ndBg(p.coverArt, p.name)} label={ndCover(p.coverArt) ? '' : p.name} name={p.name} meta={p.songCount ? p.songCount + ' låter' : 'artist' in p && p.artist && !p.playlist ? p.artist : 'Spilleliste'} onClick={() => { libUi.pl.value = { kind: 'playlist' in p && p.playlist === false ? 'album' : 'pl', id: p.id, name: p.name }; }} />;
  const h = hist.value[lib] ?? [];
  const f: NdAlbum | undefined = ytm ? ytmData.pls[0] ?? ytmData.newest[0] : ndData.newest[0];
  const fKind = f?.playlist ? 'pl' as const : 'album' as const;
  const tabName = tabs[tab] ?? '';
  return (
    <div class="dkx-lib">
      <div class="dkx-libbar">
        {open ? <button class="link0" onClick={() => { libUi.pl.value = null; }}>‹ Tilbake</button> : (
          <div class="dkx-tabs" role="tablist">{tabs.map((n, i) => <button key={n} role="tab" aria-selected={tab === i} class={tab === i ? 'on' : ''} onClick={() => { libUi.tab.value = i; libUi.pl.value = null; }}>{n}</button>)}</div>
        )}
        <div class="dkx-search sm"><Icon d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4" size={16} sw={1.8} /><input value={libUi.q.value} onInput={(e) => { libUi.q.value = e.currentTarget.value; }} placeholder={'Søk i ' + LIB_NAME[lib]} aria-label={'Søk i ' + LIB_NAME[lib]} />{q && <button class="x" onClick={() => { libUi.q.value = ''; }} aria-label="Tøm søket">×</button>}</div>
      </div>
      {off ? <NotConnected lib={lib} err={data.err} {...(data.retry ? { retry: data.retry } : {})} /> : q ? (
        <div class="col gap12">
          <SecHead title={'Treff for «' + q + '»'} kicker="LÅTER" />
          {!res && <span class="muted" style={{ fontSize: '13px' }}>Søker …</span>}
          {res && !res.length && <span class="muted" style={{ fontSize: '13px' }}>Ingen treff</span>}
          {res && res.length > 0 && <TrackTable list={res} onPick={(i) => play(res, i)} />}
        </div>
      ) : open ? <OpenList lib={lib} /> : tabName === 'Utforsk' ? (
        <div class="col gap24">
          {f ? (
            <div class="dkx-alhead hero">
              <div class="glow" style={{ background: ndBg(f.coverArt, f.name, 400) }} />
              <button class="cv" style={{ background: ndBg(f.coverArt, f.name, 400) }} onClick={() => openAl(f)} aria-label={'Åpne ' + f.name} />
              <div class="col" style={{ gap: '8px', minWidth: 0, position: 'relative' }}>
                <span class="kicker" style={{ color: 'var(--accent-2)' }}>{ytm ? 'UTVALGT' : 'NYLIG LAGT TIL'}</span>
                <h1>{f.name}</h1>
                <span class="muted">{[f.artist, f.year ? String(f.year) : '', f.songCount ? f.songCount + ' låter' : '', f.duration ? Math.round(f.duration / 60) + ' min' : ''].filter(Boolean).join(' · ')}</span>
                <div class="row gap10" style={{ marginTop: '6px' }}>
                  <button class="btn primary" onClick={() => { void collSongs(lib, fKind, f.id).then((r) => { if (r.length) play(r, 0); }); }}>Spill</button>
                  <button class="btn" onClick={() => { void collSongs(lib, fKind, f.id).then((r) => { if (r.length) addToQueue(r, lib); }); }}>Legg i kø</button>
                </div>
              </div>
            </div>
          ) : <span class="muted" style={{ fontSize: '13px' }}>{data.err || (data.done ? 'Biblioteket er tomt.' : 'Henter biblioteket …')}</span>}
          {ytm && data.rnd.length > 0 && <section class="col gap12"><SecHead title="Til deg" kicker="YOUTUBE MUSIC" /><div class="dkx-row">{data.rnd.map(alTile)}</div></section>}
          {ytm && ytmData.pls.some((p) => p.playlist) && <section class="col gap12"><SecHead title="Dine spillelister" /><div class="dkx-row">{ytmData.pls.filter((p) => p.playlist).map(plTile)}</div></section>}
          {ytm && data.newest.length > 0 && <section class="col gap12"><SecHead title="Album" /><div class="dkx-row">{data.newest.map(alTile)}</div></section>}
          {!ytm && data.newest.length > 1 && <section class="col gap12"><SecHead title="Nylig lagt til" more="Alle album ›" onMore={() => { libUi.tab.value = 1; }} /><div class="dkx-row">{data.newest.slice(1).map(alTile)}</div></section>}
          {!ytm && data.pls.length > 0 && <section class="col gap12"><SecHead title="Dine spillelister" /><div class="dkx-row">{data.pls.map(plTile)}</div></section>}
          {!ytm && data.rnd.length > 0 && <section class="col gap12"><SecHead title="Oppdag" kicker="TILFELDIGE ALBUM" /><div class="dkx-row">{data.rnd.map(alTile)}</div></section>}
          {data.freq.length > 0 && <section class="col gap12"><SecHead title="Mest spilt" kicker="FRA BIBLIOTEKET" /><div class="dkx-row">{data.freq.map(alTile)}</div></section>}
        </div>
      ) : tabName === 'Album' ? (
        <div class="dkx-grid">{(data.all.length ? data.all : data.newest).map(alTile)}</div>
      ) : tabName === 'Spillelister' ? (
        data.pls.length ? <div class="dkx-grid">{data.pls.map(plTile)}</div>
          : <span class="muted" style={{ fontSize: '13px' }}>Ingen spillelister på serveren.</span>
      ) : (
        <div class="col gap12">
          {!h.length && <span class="muted" style={{ fontSize: '13px' }}>Ingen historikk ennå.</span>}
          {h.length > 0 && <TrackTable list={h.map((x) => x.s)} meta={(i) => whenText(h[i]!.at)} onPick={(i) => play(h.map((x) => x.s), i)} />}
          {h.length > 0 && <button class="link0" style={{ alignSelf: 'flex-start' }} onClick={() => clearHist(lib)}>Tøm historikk</button>}
        </div>
      )}
    </div>
  );
}
