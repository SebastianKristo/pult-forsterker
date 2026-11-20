// Lyrion-fjernkontroll: alle spillere på Lyrion-serveren (Squeezebox Classic/Touch/Radio/Boom, piCorePlayer,
// squeezelite, Skjold Røst og Skjold-enhetene). Spiller nå, kø, favoritter, radio, apper (Lyrion-plugins som TIDAL,
// Spotty og Qobuz), biblioteket, søk og synkgrupper. Brukes som side i appen (route 'lms') og som egen modus uten
// Skjold-enhet (mode 'lyrion', serveradressen skrives inn).
import { useEffect, useRef, useState } from 'preact/hooks';
import { lms, lmsBilde, lmsDirekte, lmsSpiller, ko, settLmsDirekte, spillere, status as lmsStatus, syncGrupper, velgSpiller, type LmsSpiller, type LmsSpor, type LmsStatus } from '../lib/lms';
import { isNative } from '../lib/api';
import { go, mode, status as skjoldStatus } from '../lib/store';

const G = '#f0c46a', D = '#8b8b86', K = '#2a2a2c';
const st = {
  kort: `background:#141415;border:1px solid ${K};border-radius:18px`,
  knapp: `height:38px;padding:0 14px;border-radius:19px;border:1px solid ${K};background:#1b1b1c;color:#f2f2ee;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`,
  ikonK: 'width:44px;height:44px;border-radius:22px;border:none;background:none;color:#f2f2ee;display:flex;align-items:center;justify-content:center;cursor:pointer',
  liten: `font-size:12px;color:${D};line-height:1.4`
};
const IK = {
  play: 'M8 5v14l11-7z', pause: 'M7 5h4v14H7zM13 5h4v14h-4z', neste: 'M6 5l9 7-9 7zM17 5h2v14h-2z', forrige: 'M18 5l-9 7 9 7zM5 5h2v14H5z',
  strom: 'M12 3v9M6.3 7.3a8 8 0 1 0 11.4 0', bland: 'M4 7h3l10 10h3M4 17h3l3-3M14 10l3-3h3M17 4l3 3-3 3M17 14l3 3-3 3', gjenta: 'M4 12V9a3 3 0 0 1 3-3h12l-3-3M20 12v3a3 3 0 0 1-3 3H5l3 3',
  pluss: 'M12 5v14M5 12h14', tilbake: 'M15 5l-7 7 7 7', grupper: 'M4 6h7v5H4zM13 6h7v5h-7zM4 14h16v4H4z', sok: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4', vol: 'M4 9h4l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6'
} as const;
const Ik = ({ d, s = 22, f = false }: { d: string; s?: number; f?: boolean }) => <svg width={s} height={s} viewBox="0 0 24 24" fill={f ? 'currentColor' : 'none'} stroke="currentColor" stroke-width={f ? 0 : 1.8} stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg>;
const tid = (s?: number) => { const x = Math.max(0, Math.floor(s || 0)); return Math.floor(x / 60) + ':' + String(x % 60).padStart(2, '0'); };
const feiltekst = (e: unknown) => (e instanceof Error ? e.message : String(e));

interface Rad { key: string; navn: string; under?: string; bilde?: string; spill?: () => Promise<unknown>; legg?: () => Promise<unknown>; apne?: Niva; sok?: (term: string) => Niva }
interface Niva { tittel: string; hent: () => Promise<Rad[]> }
type Element = { id?: string | number; name?: string; isaudio?: number; hasitems?: number; image?: string; icon?: string; type?: string; url?: string };

/** Lyrions menyer (favoritter, radio, apper): «<cmd> items …» – samme mønster for alle plugins. */
function meny(spiller: string, cmd: string, tittel: string, itemId?: string, sokeord?: string): Niva {
  return {
    tittel,
    hent: async () => {
      const r = await lms<{ loop_loop?: Element[] }>(spiller, [cmd, 'items', 0, 300, 'want_url:1', ...(itemId ? ['item_id:' + itemId] : []), ...(sokeord ? ['search:' + sokeord] : [])]);
      return (r.loop_loop || []).map((x, i) => {
        const id = String(x.id ?? i), navn = x.name || '–';
        const rad: Rad = { key: id, navn, bilde: lmsBilde(x, 120) };
        if (x.type === 'search') rad.sok = (t) => meny(spiller, cmd, navn + ': ' + t, id, t);
        else if (x.hasitems) rad.apne = meny(spiller, cmd, navn, id);
        if (x.isaudio) { rad.spill = () => lms(spiller, [cmd, 'playlist', 'play', 'item_id:' + id]); rad.legg = () => lms(spiller, [cmd, 'playlist', 'add', 'item_id:' + id]); }
        return rad;
      });
    }
  };
}
function lister(spiller: string, cmd: string, tittel: string, loop: string): Niva {
  return { tittel, hent: async () => ((await lms<Record<string, { cmd: string; name: string; icon?: string }[]>>(spiller, [cmd, 0, 100]))[loop] || []).map((x) => ({ key: x.cmd, navn: x.name, bilde: lmsBilde({ icon: x.icon }, 120), apne: meny(spiller, x.cmd, x.name) })) };
}
const sporRad = (spiller: string, t: { id?: string | number; title?: string; artist?: string; album?: string; duration?: number; coverid?: string | number; tracknum?: number }, i: number, medBilde = true): Rad => ({
  key: String(t.id ?? i), navn: (t.tracknum ? t.tracknum + '. ' : '') + (t.title || '–'), under: [t.artist, t.album, t.duration ? tid(t.duration) : ''].filter(Boolean).join(' · '),
  bilde: medBilde ? lmsBilde({ coverid: t.coverid }, 120) : undefined,
  spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'track_id:' + t.id]), legg: () => lms(spiller, ['playlistcontrol', 'cmd:add', 'track_id:' + t.id])
});
const albumNiva = (spiller: string, id: string | number, navn: string): Niva => ({
  tittel: navn, hent: async () => {
    const r = await lms<{ titles_loop?: any[] }>('', ['titles', 0, 500, 'album_id:' + id, 'tags:dtac', 'sort:tracknum']);
    const alt: Rad = { key: 'alt', navn: 'Spill hele albumet', spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'album_id:' + id]), legg: () => lms(spiller, ['playlistcontrol', 'cmd:add', 'album_id:' + id]) };
    return [alt, ...(r.titles_loop || []).map((t, i) => sporRad(spiller, t, i, false))];
  }
});
const albumRad = (spiller: string, a: { id: string | number; album: string; artist?: string; artwork_track_id?: string | number; year?: number }): Rad => ({
  key: 'a' + a.id, navn: a.album, under: [a.artist, a.year || ''].filter(Boolean).join(' · '), bilde: lmsBilde({ artwork_track_id: a.artwork_track_id }, 120),
  apne: albumNiva(spiller, a.id, a.album), spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'album_id:' + a.id]), legg: () => lms(spiller, ['playlistcontrol', 'cmd:add', 'album_id:' + a.id])
});
const albumListe = (spiller: string, tittel: string, filter: string[]): Niva => ({ tittel, hent: async () => ((await lms<{ albums_loop?: any[] }>('', ['albums', 0, 500, 'tags:alyj', ...filter])).albums_loop || []).map((a) => albumRad(spiller, a)) });
function bibliotek(spiller: string): Rad[] {
  return [
    { key: 'art', navn: 'Artister', apne: { tittel: 'Artister', hent: async () => ((await lms<{ artists_loop?: { id: number; artist: string }[] }>('', ['artists', 0, 2000])).artists_loop || []).map((a) => ({ key: 'r' + a.id, navn: a.artist, apne: albumListe(spiller, a.artist, ['artist_id:' + a.id]), spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'artist_id:' + a.id]) })) } },
    { key: 'alb', navn: 'Album', apne: albumListe(spiller, 'Album', ['sort:album']) },
    { key: 'ny', navn: 'Nye album', apne: albumListe(spiller, 'Nye album', ['sort:new']) },
    { key: 'pl', navn: 'Spillelister', apne: { tittel: 'Spillelister', hent: async () => ((await lms<{ playlists_loop?: { id: number; playlist: string }[] }>('', ['playlists', 0, 500])).playlists_loop || []).map((p) => ({
      key: 'p' + p.id, navn: p.playlist, spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'playlist_id:' + p.id]), legg: () => lms(spiller, ['playlistcontrol', 'cmd:add', 'playlist_id:' + p.id]),
      apne: { tittel: p.playlist, hent: async () => ((await lms<{ playlisttracks_loop?: any[] }>('', ['playlists', 'tracks', 0, 500, 'playlist_id:' + p.id, 'tags:dac'])).playlisttracks_loop || []).map((t, i) => sporRad(spiller, t, i)) }
    })) } },
    { key: 'sjanger', navn: 'Sjangre', apne: { tittel: 'Sjangre', hent: async () => ((await lms<{ genres_loop?: { id: number; genre: string }[] }>('', ['genres', 0, 500])).genres_loop || []).map((g) => ({ key: 'g' + g.id, navn: g.genre, apne: albumListe(spiller, g.genre, ['genre_id:' + g.id]), spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'genre_id:' + g.id]) })) } },
    { key: 'tilf', navn: 'Tilfeldig miks', under: 'Låter fra hele biblioteket', spill: () => lms(spiller, ['randomplay', 'tracks']) }
  ];
}
async function sok(spiller: string, term: string): Promise<Rad[]> {
  const r = await lms<{ contributors_loop?: { contributor: string; contributor_id: number }[]; albums_loop?: { album: string; album_id: number }[]; tracks_loop?: { track: string; track_id: number }[] }>('', ['search', 0, 25, 'term:' + term]);
  return [
    ...(r.contributors_loop || []).map((a) => ({ key: 'c' + a.contributor_id, navn: a.contributor, under: 'Artist', apne: albumListe(spiller, a.contributor, ['artist_id:' + a.contributor_id]), spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'artist_id:' + a.contributor_id]) })),
    ...(r.albums_loop || []).map((a) => ({ key: 'a' + a.album_id, navn: a.album, under: 'Album', apne: albumNiva(spiller, a.album_id, a.album), spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'album_id:' + a.album_id]), legg: () => lms(spiller, ['playlistcontrol', 'cmd:add', 'album_id:' + a.album_id]) })),
    ...(r.tracks_loop || []).map((t) => ({ key: 't' + t.track_id, navn: t.track, under: 'Låt', spill: () => lms(spiller, ['playlistcontrol', 'cmd:load', 'track_id:' + t.track_id]), legg: () => lms(spiller, ['playlistcontrol', 'cmd:add', 'track_id:' + t.track_id]) }))
  ];
}

function Liste({ rader, apne, melding }: { rader: Rad[]; apne: (n: Niva) => void; melding: (t: string) => void }) {
  const kjor = async (f: () => Promise<unknown>, t: string) => { try { await f(); melding(t); } catch (e) { melding(feiltekst(e)); } };
  return <div style="display:flex;flex-direction:column">{rader.map((r) => (
    <div key={r.key} style={`display:flex;align-items:center;gap:12px;padding:8px 4px;border-bottom:1px solid #1d1d1f;cursor:${r.apne || r.sok || r.spill ? 'pointer' : 'default'}`}
      onClick={() => { if (r.sok) { const t = prompt('Søk i ' + r.navn); if (t) apne(r.sok(t)); } else if (r.apne) apne(r.apne); else if (r.spill) void kjor(r.spill, 'Spiller ' + r.navn); }}>
      {r.bilde !== undefined && <span style="width:44px;height:44px;border-radius:8px;flex-shrink:0;background:#1b1b1c;overflow:hidden">{r.bilde && <img src={r.bilde} alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />}</span>}
      <span style="flex:1;min-width:0;display:flex;flex-direction:column"><span style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r.navn}</span>{r.under && <span style={st.liten + ';white-space:nowrap;overflow:hidden;text-overflow:ellipsis'}>{r.under}</span>}</span>
      {r.legg && <button title="Legg i køen" aria-label="Legg i køen" onClick={(e) => { e.stopPropagation(); void kjor(r.legg!, 'Lagt i køen'); }} style={st.ikonK + ';width:36px;height:36px;color:' + D}><Ik d={IK.pluss} s={18} /></button>}
      {r.spill && (r.apne || r.sok) && <button title="Spill" aria-label="Spill" onClick={(e) => { e.stopPropagation(); void kjor(r.spill!, 'Spiller ' + r.navn); }} style={st.ikonK + ';width:36px;height:36px;color:' + G}><Ik d={IK.play} s={18} f /></button>}
      {(r.apne || r.sok) && <span style={`color:${D}`}>›</span>}
    </div>))}
    {!rader.length && <span style={st.liten + ';padding:14px 4px'}>Tomt.</span>}
  </div>;
}

/** Oppsett uten Skjold-enhet: skriv adressen til Lyrion-serveren. */
function Oppsett({ ferdig }: { ferdig: () => void }) {
  const [adr, setAdr] = useState(lmsDirekte.value.replace(/^https?:\/\//, '')), [feil, setFeil] = useState(''), [opptatt, setOpptatt] = useState(false);
  const prov = async () => {
    setOpptatt(true); setFeil('');
    try {
      const n = adr.trim(); const base = /^https?:/.test(n) ? n : 'http://' + n + (/:\d+$/.test(n) ? '' : ':9000');
      const r = await spillere(base);
      settLmsDirekte(adr); if (!r.spillere.some((p) => p.playerid === lmsSpiller.value) && r.spillere[0]) velgSpiller(r.spillere[0].playerid);
      ferdig();
    } catch (e) { setFeil('Fikk ikke kontakt: ' + feiltekst(e) + (isNative ? '' : '. I nettleseren må Lyrion tillate tilgang fra andre sider – bruk heller Skjold-appen eller en Skjold-enhet.')); }
    setOpptatt(false);
  };
  return (
    <div style={st.kort + ';padding:22px;display:flex;flex-direction:column;gap:12px;max-width:460px'}>
      <b style="font-size:17px">Koble til Lyrion</b>
      <span style={st.liten}>Skriv adressen til Lyrion Music Server (tidligere Logitech Media Server). Du finner den i Lyrion under Innstillinger → Informasjon, eller på ruteren. Porten er vanligvis 9000.</span>
      <input value={adr} onInput={(e) => setAdr(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter') void prov(); }} inputMode="url" autoCapitalize="off" spellcheck={false} placeholder="192.168.1.10:9000"
        style={`height:46px;border-radius:12px;border:1px solid ${K};background:#101011;color:#f2f2ee;padding:0 14px;font-size:15px`} />
      {feil && <span style="font-size:12.5px;color:#ff9a8a">{feil}</span>}
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button disabled={!adr.trim() || opptatt} onClick={() => void prov()} style={st.knapp + `;background:${G};color:#0b0b0c;border:none`}>{opptatt ? 'Kobler til …' : 'Koble til'}</button>
        {lmsDirekte.value && skjoldStatus.value?.lyrion && <button onClick={() => { settLmsDirekte(''); ferdig(); }} style={st.knapp}>Bruk Skjold-enheten</button>}
      </div>
    </div>);
}

export function LyrionPage({ frittstaende = false }: { frittstaende?: boolean }) {
  const viaSkjold = !lmsDirekte.value && !!skjoldStatus.value;
  const [oppsett, setOppsett] = useState(!lmsDirekte.value && (frittstaende || !skjoldStatus.value));
  const [liste, setListe] = useState<LmsSpiller[]>([]), [versjon, setVersjon] = useState(''), [feil, setFeil] = useState('');
  const [s, setS] = useState<LmsStatus | null>(null), [fane, setFane] = useState<'ko' | 'fav' | 'radio' | 'apper' | 'bib' | 'sok'>('fav');
  const [stabel, setStabel] = useState<Niva[]>([]), [rader, setRader] = useState<Rad[] | null>(null), [kø, setKø] = useState<LmsSpor[]>([]);
  const [msg, setMsg] = useState(''), [grupper, setGrupper] = useState<string[][]>([]), [gruppeArk, setGruppeArk] = useState(false), [sokeord, setSokeord] = useState('');
  const vol = useRef<number | null>(null), msgT = useRef(0);
  const sp = lmsSpiller.value;
  const melding = (t: string) => { setMsg(t); clearTimeout(msgT.current); msgT.current = window.setTimeout(() => setMsg(''), 2500); };

  // spillerne og synkgruppene (hvert 6. sekund)
  useEffect(() => {
    if (oppsett) return;
    let slutt = false, id = 0;
    const hent = async () => {
      try {
        const [r, g] = await Promise.all([spillere(), syncGrupper().catch(() => [])]);
        if (slutt) return;
        setListe(r.spillere); setVersjon(r.versjon); setGrupper(g); setFeil('');
        if (r.spillere.length && !r.spillere.some((p) => p.playerid === lmsSpiller.value)) {
          const egen = skjoldStatus.value as unknown as { lyrion_player?: string } | null;
          velgSpiller((r.spillere.find((p) => p.playerid === egen?.lyrion_player) || r.spillere.find((p) => p.isplaying) || r.spillere[0]!).playerid);
        }
      } catch (e) { if (!slutt) setFeil(feiltekst(e)); }
      if (!slutt) id = window.setTimeout(() => void hent(), document.hidden ? 20000 : 6000);
    };
    void hent(); return () => { slutt = true; clearTimeout(id); };
  }, [oppsett, lmsDirekte.value]);
  // valgt spiller (hvert 2. sekund)
  const oppdater = async () => { if (!sp) return; try { const x = await lmsStatus(sp); setS(x); if (vol.current !== null && x['mixer volume'] === vol.current) vol.current = null; } catch { /* neste runde */ } };
  useEffect(() => {
    if (oppsett || !sp) return;
    setS(null); let slutt = false, id = 0;
    const l = async () => { await oppdater(); if (!slutt) id = window.setTimeout(() => void l(), document.hidden ? 15000 : 2000); };
    void l(); return () => { slutt = true; clearTimeout(id); };
  }, [sp, oppsett]);
  // lister
  const rot = (f: typeof fane): Niva | null => f === 'fav' ? meny(sp, 'favorites', 'Favoritter') : f === 'radio' ? lister(sp, 'radios', 'Radio', 'radioss_loop') : f === 'apper' ? lister(sp, 'apps', 'Apper', 'appss_loop') : f === 'bib' ? { tittel: 'Bibliotek', hent: async () => bibliotek(sp) } : null;
  useEffect(() => {
    if (oppsett || !sp) return;
    if (fane === 'ko') { void ko(sp).then((x) => setKø(x.playlist_loop || [])).catch(() => setKø([])); return; }
    if (fane === 'sok') { setStabel([]); setRader(null); return; }
    const r = rot(fane); setStabel(r ? [r] : []);
  }, [fane, sp, oppsett]);
  useEffect(() => {
    const n = stabel[stabel.length - 1]; if (!n) return;
    setRader(null); let slutt = false;
    n.hent().then((r) => { if (!slutt) setRader(r); }).catch((e) => { if (!slutt) { setRader([]); melding(feiltekst(e)); } });
    return () => { slutt = true; };
  }, [stabel]);
  useEffect(() => { if (fane === 'ko' && s) void ko(sp).then((x) => setKø(x.playlist_loop || [])).catch(() => undefined); }, [s?.playlist_cur_index, s?.playlist_tracks]);

  const cmd = async (c: (string | number)[], spiller = sp) => { try { await lms(spiller, c); await oppdater(); } catch (e) { melding(feiltekst(e)); } };

  if (oppsett) return (
    <div style="display:flex;flex-direction:column;gap:16px;padding:16px">
      {frittstaende && <Topp />}
      <Oppsett ferdig={() => setOppsett(false)} />
    </div>);

  const t = s?.playlist_loop?.[0], spiller = liste.find((p) => p.playerid === sp);
  const tittel = t?.title || s?.current_title || (s?.mode === 'stop' ? 'Ingenting spiller' : '');
  const under = [t?.artist, t?.album].filter(Boolean).join(' · ') || (t?.remote && s?.current_title !== t?.title ? s?.current_title : '');
  const spiller_ = s?.mode === 'play';
  const minGruppe = grupper.find((g) => g.includes(sp)) || [sp];
  const v = vol.current ?? s?.['mixer volume'] ?? 0;
  const naa = rader === null && stabel.length > 0;

  return (
    <div style="display:flex;flex-direction:column;gap:14px;padding:14px 16px 90px;max-width:1100px;margin:0 auto;width:100%">
      <style>{'@media (max-width:560px){.lms-np{grid-template-columns:1fr!important;justify-items:stretch}.lms-np>span:first-child{width:min(240px,70vw)!important;height:min(240px,70vw)!important;justify-self:center}}'}</style>
      {frittstaende && <Topp onInnst={() => setOppsett(true)} />}
      {feil && <div style={st.kort + ';padding:12px 14px;border-color:#3a2a20;color:#ff9a8a;font-size:13px'}>Lyrion: {feil}{viaSkjold ? ' (via Skjold-enheten)' : ''} <button onClick={() => setOppsett(true)} style={st.knapp + ';height:30px;margin-left:8px'}>Endre server</button></div>}
      {/* spillervelger */}
      <div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:2px" role="tablist" aria-label="Spillere">
        {liste.map((p) => {
          const pa = p.playerid === sp, g = grupper.find((x) => x.includes(p.playerid));
          return <button key={p.playerid} role="tab" aria-selected={pa} onClick={() => velgSpiller(p.playerid)} style={`flex-shrink:0;display:flex;align-items:center;gap:8px;height:40px;padding:0 14px;border-radius:20px;cursor:pointer;font-size:13.5px;border:1px solid ${pa ? '#5a4420' : K};background:${pa ? '#1c170d' : '#141415'};color:${pa ? G : p.connected === 0 ? '#5d5d59' : '#f2f2ee'}`}>
            <ModellIkon p={p} s={18} /><i style={`width:7px;height:7px;border-radius:4px;background:${p.isplaying ? '#6fcf7f' : p.power ? '#5d5d59' : 'transparent'};border:1px solid ${p.power ? 'transparent' : '#5d5d59'}`} />{p.name}{g && g.length > 1 ? <span style={`font-size:10px;color:${D}`}>+{g.length - 1}</span> : null}</button>;
        })}
        {!liste.length && !feil && <span style={st.liten}>Henter spillere …</span>}
      </div>
      {spiller && (
        <div style={st.kort + ';padding:16px;display:grid;grid-template-columns:auto minmax(0,1fr);gap:18px;align-items:center'} class="lms-np">
          <span style="width:132px;height:132px;border-radius:14px;background:#1b1b1c;overflow:hidden;display:flex;align-items:center;justify-content:center;color:#3a3a3c">
            {t ? <img src={lmsBilde(t, 300)} alt="" style="width:100%;height:100%;object-fit:cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.visibility = 'hidden'; }} /> : <Ik d={IK.play} s={40} />}
          </span>
          <div style="display:flex;flex-direction:column;gap:6px;min-width:0">
            <span style={`font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;color:${G}`}>{(spiller.modelname || spiller.model || 'SPILLER').toUpperCase()} · {spiller.name.toUpperCase()}</span>
            <b style="font-size:18px;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{s?.power === 0 ? 'Av' : tittel || '–'}</b>
            {under && <span style="font-size:13px;color:#b9b9b4;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{under}</span>}
            {!!s?.duration && <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#8b8b86;font-variant-numeric:tabular-nums">{tid(s.time)}
              <input type="range" min="0" max={Math.round(s.duration)} value={Math.round(s.time || 0)} onChange={(e) => void cmd(['time', Number(e.currentTarget.value)])} aria-label="Spol" style={`flex:1;accent-color:${G}`} />{tid(s.duration)}</div>}
            <div style="display:flex;align-items:center;gap:2px;flex-wrap:wrap">
              <button aria-label="Forrige" onClick={() => void cmd(['playlist', 'index', '-1'])} style={st.ikonK}><Ik d={IK.forrige} f /></button>
              <button aria-label={spiller_ ? 'Pause' : 'Spill'} onClick={() => void cmd(s?.mode === 'stop' ? ['play'] : ['pause', spiller_ ? 1 : 0])} style={st.ikonK + `;background:${G};color:#0b0b0c;width:50px;height:50px;border-radius:25px`}><Ik d={spiller_ ? IK.pause : IK.play} f /></button>
              <button aria-label="Neste" onClick={() => void cmd(['playlist', 'index', '+1'])} style={st.ikonK}><Ik d={IK.neste} f /></button>
              <button aria-label="Bland" title={['Bland: av', 'Bland låter', 'Bland album'][s?.['playlist shuffle'] ?? 0]} onClick={() => void cmd(['playlist', 'shuffle'])} style={st.ikonK + `;color:${s?.['playlist shuffle'] ? G : D}`}><Ik d={IK.bland} s={19} /></button>
              <button aria-label="Gjenta" title={['Gjenta: av', 'Gjenta låten', 'Gjenta køen'][s?.['playlist repeat'] ?? 0]} onClick={() => void cmd(['playlist', 'repeat'])} style={st.ikonK + `;color:${s?.['playlist repeat'] ? G : D};position:relative`}><Ik d={IK.gjenta} s={19} />{s?.['playlist repeat'] === 1 && <span style="position:absolute;font-size:8px;font-weight:700;bottom:9px;right:9px">1</span>}</button>
              <button aria-label="Grupper" title="Spill i flere rom" onClick={() => setGruppeArk(true)} style={st.ikonK + `;color:${minGruppe.length > 1 ? G : D}`}><Ik d={IK.grupper} s={19} /></button>
              <button aria-label={s?.power ? 'Slå av' : 'Slå på'} onClick={() => void cmd(['power', s?.power ? 0 : 1])} style={st.ikonK + `;color:${s?.power ? '#6fcf7f' : D}`}><Ik d={IK.strom} s={19} /></button>
            </div>
            <div style="display:flex;align-items:center;gap:10px;color:#8b8b86"><Ik d={IK.vol} s={18} />
              <input type="range" min="0" max="100" value={Math.abs(v)} onInput={(e) => { vol.current = Number(e.currentTarget.value); setS((x) => x && { ...x, 'mixer volume': vol.current! }); void lms(sp, ['mixer', 'volume', vol.current]); }} aria-label="Volum" style={`flex:1;max-width:320px;accent-color:${G}`} />
              <span style="font-size:12px;width:28px;font-variant-numeric:tabular-nums">{Math.abs(v)}</span></div>
          </div>
        </div>)}
      {/* faner */}
      <div style="display:flex;gap:6px;overflow-x:auto">
        {([['fav', 'Favoritter'], ['ko', 'Kø'], ['radio', 'Radio'], ['apper', 'Apper'], ['bib', 'Bibliotek'], ['sok', 'Søk']] as const).map(([id, n]) =>
          <button key={id} onClick={() => setFane(id)} style={st.knapp + (fane === id ? `;background:#1c170d;border-color:#5a4420;color:${G}` : '')}>{n}</button>)}
      </div>
      <div style={st.kort + ';padding:8px 14px 12px'}>
        {fane === 'ko' ? <>
          <div style="display:flex;align-items:center;gap:8px;padding:8px 4px"><b style="flex:1">Kø · {kø.length} låter</b>{kø.length > 0 && <button onClick={() => { if (confirm('Tømme køen?')) void cmd(['playlist', 'clear']).then(() => setKø([])); }} style={st.knapp + ';height:32px'}>Tøm</button>}</div>
          {kø.map((x, i) => { const pa = Number(s?.playlist_cur_index) === i; return (
            <div key={i} onClick={() => void cmd(['playlist', 'index', i])} style={`display:flex;align-items:center;gap:12px;padding:8px 4px;border-bottom:1px solid #1d1d1f;cursor:pointer;${pa ? 'color:' + G : ''}`}>
              <span style="width:22px;font-size:11px;color:#5d5d59;text-align:right;font-variant-numeric:tabular-nums">{pa ? '▶' : i + 1}</span>
              <span style="flex:1;min-width:0;display:flex;flex-direction:column"><span style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.title}</span><span style={st.liten}>{[x.artist, x.album].filter(Boolean).join(' · ')}</span></span>
              <span style={st.liten}>{x.duration ? tid(x.duration) : ''}</span>
              <button aria-label="Fjern fra køen" onClick={(e) => { e.stopPropagation(); void cmd(['playlist', 'delete', i]).then(() => setKø(kø.filter((_, j) => j !== i))); }} style={st.ikonK + ';width:32px;height:32px;color:' + D}>×</button>
            </div>); })}
          {!kø.length && <span style={st.liten + ';padding:10px 4px;display:block'}>Køen er tom. Velg noe fra Favoritter, Radio eller Bibliotek.</span>}
        </> : <>
          {fane === 'sok' && <form onSubmit={(e) => { e.preventDefault(); const term = sokeord.trim(); if (term) setStabel([{ tittel: 'Søk: ' + term, hent: () => sok(sp, term) }]); }} style="display:flex;gap:8px;padding:8px 0">
            <input value={sokeord} onInput={(e) => setSokeord(e.currentTarget.value)} placeholder="Artist, album eller låt i Lyrion-biblioteket" style={`flex:1;height:40px;border-radius:12px;border:1px solid ${K};background:#101011;color:#f2f2ee;padding:0 12px;font-size:14px`} />
            <button style={st.knapp}><Ik d={IK.sok} s={16} /></button></form>}
          {stabel.length > 1 && <button onClick={() => setStabel(stabel.slice(0, -1))} style="display:flex;align-items:center;gap:6px;border:none;background:none;color:#f2f2ee;cursor:pointer;padding:10px 0;font-size:15px;font-weight:600"><Ik d={IK.tilbake} s={18} />{stabel[stabel.length - 1]!.tittel}</button>}
          {naa ? <span style={st.liten + ';padding:14px 4px;display:block'}>Henter …</span> : rader && <Liste rader={rader} apne={(n) => setStabel([...stabel, n])} melding={melding} />}
        </>}
      </div>
      <span style={st.liten + ';text-align:center'}>Lyrion {versjon} · {lmsDirekte.value ? lmsDirekte.value.replace(/^https?:\/\//, '') : 'via ' + (skjoldStatus.value?.name || 'Skjold')}{!frittstaende && <> · <button onClick={() => setOppsett(true)} style={`border:none;background:none;color:${G};cursor:pointer;font-size:12px;padding:0`}>Endre server</button></>}</span>
      {gruppeArk && (
        <div onClick={() => setGruppeArk(false)} style="position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.55);display:flex;align-items:flex-end;justify-content:center">
          <div onClick={(e) => e.stopPropagation()} style={st.kort + ';width:100%;max-width:520px;border-radius:22px 22px 0 0;padding:20px 18px 30px;display:flex;flex-direction:column;gap:6px'}>
            <b style="font-size:17px">Spill i takt med {spiller?.name}</b>
            <span style={st.liten}>Huk av spillerne som skal spille det samme. Lyrion holder dem synkrone.</span>
            {liste.filter((p) => p.playerid !== sp).map((p) => { const med = minGruppe.includes(p.playerid); return (
              <label key={p.playerid} style="display:flex;align-items:center;gap:12px;padding:10px 2px;border-bottom:1px solid #1d1d1f;cursor:pointer">
                <input type="checkbox" checked={med} onChange={() => void cmd(med ? ['sync', '-'] : ['sync', sp], p.playerid).then(() => syncGrupper().then(setGrupper))} style={`width:20px;height:20px;accent-color:${G}`} />
                <span style="flex:1">{p.name}<br /><span style={st.liten}>{p.modelname || p.model}</span></span></label>); })}
            {liste.length < 2 && <span style={st.liten}>Bare én spiller på serveren.</span>}
            <button onClick={() => setGruppeArk(false)} style={st.knapp + ';align-self:flex-end;margin-top:8px'}>Ferdig</button>
          </div>
        </div>)}
      {msg && <div role="status" style="position:fixed;left:50%;bottom:96px;transform:translateX(-50%);z-index:70;background:#1c1c1e;border:1px solid #2a2a2c;padding:10px 16px;border-radius:12px;font-size:13.5px">{msg}</div>}
    </div>);
}

function Topp({ onInnst }: { onInnst?: () => void }) {
  return (
    <div style="display:flex;align-items:center;gap:12px;padding-top:max(env(safe-area-inset-top),6px)">
      <span style="display:flex;gap:3px;align-items:flex-start;height:22px">{[11, 16, 21, 16, 11].map((h, i) => <i key={i} style={`width:3.6px;height:${h}px;border-radius:2px;background:${i === 2 ? '#d9a441' : '#f2f2ee'}`} />)}</span>
      <span style="flex:1;display:flex;flex-direction:column"><b style="font-size:17px">Lyrion</b><span style={`font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.16em;color:${G}`}>SKJOLD · FJERNKONTROLL</span></span>
      {onInnst && <button onClick={onInnst} style={st.knapp + ';height:34px'}>Server</button>}
      <button onClick={() => { mode.value = 'find'; }} style={st.knapp + ';height:34px'}>Finn Skjold</button>
    </div>);
}

// ---------- Squeezebox og andre Lyrion-spillere i Rom-listen, med eget ikon per modell ----------
/** Strektegninger (24×24) per spillertype – egne tegninger, ikke produsentenes logoer. */
const MODELL_IKON: Record<string, string> = {
  classic: 'M2 8.5h20v7H2zM4.5 11h11M4.5 13h7M19 12.2h.01',                                      // Squeezebox Classic / Transporter: lav boks med display
  touch: 'M4 5.5h16v10H4zM6.5 8h11v5h-11zM6 15.5l-1.5 3.5h15L18 15.5',                                     // Squeezebox Touch: skjerm på fot
  radio: 'M5 4.5h14a2 2 0 0 1 2 2V19H3V6.5a2 2 0 0 1 2-2zM6 7.5h8v4.5H6zM17.5 9.8h.01M6 15h12M6 17h12', // Squeezebox Radio
  boom: 'M2 8h20v9H2zM6.5 12.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M17.5 12.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M10.5 10.5h3v2h-3z', // Boom
  receiver: 'M4 10.5h16v5.5H4zM7 13.2h.01M14 13.2h3M8 19h8',                                      // Receiver / Duet
  pi: 'M3 6h18v12H3zM6 9h4.5v4.5H6zM13 9h5M13 11.5h5M13 14h3M3 15h2M8 18v2M12 18v2M16 18v2',      // piCorePlayer / squeezelite på en Pi
  esp: 'M8 3h8v18H8zM12 15.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M12 7h.01M10.5 9.5h3',    // SqueezeESP32 / Røst-høyttaler
  pc: 'M3 5h18v11H3zM8 20h8M12 16v4',                                                             // datamaskin/nettleser
  annen: 'M7 3h10v18H7zM12 14m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0M12 7.2h.01'
};
export function modellType(p: { model?: string; modelname?: string; name?: string }): keyof typeof MODELL_IKON {
  const m = (p.model || '').toLowerCase(), n = (p.modelname || '').toLowerCase();
  if (/squeezebox[23]|transporter|slimp3|softsqueeze/.test(m) || /classic|transporter/.test(n)) return 'classic';
  if (m === 'fab4' || /touch/.test(n)) return 'touch';
  if (m === 'baby' || /radio/.test(n)) return 'radio';
  if (m === 'boom' || /boom/.test(n)) return 'boom';
  if (m === 'receiver' || /receiver|duet/.test(n)) return 'receiver';
  if (/esp32/.test(m + n)) return 'esp';
  if (/picore|pcp/.test(n + (p.name || '').toLowerCase()) || /squeezelite/.test(m + n)) return 'pi';
  if (/squeezeplay|jive|controller|material|web/.test(m + n)) return 'pc';
  return 'annen';
}
export const ModellIkon = ({ p, s = 30 }: { p: { model?: string; modelname?: string; name?: string }; s?: number }) =>
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={MODELL_IKON[modellType(p)]} /></svg>;
const MODELL_NAVN: Record<string, string> = { classic: 'Squeezebox Classic', touch: 'Squeezebox Touch', radio: 'Squeezebox Radio', boom: 'Squeezebox Boom', receiver: 'Squeezebox Receiver', esp: 'SqueezeESP32', pi: 'squeezelite', pc: 'Programspiller', annen: 'Lyrion-spiller' };

interface RomSpiller extends LmsSpiller { st?: LmsStatus | undefined }
/** Rom → «Lyrion-spillere»: Squeezebox-er og andre spillere på samme Lyrion-server som ikke er Skjold-enheter. */
export function LyrionRom({ skjul }: { skjul: string[] }) {
  const [l, setL] = useState<RomSpiller[]>([]);
  const vis = !!lmsDirekte.value || !!skjoldStatus.value?.lyrion;
  const skjulKey = skjul.join(',');
  useEffect(() => {
    if (!vis) return;
    let slutt = false, id = 0;
    const hent = async () => {
      try {
        const { spillere: ps } = await spillere();
        const navn = new Set(skjul.map((x) => x.toLowerCase()));
        const egne = ps.filter((p) => !navn.has(p.playerid.toLowerCase()) && !navn.has(p.name.toLowerCase()) && !/^skjold r[øo]st/i.test(p.name));
        const st = await Promise.all(egne.map((p) => p.connected === 0 ? Promise.resolve(undefined) : lmsStatus(p.playerid).catch(() => undefined)));
        if (!slutt) setL(egne.map((p, i) => ({ ...p, st: st[i] })));
      } catch { if (!slutt) setL([]); }
      if (!slutt) id = window.setTimeout(() => void hent(), document.hidden ? 30000 : 6000);
    };
    void hent(); return () => { slutt = true; clearTimeout(id); };
  }, [vis, skjulKey]);
  if (!vis || !l.length) return null;
  const kjor = async (p: string, c: (string | number)[]) => { try { await lms(p, c); const ny = await lmsStatus(p); setL((x) => x.map((y) => (y.playerid === p ? { ...y, st: ny } : y))); } catch { /* neste runde */ } };
  return (
    <div style="display:flex;flex-direction:column;gap:8px">
      <span style={`font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.14em;color:${D};padding:6px 2px 0`}>LYRION-SPILLERE</span>
      {l.map((p) => {
        const s = p.st, t = s?.playlist_loop?.[0], av = s?.power === 0 || p.power === 0, spiller_ = s?.mode === 'play' && !av, borte = p.connected === 0;
        const linje = borte ? 'Frakoblet' : av ? 'Av' : t?.title ? t.title + (t.artist ? ' · ' + t.artist : '') : s?.current_title || 'Ingenting spiller';
        const vol = Math.abs(s?.['mixer volume'] ?? 0);
        return (
          <div key={p.playerid} style={`display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:12px;align-items:center;padding:12px;border-radius:14px;background:#141415;border:1px solid #242426;opacity:${borte ? 0.55 : 1}`}>
            <button onClick={() => { velgSpiller(p.playerid); go('lms'); }} aria-label={'Åpne ' + p.name} style={`width:44px;height:44px;border-radius:10px;background:#1f1f21;border:none;display:flex;align-items:center;justify-content:center;cursor:pointer;color:${spiller_ ? G : '#c9c9c4'};padding:0`}><ModellIkon p={p} /></button>
            <div style="display:flex;flex-direction:column;gap:6px;min-width:0">
              <button onClick={() => { velgSpiller(p.playerid); go('lms'); }} style="border:none;background:none;padding:0;cursor:pointer;text-align:left;display:flex;justify-content:space-between;gap:8px;align-items:baseline;color:inherit">
                <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:15px">{p.name}</span><span style="font-size:11px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p.modelname || MODELL_NAVN[modellType(p)]} · {linje}</span></span>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#c9c9c4">{s && !borte ? vol : '–'}</span>
              </button>
              {!borte && <input type="range" min="0" max="100" value={vol} aria-label={'Volum ' + p.name} onChange={(e) => void kjor(p.playerid, ['mixer', 'volume', Number(e.currentTarget.value)])} style={`width:100%;accent-color:${G}`} />}
            </div>
            {!borte && <div style="display:flex;gap:2px">
              {!av && <button aria-label={spiller_ ? 'Pause' : 'Spill'} onClick={() => void kjor(p.playerid, s?.mode === 'stop' ? ['play'] : ['pause', spiller_ ? 1 : 0])} style={st.ikonK + ';width:36px;height:36px'}><Ik d={spiller_ ? IK.pause : IK.play} s={18} f /></button>}
              <button aria-label={av ? 'Slå på' : 'Slå av'} onClick={() => void kjor(p.playerid, ['power', av ? 1 : 0])} style={st.ikonK + `;width:36px;height:36px;color:${av ? D : '#6fcf7f'}`}><Ik d={IK.strom} s={17} /></button>
            </div>}
          </div>);
      })}
    </div>);
}
