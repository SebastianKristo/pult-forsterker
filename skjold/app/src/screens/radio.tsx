// Radio: oppdagelsesside (hyller, sjangre, søk) og favorittlisten under Innstillinger → Radio (S1 Web v3 / App v2).
import { useEffect, useState } from 'preact/hooks';
import type { Fav, Station } from '../lib/api';
import { go, setSetting, settings, status } from '../lib/store';
import { art } from '../lib/settings';
import { addFav, browseState, currentStation, favMax, favOf, favs, favsLoaded, isFull, loadBrowse, loadFavs, moveFav, norm, playFav, playStation, removeFav, search, searchBusy, searchRes, shelves, testStream, toggleFav } from '../lib/radio';

const favToSt = (f: Fav): Station => ({ name: f.title, url: f.url, ...(f.genre ? { genre: f.genre } : {}), ...(f.image ? { image: f.image } : {}) });
const abbr = (n: string) => n.replace(/^NRK /, '').replace('Radio ', '').split(' ').map((w) => w.slice(0, 4)).join(' ').slice(0, 7);
const PLAY = 'M8 5v14l11-7z';
const genreLine = (s: Station) => [s.genre, s.country, s.bitrate ? s.bitrate + ' kbps' : ''].filter(Boolean).join(' · ') || 'Nettradio';

function useRadioData(): void {
  useEffect(() => { void loadFavs(); if (browseState.value === 'idle') void loadBrowse(); }, []);
}

function Row({ st, i, wide }: { st: Station; i: number; wide: boolean }) {
  const a = art(st.name, st.image), f = !!favOf(st.name, st.url);
  return (
    <div class="r-row" style={{ borderTopColor: i ? '#242426' : 'transparent' }}>
      <button class="ab" aria-label="Spill" style={{ background: a.bg, color: a.ink }} onClick={() => playStation(st)}>{a.logo ? '' : abbr(st.name).slice(0, 5)}</button>
      <button class="tx" onClick={() => playStation(st)}><span class="n">{st.name}</span><span class="g">{genreLine(st)}</span></button>
      <button class="star" aria-label="Favoritt" style={{ color: f ? '#f0c46a' : '#8b8b86' }} onClick={() => void toggleFav(st)}>{f ? '★' : '☆'}</button>
      {wide ? null : null}
    </div>
  );
}

export function RadioPage({ wide = false }: { wide?: boolean }) {
  useRadioData();
  const [q, setQ] = useState('');
  const [genre, setGenre] = useState<string | null>(null);
  const s = status.value;
  const cur = currentStation(s);
  const ql = norm(q);
  const goSet = () => go('settings', 'radio');
  const allSt: Station[] = [...favs.value.map(favToSt), ...shelves.value.flatMap((x) => x.items)];
  const findSt = (name: string) => allSt.find((x) => norm(x.name) === norm(name));
  const curSt: Station | null = cur ? (findSt(cur) ?? (s?.radio_now?.url ? { name: cur, url: s.radio_now.url, ...(s.radio_now.genre ? { genre: s.radio_now.genre } : {}), ...(s.radio_now.image ? { image: s.radio_now.image } : {}) } : { name: cur, url: '' })) : null;
  const hero = curSt ?? (favs.value[0] ? favToSt(favs.value[0]) : shelves.value[0]?.items[0] ?? null);
  const genres = shelves.value.filter((x) => x.id !== 'popular_no');
  const gSel = genre ? genres.find((g) => g.id === genre) : undefined;
  const tile = (st: Station) => ({ st, on: !!cur && norm(cur) === norm(st.name) });
  const rows = gSel ? [{ kicker: 'SJANGER', title: gSel.title, tiles: gSel.items.map(tile) }]
    : [{ kicker: favs.value.length + (favs.value.length === 1 ? ' KANAL' : ' KANALER'), title: 'Dine favoritter', tiles: favs.value.map((f) => tile(favToSt(f))) },
      ...shelves.value.filter((x) => x.id === 'popular_no').map((x) => ({ kicker: '', title: x.title, tiles: x.items.slice(0, 14).map(tile) })),
      ...genres.slice(0, 2).map((x) => ({ kicker: 'SJANGER', title: x.title, tiles: x.items.map(tile) }))];
  // Søk: lokale treff (favoritter + katalog) og daemonens søk
  const res = searchRes.value && norm(searchRes.value.q) === ql ? searchRes.value : null;
  const locMap = new Map<string, Station>();
  if (ql) { for (const x of allSt) if ((x.name + ' ' + (x.genre ?? '')).toLowerCase().includes(ql) && !locMap.has(norm(x.name))) locMap.set(norm(x.name), x); }
  for (const x of res?.norway ?? []) if (!locMap.has(norm(x.name))) locMap.set(norm(x.name), x);
  const loc = [...locMap.values()];
  const onl = (res?.world ?? []).filter((x) => !locMap.has(norm(x.name)));
  const heroFav = hero ? !!favOf(hero.name, hero.url) : false;
  const hl = !!hero && !!cur && norm(cur) === norm(hero.name);
  const ha = hero ? art(hero.name, hero.image) : null;
  const heroNow = hl && s?.radio_now?.now ? s.radio_now.now : hl && s?.title ? [s.title, s.artist].filter(Boolean).join(' · ') : '';
  return (
    <div class={'radio' + (wide ? ' wide' : '')}>
      <div class="r-top">
        <input class="r-q" value={q} placeholder="Søk etter kanal, by eller sjanger" onInput={(e) => { const v = e.currentTarget.value; setQ(v); search(v); }} />
        <button class="r-fav" onClick={goSet}><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M4 12h10M4 18h7M17 14l3 3-3 3" /></svg>{wide ? 'Administrer favoritter' : 'Favoritter'}</button>
      </div>
      {ql ? <>
        {loc.length > 0 && <><span class="kicker">NORSKE KANALER</span><div class="r-list">{loc.map((x, i) => <Row key={x.url + x.name} st={x} i={i} wide={wide} />)}</div></>}
        {searchBusy.value && <span class="lbl12">Søker i Radio Browser …</span>}
        {onl.length > 0 && <><span class="kicker">FRA HELE VERDEN · RADIO BROWSER</span><div class="r-list">{onl.map((x, i) => <Row key={x.url + x.name} st={x} i={i} wide={wide} />)}</div></>}
        {res?.offline && !searchBusy.value && <span class="lbl12">Radio Browser svarer ikke akkurat nå. Prøv igjen litt senere.</span>}
        {!searchBusy.value && !loc.length && !onl.length && ql.length >= 3 && !res?.offline && <span class="lbl13">Ingen kanaler funnet. Du kan legge til en strømadresse under Administrer favoritter.</span>}
      </> : <>
        {hero && ha && (
          <div class="r-hero">
            <div class="glow" style={{ background: ha.bg }} />
            <div class="shade" />
            <div class="in">
              <button class="cv" style={{ background: ha.bg }} aria-label="Spill" onClick={() => playStation(hero)} />
              <div class="col tx">
                <span class="kk"><i style={{ background: hl ? '#e05a4a' : '#3a3a37' }} />{hl ? 'SPILLER NÅ' : 'FRA FAVORITTENE'}</span>
                <span class="nm">{hero.name}</span>
                <span class="gn">{hero.genre || 'Radio'}</span>
                {heroNow && <span class="now">{heroNow}</span>}
              </div>
              <div class="btns">
                <button class="play" onClick={() => playStation(hero)}><svg width="12" height="12" viewBox="0 0 24 24" fill="#0b0b0c"><path d={PLAY} /></svg>{hl ? 'Spiller' : 'Spill'}</button>
                <button class="fv" style={{ color: heroFav ? '#f0c46a' : '#f2f2ee' }} onClick={() => void toggleFav(hero)}>{heroFav ? '★ I favorittene' : '☆ Legg til favoritter'}</button>
              </div>
            </div>
          </div>
        )}
        {genres.length > 0 && (
          <div class={'r-genres' + (wide ? '' : ' hscroll')}>
            {[{ id: null as string | null, title: 'Alle' }, ...genres.map((g) => ({ id: g.id as string | null, title: g.title }))].map((g) => (
              <button key={g.title} class={'r-g' + (genre === g.id ? ' on' : '')} onClick={() => setGenre(g.id)}>{g.title}</button>
            ))}
          </div>
        )}
        {rows.filter((r) => r.tiles.length).map((r) => (
          <div class="r-shelf" key={r.title}>
            <div class="col" style={{ gap: '2px' }}>{r.kicker && <span class="kicker">{r.kicker}</span>}<span class="tt">{r.title}</span></div>
            <div class="hscroll">
              {r.tiles.map(({ st, on }) => {
                const a = art(st.name, st.image);
                return (
                  <button key={st.url + st.name} class="r-tile" onClick={() => playStation(st)}>
                    <div class="sq" style={{ background: a.bg, color: a.ink }}>{on && <span class="live">DIREKTE</span>}</div>
                    <span class="n">{st.name}</span>
                    <span class="m">{st.genre || 'Radio'}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        {browseState.value === 'offline' && <span class="lbl12">Radio Browser svarer ikke akkurat nå, så bare favorittene vises.</span>}
        {favsLoaded.value && !favs.value.length && !shelves.value.length && <span class="lbl13">Ingen kanaler ennå. Søk etter en kanal over, eller legg til en strømadresse under Favoritter.</span>}
      </>}
    </div>
  );
}

// ---------- Innstillinger → Radio: favorittlisten ----------
export function RadioFavorites({ wide = false }: { wide?: boolean }) {
  useRadioData();
  const [edit, setEdit] = useState(false);
  const [adding, setAdding] = useState(false);
  const s = status.value;
  const cur = currentStation(s);
  const hold = settings.value.hold;
  const list = favs.value;
  const full = isFull.value;
  const count = list.length + (list.length === 1 ? ' favoritt' : ' favoritter');
  if (!wide && adding) return <AddChannel wide={false} onBack={() => setAdding(false)} />;
  const rows = list.map((f, i) => {
    const a = art(f.title, f.image), on = !!cur && norm(cur) === norm(f.title);
    return (
      <div key={f.n} class={'fav-row' + (wide ? ' wide' : '')} style={{ borderTopColor: i ? '#242426' : 'transparent', background: on ? '#1c170d' : 'transparent' }}>
        <div class="ab" style={{ background: a.bg, color: a.ink }}>{a.logo ? '' : abbr(f.title)}</div>
        <button class="tx" onClick={() => playFav(f)}><span class="n">{wide ? f.n + '. ' : ''}{f.title}</span><span class="g">{f.genre || 'Radio'}{wide && on ? ' · spiller' : ''}</span></button>
        {wide ? (
          <div class="row" style={{ gap: '4px' }}>
            <button class="sb" aria-label="Favoritt på radioknappen" style={{ color: hold === f.n - 1 ? '#f0c46a' : '#3a3a37', fontSize: '14px' }} onClick={() => setSetting('hold', f.n - 1)}>★</button>
            <MoveBtns i={i} n={list.length} f={f} size={32} />
          </div>
        ) : !edit ? (
          <div class="row" style={{ gap: '8px' }}>
            <span style={{ fontSize: '11px', color: '#f0c46a' }}>{on ? 'Spiller' : ''}</span>
            <button class="st" aria-label="Favoritt på radioknappen" style={{ color: hold === f.n - 1 ? '#f0c46a' : '#3a3a37' }} onClick={() => setSetting('hold', f.n - 1)}>★</button>
          </div>
        ) : <div class="row" style={{ gap: '4px' }}><MoveBtns i={i} n={list.length} f={f} size={30} /></div>}
      </div>
    );
  });
  if (wide) {
    return (
      <div class="favs-wide">
        <div class="col gap10">
          <div class="row between"><span style={{ fontSize: '13px', color: '#8b8b86' }}>{count}</span><span style={{ fontSize: '12px', color: '#8b8b86' }}>Samme rekkefølge som radioknappen</span></div>
          <section class="fav-list" style={{ borderRadius: '16px' }}>{rows}</section>
          <div class="row" style={{ gap: '12px', flexWrap: 'wrap', fontSize: '12px', color: '#8b8b86' }}><span>★ spilles når du holder radioknappen inne.</span></div>
        </div>
        <AddChannel wide />
      </div>
    );
  }
  return (
    <>
      <div class="row between"><span style={{ fontSize: '12px', color: '#8b8b86' }}>{count}</span><button class="link0" style={{ padding: '4px 0' }} onClick={() => setEdit(!edit)}>{edit ? 'Ferdig' : 'Endre rekkefølge'}</button></div>
      {list.length > 0 && <div class="fav-list">{rows}</div>}
      <button class={'dashed' + (full ? ' off' : '')} onClick={() => { if (!full) setAdding(true); }}>{full ? 'Maks ' + favMax.value + ' favoritter · fjern én for å legge til' : '+ Legg til kanal'}</button>
      <span style={{ fontSize: '11px', color: '#8b8b86', textWrap: 'pretty' }}>Rekkefølgen er den samme som på radioknappen. ★ spilles når du holder radioknappen inne.</span>
    </>
  );
}

function MoveBtns({ i, n, f, size }: { i: number; n: number; f: Fav; size: number }) {
  const st = { width: size + 'px', height: size + 'px' };
  return <>
    <button class="sb" style={{ ...st, color: i ? '#f2f2ee' : '#3a3a37' }} aria-label="Flytt opp" onClick={() => void moveFav(i, i - 1)}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 15l6-6 6 6" /></svg></button>
    <button class="sb" style={{ ...st, color: i < n - 1 ? '#f2f2ee' : '#3a3a37' }} aria-label="Flytt ned" onClick={() => void moveFav(i, i + 1)}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6" /></svg></button>
    <button class="sb red" style={st} aria-label="Fjern" onClick={() => { if (n > 1) void removeFav(f.n); }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
  </>;
}

function AddChannel({ wide, onBack }: { wide: boolean; onBack?: () => void }) {
  const [mode, setMode] = useState<'sok' | 'url'>('sok');
  const [q, setQ] = useState('');
  const [uName, setUName] = useState(''); const [uUrl, setUUrl] = useState(''); const [uGenre, setUGenre] = useState('');
  const [uTest, setUTest] = useState<null | 'busy' | 'ok' | 'bad'>(null);
  const [done, setDone] = useState('');
  const full = isFull.value;
  const has = (n: string, url?: string) => !!favOf(n, url);
  const ql = norm(q);
  const res = searchRes.value && norm(searchRes.value.q) === ql ? searchRes.value : null;
  const popular = shelves.value.find((x) => x.id === 'popular_no')?.items ?? [];
  const catalog = ql ? (res?.norway ?? popular.filter((x) => (x.name + ' ' + (x.genre ?? '')).toLowerCase().includes(ql))) : popular;
  const onl = (res?.world ?? []).filter((x) => !catalog.some((c) => norm(c.name) === norm(x.name)));
  const u = uUrl.trim(), okUrl = /^https?:\/\/\S+\.\S+/i.test(u), nm = uName.trim(), isPl = /\.(m3u8?|pls)(\?|$)/i.test(u);
  const msg: [string, string] = !u ? ['Støtter MP3, AAC, OGG, FLAC og spillelister (.m3u, .pls).', '#8b8b86'] : !okUrl ? ['Adressen må starte med http:// eller https://', '#ff8a7a'] : uTest === 'busy' ? ['Tester strømmen …', '#c9c9c4'] : uTest === 'ok' ? ['Strømmen virker.', '#6fcf7f'] : uTest === 'bad' ? (isPl ? ['Spilleliste. Lyrion henter strømmen fra den ved avspilling.', '#c9c9c4'] : ['Fikk ikke kontakt med strømmen. Sjekk adressen.', '#ff8a7a']) : ['Trykk Test for å sjekke at strømmen virker.', '#8b8b86'];
  const canAdd = okUrl && nm.length > 0 && !full && !has(nm, u);
  const addRow = (x: Station, i: number, big: boolean) => {
    const a = art(x.name, x.image), h = has(x.name, x.url);
    return (
      <div key={x.url + x.name} class={'add-row' + (big ? ' big' : '')} style={{ borderTopColor: i ? '#242426' : 'transparent' }}>
        <div class="ab" style={{ background: a.bg, color: a.ink }}>{a.logo ? '' : abbr(x.name)}</div>
        <span class="col" style={{ gap: '2px', minWidth: 0 }}><span class="n">{x.name}</span><span class="g">{genreLine(x)}</span></span>
        <button class="ad" style={{ borderColor: h || full ? '#2e2e30' : '#d9a441', color: h || full ? '#8b8b86' : '#f0c46a' }} onClick={() => { if (!h && !full) void addFav(x); }}>{h ? 'Lagt til' : full ? 'Fullt' : 'Legg til'}</button>
      </div>
    );
  };
  return (
    <div class="col" style={{ gap: wide ? '10px' : '16px' }}>
      {onBack && <button class="back" onClick={onBack}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg>Favoritter</button>}
      {wide && <span style={{ fontSize: '13px', color: '#8b8b86' }}>Legg til kanal</span>}
      <div class="seg">{([['sok', 'Søk'], ['url', 'Fra URL']] as const).map(([k, n]) => <button key={k} class={mode === k ? 'on' : ''} onClick={() => setMode(k)}>{n}</button>)}</div>
      {mode === 'sok' ? <>
        <input class="r-q" value={q} placeholder="Søk etter kanal, by eller sjanger" onInput={(e) => { const v = e.currentTarget.value; setQ(v); search(v); }} />
        {catalog.length > 0 && <><span class="kicker">NORSKE KANALER</span><section class={'add-list' + (wide ? ' scroll' : '')}>{catalog.map((x, i) => addRow(x, i, wide))}</section></>}
        {searchBusy.value && <span class="lbl12">Søker i Radio Browser …</span>}
        {onl.length > 0 && <><span class="kicker">FRA RADIO BROWSER</span><section class="add-list">{onl.map((x, i) => addRow(x, i, false))}</section></>}
        {(res?.offline || browseState.value === 'offline') && !searchBusy.value && <span class="lbl12">Radio Browser svarer ikke akkurat nå. Du kan fortsatt legge til en strømadresse under «Fra URL».</span>}
        {ql.length < 3 && <span class="lbl12" style={{ lineHeight: 1.45, textWrap: 'pretty' }}>Skriv minst tre bokstaver for å søke blant over 50 000 kanaler fra hele verden.</span>}
      </> : (
        <div class="col" style={{ gap: '10px' }}>
          <input class="r-q" value={uName} placeholder="Navn, for eksempel Jazzradio" onInput={(e) => { setUName(e.currentTarget.value.slice(0, 40)); setDone(''); }} />
          <input class="r-q mono" style={{ fontSize: '13px' }} value={uUrl} placeholder="https://… strømadresse" autoCapitalize="off" autoCorrect="off" spellcheck={false} inputMode="url" onInput={(e) => { setUUrl(e.currentTarget.value); setUTest(null); setDone(''); }} />
          <input class="r-q" value={uGenre} placeholder="Sjanger (valgfritt)" onInput={(e) => setUGenre(e.currentTarget.value.slice(0, 30))} />
          <span style={{ fontSize: '12px', color: msg[1], lineHeight: 1.45, textWrap: 'pretty' }}>{msg[0]}</span>
          <div class="row" style={{ gap: '8px' }}>
            <button class="u-test" onClick={() => { if (!okUrl) return; setUTest('busy'); void testStream(u).then((ok) => setUTest(ok ? 'ok' : 'bad')); }}>Test</button>
            <button class="u-add" style={{ background: canAdd ? '#d9a441' : '#242426', color: canAdd ? '#0b0b0c' : '#8b8b86' }} onClick={async () => {
              if (!canAdd) return;
              if (await addFav({ name: nm, url: u, genre: uGenre.trim() || 'Egen strøm' })) { setDone(nm); setUName(''); setUUrl(''); setUGenre(''); setUTest(null); }
            }}>{full ? 'Fullt · fjern en favoritt først' : nm && has(nm, u) ? 'Finnes allerede' : 'Legg til i favoritter'}</button>
          </div>
          {done && <span style={{ fontSize: '12px', color: '#6fcf7f' }}>«{done}» er lagt til i favorittene.</span>}
        </div>
      )}
    </div>
  );
}
